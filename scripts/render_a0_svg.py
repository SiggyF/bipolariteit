"""
SVG-export van de puntenwolk voor Illustrator-afwerking (issue #215),
alternatief renderpad naast `render_a0_datashader.py`: elk punt wordt een
los SVG-element i.p.v. een pixel-raster. Overlap-verdonkering (dichtheid)
en antialiasing lopen zo via Illustrators eigen blend-modes/renderer i.p.v.
via een handmatige eq_hist-kleurladder -- en omzeilt daarmee het
banding-probleem dat datashader gaf bij deze relatief lage punt-per-pixel-
dichtheid (zie het overleg in docs/handoff.md).

Volgt dezelfde 5 datashader-pipelinestappen, maar zonder rasterbinning:
- **Projection**: UMAP x/y -> SVG-coördinaten in mm, aspect behouden,
  geschaald naar echte A0-afmetingen zodat Illustrator het bestand op ware
  grootte opent.
- **Aggregation**: geen grid-binning -- in plaats daarvan een LOKALE
  dichtheidsschatting per punt (gemiddelde afstand tot de `k` dichtstbijzijnde
  buren, `scipy.spatial.cKDTree`), het per-punt-equivalent van datashader's
  per-pixel-telling.
- **Transformation**: lokale dichtheid -> puntstraal, OMGEKEERD (kleinere
  buurafstand/dichter = kleinere straal, voorkomt dat dichte clusters één
  vlek worden; grotere buurafstand/ijler = grotere straal, zodat losse
  punten zichtbaar blijven) -- rechtstreeks antwoord op "geen enorme punten
  willen maken".
- **Colormapping**: nog vast (één kleur voor de "alles"-laag; topic-kleuren
  volgen later, net als bij render_a0_datashader.py).
- **Embedding**: SVG <circle>-elementen (gedeelde `fill`/`opacity` op de
  omvattende <g>, om bestandsgrootte en Illustrator-laagcomplexiteit te
  beperken bij 135k elementen).

Gebruik (klein itereren):
    uv run python scripts/render_a0_svg.py \
        data/export/plenair-map-full.json \
        data/export/a0-map/a0-alles.svg
"""

import argparse
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

logger = logging.getLogger(__name__)

# A0 in mm.
A0_WIDTH_MM = 841
A0_HEIGHT_MM = 1189

FILL_COLOR = "#1b1b1b"  # zelfde donkerste tint als de datashader-CET_L2-ladder
FILL_OPACITY = 0.15  # laag houden: bij multiply-blend verdondert elke extra overlap alsnog, dus dit bepaalt hoeveel overlappende lagen nodig zijn vóór verzadiging naar zwart


def load_points(points_path: Path) -> pd.DataFrame:
    raw = json.loads(points_path.read_text())
    points = raw["points"]
    df = pd.DataFrame({"x": [p[1] for p in points], "y": [p[2] for p in points]})
    logger.info("%d punten geladen", len(df))
    return df


def local_density_radius(xy: np.ndarray, k: int, r_min_mm: float, r_max_mm: float) -> np.ndarray:
    """Aggregation- + Transformation-stap ineen: gemiddelde afstand tot de
    `k` dichtstbijzijnde buren (Aggregation, lokaal i.p.v. grid-gebonden),
    dan lineair herschaald naar [r_min_mm, r_max_mm] en OMGEKEERD (kleine
    buurafstand -> kleine straal) (Transformation).
    """
    tree = cKDTree(xy)
    dist, _ = tree.query(xy, k=k + 1)  # k=0 is het punt zelf (afstand 0)
    mean_neighbor_dist = dist[:, 1:].mean(axis=1)

    lo, hi = np.percentile(mean_neighbor_dist, [1, 99])  # buiten de 1e/99e percentiel afkappen tegen uitschieters
    clipped = np.clip(mean_neighbor_dist, lo, hi)
    fraction = (clipped - lo) / (hi - lo)
    return r_min_mm + fraction * (r_max_mm - r_min_mm)


def render(points_path: Path, output_path: Path, scale: float, k: int, r_min_mm: float, r_max_mm: float) -> None:
    df = load_points(points_path)
    xy = df[["x", "y"]].values

    x_range = (xy[:, 0].min(), xy[:, 0].max())
    y_range = (xy[:, 1].min(), xy[:, 1].max())
    data_width = x_range[1] - x_range[0]
    data_height = y_range[1] - y_range[0]

    # Projection: fit binnen het A0-mm-frame op de gekozen schaal, aspect behouden.
    mm_per_unit = min(A0_WIDTH_MM * scale / data_width, A0_HEIGHT_MM * scale / data_height)
    canvas_width_mm = data_width * mm_per_unit
    canvas_height_mm = data_height * mm_per_unit
    logger.info("Canvas: %.1fx%.1fmm (scale=%.3f)", canvas_width_mm, canvas_height_mm, scale)

    radius_mm = local_density_radius(xy, k=k, r_min_mm=r_min_mm, r_max_mm=r_max_mm)
    logger.info("Puntstraal: min=%.3fmm max=%.3fmm gem=%.3fmm", radius_mm.min(), radius_mm.max(), radius_mm.mean())

    # SVG-y loopt omlaag, data-y omhoog -- spiegelen zodat de kaart niet ondersteboven staat.
    svg_x = (xy[:, 0] - x_range[0]) * mm_per_unit
    svg_y = (y_range[1] - xy[:, 1]) * mm_per_unit

    circles = "\n".join(
        f'<circle cx="{cx:.3f}" cy="{cy:.3f}" r="{r:.3f}"/>'
        for cx, cy, r in zip(svg_x, svg_y, radius_mm)
    )
    # mix-blend-mode:multiply i.p.v. alleen fill-opacity (source-over):
    # source-over verzadigt snel (1-(1-a)^n -> 1 al bij een handvol overlap),
    # dus alles voorbij een paar overlappende cirkels oogt even donker --
    # exact het "vlakke grijs"-probleem dat ook eq_hist gaf. Multiply
    # verdondert geleidelijker en continu met het echte aantal overlappende
    # lagen, dichter bij hoe inkt/verf zich gedraagt -- standaard SVG/CSS,
    # Illustrator ondersteunt dit native.
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_width_mm:.1f}mm" height="{canvas_height_mm:.1f}mm" '
        f'viewBox="0 0 {canvas_width_mm:.1f} {canvas_height_mm:.1f}">\n'
        f'<g fill="{FILL_COLOR}" fill-opacity="{FILL_OPACITY}" style="mix-blend-mode:multiply">\n{circles}\n</g>\n</svg>\n'
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(svg)
    logger.info("Geschreven: %s (%d punten, %.1f MiB)", output_path, len(df), output_path.stat().st_size / 1024 / 1024)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("points", type=str, help="pad naar plenair-map-full.json")
    parser.add_argument("output", type=str, help="pad voor het te schrijven SVG-bestand")
    parser.add_argument("--scale", type=float, default=0.15, help="fractie van de volle A0-afmetingen (default: 0.15)")
    parser.add_argument("--k", type=int, default=5, help="aantal buren voor de lokale dichtheidsschatting (default: 5)")
    parser.add_argument("--r-min", type=float, default=0.15, help="minimale puntstraal in mm (default: 0.15)")
    parser.add_argument("--r-max", type=float, default=1.2, help="maximale puntstraal in mm (default: 1.2)")
    args = parser.parse_args()
    render(Path(args.points), Path(args.output), args.scale, args.k, args.r_min, args.r_max)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
