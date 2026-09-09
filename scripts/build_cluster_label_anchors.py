"""
Legt voor elk handmatig vastgesteld clusterlabel (config/cluster_label_overrides.toml)
een inhoudelijke "anchor" vast: hull, centroid, TF-IDF-termen en de gemiddelde
bge-m3-vector + ledenset van document-id's van het cluster. Zie issue #281 en
docs/design/plenaire-kaart-clustering-samenvoeging/: de overrides zijn puur
positioneel gekoppeld aan (level, cluster_id) uit één specifieke HDBSCAN-run
(scripts/apply_cluster_label_overrides.py) -- zodra de clustering verandert
(doel van #281/#186) verschuiven cluster-id's en raakt die koppeling los.

Deze anchors zijn de basis om een handmatig label na een hercluster terug te
vinden (bv. via cosine-afstand tussen mean-vectors of overlap van
ledensets) -- dat terugmatchen zelf gebeurt hier NIET, pas zodra er een
nieuwe clustering-run is om tegen te matchen.

Output is Parquet (zstd), niet JSON: de 199x1024 mean_vector-floats wegen als
JSON-tekst 4,1 MiB, als binaire float32-kolom met zstd-compressie ~0,6 MiB
(6,8x kleiner) -- en met bv. duckdb/pandas ook kolomgewijs te doorzoeken
zonder alles te parsen.

Gebruik:
    uv run python scripts/build_cluster_label_anchors.py
"""

import json
import tomllib
from pathlib import Path

import click
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from pipeline.paths import REPO_ROOT

OVERRIDES_PATH = REPO_ROOT / "config" / "cluster_label_overrides.toml"
CLUSTERS_FULL_PATH = REPO_ROOT / "data" / "export" / "a0-map" / "maps" / "plenair-map-clusters-full.json"
POINTS_FULL_PATH = REPO_ROOT / "data" / "export" / "a0-map" / "maps" / "plenair-map-full.json"
EMBEDDINGS_PATH = REPO_ROOT / "data" / "embeddings" / "text-embedding-bge-m3_plenair-full.npz"
OUTPUT_PATH = REPO_ROOT / "data" / "cluster-label-anchors.parquet"

# Parquet i.p.v. JSON (issue #281): JSON schreef de 199x1024 mean_vector-floats
# als volledige-precisie tekst, plus alle veldnamen letterlijk herhaald per
# record -- 4,1 MiB. Parquet met zstd (binaire float32-arrays, kolomgewijs)
# komt op ~0,6 MiB (6,8x kleiner), en is bovendien met bv. duckdb of pandas
# direct kolomgewijs te doorzoeken zonder alles in het geheugen te parsen.
SCHEMA = pa.schema([
    ("key", pa.string()),
    ("level", pa.int32()),
    ("cluster_id", pa.int32()),
    ("label", pa.string()),
    ("size", pa.int32()),
    ("centroid", pa.list_(pa.float32())),
    ("hull", pa.list_(pa.list_(pa.float32()))),
    ("terms", pa.list_(pa.string())),
    ("topic_breakdown", pa.map_(pa.string(), pa.int32())),
    ("member_document_ids", pa.list_(pa.int64())),
    ("mean_vector", pa.list_(pa.float32())),
])


def parse_override_key(key):
    """"L4-506" -> (4, 506)."""
    level_part, cluster_part = key.split("-")
    return int(level_part[1:]), int(cluster_part)


@click.command()
@click.option("--overrides-path", type=click.Path(exists=True, path_type=Path), default=OVERRIDES_PATH)
@click.option("--clusters-json", type=click.Path(exists=True, path_type=Path), default=CLUSTERS_FULL_PATH)
@click.option("--points-json", type=click.Path(exists=True, path_type=Path), default=POINTS_FULL_PATH)
@click.option("--embeddings-npz", type=click.Path(exists=True, path_type=Path), default=EMBEDDINGS_PATH)
@click.option("--output-path", type=click.Path(path_type=Path), default=OUTPUT_PATH)
def main(overrides_path: Path, clusters_json: Path, points_json: Path, embeddings_npz: Path, output_path: Path):
    with open(overrides_path, "rb") as f:
        overrides = tomllib.load(f)
    labels = overrides.get("labels", {})
    click.echo(f"{len(labels)} handmatige labels gevonden in {overrides_path}")

    with open(clusters_json, "r", encoding="utf-8") as f:
        clusters_data = json.load(f)
    levels = clusters_data["levels"]
    cluster_index = {
        (lvl_idx, c["cluster_id"]): c
        for lvl_idx, lvl_clusters in enumerate(levels)
        for c in lvl_clusters
    }

    with open(points_json, "r", encoding="utf-8") as f:
        points_data = json.load(f)
    # Elke rij: [id, x, y, topicIdx, actorIdx, partyIdx, debateIdx, soortIdx,
    # published_at, text, cluster, cluster_levels]. Alleen id (0) en
    # cluster_levels (11) zijn hier nodig.
    doc_cluster_levels = {row[0]: row[11] for row in points_data["points"] if len(row) > 11}
    click.echo(f"{len(doc_cluster_levels)}/{len(points_data['points'])} punten hebben cluster_levels")

    embeddings = np.load(embeddings_npz, allow_pickle=True)
    emb_ids = embeddings["ids"]
    emb_vectors = embeddings["vectors"]
    id_to_vec_idx = {int(doc_id): idx for idx, doc_id in enumerate(emb_ids)}
    click.echo(f"{len(id_to_vec_idx)} vectoren geladen uit {embeddings_npz} (dim={emb_vectors.shape[1]})")

    anchors = []
    total_missing_embeddings = 0
    for key, label in labels.items():
        level, cluster_id = parse_override_key(key)
        cluster = cluster_index.get((level, cluster_id))
        if cluster is None:
            raise KeyError(f"Cluster {key} niet gevonden in {clusters_json}")

        member_ids = [
            doc_id for doc_id, cluster_levels in doc_cluster_levels.items()
            if level < len(cluster_levels) and cluster_levels[level] == cluster_id
        ]

        vec_indices = [id_to_vec_idx[doc_id] for doc_id in member_ids if doc_id in id_to_vec_idx]
        missing = len(member_ids) - len(vec_indices)
        total_missing_embeddings += missing
        if missing:
            click.echo(f"  {key}: {missing}/{len(member_ids)} document-id's ontbreken in de embeddings-cache", err=True)

        # Afronden op 5 decimalen (ruim voldoende precisie voor toekomstige
        # cosine-matching) comprimeert met zstd merkbaar beter dan de volle
        # float64-precisie: minder entropie in de laagste mantissa-bits,
        # zonder dat gemiste embeddings ooit tot exact 0 leiden (zie ook
        # de bestaande afronding elders in dit script, bv. de hull-punten).
        mean_vector = (
            np.mean(emb_vectors[vec_indices], axis=0).round(5).tolist() if vec_indices else None
        )

        anchors.append({
            "key": key,
            "level": level,
            "cluster_id": cluster_id,
            "label": label,
            "size": cluster["size"],
            "centroid": [float(x) for x in cluster["centroid"]],
            "hull": [[float(x), float(y)] for x, y in cluster["hull"]] if cluster["hull"] else None,
            "terms": cluster["terms"],
            "topic_breakdown": list(cluster["topic_breakdown"].items()),
            "member_document_ids": sorted(member_ids),
            "mean_vector": mean_vector,
        })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(anchors, schema=SCHEMA)
    pq.write_table(table, output_path, compression="zstd")
    size_kb = output_path.stat().st_size / 1024
    click.echo(
        f"{len(anchors)} anchors geschreven naar {output_path} ({size_kb:.0f} KiB), "
        f"{total_missing_embeddings} ontbrekende document-embeddings in totaal"
    )


if __name__ == "__main__":
    main()
