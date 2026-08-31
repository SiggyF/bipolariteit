"""
Custom morecantile-tilegrid over de UMAP-coördinatenruimte van de plenaire
kaart (zie issue #215/#253: vector-tile-pyramide i.p.v. één platte
plenair-map.json, zodat dezelfde aanpak schaalt naar meer punten en de
punteigenschappen -- incl. cluster-id -- per tile behouden blijven).

De punten hebben geen echte geografische CRS: het zijn UMAP-coördinaten. We
hergebruiken daarom een vlakke/planaire CRS (EPSG:3857, "Web Mercator"-eenheden)
puur als generieke Cartesische meter-eenheid -- morecantile's schaal-wiskunde
(resolution/scale denominator) is zelf CRS-eenheid-onafhankelijk consistent,
ook al stellen de "meters" hier geen echte aardse afstand voor. Zie de
toelichting in issue #215 (comment-thread over tile-servers/morecantile).

`TileMatrixSet.tile(x, y, zoom, geographic_crs=CRS)` behandelt (x, y) hierdoor
als coördinaten in de eigen CRS i.p.v. lengte-/breedtegraad te reprojecteren
(reden: `geographic_crs` gelijk aan de native CRS geeft een identity-transform).

Gebruik:
    from pipeline.tiling.grid import build_grid, tile_for_point
"""

import json
from pathlib import Path

import morecantile
import pyproj
from morecantile.commons import Tile

CRS = pyproj.CRS.from_epsg(3857)
TILE_SIZE = 256
DEFAULT_MAXZOOM = 8

# Zelfde 8%-marge als PlenairMap.vue's `rawBounds` (frontend/src/components/
# PlenairMap.vue), zodat punten aan de rand van de UMAP-ruimte niet precies op
# de tile-grid-rand vallen.
MARGIN_FACTOR = 1.08


def bounds_from_points(points: list) -> tuple[float, float, float, float]:
    """Bounding box (minx, miny, maxx, maxy) met marge rond alle punten.

    `points` is de ruwe `points`-array uit plenair-map.json: elke rij is
    `[id, x, y, topic_idx, actor_idx, party_idx, debate_idx, soort_idx,
    published_at, text, cluster]`.
    """
    xs = [p[1] for p in points]
    ys = [p[2] for p in points]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    span_x = (maxx - minx) * MARGIN_FACTOR
    span_y = (maxy - miny) * MARGIN_FACTOR
    return (cx - span_x / 2, cy - span_y / 2, cx + span_x / 2, cy + span_y / 2)


def build_grid(points: list, maxzoom: int = DEFAULT_MAXZOOM) -> morecantile.TileMatrixSet:
    """Bouw een custom TileMatrixSet over de bounding box van `points`."""
    extent = bounds_from_points(points)
    return morecantile.TileMatrixSet.custom(
        extent=list(extent),
        crs=CRS,
        tile_width=TILE_SIZE,
        tile_height=TILE_SIZE,
        minzoom=0,
        maxzoom=maxzoom,
        title="plenair-map-grid",
        id="PlenairMapGrid",
    )


def tile_for_point(tms: morecantile.TileMatrixSet, x: float, y: float, zoom: int) -> Tile:
    """Zoek de tile-index voor UMAP-punt (x, y) op een gegeven zoomniveau."""
    return tms.tile(x, y, zoom, geographic_crs=CRS)


def tile_bounds(tms: morecantile.TileMatrixSet, tile: Tile) -> tuple[float, float, float, float]:
    """Tile-bounds (minx, miny, maxx, maxy) in native CRS-eenheden."""
    b = tms.xy_bounds(tile)
    return (b.left, b.bottom, b.right, b.top)


def write_grid_metadata(tms: morecantile.TileMatrixSet, path: Path) -> None:
    """Schrijf de daadwerkelijke grid-bounds (na eventuele aanpassing door
    `custom()` zelf, bv. voor vierkante schaalverhouding) weg als klein JSON
    bestand, zodat de frontend exact dezelfde wereld<->scherm-transform kan
    reconstrueren zonder morecantile te hoeven spiegelen in JS."""
    bbox = tms.xy_bbox
    metadata = {
        "tile_size": TILE_SIZE,
        "minzoom": tms.minzoom,
        "maxzoom": tms.maxzoom,
        "extent": [bbox.left, bbox.bottom, bbox.right, bbox.top],
    }
    Path(path).write_text(json.dumps(metadata, indent=2))
