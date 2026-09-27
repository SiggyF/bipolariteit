"""
Matcht de vastgelegde clusterlabel-anchors (data/plenair-map/cluster-label-anchors.parquet,
zie scripts/build_cluster_label_anchors.py) terug op een nieuwe clustering-run.

Aanleiding (issue #281): de 199 handmatige labels in
config/cluster_label_overrides.toml zijn puur positioneel gekoppeld aan
(level, cluster_id) uit één specifieke HDBSCAN-run. Zodra de clustering
verandert -- bv. na het regenereren van de productie-export met
build_multilevel_clusters -- verschuiven cluster-id's en raakt die koppeling
los. Dit script vindt per anchor het beste kandidaat-cluster in de nieuwe
run, op basis van drie onafhankelijke signalen:

- **Jaccard van member_document_ids**: robuust bij een vrijwel 1-op-1 match
  (lichte randverschuiving door een nieuwe HDBSCAN-run).
- **overlap-coëfficiënt** (|A∩B| / min(|A|,|B|)): Jaccard is symmetrisch en
  straft een schone split/merge onterecht af -- een cluster dat 50/50
  splitst haalt met Jaccard nooit meer dan 0,5, ook al zit één helft
  volledig in het oude cluster. De overlap-coëfficiënt normaliseert op de
  kleinste van de twee sets en detecteert containment ook bij een split of
  merge.
- **cosine-afstand van mean_vector**: laatste redmiddel wanneer de ledenset
  geen bruikbare overlap meer heeft, maar de inhoud (bge-m3-gemiddelde) nog
  herkenbaar is.

Conform de werkwijze in docs/cluster-labeling-werkwijze.md ("wijzigingen
worden nooit en bloc geautomatiseerd doorgevoerd") past dit script niets
automatisch toe. Het schrijft een kandidaat-TOML plus een leesbaar rapport
met confidence per match, zodat elke wijziging nog één voor één te
beoordelen is voor die wordt overgenomen in cluster_label_overrides.toml.
Twee anchors die op hetzelfde nieuwe cluster uitkomen (bv. na een merge)
worden nooit als los TOML-paar weggeschreven -- dat zou een ongeldig
dubbele key opleveren -- maar als commentaarblok voor handmatige keuze.

Gebruik:
    uv run python scripts/rematch_cluster_label_anchors.py \\
        --clusters-json data/export/a0-map/maps/plenair-map-clusters-full.json \\
        --points-json data/export/a0-map/maps/plenair-map-full.json
"""

import json
from collections import defaultdict
from pathlib import Path

import click
import numpy as np
import pyarrow.parquet as pq

from pipeline.paths import REPO_ROOT

ANCHORS_PATH = REPO_ROOT / "data" / "plenair-map" / "cluster-label-anchors.parquet"
CLUSTERS_FULL_PATH = REPO_ROOT / "data" / "export" / "a0-map" / "maps" / "plenair-map-clusters-full.json"
POINTS_FULL_PATH = REPO_ROOT / "data" / "export" / "a0-map" / "maps" / "plenair-map-full.json"
EMBEDDINGS_PATH = REPO_ROOT / "data" / "embeddings" / "text-embedding-bge-m3_plenair-full.npz"
OUTPUT_TOML_PATH = REPO_ROOT / "config" / "cluster_label_overrides.rematched.toml"

# Onder deze Jaccard-score wordt een ledenset-match niet als betrouwbaar genoeg
# beschouwd om zonder verder bewijs te vertrouwen.
JACCARD_CONFIDENT = 0.6
# Overlap-coëfficiënt (containment) drempel voor het split/merge-pad.
OVERLAP_CONFIDENT = 0.8
# Absolute ondergrens op de intersectiegrootte voor een overlap-match, zodat
# een kandidaat-cluster van bv. 3 documenten die toevallig alle 3 in een
# anchor van 5000 documenten zitten niet als "containment" telt.
MIN_OVERLAP_INTERSECTION = 5
COSINE_CONFIDENT = 0.9


def toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def best_by_key(scored_candidates):
    """(cluster_id, score) met de hoogste score, of (None, 0.0) als leeg."""
    if not scored_candidates:
        return None, 0.0
    return max(scored_candidates, key=lambda pair: pair[1])


@click.command()
@click.option("--anchors-parquet", type=click.Path(exists=True, path_type=Path), default=ANCHORS_PATH)
@click.option("--clusters-json", type=click.Path(exists=True, path_type=Path), default=CLUSTERS_FULL_PATH)
@click.option("--points-json", type=click.Path(exists=True, path_type=Path), default=POINTS_FULL_PATH)
@click.option("--embeddings-npz", type=click.Path(exists=True, path_type=Path), default=EMBEDDINGS_PATH)
@click.option("--output-toml", type=click.Path(path_type=Path), default=OUTPUT_TOML_PATH)
def main(anchors_parquet: Path, clusters_json: Path, points_json: Path, embeddings_npz: Path, output_toml: Path):
    anchors = pq.read_table(anchors_parquet).to_pylist()
    # Parquet int64-kolommen komen als Python int binnen, maar normaliseer
    # expliciet -- verderop worden id's uit drie verschillende bronnen
    # (parquet/JSON/NPZ) tegen elkaar vergeleken en een stilzwijgende
    # int/str-mismatch laat elke match zonder foutmelding leeglopen.
    for anchor in anchors:
        anchor["member_document_ids"] = {int(doc_id) for doc_id in anchor["member_document_ids"]}
    click.echo(f"{len(anchors)} anchors geladen uit {anchors_parquet}")

    with open(clusters_json, "r", encoding="utf-8") as f:
        clusters_data = json.load(f)
    levels = clusters_data["levels"]

    with open(points_json, "r", encoding="utf-8") as f:
        points_data = json.load(f)
    # Zelfde puntformaat als build_cluster_label_anchors.py: index 0 = id,
    # index 11 = cluster_levels (lijst van cluster-id per niveau).
    doc_cluster_levels = {int(row[0]): row[11] for row in points_data["points"] if len(row) > 11}

    # Ledensets per (level, cluster_id) in de nieuwe run.
    members_by_level = [dict() for _ in levels]
    for doc_id, cluster_levels in doc_cluster_levels.items():
        for level, cluster_id in enumerate(cluster_levels):
            if level >= len(levels) or cluster_id is None or cluster_id < 0:
                continue
            members_by_level[level].setdefault(int(cluster_id), set()).add(doc_id)

    embeddings = np.load(embeddings_npz, allow_pickle=True)
    id_to_vec_idx = {int(doc_id): idx for idx, doc_id in enumerate(embeddings["ids"])}
    emb_vectors = embeddings["vectors"]
    click.echo(f"{len(id_to_vec_idx)} vectoren geladen uit {embeddings_npz} voor cosine-matching")

    # Genormaliseerde mean-vector-matrix per niveau, lazy gebouwd (alleen
    # voor niveaus waar Jaccard/overlap geen confident match oplevert) en
    # daarna hergebruikt: één BLAS matrix-vector-product per anchor i.p.v.
    # een Python-loop met np.dot per kandidaat-cluster.
    level_matrix_cache = {}

    def level_cosine_matrix(level):
        if level not in level_matrix_cache:
            cluster_ids, vectors = [], []
            for cluster_id, member_set in members_by_level[level].items():
                vec_indices = [id_to_vec_idx[doc_id] for doc_id in member_set if doc_id in id_to_vec_idx]
                if not vec_indices:
                    continue
                cluster_ids.append(cluster_id)
                vectors.append(np.mean(emb_vectors[vec_indices], axis=0))
            if not vectors:
                level_matrix_cache[level] = (np.empty((0, 0)), [])
            else:
                matrix = np.array(vectors)
                norms = np.linalg.norm(matrix, axis=1, keepdims=True)
                norms[norms == 0] = 1.0
                level_matrix_cache[level] = (matrix / norms, cluster_ids)
        return level_matrix_cache[level]

    def best_cosine_match(level, anchor_vector):
        matrix, cluster_ids = level_cosine_matrix(level)
        if not cluster_ids or anchor_vector is None:
            return None, None
        norm = np.linalg.norm(anchor_vector)
        if not norm:
            return None, None
        scores = matrix @ (anchor_vector / norm)
        best_idx = int(np.argmax(scores))
        return cluster_ids[best_idx], float(scores[best_idx])

    matches = []
    for anchor in anchors:
        level = anchor["level"]
        anchor_members = anchor["member_document_ids"]
        anchor_vector = np.array(anchor["mean_vector"]) if anchor["mean_vector"] is not None else None
        candidates = members_by_level[level] if level < len(members_by_level) else {}

        jaccard_scores, overlap_scores = [], []
        for cluster_id, member_set in candidates.items():
            intersection = len(anchor_members & member_set)
            if not intersection:
                continue
            jaccard_scores.append((cluster_id, intersection / len(anchor_members | member_set)))
            if intersection >= MIN_OVERLAP_INTERSECTION:
                overlap_scores.append((cluster_id, intersection / min(len(anchor_members), len(member_set))))

        best_jaccard_id, best_jaccard = best_by_key(jaccard_scores)
        best_overlap_id, best_overlap = best_by_key(overlap_scores)

        # Jaccard/overlap zijn duur (kwadratisch in aantal kandidaten * anchors)
        # maar per anchor goedkoop t.o.v. cosine; cosine wordt alleen berekend
        # als geen van beide al een confident match opleverde.
        if best_jaccard >= JACCARD_CONFIDENT or best_overlap >= OVERLAP_CONFIDENT:
            best_cosine_id, best_cosine = None, None
        else:
            best_cosine_id, best_cosine = best_cosine_match(level, anchor_vector)

        # Kandidaten met hun score genormaliseerd op de eigen confident-drempel,
        # zodat "net onder cosine-drempel maar sterk" niet wordt weggegooid
        # voor "toevallige jaccard-treffer met 1 document" (het fallthrough-bug
        # van de eerste versie: een vaste elif-volgorde koos altijd jaccard
        # zodra er ook maar íéts overlapte, ongeacht hoe zwak).
        ranked = [
            ("jaccard", best_jaccard_id, best_jaccard, best_jaccard / JACCARD_CONFIDENT if best_jaccard_id is not None else -1),
            ("overlap", best_overlap_id, best_overlap, best_overlap / OVERLAP_CONFIDENT if best_overlap_id is not None else -1),
            ("cosine", best_cosine_id, best_cosine, (best_cosine or 0) / COSINE_CONFIDENT if best_cosine_id is not None else -1),
        ]
        basis, match_id, score, normalized = max(ranked, key=lambda r: r[3])

        confident = normalized >= 1.0
        matches.append({
            "key": anchor["key"],
            "label": anchor["label"],
            "level": level,
            "old_cluster_id": anchor["cluster_id"],
            "old_size": anchor["size"],
            "new_cluster_id": match_id if normalized >= 0 else None,
            "new_size": len(candidates.get(match_id, [])) if match_id is not None else None,
            "score": score if normalized >= 0 else None,
            "basis": basis,
            "confident": confident,
        })

    n_confident = sum(m["confident"] for m in matches)
    n_unmatched = sum(m["new_cluster_id"] is None for m in matches)
    click.echo(
        f"{n_confident}/{len(matches)} anchors matchen met voldoende confidence "
        f"(Jaccard >= {JACCARD_CONFIDENT}, overlap >= {OVERLAP_CONFIDENT} of cosine >= {COSINE_CONFIDENT}), "
        f"{n_unmatched} zonder enige kandidaat (cluster waarschijnlijk verdwenen)"
    )

    # Groepeer op gekozen nieuwe key: bij een merge kunnen twee anchors
    # dezelfde (level, cluster_id) kiezen. Beide als los TOML-paar
    # wegschrijven geeft een dubbele key, die tomllib/tomli als ongeldig
    # weigert -- dus zulke groepen gaan als commentaarblok naar de output.
    by_new_key = defaultdict(list)
    for m in matches:
        if m["new_cluster_id"] is not None:
            by_new_key[(m["level"], m["new_cluster_id"])].append(m)

    output_toml.parent.mkdir(parents=True, exist_ok=True)
    with open(output_toml, "w", encoding="utf-8") as f:
        f.write(
            "# Kandidaat-rematch van cluster_label_overrides.toml na een nieuwe clustering-run.\n"
            "# Gegenereerd door scripts/rematch_cluster_label_anchors.py -- NIET automatisch\n"
            "# overnemen. Elke regel eerst een-voor-een beoordelen (zie\n"
            "# docs/cluster-labeling-werkwijze.md) en pas dan overzetten naar\n"
            "# config/cluster_label_overrides.toml. Regels met confident = false of een\n"
            "# lege new_cluster_id vergen extra aandacht: het cluster is mogelijk gesplitst,\n"
            "# samengevoegd of niet meer als apart cluster teruggekomen. Een CONFLICT-blok\n"
            "# betekent dat meerdere oude labels op hetzelfde nieuwe cluster uitkwamen\n"
            "# (waarschijnlijk een merge) -- kies handmatig welk label blijft staan.\n\n"
            "[labels]\n"
        )
        for m in matches:
            if m["new_cluster_id"] is None:
                f.write(f'# GEEN MATCH  "{m["key"]}" ({m["label"]}, was size={m["old_size"]}) -- handmatig herzoeken\n')
                continue
            new_key_tuple = (m["level"], m["new_cluster_id"])
            if len(by_new_key[new_key_tuple]) > 1:
                continue  # apart als CONFLICT-blok geschreven, zie hieronder
            score = f"{m['score']:.2f}" if m["score"] is not None else "?"
            flag = "" if m["confident"] else f"  # LAGE CONFIDENCE, {m['basis']}={score}, controleren"
            new_key = f"L{m['level']}-{m['new_cluster_id']}"
            f.write(f'"{new_key}" = "{toml_escape(m["label"])}"{flag}\n')

        conflicts = {k: v for k, v in by_new_key.items() if len(v) > 1}
        if conflicts:
            f.write("\n# --- CONFLICTEN: meerdere oude labels naar hetzelfde nieuwe cluster ---\n")
            for (level, cluster_id), group in conflicts.items():
                new_key = f"L{level}-{cluster_id}"
                f.write(f'# CONFLICT "{new_key}": kies er één --\n')
                for m in group:
                    score = f"{m['score']:.2f}" if m["score"] is not None else "?"
                    f.write(f'#   "{new_key}" = "{toml_escape(m["label"])}"  # was {m["key"]}, {m["basis"]}={score}\n')

    click.echo(f"Kandidaat-TOML geschreven naar {output_toml}")
    if conflicts_count := sum(len(v) for v in by_new_key.values() if len(v) > 1):
        click.echo(f"Let op: {conflicts_count} anchors zitten in een CONFLICT-groep (zelfde nieuwe cluster) -- zie onderaan de TOML.", err=True)
    if n_unmatched:
        click.echo(
            f"Let op: {n_unmatched} anchors hebben geen enkele overlap gevonden op hun niveau "
            "-- controleer handmatig of het cluster is opgesplitst of verdwenen.",
            err=True,
        )


if __name__ == "__main__":
    main()
