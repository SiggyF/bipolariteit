"""
Bouwt de vector-tile-pyramide voor de plenaire kaart: leest de bestaande
`data/export/plenair-map.json` (dezelfde brondata als `PlenairMap.vue`,
gegenereerd door `pipeline/plenary_map/cluster.py --export-frontend`) en
schrijft `data/export/plenair-map.pmtiles` -- een MVT-tile-pyramide over een
custom morecantile-grid (`pipeline.tiling.grid`), met tile-encodering
(`pipeline.tiling.encode`) verdeeld over dask-taken per `(z, x, y)`-tile.

Dit is een alternatief renderpad naast de bestaande platte-JSON-aanpak (zie
issue #215/#253), geen vervanging: `plenair-map.json` blijft bestaan en
`PlenairMap.vue` blijft die rechtstreeks gebruiken. `TiledPlenairMap.vue`
(frontend/src/components/) leest in plaats daarvan dit .pmtiles-bestand plus
het losse grid-metadata-bestand (`plenair-map-grid.json`) om exact dezelfde
wereld<->tile-transform te reconstrueren.

Reikwijdte bewust beperkt: geen nieuwe crawl/UMAP-berekening, puur een
downstream tiling-stap op de al bestaande export. Nog niet opgenomen in
`make export` -- experimenteel, apart te draaien via `make tiles`.

Gebruik:
    uv run python -m pipeline.tiling.build_pyramid [--maxzoom N] [--out PATH]
"""

import argparse
import json
import logging
import time
from pathlib import Path

import dask
from morecantile.commons import Tile
from pmtiles.tile import Compression, TileType, tileid_to_zxy, zxy_to_tileid
from pmtiles.writer import write

from pipeline.dask_client import make_client
from pipeline.paths import REPO_ROOT
from pipeline.tiling.encode import encode_tile, field_types
from pipeline.tiling.grid import (
    DEFAULT_MAXZOOM,
    build_grid,
    lonlat_bounds,
    tile_bounds,
    tile_for_point,
    umap_to_mercator,
    umap_to_mercator_affine,
    write_grid_metadata,
)

logger = logging.getLogger(__name__)

DEFAULT_INPUT = REPO_ROOT / "data" / "export" / "plenair-map.json"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "export" / "plenair-map.pmtiles"
DEFAULT_GRID_OUTPUT = REPO_ROOT / "data" / "export" / "plenair-map-grid.json"

LOOKUP_KEYS = ["topics", "actors", "parties", "debates", "soorten"]


def assign_tiles_for_zoom(points: list, tms, zoom: int) -> dict[int, list]:
    """Groepeer alle punten per tile-id op één zoomniveau."""
    grouped: dict[int, list] = {}
    for point in points:
        tile = tile_for_point(tms, point[1], point[2], zoom)
        tile_id = zxy_to_tileid(tile.z, tile.x, tile.y)
        grouped.setdefault(tile_id, []).append(point)
    return grouped


def encode_one_tile(tile_id: int, points: list, lookups: dict, tms) -> tuple[int, bytes]:
    z, x, y = tileid_to_zxy(tile_id)
    bounds = tile_bounds(tms, Tile(x=x, y=y, z=z))
    data = encode_tile(points, lookups, bounds)
    return tile_id, data


def build(
    input_path,
    output_path,
    grid_output_path,
    maxzoom: int,
    dashboard: bool = True,
    dashboard_hold_seconds: int = 0,
) -> None:
    client = make_client(dashboard)

    try:
        logger.info("Lees brondata uit %s", input_path)
        raw = json.loads(input_path.read_text())
        points = raw["points"]
        lookups = {key: raw[key] for key in LOOKUP_KEYS}
        logger.info("%d punten geladen", len(points))

        # UMAP-coördinaten (x, y op index 1, 2) één keer uniform naar
        # Mercator-meters herschalen zodat de tile-pyramide de volle
        # standaard Web-Mercator-extent vult -- zie grid.py's moduledocstring
        # voor waarom een custom, kleinere extent hier fout gaat in generieke
        # viewers (QGIS/pmtiles.io/MapLibre).
        affine = umap_to_mercator_affine(points)
        lon_min, lat_min, lon_max, lat_max = lonlat_bounds(points, affine)
        points = [[p[0], *umap_to_mercator(p[1], p[2], affine), *p[3:]] for p in points]

        tms = build_grid()
        write_grid_metadata(affine, maxzoom, grid_output_path)
        logger.info("Grid geschreven naar %s (zoom 0-%d)", grid_output_path, maxzoom)

        # `points`/`tms`/`lookups` één keer als delayed-waarde wrappen i.p.v.
        # ze per taak by-value in de graaf te laten meekopiëren -- anders
        # krijgt elk van de ~2500 tile-taken zijn eigen kopie van alle ~40k
        # punten (zichtbaar als een "sending large graph"-waarschuwing bij een
        # remote scheduler), wat niet opweegt tegen wat er per taak echt
        # gebeurt en met meer punten (bredere crawl) alleen maar erger wordt.
        points_d = dask.delayed(points)
        tms_d = dask.delayed(tms)
        lookups_d = dask.delayed(lookups)

        logger.info("Verdeel punten over tiles per zoomniveau (dask-taak per zoomniveau)")
        per_zoom_assignments = dask.compute(
            *[dask.delayed(assign_tiles_for_zoom)(points_d, tms_d, zoom) for zoom in range(0, maxzoom + 1)]
        )

        encode_tasks = []
        for grouped in per_zoom_assignments:
            for tile_id, tile_points in grouped.items():
                encode_tasks.append(dask.delayed(encode_one_tile)(tile_id, tile_points, lookups_d, tms_d))
        logger.info("%d tiles te encoderen (dask-taak per tile)", len(encode_tasks))

        encoded_tiles = dask.compute(*encode_tasks)
        encoded_tiles = sorted(encoded_tiles, key=lambda entry: entry[0])

        # 12e element (cluster-ids per niveau) is optioneel, zie encode.py's
        # module-docstring -- alleen aanwezig bij N-laagse clustering.
        cluster_level_count = len(points[0][11]) if points and len(points[0]) > 11 else 0

        logger.info("Schrijf %s", output_path)
        with write(str(output_path)) as writer:
            for tile_id, data in encoded_tiles:
                writer.write_tile(tile_id, data)
            header = {
                "tile_type": TileType.MVT,
                "tile_compression": Compression.NONE,
                "min_lon_e7": round(lon_min * 10_000_000),
                "min_lat_e7": round(lat_min * 10_000_000),
                "max_lon_e7": round(lon_max * 10_000_000),
                "max_lat_e7": round(lat_max * 10_000_000),
                "center_lon_e7": round((lon_min + lon_max) / 2 * 10_000_000),
                "center_lat_e7": round((lat_min + lat_max) / 2 * 10_000_000),
            }
            metadata = {
                "name": "plenair-map",
                "format": "pbf",
                "vector_layers": [{"id": "points", "fields": field_types(cluster_level_count)}],
            }
            writer.finalize(header, metadata)
        logger.info("Klaar: %d tiles geschreven", len(encoded_tiles))

        if client is not None and dashboard_hold_seconds > 0:
            logger.info(
                "Dashboard blijft nog %ds bereikbaar op %s", dashboard_hold_seconds, client.dashboard_link
            )
            time.sleep(dashboard_hold_seconds)
    finally:
        if client is not None:
            client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=str, default=str(DEFAULT_INPUT))
    parser.add_argument("--out", type=str, default=str(DEFAULT_OUTPUT))
    parser.add_argument("--grid-out", type=str, default=str(DEFAULT_GRID_OUTPUT))
    parser.add_argument("--maxzoom", type=int, default=DEFAULT_MAXZOOM)
    parser.add_argument("--no-dashboard", dest="dashboard", action="store_false", help="Draai zonder dask-distributed-dashboard (synchronous scheduler)")
    parser.add_argument(
        "--dashboard-hold-seconds",
        type=int,
        default=0,
        help="Blijf na afloop nog N seconden draaien zodat het dashboard bereikbaar blijft",
    )
    args = parser.parse_args()

    build(
        Path(args.input),
        Path(args.out),
        Path(args.grid_out),
        args.maxzoom,
        dashboard=args.dashboard,
        dashboard_hold_seconds=args.dashboard_hold_seconds,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
