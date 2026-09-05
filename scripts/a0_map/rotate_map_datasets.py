"""
Roteer plenaire kaart datasets zodat moties en voorzitter onderop komen te liggen,
en sla de resultaten op met het `_rotated` postfix.

Datasets die gegenereerd/geroteerd worden:
- data/export/a0-map/maps/plenair-map-full_rotated.json
- data/export/a0-map/maps/plenair-map-full-grid_rotated.json
- data/export/a0-map/maps/plenair-map-clusters-full_rotated.json
- data/export/a0-map/maps/plenair-map-clusters-full_rotated.geojson
- data/export/a0-map/maps/plenair-map-clusters-full-flat_rotated.geojson

Gebruik:
    uv run python scripts/a0_map/rotate_map_datasets.py --angle 129.0
"""

import json
import logging
import subprocess
import sys
from pathlib import Path

import click
import numpy as np
from pipeline.tiling.grid import build_grid, write_grid_metadata

logger = logging.getLogger(__name__)


def rotate_coords(x: float, y: float, cx: float, cy: float, cos_a: float, sin_a: float) -> tuple[float, float]:
    rx = cos_a * (x - cx) - sin_a * (y - cy) + cx
    ry = sin_a * (x - cx) + cos_a * (y - cy) + cy
    return rx, ry


@click.command()
@click.option("--angle", type=float, default=129.0, help="Rotatiehoek in graden tegen de klok in (standaard 129°).")
@click.option(
    "--points-in",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=Path("data/export/a0-map/maps/plenair-map-full.json"),
    help="Bronbestand met ruwe UMAP punten.",
)
@click.option(
    "--clusters-in",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=Path("data/export/a0-map/maps/plenair-map-clusters-full.json"),
    help="Bronbestand met clusterhiërarchie.",
)
def main(angle: float, points_in: Path, clusters_in: Path):
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger.info("Start rotatie met hoek: %.1f graden", angle)

    # 1. Laad punten en bepaal rotatiecentrum
    with open(points_in, "r", encoding="utf-8") as f:
        points_data = json.load(f)

    raw_points = points_data["points"]
    xs = np.array([p[1] for p in raw_points], dtype=np.float64)
    ys = np.array([p[2] for p in raw_points], dtype=np.float64)
    cx, cy = float(xs.mean()), float(ys.mean())
    logger.info("Rotatiecentrum (gemiddelde UMAP coördinaat): (%.4f, %.4f)", cx, cy)

    rad = np.radians(angle)
    cos_a, sin_a = float(np.cos(rad)), float(np.sin(rad))

    # 2. Roteer punten
    logger.info("Roteren van %d punten...", len(raw_points))
    rotated_points = []
    for p in raw_points:
        p_copy = list(p)
        rx, ry = rotate_coords(p[1], p[2], cx, cy, cos_a, sin_a)
        p_copy[1] = round(rx, 4)
        p_copy[2] = round(ry, 4)
        rotated_points.append(p_copy)

    points_out_path = points_in.parent / f"{points_in.stem}_rotated.json"
    rotated_points_data = dict(points_data)
    rotated_points_data["points"] = rotated_points
    logger.info("Opslaan geroteerde punten naar: %s", points_out_path)
    points_out_path.write_text(json.dumps(rotated_points_data, ensure_ascii=False), encoding="utf-8")

    # 3. Bereken en bewaar nieuw morecantile grid
    logger.info("Berekenen van grid metadata...")
    tms = build_grid(rotated_points)
    grid_out_path = points_in.parent / f"{points_in.stem}-grid_rotated.json"
    write_grid_metadata(tms, grid_out_path)
    logger.info("Opslaan geroteerd grid naar: %s", grid_out_path)

    # 4. Roteer clusters (centroids & hulls)
    with open(clusters_in, "r", encoding="utf-8") as f:
        clusters_data = json.load(f)

    logger.info("Roteren van clusterhiërarchie...")
    rotated_clusters_data = dict(clusters_data)
    rotated_levels = []
    for level in clusters_data["levels"]:
        new_level = []
        for c in level:
            c_copy = dict(c)
            # Roteer centroid
            if c.get("centroid"):
                c_rx, c_ry = rotate_coords(c["centroid"][0], c["centroid"][1], cx, cy, cos_a, sin_a)
                c_copy["centroid"] = [round(c_rx, 4), round(c_ry, 4)]
            # Roteer hull
            if c.get("hull"):
                new_hull = []
                for hp in c["hull"]:
                    h_rx, h_ry = rotate_coords(hp[0], hp[1], cx, cy, cos_a, sin_a)
                    new_hull.append([round(h_rx, 4), round(h_ry, 4)])
                c_copy["hull"] = new_hull
            new_level.append(c_copy)
        rotated_levels.append(new_level)

    rotated_clusters_data["levels"] = rotated_levels
    clusters_out_path = clusters_in.parent / f"{clusters_in.stem}_rotated.json"
    logger.info("Opslaan geroteerde clusters naar: %s", clusters_out_path)
    clusters_out_path.write_text(json.dumps(rotated_clusters_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 5. Exporteer GeoJSON bestanden (flat en WGS84)
    flat_geojson_out = clusters_in.parent / f"{clusters_in.stem}-flat_rotated.geojson"
    wgs84_geojson_out = clusters_in.parent / f"{clusters_in.stem}_rotated.geojson"

    logger.info("Exporteren van geroteerde GeoJSON bestanden...")
    # Flat
    cmd_flat = [
        sys.executable,
        "scripts/a0_map/export_clusters_geojson.py",
        str(clusters_out_path),
        str(flat_geojson_out),
        "--flat",
    ]
    res_flat = subprocess.run(cmd_flat, capture_output=True, text=True)
    if res_flat.returncode != 0:
        logger.error(res_flat.stderr)
        res_flat.check_returncode()

    # WGS84
    cmd_wgs84 = [
        sys.executable,
        "scripts/a0_map/export_clusters_geojson.py",
        str(clusters_out_path),
        str(wgs84_geojson_out),
        "--grid",
        str(grid_out_path),
    ]
    res_wgs84 = subprocess.run(cmd_wgs84, capture_output=True, text=True)
    if res_wgs84.returncode != 0:
        logger.error(res_wgs84.stderr)
        res_wgs84.check_returncode()

    logger.info("Klaar! Alle geroteerde datasets succesvol gegenereerd.")


if __name__ == "__main__":
    main()
