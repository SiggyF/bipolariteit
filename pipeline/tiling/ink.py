"""
Inktdichtheid per zoomniveau van een plenaire-kaart-pmtiles (issue #390).

De frontend tekent elk punt als een schijf met een vaste kleursterkte in een
multiply-blend ("inkt"): hoe meer schijven op één pixel, hoe donkerder. Wat het
oog ziet is dus het aantal overlappende punten per pixel, en dat hangt af van
hoeveel punten een zoomniveau na uitdunning (`thin_zoom_points_globally()`)
nog heeft. In plaats van puntgrootte en kleursterkte met de hand af te stellen
meten we hier per zoomniveau hoe dicht de punten op het scherm staan, zodat de
frontend er een straal en kleursterkte uit kan afleiden.

Meetmethode: elke tegel wordt op `render_tile_px` (512, de weergavegrootte van
`TiledPlenairMap.vue`) gelegd en in cellen van `cell_px` px verdeeld. Per
niet-lege cel tellen we de punten; dat levert punten per px² op. Alleen
niet-lege cellen tellen mee, want de lege marge rond de wolk zegt niets over
de dichtheid waar wel inkt staat.

De tabel wordt in `<naam>-grid.json` onder de sleutel `ink` bewaard (`--grid`),
zodat de frontend hem samen met de rest van de grid-metadata ophaalt. Opnieuw
draaien overschrijft alleen die sleutel. `make tiles-full` doet dit na de build.

Gebruik:
    python -m pipeline.tiling.ink --input plenair-map-full.pmtiles --grid plenair-map-full-grid.json
"""

import argparse
import gzip
import json
import logging
import time
from pathlib import Path

import mapbox_vector_tile
import numpy as np
from pmtiles.reader import MmapSource, all_tiles, deserialize_header
from pmtiles.tile import Compression

logger = logging.getLogger(__name__)

RENDER_TILE_PX = 512
CELL_PX = 16
PERCENTILES = (50, 90, 99)


def cell_counts(xs: np.ndarray, ys: np.ndarray, extent: int, render_tile_px: int = RENDER_TILE_PX, cell_px: int = CELL_PX) -> np.ndarray:
    """Aantal punten per niet-lege cel voor één tegel; xs/ys in MVT-tegelcoördinaten."""
    if len(xs) == 0:
        return np.zeros(0, dtype=np.int64)
    cells_per_side = render_tile_px // cell_px
    col = np.clip((xs / extent * cells_per_side).astype(np.int64), 0, cells_per_side - 1)
    row = np.clip((ys / extent * cells_per_side).astype(np.int64), 0, cells_per_side - 1)
    counts = np.bincount(row * cells_per_side + col, minlength=cells_per_side * cells_per_side)
    return counts[counts > 0]


def summarize_zoom(zoom: int, per_tile_counts: list[np.ndarray], tiles: int, points: int, cell_px: int = CELL_PX) -> dict:
    """Samenvatting per zoomniveau: percentielen van punten per px² over niet-lege cellen."""
    cell_area = float(cell_px * cell_px)
    all_counts = np.concatenate(per_tile_counts) if per_tile_counts else np.zeros(0, dtype=np.int64)
    summary: dict = {"zoom": zoom, "tiles": tiles, "points": points, "cells": int(len(all_counts))}
    if len(all_counts) == 0:
        return {**summary, **{f"per_px2_p{p}": 0.0 for p in PERCENTILES}, "per_px2_max": 0.0}
    for p in PERCENTILES:
        summary[f"per_px2_p{p}"] = float(np.percentile(all_counts, p)) / cell_area
    summary["per_px2_max"] = float(all_counts.max()) / cell_area
    return summary


def measure(pmtiles_path: Path, max_zoom: int | None = None) -> list[dict]:
    """Loop alle tegels door en geef een samenvatting per zoomniveau."""
    with open(pmtiles_path, "rb") as handle:
        get_bytes = MmapSource(handle)
        header = deserialize_header(get_bytes(0, 127))
        compression = header["tile_compression"]
        per_zoom_counts: dict[int, list[np.ndarray]] = {}
        per_zoom_tiles: dict[int, int] = {}
        per_zoom_points: dict[int, int] = {}
        started = time.monotonic()
        for index, ((z, _x, _y), data) in enumerate(all_tiles(get_bytes)):
            if max_zoom is not None and z > max_zoom:
                continue
            raw = gzip.decompress(data) if compression == Compression.GZIP else data
            layer = mapbox_vector_tile.decode(raw).get("points")
            if not layer:
                continue
            coords = np.array([f["geometry"]["coordinates"] for f in layer["features"]], dtype=np.float64)
            per_zoom_tiles[z] = per_zoom_tiles.get(z, 0) + 1
            per_zoom_points[z] = per_zoom_points.get(z, 0) + len(coords)
            if len(coords):
                per_zoom_counts.setdefault(z, []).append(cell_counts(coords[:, 0], coords[:, 1], layer.get("extent", 4096)))
            if index % 500 == 0:
                logger.info("%d tegels gelezen (%.0f s)", index, time.monotonic() - started)
    return [summarize_zoom(z, per_zoom_counts.get(z, []), per_zoom_tiles[z], per_zoom_points[z]) for z in sorted(per_zoom_tiles)]


def ink_block(summaries: list[dict]) -> dict:
    """Compacte vorm voor in grid.json: alleen wat de frontend nodig heeft."""
    keep = ("zoom", "tiles", "points", *(f"per_px2_p{p}" for p in PERCENTILES))
    return {
        "render_tile_px": RENDER_TILE_PX,
        "cell_px": CELL_PX,
        "zooms": [{key: s[key] for key in keep} for s in summaries],
    }


def merge_into_grid(grid_path: Path, summaries: list[dict]) -> None:
    """Zet het `ink`-blok in een bestaand grid.json; de overige sleutels blijven staan."""
    grid = json.loads(Path(grid_path).read_text())
    grid["ink"] = ink_block(summaries)
    Path(grid_path).write_text(json.dumps(grid, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--grid", type=Path, default=None, help="grid.json waar het `ink`-blok in komt")
    parser.add_argument("--output", type=Path, default=None, help="los JSON-bestand met de volledige samenvatting")
    parser.add_argument("--max-zoom", type=int, default=None)
    args = parser.parse_args()
    if args.grid is None and args.output is None:
        parser.error("geef --grid en/of --output op")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    summaries = measure(args.input, args.max_zoom)
    if args.output is not None:
        payload = {"render_tile_px": RENDER_TILE_PX, "cell_px": CELL_PX, "zooms": summaries}
        args.output.write_text(json.dumps(payload, indent=2))
    if args.grid is not None:
        merge_into_grid(args.grid, summaries)
        logger.info("ink-blok geschreven naar %s", args.grid)
    for s in summaries:
        logger.info(
            "z%d: %d tegels, %d punten, p50=%.4f p90=%.4f p99=%.4f per px2",
            s["zoom"], s["tiles"], s["points"], s["per_px2_p50"], s["per_px2_p90"], s["per_px2_p99"],
        )


if __name__ == "__main__":
    main()
