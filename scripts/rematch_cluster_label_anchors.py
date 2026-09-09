"""
Matcht de vastgelegde clusterlabel-anchors (data/cluster-label-anchors.parquet,
zie scripts/build_cluster_label_anchors.py) terug op een nieuwe clustering-run.

Aanleiding (issue #281): de 199 handmatige labels in
config/cluster_label_overrides.toml zijn puur positioneel gekoppeld aan
(level, cluster_id) uit één specifieke HDBSCAN-run. Zodra de clustering
verandert -- bv. na het regenereren van de productie-export met
build_multilevel_clusters -- verschuiven cluster-id's en raakt die koppeling
los. Dit script vindt per anchor het beste kandidaat-cluster in de nieuwe
run, op basis van twee onafhankelijke signalen:

- **ledensetoverlap** (Jaccard van member_document_ids): het meest robuuste
  signaal, want clusters bestaan uit dezelfde onderliggende punten, ongeacht
  hoe de HDBSCAN-run de ruimte opnieuw heeft opgedeeld.
- **cosine-afstand van mean_vector**: vult aan wanneer een cluster is
  gesplitst of samengevoegd en de ledenset dus geen dominante 1-op-1 match
  meer heeft.

Conform de werkwijze in docs/cluster-labeling-werkwijze.md ("wijzigingen
worden nooit en bloc geautomatiseerd doorgevoerd") past dit script niets
automatisch toe. Het schrijft een kandidaat-TOML plus een leesbaar rapport
met confidence per match, zodat elke wijziging nog één voor één te
beoordelen is voor die wordt overgenomen in cluster_label_overrides.toml.

Gebruik:
    uv run python scripts/rematch_cluster_label_anchors.py \\
        --clusters-json data/export/a0-map/maps/plenair-map-clusters-full.json \\
        --points-json data/export/a0-map/maps/plenair-map-full.json
"""

import json
import sys
from pathlib import Path

import click
import numpy as np
import pyarrow.parquet as pq

from pipeline.paths import REPO_ROOT

ANCHORS_PATH = REPO_ROOT / "data" / "cluster-label-anchors.parquet"
CLUSTERS_FULL_PATH = REPO_ROOT / "data" / "export" / "a0-map" / "maps" / "plenair-map-clusters-full.json"
POINTS_FULL_PATH = REPO_ROOT / "data" / "export" / "a0-map" / "maps" / "plenair-map-full.json"
EMBEDDINGS_PATH = REPO_ROOT / "data" / "embeddings" / "text-embedding-bge-m3_plenair-full.npz"
OUTPUT_TOML_PATH = REPO_ROOT / "config" / "cluster_label_overrides.rematched.toml"

# Onder deze Jaccard-score wordt een ledenset-match niet als betrouwbaar genoeg
# beschouwd om zonder cosine-bevestiging te vertrouwen -- gekozen zodat een
# cluster dat pakweg tweederde overlapt (lichte randverschuiving door een
# nieuwe HDBSCAN-run) nog telt, maar een toevallige kleine overlap niet.
JACCARD_CONFIDENT = 0.6
COSINE_CONFIDENT = 0.9


def toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


@click.command()
@click.option("--anchors-parquet", type=click.Path(exists=True, path_type=Path), default=ANCHORS_PATH)
@click.option("--clusters-json", type=click.Path(exists=True, path_type=Path), default=CLUSTERS_FULL_PATH)
@click.option("--points-json", type=click.Path(exists=True, path_type=Path), default=POINTS_FULL_PATH)
@click.option("--embeddings-npz", type=click.Path(exists=True, path_type=Path), default=EMBEDDINGS_PATH)
@click.option("--output-toml", type=click.Path(path_type=Path), default=OUTPUT_TOML_PATH)
def main(anchors_parquet: Path, clusters_json: Path, points_json: Path, embeddings_npz: Path, output_toml: Path):
    anchors = pq.read_table(anchors_parquet).to_pylist()
    click.echo(f"{len(anchors)} anchors geladen uit {anchors_parquet}")

    with open(clusters_json, "r", encoding="utf-8") as f:
        clusters_data = json.load(f)
    levels = clusters_data["levels"]

    with open(points_json, "r", encoding="utf-8") as f:
        points_data = json.load(f)
    # Zelfde puntformaat als build_cluster_label_anchors.py: index 0 = id,
    # index 11 = cluster_levels (lijst van cluster-id per niveau).
    doc_cluster_levels = {row[0]: row[11] for row in points_data["points"] if len(row) > 11}

    # Ledensets per (level, cluster_id) in de nieuwe run, zodat Jaccard tegen
    # alle kandidaten op dat niveau in één keer te berekenen is.
    members_by_level = [dict() for _ in levels]
    for doc_id, cluster_levels in doc_cluster_levels.items():
        for level, cluster_id in enumerate(cluster_levels):
            if level >= len(levels) or cluster_id is None or cluster_id < 0:
                continue
            members_by_level[level].setdefault(cluster_id, set()).add(doc_id)

    embeddings = np.load(embeddings_npz, allow_pickle=True)
    id_to_vec_idx = {int(doc_id): idx for idx, doc_id in enumerate(embeddings["ids"])}
    emb_vectors = embeddings["vectors"]
    click.echo(f"{len(id_to_vec_idx)} vectoren geladen uit {embeddings_npz} voor cosine-matching")

    # Mean-vector per (level, cluster_id) in de nieuwe run, lazy berekend en
    # gecached: alleen nodig voor de niveaus waarop anchors bestaan, en
    # herbruikt binnen dat niveau over alle anchors heen.
    mean_vector_cache = {}

    def mean_vector_for(level, cluster_id):
        cache_key = (level, cluster_id)
        if cache_key not in mean_vector_cache:
            member_set = members_by_level[level][cluster_id]
            vec_indices = [id_to_vec_idx[doc_id] for doc_id in member_set if doc_id in id_to_vec_idx]
            mean_vector_cache[cache_key] = (
                np.mean(emb_vectors[vec_indices], axis=0) if vec_indices else None
            )
        return mean_vector_cache[cache_key]

    def cosine(a, b):
        if a is None or b is None:
            return None
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        return float(np.dot(a, b) / denom) if denom else None

    matches = []
    for anchor in anchors:
        level = anchor["level"]
        anchor_members = set(anchor["member_document_ids"])
        anchor_vector = np.array(anchor["mean_vector"]) if anchor["mean_vector"] is not None else None
        candidates = members_by_level[level] if level < len(members_by_level) else {}

        best_jaccard_id, best_jaccard = None, 0.0
        for cluster_id, member_set in candidates.items():
            intersection = len(anchor_members & member_set)
            if not intersection:
                continue
            jaccard = intersection / len(anchor_members | member_set)
            if jaccard > best_jaccard:
                best_jaccard_id, best_jaccard = cluster_id, jaccard

        # Cosine over alle kandidaten op het niveau: vangt een gesplitst of
        # samengevoegd cluster op waarvoor de ledenset geen dominante overlap
        # meer heeft, maar de inhoud (bge-m3-gemiddelde) wel herkenbaar bleef.
        best_cosine_id, best_cosine = None, -1.0
        if anchor_vector is not None:
            for cluster_id in candidates:
                score = cosine(anchor_vector, mean_vector_for(level, cluster_id))
                if score is not None and score > best_cosine:
                    best_cosine_id, best_cosine = cluster_id, score

        if best_jaccard >= JACCARD_CONFIDENT:
            match_id, match_score, match_basis = best_jaccard_id, best_jaccard, "jaccard"
        elif best_cosine_id is not None and best_cosine >= COSINE_CONFIDENT:
            match_id, match_score, match_basis = best_cosine_id, best_cosine, "cosine"
        elif best_jaccard_id is not None:
            match_id, match_score, match_basis = best_jaccard_id, best_jaccard, "jaccard"
        else:
            match_id, match_score, match_basis = best_cosine_id, best_cosine if best_cosine_id is not None else None, "cosine"

        matches.append({
            "key": anchor["key"],
            "label": anchor["label"],
            "level": level,
            "old_cluster_id": anchor["cluster_id"],
            "old_size": anchor["size"],
            "new_cluster_id": match_id,
            "new_size": len(candidates.get(match_id, [])) if match_id is not None else None,
            "score": match_score,
            "basis": match_basis,
            "confident": match_basis == "jaccard" and match_score >= JACCARD_CONFIDENT
            or match_basis == "cosine" and match_score is not None and match_score >= COSINE_CONFIDENT,
        })

    n_confident = sum(m["confident"] for m in matches)
    n_unmatched = sum(m["new_cluster_id"] is None for m in matches)
    click.echo(
        f"{n_confident}/{len(matches)} anchors matchen met voldoende confidence "
        f"(Jaccard >= {JACCARD_CONFIDENT} of cosine >= {COSINE_CONFIDENT}), "
        f"{n_unmatched} zonder enige kandidaat (cluster waarschijnlijk verdwenen)"
    )

    output_toml.parent.mkdir(parents=True, exist_ok=True)
    with open(output_toml, "w", encoding="utf-8") as f:
        f.write(
            "# Kandidaat-rematch van cluster_label_overrides.toml na een nieuwe clustering-run.\n"
            "# Gegenereerd door scripts/rematch_cluster_label_anchors.py -- NIET automatisch\n"
            "# overnemen. Elke regel eerst een-voor-een beoordelen (zie\n"
            "# docs/cluster-labeling-werkwijze.md) en pas dan overzetten naar\n"
            "# config/cluster_label_overrides.toml. Regels met confident = false of een\n"
            "# lege new_cluster_id vergen extra aandacht: het cluster is mogelijk gesplitst,\n"
            "# samengevoegd of niet meer als apart cluster teruggekomen.\n\n"
            "[labels]\n"
        )
        for m in matches:
            if m["new_cluster_id"] is None:
                f.write(f'# GEEN MATCH  "{m["key"]}" ({m["label"]}, was size={m["old_size"]}) -- handmatig herzoeken\n')
                continue
            score = f"{m['score']:.2f}" if m["score"] is not None else "?"
            flag = "" if m["confident"] else f"  # LAGE CONFIDENCE, {m['basis']}={score}, controleren"
            new_key = f"L{m['level']}-{m['new_cluster_id']}"
            f.write(f'"{new_key}" = "{toml_escape(m["label"])}"{flag}\n')

    click.echo(f"Kandidaat-TOML geschreven naar {output_toml}")

    if n_unmatched:
        click.echo(
            f"Let op: {n_unmatched} anchors hebben geen enkele overlap gevonden op hun niveau "
            "-- controleer handmatig of het cluster is opgesplitst of verdwenen.",
            err=True,
        )


if __name__ == "__main__":
    main()
