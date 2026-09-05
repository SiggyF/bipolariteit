"""
Print-kwaliteit puntenwolk-rasterrender voor de A0-printposter (issue #215),
op basis van `data/export/a0-map/maps/plenair-map-full.json`.

Basisversie: alleen de "alles"-laag (alle punten, alle topics samen), met
een kant-en-klare colorcet-colormap (`cc.fire`) en datashader's eigen
standaardpad (`tf.shade(cvs.points(...), how="eq_hist")`). Geen eigen
spreid-/kleurladder-functies.

Gebruik (klein itereren, standaard ~1/6 A0):
    uv run python scripts/a0_map/render_a0_datashader.py \
        data/export/a0-map/maps/plenair-map-full.json \
        data/export/a0-map/a0-alles.png
"""

import argparse
import json
import logging
from pathlib import Path

import colorcet as cc
import datashader as ds
import datashader.transfer_functions as tf
import pandas as pd

logger = logging.getLogger(__name__)

# A0 bij 300dpi: 841x1189mm -> inch -> px.
A0_WIDTH_PX = round(841 / 25.4 * 300)
A0_HEIGHT_PX = round(1189 / 25.4 * 300)


def load_points(points_path: Path) -> pd.DataFrame:
    raw = json.loads(points_path.read_text())
    points = raw["points"]
    df = pd.DataFrame({"x": [p[1] for p in points], "y": [p[2] for p in points]})
    logger.info("%d punten geladen", len(df))
    return df


def render(points_path: Path, output_path: Path, scale: float) -> None:
    df = load_points(points_path)

    x_range = (df["x"].min(), df["x"].max())
    y_range = (df["y"].min(), df["y"].max())
    data_width = x_range[1] - x_range[0]
    data_height = y_range[1] - y_range[0]

    # Aspect ratio van de data behouden (geen A0-portrait-vervorming) --
    # fit binnen het A0-frame op de gekozen schaal.
    px_per_unit = min(A0_WIDTH_PX * scale / data_width, A0_HEIGHT_PX * scale / data_height)
    plot_width = max(1, round(data_width * px_per_unit))
    plot_height = max(1, round(data_height * px_per_unit))
    logger.info("Canvas: %dx%d px (scale=%.3f)", plot_width, plot_height, scale)

    cvs = ds.Canvas(plot_width=plot_width, plot_height=plot_height, x_range=x_range, y_range=y_range)
    agg = cvs.points(df, "x", "y", agg=ds.count())
    # tf.spread (niet dynspread, zie eerder overleg: dynspread's dichtheids-
    # heuristiek triggert hier niet) op de RUWE telling, vóór het shaden --
    # how=None resolveert naar "add" voor een niet-Image DataArray, dus
    # overlappende punt-footprints tellen op i.p.v. alleen te dilateren.
    agg = tf.spread(agg, px=1)
    # CET_L2 gaat van donker (lage waarde) naar licht (hoge waarde) -- omgekeerd,
    # zodat laag=wit, hoog=zwart.
    img = tf.shade(agg, cmap=list(reversed(cc.CET_L2)), how="eq_hist")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.to_pil().save(output_path)
    logger.info("Geschreven: %s", output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("points", type=str, help="pad naar plenair-map-full.json")
    parser.add_argument("output", type=str, help="pad voor het te schrijven PNG-bestand")
    parser.add_argument("--scale", type=float, default=0.15, help="fractie van de volle A0/300dpi-resolutie (default: 0.15)")
    args = parser.parse_args()
    render(Path(args.points), Path(args.output), args.scale)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
