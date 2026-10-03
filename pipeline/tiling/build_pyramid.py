"""
Bouwt de vector-tile-pyramide voor de plenaire kaart: leest de bestaande
`data/export/plenair-map/plenair-map.json` (dezelfde brondata als
`PlenairMap.vue`, gegenereerd door `pipeline/plenary_map/cluster.py
--export-frontend`) en schrijft `data/export/plenair-map/plenair-map.pmtiles`
-- een MVT-tile-pyramide over een
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
import hashlib
import json
import logging
import math
import time
from pathlib import Path

import dask
import numpy as np
from morecantile.commons import Tile
from scipy.spatial import cKDTree
from pmtiles.tile import Compression, TileType, tileid_to_zxy, zxy_to_tileid
from pmtiles.writer import write

from pipeline.build_static_data import _speaker_event_url
from pipeline.dask_client import make_client
from pipeline.db import db
from pipeline.paths import REPO_ROOT
from pipeline.tiling.density import compute_density_grid, write_cog
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

# data/export/plenair-map/ bundelt alle plenair-map-exportbestanden bij
# elkaar (issue #316), zelfde map als pipeline/plenary_map/cluster.py's
# EXPORT_DIR.
DEFAULT_INPUT = REPO_ROOT / "data" / "export" / "plenair-map" / "plenair-map.json"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "export" / "plenair-map" / "plenair-map.pmtiles"
# Geen los DEFAULT_GRID_OUTPUT meer: --grid-out wordt afgeleid van --out
# (<stem>-grid.json), zie main() -- voor DEFAULT_OUTPUT komt dat nog steeds
# uit op plenair-map-grid.json.

LOOKUP_KEYS = ["topics", "actors", "parties", "debates", "soorten"]

# Zonder cap zit op zoom 0 letterlijk de hele dataset in de ene tile (live
# gemeten: 731.985 punten, 134MB voor de volledige dataset, zie issue #259) --
# 3000 hield in die meting elke tile onder ~1-2MB MVT-bytes, ruim genoeg voor
# een overzichtsbeeld per zoomniveau.
DEFAULT_MAX_POINTS_PER_TILE = 3000

# Dichtheidsraster (issue #367) -- resolutie los van de A0-printposter-
# constantes (die zijn 300dpi-print-specifiek, zie scripts/a0_map/
# generate_a0_density_raster.py). 2048x2048 is ruim genoeg voor zowel
# per-punt sampling tijdens thinning als een herkenbare visuele laag, zonder
# de ~9933x14043px A0-resolutie (en dus -rekentijd) nodig te hebben.
DEFAULT_DENSITY_WIDTH = 2048
DEFAULT_DENSITY_HEIGHT = 2048
DEFAULT_DENSITY_SIGMA_PX = 6.0
DEFAULT_DENSITY_GAMMA = 0.45


def assign_tiles_for_zoom(points: list, tms, zoom: int) -> dict[int, list]:
    """Groepeer alle punten per tile-id op één zoomniveau."""
    grouped: dict[int, list] = {}
    for point in points:
        tile = tile_for_point(tms, point[1], point[2], zoom)
        tile_id = zxy_to_tileid(tile.z, tile.x, tile.y)
        grouped.setdefault(tile_id, []).append(point)
    return grouped


def _uniform_from_id(point_id: int) -> float:
    """Vaste, deterministische pseudo-random uniform(0,1] per punt -- hash-
    gebaseerd i.p.v. Python's `random`, dus reproduceerbaar zonder seed-beheer."""
    digest = hashlib.blake2b(str(point_id).encode(), digest_size=8).digest()
    return max(int.from_bytes(digest, "big") / (2**64 - 1), 1e-12)


def point_priority(point_id: int, weight: float) -> float:
    """Dichtheidsgewogen rangorde-sleutel: Efraimidis-Spirakis-sampling zonder
    teruglegging (`key = -ln(U) / weight`, U een deterministische
    pseudo-random uniform(0,1], zie `_uniform_from_id()`). Bij een vast
    gewicht per punt (zelfde voor elk zoomniveau/elke tile) geeft dit, net
    als de vorige puur-hash-gebaseerde versie, de invariant die
    `thin_zoom_points_globally()` nodig heeft: een punt dat op een grof
    niveau overleeft, overleeft per definitie ook op elk fijner niveau (geen
    "pop in/out" bij zoomen).

    Het gewicht is hier `1 / (lokale_dichtheid + epsilon)` (zie `build()`):
    een punt in een dichtbevolkt gebied krijgt een laag gewicht, dus
    gemiddeld een hogere (= slechter geplaatste) sleutel, en wordt bij
    thinning dus eerder weggelaten dan een punt in een dun gebied --
    tippecanoe's `--drop-densest-as-needed`-idee, maar gevoed door ons eigen
    dichtheidsraster (`pipeline.tiling.density`, issue #367) i.p.v. een
    per-tegel-interne berekening. Met een vlak gewicht (1.0 overal) is dit
    identiek aan de oude puur-uniforme rangorde."""
    return -math.log(_uniform_from_id(point_id)) / max(weight, 1e-12)


def compute_global_point_ranks(points: list, weights: dict[int, float]) -> dict[int, int]:
    """Rangnummer per punt-id (0 = laagste `point_priority()`), één keer over
    de volledige dataset berekend en hergebruikt voor elk zoomniveau in
    `thin_zoom_points_globally()` -- zie die functie voor waarom een globale
    rangorde nodig is i.p.v. een per-tile cap."""
    ranked_ids = sorted((point[0] for point in points), key=lambda pid: point_priority(pid, weights[pid]))
    return {point_id: rank for rank, point_id in enumerate(ranked_ids)}


def _assign_point_counts(survivors: list, dropped: list) -> dict[int, int]:
    """Voronoi-toewijzing: elk weggelaten punt telt mee bij zijn dichtstbijzijnde
    overlevende punt (KD-tree nearest-neighbor op x/y, index 1/2) -- zo krijgt
    elke overlevende een exacte `point_count`: zichzelf plus alle punten die op
    dit zoomniveau/deze tile aan hem zijn "toegewezen". Geen schatting zoals de
    `density`-waarde, maar een letterlijke telling (issue #367-vervolg, mirrort
    tippecanoe's `--cluster-distance`/`point_count`, hier gevoed door de
    dichtheidsgewogen thinning i.p.v. een afstandsdrempel)."""
    counts = {point[0]: 1 for point in survivors}
    if not dropped or not survivors:
        return counts
    survivor_xy = np.array([[p[1], p[2]] for p in survivors])
    dropped_xy = np.array([[p[1], p[2]] for p in dropped])
    _, nearest_idx = cKDTree(survivor_xy).query(dropped_xy)
    for idx in nearest_idx:
        counts[survivors[idx][0]] += 1
    return counts


def thin_zoom_points_globally(
    grouped: dict[int, list], ranks: dict[int, int], max_points_per_tile: int
) -> dict[int, list]:
    """Cap het totale aantal punten op één zoomniveau op
    `len(grouped) * max_points_per_tile` (hetzelfde totaalbudget als een
    vlakke per-tile-cap zou geven), maar afgekapt op de globale
    prioriteitsrangorde (`ranks`, zelfde voor elk zoomniveau/elke tile)
    i.p.v. per tile apart. Effect: een dichte tile houdt evenredig meer
    punten dan een dunne tile, in plaats van dat beide plat worden afgekapt
    op dezelfde absolute grens -- dat laatste gaf juist het omgekeerde beeld
    van de werkelijke dichtheid (issue #259: kleine, van nature al onder een
    vlakke cap zittende randclusters oogden na thinning drukker dan het
    zwaar uitgedunde centrum). Omdat `ranks` positie-/zoomniveau-onafhankelijk
    is, groeit het budget mee met het aantal tiles per zoomniveau (elk
    zoomniveau kwadrant-splitst tiles, dus het budget groeit ongeveer 4x per
    stap) -- de bewaarde set op een fijner niveau is dus altijd een superset
    van die op het grovere niveau: geen "pop in/out" van punten meer bij
    zoomen.

    Overlevende punten krijgen hier een `point_count` aangeplakt (zie
    `_assign_point_counts()`) -- dat gebeurt op een KOPIE van de rij, per
    zoomniveau opnieuw, nooit op de gedeelde `points`-lijst zelf (dezelfde rij
    heeft op elk zoomniveau een ander point_count, de brondata moet dus
    ongemoeid blijven)."""
    budget = len(grouped) * max_points_per_tile
    result: dict[int, list] = {}
    for tile_id, tile_points in grouped.items():
        survivors = [point for point in tile_points if ranks[point[0]] < budget]
        dropped = [point for point in tile_points if ranks[point[0]] >= budget]
        counts = _assign_point_counts(survivors, dropped)
        result[tile_id] = [[*point, counts[point[0]]] for point in survivors]
    return result


def load_video_hrefs(point_ids: set[int], videos_json_path: Path | None = None) -> dict[int, str]:
    """id->video-deep-link voor de gegeven document-id's, hier per tile
    meegecodeerd i.p.v. als los plenair-map-videos.json-bestand (dat bestand
    dekte maar de kleine steekproef en zou voor de volle dataset tot ~190MB
    groeien, zie issue #356-vervolg).

    Eerst `videos_json_path` geraadpleegd (standaard plenair-map-videos.json
    naast de input, zie scripts/export_plenair_map_videos.py): die bevat voor
    ~5300 document-id's een gecureerde `is_internal=true`-link naar onze
    eigen /debatten/{id}/-pagina i.p.v. Debat Direct (handmatig/uit de
    verloren originele generator afkomstig, niet in Python te reconstrueren
    zonder frontend/src/lib/debateId.ts' debateId()-matching hier te
    dupliceren -- expliciet afgeraden in dat script's eigen docstring).
    Alleen voor id's die daar ontbreken (de rest van de volle dataset) wordt
    hier zelf, rechtstreeks uit `documents`, de externe Debat Direct-link
    berekend via dezelfde `_speaker_event_url()`-logica."""
    hrefs: dict[int, str] = {}
    if videos_json_path is not None and videos_json_path.exists():
        curated = json.loads(videos_json_path.read_text())
        for doc_id, entry in curated.items():
            point_id = int(doc_id)
            if point_id in point_ids:
                hrefs[point_id] = entry["href"]

    conn = db.connect()
    try:
        rows = conn.execute(
            """SELECT id, video_url, published_at, speaker_event_anchor_at, turn_type, is_voorzitter_turn
               FROM documents
               WHERE video_url IS NOT NULL"""
        ).fetchall()
    finally:
        conn.close()

    for row in rows:
        if row["id"] not in point_ids or row["id"] in hrefs:
            continue
        href = _speaker_event_url(
            row["video_url"],
            row["published_at"],
            anchor_at=row["speaker_event_anchor_at"],
            turn_type=row["turn_type"],
            is_voorzitter_turn=bool(row["is_voorzitter_turn"]),
        )
        if href is not None:
            hrefs[row["id"]] = href
    return hrefs


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
    max_points_per_tile: int = DEFAULT_MAX_POINTS_PER_TILE,
    dashboard: bool = True,
    dashboard_hold_seconds: int = 0,
    videos_json_path: Path | None = None,
    density_cog_output_path: Path | None = None,
    density_width: int = DEFAULT_DENSITY_WIDTH,
    density_height: int = DEFAULT_DENSITY_HEIGHT,
    density_sigma_px: float = DEFAULT_DENSITY_SIGMA_PX,
    density_gamma: float = DEFAULT_DENSITY_GAMMA,
) -> None:
    client = make_client(dashboard)

    try:
        logger.info("Lees brondata uit %s", input_path)
        raw = json.loads(input_path.read_text())
        points = raw["points"]
        lookups = {key: raw[key] for key in LOOKUP_KEYS}
        logger.info("%d punten geladen", len(points))

        logger.info("Haal video-links op voor deze punten")
        if videos_json_path is None:
            videos_json_path = input_path.with_name("plenair-map-videos.json")
        video_by_id = load_video_hrefs({p[0] for p in points}, videos_json_path)
        logger.info("%d punten met video-link", len(video_by_id))

        # video_href als vast veld tussen `cluster` (index 10) en het optionele
        # cluster_levels-element invoegen i.p.v. als los id->href-object door de
        # dask-graaf sturen: dat laatste verdubbelde in feite het datavolume
        # van `points` als tweede, apart gedeelde dependency voor elk van de
        # ~2000 tile-taken, en bracht de graaf (al 482MB bij de volle dataset)
        # over de OOM-grens (issue #356-vervolg, Error 137). Eén keer invoegen,
        # hier, voordat `points` verderop via client.scatter() naar de workers
        # gaat -- daarna reist het gewoon mee in de al bewezen-veilige
        # punten-rij, net als cluster_levels.
        points = [[*p[:11], video_by_id.get(p[0], ""), *p[11:]] for p in points]

        # UMAP-coördinaten (x, y op index 1, 2) één keer uniform naar
        # Mercator-meters herschalen zodat de tile-pyramide de volle
        # standaard Web-Mercator-extent vult -- zie grid.py's moduledocstring
        # voor waarom een custom, kleinere extent hier fout gaat in generieke
        # viewers (QGIS/pmtiles.io/MapLibre).
        affine = umap_to_mercator_affine(points)
        lon_min, lat_min, lon_max, lat_max = lonlat_bounds(points, affine)
        points = [[p[0], *umap_to_mercator(p[1], p[2], affine), *p[3:]] for p in points]

        # Dichtheidsraster over de puntenwolk (issue #367): dezelfde
        # histogram+Gaussian-blur-aanpak als scripts/a0_map/
        # generate_a0_density_raster.py, hier losgetrokken van de A0-print-
        # specifieke afmetingen. Twee toepassingen hieronder: (1) als gewicht
        # voor dichtheidsbewuste thinning i.p.v. de vlakke globale rangorde,
        # (2) als losse COG naast de pmtiles, zodat de frontend 'm optioneel
        # als eigen laag kan tonen.
        xs = np.array([p[1] for p in points], dtype=np.float64)
        ys = np.array([p[2] for p in points], dtype=np.float64)
        density_bounds = (float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max()))
        logger.info(
            "Bereken dichtheidsraster (%dx%d, sigma=%.1fpx, gamma=%.2f)",
            density_width, density_height, density_sigma_px, density_gamma,
        )
        density_grid = compute_density_grid(
            xs, ys, density_bounds, width=density_width, height=density_height,
            sigma_px=density_sigma_px, gamma=density_gamma,
        )
        density_values = density_grid.sample(xs, ys)
        # `represents`-gewicht voor point_priority(): omgekeerd evenredig met
        # lokale dichtheid, zodat dichte gebieden bij thinning eerder worden
        # weggelaten dan dunne (zie point_priority()'s docstring). epsilon
        # voorkomt delen door 0 in lege/zeer dunne gebieden.
        density_weights = {int(p[0]): 1.0 / (float(d) + 1e-3) for p, d in zip(points, density_values)}
        # Afgerond op 3 decimalen voor de MVT-encodering: minder entropie dus
        # betere waarde-deduplicatie in mapbox_vector_tile's values-tabel,
        # zonder merkbaar verlies aan visuele precisie (dichtheid is toch al
        # een vloeiend, geen exact, signaal).
        points = [[*p[:12], round(float(d), 3), *p[12:]] for p, d in zip(points, density_values)]

        if density_cog_output_path is not None:
            write_cog(density_grid, density_cog_output_path)
            logger.info(
                "Dichtheids-COG geschreven naar %s (%.2f MB)",
                density_cog_output_path, density_cog_output_path.stat().st_size / 1e6,
            )

        tms = build_grid()
        write_grid_metadata(affine, maxzoom, grid_output_path)
        logger.info("Grid geschreven naar %s (zoom 0-%d)", grid_output_path, maxzoom)

        # `points`/`lookups` via client.scatter() i.p.v. dask.delayed(): delayed()
        # embedt de waarde als letterlijk object in de taakgraaf, en dask moet
        # die bij het bouwen van de graaf recursief tokenizen (hashen) voor
        # caching/dedup -- voor de volle dataset (731k rijen, elk nu ook nog
        # met video_href erbij) is dat single-threaded Python-werk dat op de
        # host minutenlang vastliep op één core, nog vóór er iets naar een
        # worker ging (issue #356-vervolg, naast de eerdere OOM/Error 137).
        # scatter() stuurt de data één keer binair naar de workers en geeft
        # een lichte Future terug, zonder die tokenisatiepas. `[data]`/`[0]`
        # omdat scatter() een list standaard element-voor-element verdeelt --
        # wij willen juist elke waarde als één geheel. Alleen beschikbaar met
        # een echte distributed Client -- `--no-dashboard` geeft `client=None`
        # (synchrone scheduler), dan gewoon de platte waarde doorgeven zoals
        # dask.delayed() dat toch al accepteert.
        if client is not None:
            # hash=False: scatter() berekent anders standaard tokenize(data)
            # om een deterministische cache-sleutel te maken -- dat is exact
            # dezelfde dure recursieve hash-pas over de hele structuur die we
            # met scatter() juist wilden vermijden. We hebben geen caching
            # over meerdere scatter-aanroepen nodig (één build() -> één
            # scatter per waarde), dus hash=False laat dask gewoon een losse
            # uuid als sleutel gebruiken i.p.v. tokenize().
            [points_future] = client.scatter([points], broadcast=True, hash=False)
            [lookups_future] = client.scatter([lookups], broadcast=True, hash=False)
            # tms (morecantile TileMatrixSet) bevat een pyproj.CRS -- CRS-objecten
            # zijn zelf al traag om te hashen/naar WKT te serialiseren, dus ook
            # dask.delayed(tms) zou die kost nog betalen. Niet-groot in bytes,
            # maar wel dezelfde single-core tokenize-bottleneck.
            [tms_future] = client.scatter([tms], broadcast=True, hash=False)
        else:
            points_future, lookups_future, tms_future = points, lookups, tms

        logger.info("Verdeel punten over tiles per zoomniveau (dask-taak per zoomniveau)")
        per_zoom_assignments = dask.compute(
            *[dask.delayed(assign_tiles_for_zoom)(points_future, tms_future, zoom) for zoom in range(0, maxzoom + 1)]
        )

        logger.info("Bereken globale (dichtheidsgewogen) prioriteitsrangorde (%d punten)", len(points))
        ranks = compute_global_point_ranks(points, density_weights)

        encode_tasks = []
        for grouped in per_zoom_assignments:
            thinned = thin_zoom_points_globally(grouped, ranks, max_points_per_tile)
            for tile_id, tile_points in thinned.items():
                encode_tasks.append(dask.delayed(encode_one_tile)(tile_id, tile_points, lookups_future, tms_future))
        logger.info("%d tiles te encoderen (dask-taak per tile)", len(encode_tasks))

        encoded_tiles = dask.compute(*encode_tasks)
        encoded_tiles = sorted(encoded_tiles, key=lambda entry: entry[0])

        # 14e element (cluster-ids per niveau, na video_href op index 11 en
        # density op index 12) is optioneel, zie encode.py's module-docstring
        # -- alleen aanwezig bij N-laagse clustering.
        cluster_level_count = len(points[0][13]) if points and len(points[0]) > 13 else 0

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
    parser.add_argument(
        "--grid-out",
        type=str,
        default=None,
        help="standaard afgeleid van --out als '<stem-van---out>-grid.json' (zelfde map, "
        "consistente naamvolgorde <naam>-grid.json) -- alleen expliciet zetten voor een "
        "afwijkend pad. Los getypte grid-paden hebben eerder tot inconsistente naamvolgorde "
        "geleid (plenair-map-full-grid.json vs. plenair-map-grid-full.json, issue #316).",
    )
    parser.add_argument("--maxzoom", type=int, default=DEFAULT_MAXZOOM)
    parser.add_argument(
        "--max-points-per-tile", type=int, default=DEFAULT_MAX_POINTS_PER_TILE,
        help="richtgetal voor het totaalbudget per zoomniveau (aantal populated tiles * "
        "deze waarde), globaal verdeeld naar prioriteitsrangorde i.p.v. per tile apart "
        "afgekapt -- zie thin_zoom_points_globally()",
    )
    parser.add_argument("--no-dashboard", dest="dashboard", action="store_false", help="Draai zonder dask-distributed-dashboard (synchronous scheduler)")
    parser.add_argument(
        "--dashboard-hold-seconds",
        type=int,
        default=0,
        help="Blijf na afloop nog N seconden draaien zodat het dashboard bereikbaar blijft",
    )
    parser.add_argument(
        "--videos-json",
        type=str,
        default=None,
        help="pad naar de gecureerde plenair-map-videos.json (standaard: naast --input, "
        "zie scripts/export_plenair_map_videos.py) -- levert de interne /debatten/{id}/-"
        "links voor de document-id's die daar in staan; voor de rest wordt de externe "
        "Debat Direct-link berekend.",
    )
    parser.add_argument(
        "--density-cog-out",
        type=str,
        default=None,
        help="pad voor de dichtheids-COG (standaard afgeleid van --out als "
        "'<stem-van---out>-density.tif', zelfde map). '' om geen COG te schrijven.",
    )
    parser.add_argument("--density-width", type=int, default=DEFAULT_DENSITY_WIDTH)
    parser.add_argument("--density-height", type=int, default=DEFAULT_DENSITY_HEIGHT)
    parser.add_argument("--density-sigma-px", type=float, default=DEFAULT_DENSITY_SIGMA_PX)
    parser.add_argument("--density-gamma", type=float, default=DEFAULT_DENSITY_GAMMA)
    args = parser.parse_args()

    out_path = Path(args.out)
    grid_out_path = Path(args.grid_out) if args.grid_out else out_path.with_name(f"{out_path.stem}-grid.json")
    if args.density_cog_out == "":
        density_cog_out_path = None
    elif args.density_cog_out:
        density_cog_out_path = Path(args.density_cog_out)
    else:
        density_cog_out_path = out_path.with_name(f"{out_path.stem}-density.tif")

    build(
        Path(args.input),
        out_path,
        grid_out_path,
        args.maxzoom,
        max_points_per_tile=args.max_points_per_tile,
        dashboard=args.dashboard,
        dashboard_hold_seconds=args.dashboard_hold_seconds,
        videos_json_path=Path(args.videos_json) if args.videos_json else None,
        density_cog_output_path=density_cog_out_path,
        density_width=args.density_width,
        density_height=args.density_height,
        density_sigma_px=args.density_sigma_px,
        density_gamma=args.density_gamma,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
