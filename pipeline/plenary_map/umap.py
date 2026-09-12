"""
Stage 2a van de plenaire-kaart-pijplijn (embedden -> UMAP -> clusteren ->
labelen): UMAP op de bge-m3-embeddings van pipeline/embed/documents.py.

Host-only qua geheugengebruik op de volle dataset (NN-descent op
~768k x 1024-dim, gaf herhaaldelijk OOM in de devcontainer, ook bij 32 GB --
zie docs/handoff.md). Schrijft uitsluitend de resulterende 2D-coördinaten
weg; clustering (pipeline/plenary_map/cluster.py, --coords-path) en
LLM-naamgeving (pipeline/plenary_map/label_export.py) zijn losse,
vervolgstappen die dat coördinatenbestand inlezen i.p.v. dit opnieuw te
draaien.

Gebruik:
    uv run python -m pipeline.plenary_map.umap \
        --start 2000-01-01 --end 2026-08-30 --label full \
        --export-coords docs/poc/umap-documenten/coords-full.json
"""
import argparse
import json
import logging
import time
from pathlib import Path

from pipeline.embed.documents import fetch_and_embed
from scripts.experiment_umap_arguments import run_umap

logger = logging.getLogger(__name__)


def write_umap_coords(path: Path, rows, coords) -> None:
    """Schrijft de UMAP-uitkomst weg als platte (document-id -> [x, y])-JSON,
    voor pipeline/plenary_map/cluster.py (--coords-path) om in te lezen i.p.v.
    UMAP zelf opnieuw te draaien."""
    data = {str(row["id"]): [round(float(x), 4), round(float(y), 4)] for row, (x, y) in zip(rows, coords)}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", required=True, help="published_at ondergrens, ISO-datum (inclusief)")
    parser.add_argument("--end", required=True, help="published_at bovengrens, ISO-datum (exclusief)")
    parser.add_argument("--label", required=True, help="korte periode-naam, zelfde als de embed-cache (pipeline/embed/documents.py)")
    parser.add_argument("--min-content-len", type=int, default=30)
    parser.add_argument(
        "--base-url", default=None,
        help="alleen gebruikt als de embeddingscache nog missende ids heeft, zie pipeline/embed/documents.py",
    )
    parser.add_argument("--refresh", action="store_true", help="embeddingscache negeren en herberekenen")
    parser.add_argument("--export-coords", required=True, help="pad om de UMAP-coördinaten naar weg te schrijven")
    args = parser.parse_args()

    rows, texts, vectors, embed_elapsed = fetch_and_embed(
        args.start, args.end, args.min_content_len, args.label,
        base_url=args.base_url, refresh=args.refresh,
    )
    logger.info("%d documenten tussen %s en %s", len(texts), args.start, args.end)

    t0 = time.monotonic()
    coords = run_umap(vectors)
    umap_elapsed = time.monotonic() - t0
    logger.info("UMAP in %.1fs", umap_elapsed)

    write_umap_coords(Path(args.export_coords), rows, coords)
    logger.info("UMAP-coördinaten geschreven naar %s", args.export_coords)

    if embed_elapsed is not None:
        logger.info(
            "timing: embeddings %.1fs, UMAP %.1fs, totaal %.1fs",
            embed_elapsed, umap_elapsed, embed_elapsed + umap_elapsed,
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
