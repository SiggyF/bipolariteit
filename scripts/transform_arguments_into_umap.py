"""
Vervolg op scripts/experiments/experiment_argument_vs_document_clustering.py (issue #253):
plaats argument-embeddings met de al-gefitte UMAP-reducer
(pipeline/plenary_map/umap.py --export-reducer) in dezelfde 2D-ruimte als de
gepubliceerde plenaire-kaart-coördinaten, i.p.v. een eigen, losse UMAP-fit.

Waarom: een eigen fit (zoals het eerdere experiment deed) staat in een
willekeurige, niet-vergelijkbare ruimte -- reducer.transform() plaatst nieuwe
punten wél in de bestaande, gepubliceerde ruimte, dus rechtstreeks
vergelijkbaar met data/export/plenair-map/plenair-map.json en
plenair-map-clusters.json.

Host-only: de reducer is groot (ongecomprimeerd ~9,6 GiB voor de volle
dataset) en dit script laadt 'm volledig in het geheugen. Draai dit waar
`make umap` ook gedraaid is, niet in de devcontainer. Schrijft alleen een
klein resultaatbestand weg (coördinaten + aggregaatstatistieken, geen
kopie van de reducer of de trainingsvectoren), zodat het resultaat probleemloos
overal verder geanalyseerd kan worden.

Gebruik:
    uv run python scripts/transform_arguments_into_umap.py \
        --topic-slug abortus \
        --reducer-path data/plenair-map/umap-reducer-full.joblib \
        --plenair-map-export data/export/plenair-map/plenair-map-full.json \
        --clusters-export data/export/plenair-map/plenair-map-clusters-full.json
"""
import argparse
import json
import logging
from pathlib import Path

import joblib
import numpy as np
from shapely.geometry import Point, Polygon

from pipeline.paths import REPO_ROOT
from scripts.experiments.experiment_argument_vs_document_clustering import cache_path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def load_argument_cache(topic_slug):
    path = cache_path(topic_slug)
    if not path.exists():
        raise SystemExit(
            f"{path} niet gevonden -- draai eerst "
            f"scripts/experiments/experiment_argument_vs_document_clustering.py --topic-slug {topic_slug} "
            "om de argument-embeddings te cachen"
        )
    data = np.load(path, allow_pickle=True)
    return data["ids"], data["document_ids"], data["vectors"], list(data["texts"]), list(data["meta"])


def load_document_points(export_path, topic_slug):
    with open(export_path) as f:
        export = json.load(f)
    topic_idx = export["topics"].index(topic_slug)
    return {
        point[0]: {"xy": (point[1], point[2]), "cluster": point[10]}
        for point in export["points"]
        if point[3] == topic_idx
    }


def load_cluster_lookup(clusters_export_path):
    with open(clusters_export_path) as f:
        clusters = json.load(f)
    lookup = {}
    for c in clusters["fine"]:
        hull = c.get("hull")
        polygon = Polygon(hull) if hull and len(hull) >= 3 else None
        lookup[c["cluster_id"]] = {**c, "polygon": polygon}
    return lookup


def nearest_cluster(xy, cluster_lookup):
    """Dichtstbijzijnde cluster op hull-**rand**afstand (shapely
    Polygon.distance/.contains), niet op centroïde-afstand -- bij
    onregelmatige/grote hulls wijst centroïde-afstand soms een heel ander
    cluster aan dan waar het punt zich feitelijk bevindt (live gezien: punt
    lag tegen de rand van cluster "D66" aan, maar centroïde-afstand wees
    "Transparantie" aan, 12x verder weg qua randafstand)."""
    pt = Point(xy)
    best_id, best_dist, best_contains = None, float("inf"), False
    for cluster_id, cluster in cluster_lookup.items():
        polygon = cluster["polygon"]
        if polygon is not None:
            dist = polygon.distance(pt)
            contains = polygon.contains(pt)
        else:
            cx, cy = cluster["centroid"]
            dist = pt.distance(Point(cx, cy))
            contains = False
        if dist < best_dist:
            best_id, best_dist, best_contains = cluster_id, dist, contains
    return best_id, best_dist, best_contains


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic-slug", default="abortus")
    parser.add_argument("--reducer-path", required=True, type=Path)
    parser.add_argument("--plenair-map-export", required=True, type=Path, help="plenair-map(-full).json, voor document-punten")
    parser.add_argument("--clusters-export", required=True, type=Path, help="plenair-map-clusters(-full).json, voor cluster-hulls")
    parser.add_argument("--out-path", default=None, type=Path, help="pad voor het resultaatbestand (geojson)")
    args = parser.parse_args()

    ids, document_ids, vectors, texts, meta = load_argument_cache(args.topic_slug)
    logger.info("%d argument-embeddings geladen voor topic '%s'", len(ids), args.topic_slug)

    logger.info("reducer laden vanuit %s (dit is de grote stap, kan even duren) ...", args.reducer_path)
    reducer = joblib.load(args.reducer_path)
    logger.info("reducer geladen, transformeren ...")
    coords = reducer.transform(vectors)
    logger.info("%d argumenten getransformeerd naar de bestaande UMAP-ruimte", len(coords))

    document_points = load_document_points(args.plenair_map_export, args.topic_slug)
    cluster_lookup = load_cluster_lookup(args.clusters_export)

    features = []
    own_doc_distances = []
    same_cluster_flags = []
    for arg_id, doc_id, (x, y), text, meta_str in zip(ids, document_ids, coords, texts, meta):
        doc_point = document_points.get(int(doc_id))
        nearest_id, nearest_dist, in_hull = nearest_cluster((x, y), cluster_lookup)

        own_dist = None
        same_cluster = None
        if doc_point is not None:
            dx, dy = doc_point["xy"]
            own_dist = float(((x - dx) ** 2 + (y - dy) ** 2) ** 0.5)
            own_doc_distances.append(own_dist)
            same_cluster = bool(nearest_id == doc_point["cluster"])
            same_cluster_flags.append(same_cluster)

        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [float(x), float(y)]},
                "properties": {
                    "argument_id": int(arg_id),
                    "document_id": int(doc_id),
                    "nearest_cluster_id": int(nearest_id) if nearest_id is not None else None,
                    "nearest_cluster_name": cluster_lookup[nearest_id]["name"] if nearest_id is not None else None,
                    "nearest_cluster_distance": round(float(nearest_dist), 4),
                    "in_nearest_cluster_hull": bool(in_hull),
                    "document_cluster_id": int(doc_point["cluster"]) if doc_point else None,
                    "distance_to_own_document": round(own_dist, 4) if own_dist is not None else None,
                    "lands_in_own_document_cluster": same_cluster,
                    "meta": meta_str,
                    "quote_snippet": text[:200],
                },
            }
        )

    if own_doc_distances:
        logger.info(
            "afstand tot eigen brondocument -- mediaan=%.3f, p90=%.3f (n=%d)",
            float(np.median(own_doc_distances)), float(np.percentile(own_doc_distances, 90)), len(own_doc_distances),
        )
    if same_cluster_flags:
        rate = float(np.mean(same_cluster_flags))
        logger.info(
            "aandeel argumenten dat na transform in hetzelfde fine-cluster valt als het eigen brondocument: %.1f%% (n=%d)",
            rate * 100, len(same_cluster_flags),
        )
    in_hull_rate = float(np.mean([f["properties"]["in_nearest_cluster_hull"] for f in features]))
    logger.info("aandeel argumenten binnen een cluster-hull (niet alleen dichtstbij): %.1f%%", in_hull_rate * 100)

    out_path = args.out_path or REPO_ROOT / "docs" / "research" / f"argument-transform-{args.topic_slug}.geojson"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f)
    logger.info("resultaat geschreven naar %s", out_path)


if __name__ == "__main__":
    main()
