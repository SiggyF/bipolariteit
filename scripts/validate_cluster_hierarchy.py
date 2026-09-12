"""
Topologische validatie van een N-laagse `plenair-map-clusters*.json`
(zie `pipeline/plenary_map/cluster.py`'s `label_multilevel_clusters()`).

Twee regels, beide bedoeld om de "hoofdtak overheerst het hele niveau"-bug
te detecteren die live in QGIS zichtbaar werd (zie ook build_multilevel_clusters'
docstring): een niveau waarop alle massa in één ongesplitste cluster blijft
hangen, is in feite geen zinvolle subdivisie van dat niveau.

1. Containment (DE-9IM via shapely's .contains(), zelf een DE-9IM-predicaat):
   geen twee clusters op HETZELFDE niveau mogen elkaar volledig bevatten --
   clusters op een niveau horen een partitie te zijn (grotendeels
   disjunct/naast elkaar), niet genest in elkaar. Nesting hoort alleen
   tussen niveaus (ouder/kind) voor te komen, niet binnen een niveau.
2. Dominantie: het grootste cluster op een niveau mag niet meer dan
   `--max-area-ratio` (default 0.5) van de totale hull-oppervlakte van dat
   niveau innemen -- een goede indicatie dat een niveau niet gewoon "1
   hoofdtak + een paar losse afsplitsingen" is.

Gebruik:
    uv run python scripts/validate_cluster_hierarchy.py \
        data/export/plenair-map-clusters-full.json
"""

import argparse
import json
import logging
from pathlib import Path

from shapely.geometry import Polygon

logger = logging.getLogger(__name__)


def load_levels(clusters_data: dict) -> list[list[dict]]:
    if "levels" in clusters_data:
        return clusters_data["levels"]
    return [clusters_data["coarse"], clusters_data["fine"]]


def cluster_polygon(cluster: dict) -> Polygon | None:
    hull = cluster.get("hull")
    if not hull or len(hull) < 3:
        return None
    poly = Polygon(hull)
    return poly if poly.is_valid else poly.buffer(0)


def validate_level(level_idx: int, clusters: list[dict], max_area_ratio: float) -> list[str]:
    problems = []
    polygons = {}
    for cluster in clusters:
        poly = cluster_polygon(cluster)
        if poly is not None and not poly.is_empty:
            polygons[cluster["cluster_id"]] = (poly, cluster["name"], cluster["size"])

    ids = list(polygons.keys())
    for i, id_a in enumerate(ids):
        poly_a, name_a, _ = polygons[id_a]
        for id_b in ids[i + 1:]:
            poly_b, name_b, _ = polygons[id_b]
            if poly_a.contains(poly_b) or poly_b.contains(poly_a):
                bigger, smaller = (name_a, name_b) if poly_a.contains(poly_b) else (name_b, name_a)
                problems.append(
                    f"niveau {level_idx}: '{bigger}' bevat volledig '{smaller}' "
                    f"(zelfde niveau -- clusters horen een partitie te zijn, niet genest)"
                )

    if polygons:
        areas = {cid: poly.area for cid, (poly, _, _) in polygons.items()}
        total_area = sum(areas.values())
        max_id = max(areas, key=areas.get)
        ratio = areas[max_id] / total_area if total_area > 0 else 0.0
        if ratio > max_area_ratio:
            _, max_name, max_size = polygons[max_id]
            problems.append(
                f"niveau {level_idx}: '{max_name}' (n={max_size}) beslaat {ratio:.0%} van de "
                f"totale hull-oppervlakte op dit niveau (grens: {max_area_ratio:.0%}) -- "
                f"waarschijnlijk een ongesplitste hoofdtak i.p.v. een echte subdivisie"
            )

    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", type=str, help="pad naar plenair-map-clusters(-<suffix>).json")
    parser.add_argument("--max-area-ratio", type=float, default=0.5, help="max. aandeel van het grootste cluster in de totale hull-oppervlakte per niveau")
    args = parser.parse_args()

    clusters_data = json.loads(Path(args.input).read_text())
    levels = load_levels(clusters_data)

    all_problems = []
    for level_idx, clusters in enumerate(levels):
        all_problems.extend(validate_level(level_idx, clusters, args.max_area_ratio))

    if all_problems:
        logger.warning("%d topologie-problemen gevonden:", len(all_problems))
        for problem in all_problems:
            logger.warning("  - %s", problem)
        raise SystemExit(1)

    logger.info("Geen topologie-problemen gevonden over %d niveaus.", len(levels))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
