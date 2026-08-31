"""
Snelle, lage-resolutie preview van de A0-printkaart (issue #215) voor een
designer-feedbackronde -- GEEN vervanging voor de uiteindelijke print-
kwaliteit render (die komt uit `datashader`/QGIS, zie het plan in
docs/handoff.md). Puur bedoeld om snel een visuele richting te kunnen tonen
en bijstellen ("in cycli werken"), met matplotlib (al een dependency, geen
nieuwe install nodig zoals datashader dat wel zou zijn).

Tekent de puntenwolk (kleur per topic, semi-transparant) plus alle
clusterhulls over alle niveaus heen, met lijndikte aflopend van grof (dik)
naar fijn (dun) -- de door de gebruiker gekozen visuele encodering van de
hiërarchie. Geen labels (te veel clutter op deze schaal/resolutie, dat is
onderdeel van de latere QGIS-compositie).

Gebruik:
    uv run python scripts/render_design_preview.py \
        data/export/plenair-map-full.json \
        data/export/plenair-map-clusters-full.json \
        data/export/design-handoff/plenaire-kaart-print/screenshots/preview.png
"""

import argparse
import json
import logging
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)

# Zelfde palet als frontend/src/lib/plenairMapColors.ts -- niet opnieuw
# verzinnen, consistentie met de rest van de site/kaart.
TOPIC_COLOR = {
    "stikstof": "#4a7a4a",
    "abortus": "#a64d5f",
    "asiel": "#c07a2e",
    "energietransitie": "#3d6e8f",
    "plenair": "#a89e8c",
}
DEFAULT_TOPIC_COLOR = "#a89e8c"

# Lijndikte per niveau (grofste eerst): dikker = grover, per het door de
# gebruiker gekozen ontwerp ("line thickness to represent the level").
LEVEL_LINEWIDTHS = [2.4, 1.6, 1.0, 0.6, 0.35]


def load_points(points_path: Path):
    data = json.loads(points_path.read_text())
    points = data["points"]
    topics = data["topics"]
    xs = np.array([p[1] for p in points])
    ys = np.array([p[2] for p in points])
    topic_idx = np.array([p[3] for p in points])
    return xs, ys, topic_idx, topics


def load_levels(clusters_path: Path):
    data = json.loads(clusters_path.read_text())
    if "levels" in data:
        return data["levels"]
    return [data["coarse"], data["fine"]]


def render(
    points_path: Path, clusters_path: Path, output_path: Path, fig_size: float, dpi: int,
    max_level: int | None, point_size: float, point_alpha: float,
) -> None:
    xs, ys, topic_idx, topics = load_points(points_path)
    levels = load_levels(clusters_path)
    if max_level is not None:
        levels = levels[: max_level + 1]

    fig, ax = plt.subplots(figsize=(fig_size, fig_size), dpi=dpi)
    fig.patch.set_facecolor("#f2efe7")  # --color-bg ("newsprint"), zie styling-tokens.md
    ax.set_facecolor("#f2efe7")

    # Puntenwolk EERST, ruim zichtbaar (in de eerste versie van deze preview
    # bleken s=1.2/alpha=0.22 op een 2400px-canvas de topic-kleur bijna
    # onzichtbaar te maken -- de contouren overheersten alles tot een
    # "gebarsten glas"-effect zonder dat de data zelf nog te zien was).
    for i, topic in enumerate(topics):
        mask = topic_idx == i
        if not mask.any():
            continue
        color = TOPIC_COLOR.get(topic, DEFAULT_TOPIC_COLOR)
        ax.scatter(
            xs[mask], ys[mask], s=point_size, c=color, alpha=point_alpha,
            linewidths=0, rasterized=True,
        )

    # Contouren DAARNA, dunner/transparanter dan de eerste versie, zodat de
    # punten eronder zichtbaar blijven i.p.v. overtekend te worden.
    for level_idx, clusters in enumerate(levels):
        linewidth = LEVEL_LINEWIDTHS[min(level_idx, len(LEVEL_LINEWIDTHS) - 1)]
        for cluster in clusters:
            if cluster.get("redundant_with_parent") or cluster.get("contained_by_sibling") is not None:
                continue
            hull = cluster.get("hull")
            if not hull or len(hull) < 3:
                continue
            ring = hull + [hull[0]]
            hx = [p[0] for p in ring]
            hy = [p[1] for p in ring]
            ax.plot(hx, hy, color="#221f1b", linewidth=linewidth, alpha=0.45, solid_capstyle="round")

    ax.set_aspect("equal")
    ax.axis("off")
    fig.tight_layout(pad=0)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, facecolor=fig.get_facecolor())
    logger.info("Preview geschreven naar %s", output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("points", type=str, help="pad naar plenair-map-full.json")
    parser.add_argument("clusters", type=str, help="pad naar plenair-map-clusters-full.json")
    parser.add_argument("output", type=str, help="pad voor het te schrijven PNG-bestand")
    parser.add_argument("--fig-size", type=float, default=16.0, help="figuurgrootte in inches (vierkant)")
    parser.add_argument("--dpi", type=int, default=150, help="resolutie -- laag houden, dit is een snelle preview, geen printrender")
    parser.add_argument("--max-level", type=int, default=None, help="toon alleen niveaus 0..N (default: alle niveaus)")
    parser.add_argument("--point-size", type=float, default=6.0, help="matplotlib scatter-'s' (punten^2), groter = zichtbaarder")
    parser.add_argument("--point-alpha", type=float, default=0.5, help="transparantie van de punten (0-1)")
    args = parser.parse_args()

    render(
        Path(args.points), Path(args.clusters), Path(args.output), args.fig_size, args.dpi,
        args.max_level, args.point_size, args.point_alpha,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
