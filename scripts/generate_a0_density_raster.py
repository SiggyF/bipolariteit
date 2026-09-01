"""
Hoge-resolutie continue dichtheidsraster-generator voor de A0-printposter (issue #215).

Berekent een 2D Gaussian Kernel Density Estimation (KDE) over alle punten in
`plenair-map-full.json` op A0/300dpi-formaat (~9933x14043 px) via snelle 2D
Gaussian-convolutie (scipy.ndimage.gaussian_filter). Voorkomt histogram-banding
door een vloeiende asinh/power-dynamisch-bereik-transformatie toe te passen.

Ondersteunt georeferencing via World File (.tfw) + .prj (EPSG:3857) voor directe
uitlijning met a0-umap.qgz in QGIS, of --flat voor rauwe UMAP-eenheden.

Gebruik:
    uv run python scripts/generate_a0_density_raster.py \
        data/export/plenair-map-full.json \
        data/export/a0-map/density_a0_300dpi.tif \
        --grid data/export/plenair-map-full-grid.json \
        --scale 1.0 \
        --sigma-mm 3.0
"""

import json
import logging
from pathlib import Path

import click
import numpy as np
from scipy.ndimage import gaussian_filter
import tifffile

logger = logging.getLogger(__name__)

# A0 afmetingen bij 300 DPI
A0_WIDTH_MM = 841.0
A0_HEIGHT_MM = 1189.0
DPI = 300.0
MM_PER_INCH = 25.4
A0_WIDTH_PX = round(A0_WIDTH_MM / MM_PER_INCH * DPI)
A0_HEIGHT_PX = round(A0_HEIGHT_MM / MM_PER_INCH * DPI)

WEB_MERCATOR_HALF_EXTENT = 20037508.342789244
EPSG_3857_WKT = (
    'PROJCS["WGS 84 / Pseudo-Mercator",'
    'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],'
    'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]],'
    'PROJECTION["Mercator_1SP"],PARAMETER["central_meridian",0],'
    'PARAMETER["scale_factor",1],PARAMETER["false_easting",0],'
    'PARAMETER["false_northing",0],UNIT["metre",1]]'
)


def load_points_and_grid(points_path: Path, grid_path: Path | None, flat: bool):
    raw_points = json.loads(points_path.read_text(encoding="utf-8"))
    points = raw_points["points"]
    xs = np.array([p[1] for p in points], dtype=np.float64)
    ys = np.array([p[2] for p in points], dtype=np.float64)
    topic_idx = np.array([p[3] for p in points], dtype=np.int32)
    topics = raw_points["topics"]

    if flat or grid_path is None:
        return xs, ys, topic_idx, topics, (xs.min(), ys.min(), xs.max(), ys.max())

    grid_data = json.loads(grid_path.read_text(encoding="utf-8"))
    left, bottom, right, top = grid_data["extent"]
    span_x = right - left
    span_y = top - bottom

    merc_x = -WEB_MERCATOR_HALF_EXTENT + ((xs - left) / span_x) * 2.0 * WEB_MERCATOR_HALF_EXTENT
    merc_y = -WEB_MERCATOR_HALF_EXTENT + ((ys - bottom) / span_y) * 2.0 * WEB_MERCATOR_HALF_EXTENT
    bounds = (
        -WEB_MERCATOR_HALF_EXTENT,
        -WEB_MERCATOR_HALF_EXTENT,
        WEB_MERCATOR_HALF_EXTENT,
        WEB_MERCATOR_HALF_EXTENT,
    )
    return merc_x, merc_y, topic_idx, topics, bounds


def write_world_files(output_tif: Path, bounds: tuple[float, float, float, float], width_px: int, height_px: int, flat: bool):
    min_x, min_y, max_x, max_y = bounds
    dx = (max_x - min_x) / width_px
    dy = -(max_y - min_y) / height_px
    top_left_x = min_x + 0.5 * dx
    top_left_y = max_y + 0.5 * dy

    tfw_content = f"{dx:.8f}\n0.0\n0.0\n{dy:.8f}\n{top_left_x:.8f}\n{top_left_y:.8f}\n"
    tfw_path = output_tif.with_suffix(".tfw")
    tfw_path.write_text(tfw_content, encoding="utf-8")

    if not flat:
        prj_path = output_tif.with_suffix(".prj")
        prj_path.write_text(EPSG_3857_WKT, encoding="utf-8")


@click.command()
@click.argument("points_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("output_path", type=click.Path(dir_okay=False, path_type=Path))
@click.option("--grid", "grid_path", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None, help="Pad naar plenair-map-full-grid.json voor EPSG:3857 georeferencing.")
@click.option("--flat", is_flag=True, default=False, help="Schrijf in rauwe UMAP-coördinaten zonder Mercator-projectie.")
@click.option("--scale", type=float, default=1.0, help="Schaalfactor van A0-resolutie (default: 1.0 = 300dpi, 0.2 = ~60dpi preview).")
@click.option("--sigma-mm", type=float, default=3.0, help="Gaussian filter sigma in millimeters op de A0-kaart (default: 3.0 mm).")
@click.option("--gamma", type=float, default=0.45, help="Exponentiële contrast-scaling om zwakke dichtheden zichtbaar te maken (default: 0.45).")
def main(points_path: Path, output_path: Path, grid_path: Path | None, flat: bool, scale: float, sigma_mm: float, gamma: float):
    """Genereer een continue 2D dichtheids-GeoTIFF voor de A0-plenaire kaart."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not flat and grid_path is None:
        raise click.UsageError("Specificeer --grid of gebruik --flat voor rauwe coördinaten.")

    xs, ys, _, _, bounds = load_points_and_grid(points_path, grid_path, flat)
    min_x, min_y, max_x, max_y = bounds

    width_px = max(100, round(A0_WIDTH_PX * scale))
    height_px = max(100, round(A0_HEIGHT_PX * scale))
    logger.info("Canvas grid: %dx%d px (scale=%.2f, points=%d)", width_px, height_px, scale, len(xs))

    # 2D histogram binning (y loopt van max naar min voor raster-afbeeldingen)
    hist, _, _ = np.histogram2d(
        xs, ys,
        bins=[width_px, height_px],
        range=[[min_x, max_x], [min_y, max_y]],
    )
    # Transpose en flip om de standaard (rij=y-omlaag, kolom=x-rechts) matrix te krijgen
    raster_counts = np.flipud(hist.T).astype(np.float32)

    # Bereken sigma in pixels op basis van schaal en DPI
    px_per_mm = (DPI * scale) / MM_PER_INCH
    sigma_px = max(0.5, sigma_mm * px_per_mm)
    logger.info("Gaussian smoothing: sigma=%.1f mm (%.2f px)", sigma_mm, sigma_px)

    smoothed = gaussian_filter(raster_counts, sigma=sigma_px)

    # Normalisatie en dynamisch bereik transformatie (gamma + asinh)
    max_val = smoothed.max()
    if max_val > 0:
        normalized = smoothed / max_val
        transformed = np.power(normalized, gamma).astype(np.float32)
    else:
        transformed = smoothed

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tifffile.imwrite(
        output_path,
        transformed,
        photometric="minisblack",
        compression="deflate",
    )
    write_world_files(output_path, bounds, width_px, height_px, flat)
    logger.info("Dichtheidsraster geschreven naar: %s (%.2f MB)", output_path, output_path.stat().st_size / (1024 * 1024))


if __name__ == "__main__":
    main()
