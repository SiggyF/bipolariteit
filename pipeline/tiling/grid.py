"""
Tile-grid voor de plenaire kaart, over de UMAP-coördinatenruimte heen
afgebeeld op de standaard Web-Mercator-tegelpyramide (zie issue #215/#253:
vector-tile-pyramide i.p.v. één platte plenair-map.json).

De punten hebben geen echte geografische CRS: het zijn UMAP-coördinaten. We
schalen/verschuiven ze daarom (één keer, uniform, aspect-ratio-behoudend) zodat
de (marge-uitgebreide, vierkant-gemaakte) UMAP-bounding-box exact de volle
standaard Web-Mercator-extent vult, en gebruiken vanaf dan gewoon
`morecantile`'s ingebouwde `WebMercatorQuad`-preset voor alle tile-wiskunde.

Waarom niet (zoals eerder) een custom, veel kleinere `TileMatrixSet.custom()`-
extent: een pmtiles-archief draagt zelf geen CRS/extent-metadata -- elke
generieke vector-tile-viewer (QGIS' native provider, pmtiles.io, MapLibre)
rekent een tegel-`z/x/y` altijd terug naar de standaard wereldwijde
Web-Mercator-formule. Met een custom, veel kleinere extent kwam een tegel die
wij op onze eigen kleine grid plaatsten bij zo'n viewer op een compleet
andere, willekeurige plek op de aardbol terecht (tot en met de
pool-vervorming rond ~85 breedtegraad) -- zichtbaar als punten die "over de
aardbol heen gewikkeld" leken (issue #281, QGIS-inspectie). Onze eigen
frontend (`TiledPlenairMap.vue`) rekende toen zelf terug met de losse
grid-metadata en had dat probleem niet, maar QGIS (het primaire
inspectie-/renderpad voor de A0-poster, issue #215 -- Illustrator loopt vast
op dit aantal punten) wél.

`tile_for_point()` gebruikt `TileMatrixSet._tile(x, y, zoom)` (privé-API) om
(x, y) rechtstreeks als coördinaten in de eigen CRS te behandelen i.p.v. via
de publieke `tile(..., geographic_crs=CRS)` een (voor ons altijd identity-)
pyproj-transform te laten lopen -- zie die functie's docstring voor waarom:
op schaal (miljoenen aanroepen) was de `lru_cache`/CRS-hash-overhead van die
publieke route zelf de bottleneck, niet de tegel-rekenkunde.

Gebruik:
    from pipeline.tiling.grid import build_grid, umap_to_mercator_affine, umap_to_mercator, tile_for_point
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

# Standaard Web-Mercator-halve-extent (EPSG:3857, meters) -- dezelfde
# constante die elke WebMercatorQuad-implementatie gebruikt. Blijft de
# extent van het grid-metadatabestand (write_grid_metadata) en dus van de
# echte z/x/y-tegeladressering -- ONAFHANKELIJK van hoeveel van die extent de
# data daadwerkelijk gebruikt (zie MAX_LON_DEG/MAX_LAT_DEG hieronder).
WEB_MERCATOR_HALF_EXTENT = 20037508.342789244

# Harde grens op het daadwerkelijke voetprint van de data: geen punt voorbij
# ±60 breedte-/lengtegraad (expliciete gebruikerswens, issue #281 -- de data
# heeft geen echte geografische betekenis, dus de volle breedtegraadrange
# (tot ±85,05° bij het vullen van de bredere as) oogt op een kaart/print
# alsof het over de polen uitsmeert). Breedtegraad is niet-lineair in
# Mercator-meters (secans-vervorming), dus x- en y-cap apart via een echte
# voorwaartse projectie berekenen i.p.v. dezelfde meterswaarde voor beide.
MAX_LON_DEG = 60.0
MAX_LAT_DEG = 60.0

STANDARD_TMS = morecantile.tms.get("WebMercatorQuad")


def _mercator_cap(lon_deg: float, lat_deg: float) -> tuple[float, float]:
    transformer = pyproj.Transformer.from_crs("EPSG:4326", CRS, always_xy=True)
    cap_x, _ = transformer.transform(lon_deg, 0.0)
    _, cap_y = transformer.transform(0.0, lat_deg)
    return cap_x, cap_y


MERCATOR_CAP_X, MERCATOR_CAP_Y = _mercator_cap(MAX_LON_DEG, MAX_LAT_DEG)


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


def umap_to_mercator_affine(points: list) -> tuple[float, float, float]:
    """(scale, cx, cy) die de UMAP-bounding-box (met marge) uniform (aspect-
    ratio-behoudend) naar Mercator-meters schaalt, begrensd tot
    ±MAX_LON_DEG/±MAX_LAT_DEG: `mx = (x - cx) * scale`, `my = (y - cy) * scale`.
    Neemt de kleinste van de twee toegestane schalen (x- en y-as apart tegen
    hun eigen cap getoetst) zodat GEEN van beide assen zijn cap overschrijdt --
    de andere as vult dan het eigen cap niet helemaal, wat prima is (geen
    vaste aspect ratio tussen de twee caps zelf, want breedtegraad is
    niet-lineair)."""
    minx, miny, maxx, maxy = bounds_from_points(points)
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    half_x, half_y = (maxx - minx) / 2, (maxy - miny) / 2
    scale = min(MERCATOR_CAP_X / half_x, MERCATOR_CAP_Y / half_y)
    return scale, cx, cy


def umap_to_mercator(x: float, y: float, affine: tuple[float, float, float]) -> tuple[float, float]:
    scale, cx, cy = affine
    return (x - cx) * scale, (y - cy) * scale


def build_grid() -> morecantile.TileMatrixSet:
    """De standaard WebMercatorQuad-preset -- geen custom extent meer, zie moduledocstring."""
    return STANDARD_TMS


def tile_for_point(tms: morecantile.TileMatrixSet, x: float, y: float, zoom: int) -> Tile:
    """Zoek de tile-index voor een al naar Mercator-meters getransformeerd punt (x, y).

    Gebruikt bewust `tms._tile()` (privé-API) i.p.v. de publieke `tms.tile(...,
    geographic_crs=CRS)`: die laatste bouwt via `morecantile`'s
    `TransformerFromCRS` (een `lru_cache` om `pyproj.Transformer.from_crs`)
    voor élke aanroep een from/to-pyproj-transformer op -- een no-op omdat
    `geographic_crs` hier al gelijk is aan de TMS's eigen CRS (identity-
    transform, zie moduledocstring), maar `lru_cache` moet de CRS-objecten
    dan nog steeds hashen/vergelijken om de cache-hit te vinden, en
    `pyproj.CRS`-hashing is zelf traag. Op schaal (731985 punten x 9
    zoomniveaus = ~6,6 miljoen aanroepen in `assign_tiles_for_zoom()`) was
    dat de daadwerkelijke bottleneck (issue #356-vervolg, zichtbaar in een
    host-profiel als tijd in `crs.py`'s hash-pad), niet de eigenlijke
    tegel-rekenkunde. `_tile(x, y, zoom)` doet exact die rekenkunde (floor-
    deling op cel-grootte) rechtstreeks in de TMS-CRS, zonder pyproj erbij --
    precies wat hier nodig is, want x/y staan al in die CRS."""
    return tms._tile(x, y, zoom)  # noqa: SLF001 -- zie docstring


def tile_bounds(tms: morecantile.TileMatrixSet, tile: Tile) -> tuple[float, float, float, float]:
    """Tile-bounds (minx, miny, maxx, maxy) in Mercator-meters."""
    b = tms.xy_bounds(tile)
    return (b.left, b.bottom, b.right, b.top)


def lonlat_bounds(points: list, affine: tuple[float, float, float]) -> tuple[float, float, float, float]:
    """Werkelijke WGS84-lon/lat-bbox van de data, voor de pmtiles-headervelden
    (`min_lon_e7`/`max_lon_e7`/`min_lat_e7`/`max_lat_e7`) -- puur informatief
    (bv. "zoom naar laag-extent" in een generieke viewer), telt niet mee voor
    de daadwerkelijke tile-plaatsing (die gebeurt in Mercator-meters, zie
    `tile_for_point()`)."""
    minx, miny, maxx, maxy = bounds_from_points(points)
    mminx, mminy = umap_to_mercator(minx, miny, affine)
    mmaxx, mmaxy = umap_to_mercator(maxx, maxy, affine)
    transformer = pyproj.Transformer.from_crs(CRS, "EPSG:4326", always_xy=True)
    lon_min, lat_min = transformer.transform(mminx, mminy)
    lon_max, lat_max = transformer.transform(mmaxx, mmaxy)
    return lon_min, lat_min, lon_max, lat_max


def write_grid_metadata(affine: tuple[float, float, float], maxzoom: int, path: Path) -> None:
    """Schrijf de grid-metadata weg als klein JSON-bestand: de (altijd
    constante) volle Web-Mercator-extent, plus de UMAP->Mercator-affiene
    transform (`umap_scale`/`umap_center`) zodat de frontend ook los van de
    tile-pyramide staande UMAP-coördinaten (bv. cluster-hull-polygonen uit
    plenair-map-clusters(-full).json) in dezelfde ruimte kan tekenen als de
    punten die uit de tiles zelf gedecodeerd worden."""
    scale, cx, cy = affine
    metadata = {
        "tile_size": TILE_SIZE,
        "minzoom": 0,
        "maxzoom": maxzoom,
        "extent": [
            -WEB_MERCATOR_HALF_EXTENT,
            -WEB_MERCATOR_HALF_EXTENT,
            WEB_MERCATOR_HALF_EXTENT,
            WEB_MERCATOR_HALF_EXTENT,
        ],
        "umap_scale": scale,
        "umap_center": [cx, cy],
    }
    Path(path).write_text(json.dumps(metadata, indent=2))
