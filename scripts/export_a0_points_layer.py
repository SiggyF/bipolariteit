"""
Exporteert de 135k punten uit `plenair-map-full.json` naar GeoJSON / GeoPackage voor QGIS (issue #215).

Ondersteunt:
- Volledige attribuutkoppeling: point_id, x, y, topic_id, topic_name, actor_id, speaker_name, party, snippet.
- `--grid` voor WGS84/EPSG:3857-georeferencing conform a0-umap.qgz.
- `--flat` voor rauwe UMAP-vlakke coördinaten.

Gebruik:
    uv run python scripts/export_a0_points_layer.py \
        data/export/plenair-map-full.json \
        data/export/a0-map/points_a0_flat.geojson \
        --grid data/export/plenair-map-full-grid.json
"""

import json
import logging
from pathlib import Path

import click

from scripts.export_clusters_geojson import make_rescaler, flat_rescale

logger = logging.getLogger(__name__)


@click.command()
@click.argument("points_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("output_path", type=click.Path(dir_okay=False, path_type=Path))
@click.option("--grid", "grid_path", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None, help="Pad naar plenair-map-full-grid.json voor WGS84/EPSG:3857 herprojectie.")
@click.option("--flat", is_flag=True, default=False, help="Schrijf in rauwe UMAP-coördinaten zonder Mercator-rescaling.")
def main(points_path: Path, output_path: Path, grid_path: Path | None, flat: bool):
    """Exporteer 135k spreekbeurtpunten naar GeoJSON voor QGIS."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not flat and grid_path is None:
        raise click.UsageError("Specificeer --grid of gebruik --flat voor rauwe coördinaten.")

    raw_data = json.loads(points_path.read_text(encoding="utf-8"))
    points = raw_data["points"]
    topics = raw_data["topics"]

    grid_dict = None if flat else json.loads(grid_path.read_text(encoding="utf-8"))
    rescale = flat_rescale if flat else make_rescaler(grid_dict)

    logger.info("Converteren van %d punten naar GeoJSON...", len(points))
    features = []
    for p in points:
        doc_id = p[0]
        x, y = p[1], p[2]
        topic_idx = p[3]
        topic_name = topics[topic_idx] if topic_idx < len(topics) else "plenair"
        actor_id = p[4]
        party_id = p[5] if len(p) > 5 else None
        debate_id = p[6] if len(p) > 6 else None
        published_at = p[8] if len(p) > 8 else None
        snippet = p[9] if len(p) > 9 else ""

        geo_pt = rescale([x, y])
        features.append({
            "type": "Feature",
            "id": doc_id,
            "geometry": {
                "type": "Point",
                "coordinates": [geo_pt[0], geo_pt[1]],
            },
            "properties": {
                "document_id": doc_id,
                "topic": topic_name,
                "is_topic": topic_name != "plenair",
                "actor_id": actor_id,
                "party_id": party_id,
                "debate_id": debate_id,
                "published_at": published_at,
                "snippet": snippet,
                "raw_x": round(float(x), 4),
                "raw_y": round(float(y), 4),
            },
        })

    output_geojson = {
        "type": "FeatureCollection",
        "features": features,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output_geojson, ensure_ascii=False), encoding="utf-8")
    logger.info("Puntenlaag geschreven naar: %s (%d features, %.2f MB)", output_path, len(features), output_path.stat().st_size / (1024 * 1024))


if __name__ == "__main__":
    main()
