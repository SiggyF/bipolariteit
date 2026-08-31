"""
Zet een `plenair-map-clusters*.json`-bestand (coarse/fine of N-laags, zie
`scripts/experiment_umap_documents.py`'s `label_hierarchical_clusters()`/
`label_multilevel_clusters()`) om naar GeoJSON, voor visuele inspectie in
QGIS naast de puntenlaag (het .pmtiles-bestand, zie pipeline/tiling/).

Elk cluster wordt een Polygon-feature (de convex hull), met properties
cluster_id/level/name/parent_id/parent_name/terms/size/topic_breakdown.
Clusters zonder hull (te weinig punten, <3) worden een Point-feature op hun
centroid i.p.v. overgeslagen, zodat je niets mist bij het filteren op level.

Coördinaten zijn in de brondata dezelfde "neppe" vlakke UMAP-eenheden als de
rest van de tiling-pijplijn (geen echte lengte-/breedtegraad, zie
pipeline/tiling/grid.py) -- veel te klein (enkele/dubbele cijfers) om als
letterlijke EPSG:3857-meters te declareren: QGIS reprojecteert dan met de
ECHTE Web Mercator-formule (gekalibreerd op een ~40.000km-omtrek-planeet),
en perst onze punten samen tot een speldenprikje bij (0,0) -- live gezien in
QGIS (clusterlaag-extent kromp tot ~0,0001° i.p.v. overeen te komen met de
puntenlaag). De .pmtiles-puntenlaag heeft dit probleem niet: vector-tile-
rendering gebruikt de gedeclareerde header-bounds puur lineair (behandelt het
hele archief als "de hele wereld"), geen echte CRS-herprojectie.

Om dezelfde lineaire "hele wereld"-truc te volgen i.p.v. een neppe CRS te
declareren, wordt hier expliciet dezelfde grid-extent (uit
plenair-map-<suffix>-grid.json, door pipeline/tiling/grid.py geschreven)
lineair herschaald naar -180..180 / -90..90 -- exact hoe de tile-pyramide
zijn eigen custom-grid al behandelt als "de hele wereld" op zoom 0. De
GeoJSON draagt dan gewoon impliciet WGS84 (RFC7946-default, geen crs-member
nodig), en lijnt zo op natuurlijke wijze uit met de puntenlaag.

Gebruik:
    uv run python scripts/export_clusters_geojson.py \
        data/export/plenair-map-clusters-full.json \
        data/export/plenair-map-clusters-full.geojson \
        --grid data/export/plenair-map-full-grid.json

Voor de print-pijplijn (datashader/QGIS-compositie op A0, geen vector-tile-
viewer erbij) is die WGS84-heenenweer-reis niet nodig -- ze bestaat alleen om
uit te lijnen met hoe generieke MVT/PMTiles-viewers de puntenlaag interpreteren.
`--flat` slaat `make_rescaler`/`_to_wgs84` over en schrijft de rauwe UMAP-
grid-eenheden (dezelfde eenheden als `plenair-map-<suffix>.json`'s punten en
dus als `render_design_preview.py`) direct als GeoJSON-coördinaten -- geen
`--grid` nodig, geen Mercator-vervorming, 1:1 dezelfde ruimte als de
puntenwolk die er in QGIS naast komt te liggen. QGIS importeert zo'n bestand
als "no CRS"/vlakke coördinaten (RFC7946 vermeldt geen `crs`-member meer,
dus behandel de laag na import expliciet als projectloos, niet als EPSG:4326):
    uv run python scripts/export_clusters_geojson.py \
        data/export/plenair-map-clusters-full.json \
        data/export/plenair-map-clusters-full-flat.geojson \
        --flat
"""

import argparse
import json
import logging
from pathlib import Path

import numpy as np
from pyproj import Transformer
from scipy.interpolate import splev, splprep

logger = logging.getLogger(__name__)

# Halve omtrek van de EPSG:3857-vierkante wereldkaart in meter (pyproj/PROJ-
# constante, gebaseerd op de WGS84-equatorradius). De .pmtiles-puntenlaag
# (pipeline/tiling/grid.py) bucket't punten via een custom morecantile-grid
# met dezelfde quadtree-onderverdeling (2^z x 2^z) als de STANDAARD globale
# Web Mercator-tegelpiramide -- een generieke MVT/PMTiles-viewer kent onze
# custom grid-extent niet en interpreteert diezelfde z/x/y-tegelindices dus
# als tegels in de standaard wereldwijde piramide. Relatieve positie binnen
# onze grid-extent bepaalt zo (via de quadtree-onderverdeling) al impliciet
# een ECHTE Web Mercator-locatie. Door hier expliciet dezelfde stap te zetten
# (relatieve positie -> echte 3857-meters -> terugprojecteren naar WGS84)
# krijgt de clusterlaag precies dezelfde projectie-vervorming als de
# puntenlaag al ondergaat, i.p.v. een losse, inconsistente lineaire
# graden-schaling. Bijkomend effect (geen doel op zich): de breedtegraad
# verzadigt vanzelf bij ±85.0511° (de bekende Web Mercator-afkapgrens),
# zonder handmatige clamp.
WEB_MERCATOR_HALF_EXTENT = 20037508.342789244

_to_wgs84 = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)


def flat_rescale(point: list[float]) -> list[float]:
    return [round(float(point[0]), 4), round(float(point[1]), 4)]


def make_rescaler(grid: dict):
    left, bottom, right, top = grid["extent"]
    span_x = right - left
    span_y = top - bottom

    def rescale(point: list[float]) -> list[float]:
        x, y = point
        fraction_x = (x - left) / span_x
        fraction_y = (y - bottom) / span_y
        merc_x = -WEB_MERCATOR_HALF_EXTENT + fraction_x * 2 * WEB_MERCATOR_HALF_EXTENT
        merc_y = -WEB_MERCATOR_HALF_EXTENT + fraction_y * 2 * WEB_MERCATOR_HALF_EXTENT
        lon, lat = _to_wgs84.transform(merc_x, merc_y)
        return [lon, lat]

    return rescale


def smooth_hull(hull: list[list[float]], num_samples: int = 60) -> list[list[float]]:
    """Rondt de rechte convex-hull-randen af tot een gladde gesloten curve.

    Een periodieke kubische B-spline (`per=True`, `s=0`) door de hull-
    hoekpunten interpoleert EXACT door diezelfde punten (geen least-squares-
    afvlakking die de vorm zou verkleinen), maar buigt gecontroleerd tussen
    de hoekpunten door i.p.v. rechte segmenten -- zichtbaar minder "polygonaal"
    in QGIS zonder de eigenlijke vorm/omvang van de hull te veranderen. Bij
    te weinig hoekpunten voor een kubische periodieke fit (nodig: >3) of een
    numeriek gedegenereerde hull: ongewijzigd teruggeven.
    """
    if not hull or len(hull) < 4:
        return hull
    pts = np.array(hull)
    try:
        tck, _ = splprep([pts[:, 0], pts[:, 1]], per=True, s=0, k=3)
    except Exception as e:
        logger.debug("Kon hull niet gladstrijken, ongewijzigd gebruikt: %s", e)
        return hull
    u = np.linspace(0.0, 1.0, num_samples, endpoint=False)
    x, y = splev(u, tck)
    return [[round(float(px), 4), round(float(py), 4)] for px, py in zip(x, y)]


def cluster_to_feature(cluster: dict, level: int, rescale) -> dict:
    hull = smooth_hull(cluster.get("hull"))
    centroid = rescale(cluster["centroid"])
    if hull and len(hull) >= 3:
        ring = [rescale(p) for p in hull]
        ring.append(ring[0])  # GeoJSON-polygonen moeten gesloten zijn
        geometry = {"type": "Polygon", "coordinates": [ring]}
    else:
        geometry = {"type": "Point", "coordinates": centroid}

    # "L<level>-<cluster_id>": leesbare, stabiele feature-id (cluster_id op
    # zich is niet uniek over niveaus heen, ze beginnen elk bij 0) -- zowel
    # als top-level GeoJSON-"id" (QGIS' interne feature-id) als losse
    # attribuutkolom, zodat 'm ook zichtbaar is in de attributentabel zonder
    # cluster_id+level zelf te hoeven combineren.
    feature_id = f"L{level}-{cluster['cluster_id']}"
    return {
        "type": "Feature",
        "id": feature_id,
        "geometry": geometry,
        "properties": {
            "feature_id": feature_id,
            "cluster_id": cluster["cluster_id"],
            "level": level,
            "name": cluster["name"],
            "parent_id": cluster.get("parent_id"),
            "parent_feature_id": f"L{level - 1}-{cluster['parent_id']}" if cluster.get("parent_id") is not None else None,
            "parent_name": cluster.get("parent_name"),
            "terms": ", ".join(cluster.get("terms", [])),
            "size": cluster["size"],
            "topic_breakdown": json.dumps(cluster.get("topic_breakdown", {}), ensure_ascii=False),
            "redundant_with_parent": cluster.get("redundant_with_parent", False),
        },
    }


def build_geojson(clusters_data: dict, grid: dict | None, include_redundant: bool = False) -> dict:
    if "levels" in clusters_data:
        levels = clusters_data["levels"]
    else:
        levels = [clusters_data["coarse"], clusters_data["fine"]]

    rescale = flat_rescale if grid is None else make_rescaler(grid)
    features = []
    n_points_fallback = 0
    n_skipped_redundant = 0
    for level, clusters in enumerate(levels):
        for cluster in clusters:
            if not include_redundant and cluster.get("redundant_with_parent"):
                # Zonder echte splitsing t.o.v. de ouder (zie label_multilevel_
                # clusters' redundancy_overlap) duikt dezelfde hull vrijwel
                # ongewijzigd op bij meerdere niveaus -- live gezien in QGIS
                # als meerdere bijna-identieke, gestapelde polygonen ("quadruple
                # overlapping"). Standaard overgeslagen; --include-redundant om
                # ze alsnog te zien (bv. om de drempel te tunen).
                n_skipped_redundant += 1
                continue
            if not cluster.get("hull") or len(cluster["hull"]) < 3:
                n_points_fallback += 1
            features.append(cluster_to_feature(cluster, level, rescale))

    logger.info(
        "%d clusters over %d niveaus (%d zonder hull, als punt geëxporteerd; %d overgeslagen als redundant_with_parent)",
        len(features), len(levels), n_points_fallback, n_skipped_redundant,
    )
    return {"type": "FeatureCollection", "features": features}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", type=str, help="pad naar plenair-map-clusters(-<suffix>).json")
    parser.add_argument("output", type=str, help="pad voor het te schrijven .geojson-bestand")
    grid_group = parser.add_mutually_exclusive_group(required=True)
    grid_group.add_argument("--grid", type=str, help="pad naar het bijbehorende plenair-map(-<suffix>)-grid.json (WGS84-reprojectie, voor naast de .pmtiles-viewer)")
    grid_group.add_argument(
        "--flat", action="store_true",
        help="geen reprojectie -- schrijf de rauwe UMAP-grid-eenheden direct (voor de print-pijplijn, "
        "geen vector-tile-viewer erbij, zie de module-docstring)",
    )
    parser.add_argument(
        "--include-redundant", action="store_true",
        help="ook clusters met redundant_with_parent=true meenemen (standaard overgeslagen, "
        "zie build_geojson's docstring-commentaar)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    grid = None if args.flat else json.loads(Path(args.grid).read_text())

    clusters_data = json.loads(input_path.read_text())
    geojson = build_geojson(clusters_data, grid, include_redundant=args.include_redundant)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(geojson, ensure_ascii=False), encoding="utf-8")
    logger.info("Geschreven naar %s", output_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
