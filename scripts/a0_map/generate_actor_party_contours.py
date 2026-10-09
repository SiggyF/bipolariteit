"""
Berekent per partij en per Kamerlid een "politieke vingerafdruk": de gebieden
op de plenaire kaart waar die partij/persoon vaker spreekt dan gemiddeld, als
GeoJSON voor QGIS (issue #261).

Absolute dichtheid blijkt daarvoor ongeschikt: elke partij en elk Kamerlid
volgt grotendeels de algemene dichtheid van het landschap (waar veel
gedebatteerd wordt), waardoor de contouren sterk op elkaar lijken. Daarom
wordt de dichtheid van de groep gedeeld door de totale dichtheid. Een
verhouding van 1,5 betekent: anderhalf keer zoveel spreekbeurten in dit
gebied als je op grond van het totaal zou verwachten.

Werkwijze:
  1. Alle punten (x, y uit plenair-map<-suffix>.json) naar een raster van
     `--bins` x `--bins` cellen, gladgestreken met een gaussiaans filter
     (`--sigma`, in cellen). Dat is veel sneller dan een echte KDE op >700k
     punten en geeft vergelijkbare vormen.
  2. Per groep: dichtheid / totale dichtheid. Cellen waar de totale dichtheid
     onder `--floor` x het maximum ligt tellen niet mee (de verhouding is
     daar ruis).
  3. Per drempel (standaard 1,5x en 3x): een gevuld contour met gaten, als
     Polygon/MultiPolygon. Elke drempel is een geneste laag (3x ligt binnen
     1,5x), zodat je in QGIS lagen kunt stapelen.

Groepen onder `--min-points` spreekbeurten krijgen geen contour: daaronder
is het patroon ruis.

Coordinaten: standaard de ruwe UMAP-eenheden (`--flat`-gedrag van
export_clusters_geojson.py, zelfde ruimte als render_design_preview.py en de
A0-printpijplijn). Met `--grid` worden ze herschaald en naar WGS84
geprojecteerd, om uit te lijnen met de .pmtiles-puntenlaag.

Gebruik:
    uv run python scripts/a0_map/generate_actor_party_contours.py \\
        data/export/plenair-map/plenair-map-full.json \\
        data/export/a0-map/
"""

import argparse
import json
import logging
from collections import Counter
from pathlib import Path

import numpy as np
from contourpy import FillType, contour_generator
from scipy.ndimage import gaussian_filter
from shapely.geometry import MultiPolygon, Polygon, mapping

from scripts.a0_map.export_clusters_geojson import flat_rescale, make_rescaler

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLDS = (1.5, 3.0)

# Zelfde alias-normalisatie als `canonicalParty()` in frontend/src/lib/parties.ts.
PARTY_ALIASSEN = {"Nieuw Sociaal Contract": "NSC", "FvD": "FVD"}

# Partijkleuren, gemeten uit de logo's in frontend/public/party-logos/simplified/
# (de kleur die de meeste pixels inneemt, zonder wit en transparant). Voor
# partijen zonder logo (GroenLinks en PvdA los, 50PLUS, BIJ1) een benadering
# van de huisstijl. Partijen die er helemaal niet in staan krijgen
# `FALLBACK_COLOR`.
PARTY_COLORS = {
    "BBB": "#93c01f",
    "CDA": "#2cc84d",
    "ChristenUnie": "#00a5e8",
    "D66": "#00ae41",
    "DENK": "#00b7b2",
    "FVD": "#a81815",
    "GroenLinks-PvdA": "#d81f27",
    "JA21": "#252b53",
    "NSC": "#171c60",
    "PRO": "#00aa00",
    "PvdD": "#00743c",
    "PVV": "#1b3962",
    "SGP": "#e95d0f",
    "SP": "#ed1c24",
    "Volt": "#502379",
    "VVD": "#ff6400",
    # Geen logo in de set:
    "GroenLinks": "#6DB33F",
    "PvdA": "#C8102E",
    "50PLUS": "#7A3E9D",
    "BIJ1": "#FFD100",
}
FALLBACK_COLOR = "#888888"

# Afwijkende kleur voor het donkere thema van de kaart (#121622). De
# logokleur van NSC en JA21 is bijna even donker als die achtergrond
# (contrast 1,0 en 1,3); hun tweede huisstijlkleur (geel, rood) valt er wel
# op. Op het lichte thema blijft de logokleur.
PARTY_COLORS_DARK = {
    "NSC": "#ffd000",
    "JA21": "#cc372a",
}


def canonical_party(party: str) -> str:
    return PARTY_ALIASSEN.get(party, party)


def party_color(party: str) -> str:
    return PARTY_COLORS.get(party, FALLBACK_COLOR)


def party_colors(party: str) -> dict:
    """`color` voor het lichte thema, plus `color_dark` als die afwijkt."""
    colors = {"color": party_color(party)}
    if party in PARTY_COLORS_DARK:
        colors["color_dark"] = PARTY_COLORS_DARK[party]
    return colors


class DensityGrid:
    """Raster met de totale dichtheid, herbruikbaar voor alle groepen."""

    def __init__(self, xy: np.ndarray, bins: int, sigma: float, floor: float):
        self.bins = bins
        self.sigma = sigma
        self.x0, self.y0 = xy.min(axis=0)
        self.x1, self.y1 = xy.max(axis=0)
        self.xs = np.linspace(self.x0, self.x1, bins)
        self.ys = np.linspace(self.y0, self.y1, bins)
        self.total = self._density(xy)
        self.floor = self.total.max() * floor

    def _density(self, pts: np.ndarray) -> np.ndarray:
        hist, _, _ = np.histogram2d(
            pts[:, 0], pts[:, 1], bins=self.bins,
            range=[[self.x0, self.x1], [self.y0, self.y1]],
        )
        smooth = gaussian_filter(hist, self.sigma)
        return smooth / smooth.sum()

    def ratio(self, pts: np.ndarray) -> np.ndarray:
        """Verhouding groepsdichtheid / totale dichtheid, 0 waar de totale
        dichtheid te laag is om iets over te zeggen. Index [ix, iy]."""
        return np.where(
            self.total > self.floor,
            self._density(pts) / np.maximum(self.total, self.floor),
            0.0,
        )


def ratio_to_polygons(grid: DensityGrid, ratio: np.ndarray, threshold: float,
                      min_cells: float = 4.0) -> list[Polygon]:
    """Gevulde gebieden waar `ratio >= threshold`, als shapely-polygonen met
    gaten. Gebieden kleiner dan `min_cells` rastercellen vervallen (ruis)."""
    gen = contour_generator(
        grid.xs, grid.ys, ratio.T, fill_type=FillType.OuterOffset,
    )
    points_list, offsets_list = gen.filled(threshold, np.inf)
    cell_area = (grid.xs[1] - grid.xs[0]) * (grid.ys[1] - grid.ys[0])
    polygons = []
    for points, offsets in zip(points_list, offsets_list):
        rings = [points[a:b] for a, b in zip(offsets[:-1], offsets[1:])]
        poly = Polygon(rings[0], holes=rings[1:])
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.area >= min_cells * cell_area:
            polygons.append(poly)
    return polygons


def round_coords(geometry: dict, rescale) -> dict:
    def convert(coords):
        if coords and isinstance(coords[0], (int, float)):
            # 5 decimalen (~1 m) i.p.v. de volle float-precisie van de
            # WGS84-projectie: houdt de web-variant klein.
            return [round(v, 5) for v in rescale(list(coords))]
        return [convert(c) for c in coords]

    return {"type": geometry["type"], "coordinates": convert(geometry["coordinates"])}


def group_features(grid: DensityGrid, pts: np.ndarray, properties: dict,
                   thresholds: tuple[float, ...], rescale) -> list[dict]:
    ratio = grid.ratio(pts)
    features = []
    for threshold in thresholds:
        polygons = ratio_to_polygons(grid, ratio, threshold)
        if not polygons:
            continue
        geom = polygons[0] if len(polygons) == 1 else MultiPolygon(polygons)
        features.append({
            "type": "Feature",
            "properties": {**properties, "threshold": threshold},
            "geometry": round_coords(mapping(geom), rescale),
        })
    return features


def build_contours(data: dict, rescale, bins: int = 400, sigma: float = 6.0,
                   floor: float = 0.02, min_points: int = 1000,
                   thresholds: tuple[float, ...] = DEFAULT_THRESHOLDS) -> tuple[dict, dict]:
    """Geeft (party_collection, actor_collection) als GeoJSON-dicts."""
    points = data["points"]
    xy = np.array([[p[1], p[2]] for p in points], dtype=float)
    actor_idx = np.array([p[4] for p in points])
    party_names = np.array([canonical_party(data["parties"][p[5]]) for p in points])
    grid = DensityGrid(xy, bins, sigma, floor)

    party_features = []
    for party, n in Counter(party_names).most_common():
        if n < min_points or party == "onbekend":
            continue
        props = {"party": party, "n": n, **party_colors(party)}
        party_features += group_features(grid, xy[party_names == party], props, thresholds, rescale)

    actor_features = []
    for idx, n in Counter(actor_idx.tolist()).most_common():
        if n < min_points:
            continue
        mask = actor_idx == idx
        main_party = Counter(party_names[mask]).most_common(1)[0][0]
        props = {
            "actor": data["actors"][idx], "party": main_party, "n": n,
            **party_colors(main_party),
        }
        actor_features += group_features(grid, xy[mask], props, thresholds, rescale)

    def collection(features):
        return {"type": "FeatureCollection", "features": features}

    return collection(party_features), collection(actor_features)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", type=Path, help="pad naar plenair-map(-<suffix>).json")
    parser.add_argument("output_dir", type=Path, help="map voor party_contours.geojson en actor_contours.geojson")
    parser.add_argument("--grid", type=Path, help="plenair-map(-<suffix>)-grid.json: herschaal naar WGS84 i.p.v. rauwe UMAP-eenheden")
    parser.add_argument("--prefix", default="", help="voorvoegsel voor de bestandsnamen (bv. plenair-map-full- voor de web-variant)")
    parser.add_argument("--bins", type=int, default=400)
    parser.add_argument("--sigma", type=float, default=6.0, help="gladstrijken in rastercellen")
    parser.add_argument("--floor", type=float, default=0.02, help="minimale totale dichtheid, als fractie van het maximum")
    parser.add_argument("--min-points", type=int, default=1000, help="minimaal aantal spreekbeurten voor een contour")
    parser.add_argument("--thresholds", type=float, nargs="+", default=list(DEFAULT_THRESHOLDS))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    data = json.loads(args.input.read_text())
    rescale = make_rescaler(json.loads(args.grid.read_text())) if args.grid else flat_rescale

    parties, actors = build_contours(
        data, rescale, args.bins, args.sigma, args.floor, args.min_points, tuple(args.thresholds),
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, collection in (("party_contours", parties), ("actor_contours", actors)):
        path = args.output_dir / f"{args.prefix}{name}.geojson"
        path.write_text(json.dumps(collection, ensure_ascii=False, separators=(",", ":")))
        logger.info("%s: %d features, %.1f MB", path, len(collection["features"]), path.stat().st_size / 1e6)


if __name__ == "__main__":
    main()
