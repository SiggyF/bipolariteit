"""
Stage 2a van de plenaire-kaart-pijplijn (embedden -> UMAP -> clusteren ->
labelen): UMAP op de bge-m3-embeddings van pipeline/embed/documents.py.

Host-only qua geheugengebruik op de volle dataset (NN-descent op
~768k x 1024-dim, gaf herhaaldelijk OOM in de devcontainer, ook bij 32 GB --
zie docs/handoff.md). Schrijft de resulterende 2D-coördinaten weg;
clustering (pipeline/plenary_map/cluster.py, --coords-path) en LLM-naamgeving
(pipeline/plenary_map/label_export.py) zijn losse, vervolgstappen die dat
coördinatenbestand inlezen i.p.v. dit opnieuw te draaien.

Schrijft optioneel (--export-reducer) de gefitte UMAP-reducer zelf weg
(joblib, compress=3 -- ook gecomprimeerd nog altijd GiB's op de volle
dataset, want de reducer pickelt zijn eigen kopie van de ~768k x 1024
trainingsvectoren mee). run_umap gebruikt een vaste random_state, dus de fit
is reproduceerbaar -- maar zonder de reducer op te slaan is er geen manier om
lósse, nieuwe punten (bv. individuele argument-embeddings) in dezelfde
2D-ruimte te plaatsen als de gepubliceerde coördinaten, anders dan de hele
fit opnieuw te draaien. Met de opgeslagen reducer kan dat met
reducer.transform(nieuwe_vectoren) (nieuwe punten in de bestaande ruimte) en
bij benadering ook andersom met reducer.inverse_transform(coords) (2D-punt
terug naar een schatting van de 1024-dim embeddingruimte).

Vanwege die omvang is dit geen standaard-lokaal bestand: `make tiles-full`
neemt 'm mee de Zenodo/Hugging Face-bundel in (data/export/plenair-map/
bundel/, zie make publish-zenodo), net als de overige -full-varianten --
lokaal alleen aanmaken/downloaden wanneer reducer.transform()/
.inverse_transform() ook echt nodig is, niet routinematig bij elke
`make umap`.

Gebruik:
    uv run python -m pipeline.plenary_map.umap \
        --start 2000-01-01 --end 2026-08-30 --label full \
        --export-coords data/plenair-map/coords-full.json \
        --export-reducer data/plenair-map/umap-reducer-full.joblib
"""
import argparse
import json
import logging
import time
from pathlib import Path

import joblib

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
    parser.add_argument(
        "--export-reducer", default=None,
        help="pad om de gefitte UMAP-reducer naar weg te schrijven (joblib), voor "
        "reducer.transform() op latere, losse punten (bv. argument-embeddings) in "
        "dezelfde ruimte, en bij benadering reducer.inverse_transform() terug. Optioneel.",
    )
    parser.add_argument("--seed", type=int, default=42, help="random_state voor UMAP, zelfde default als run_umap")
    args = parser.parse_args()

    rows, texts, vectors, embed_elapsed = fetch_and_embed(
        args.start, args.end, args.min_content_len, args.label,
        base_url=args.base_url, refresh=args.refresh,
    )
    logger.info("%d documenten tussen %s en %s", len(texts), args.start, args.end)

    t0 = time.monotonic()
    coords, reducer = run_umap(vectors, seed=args.seed, return_reducer=True)
    umap_elapsed = time.monotonic() - t0
    logger.info("UMAP in %.1fs", umap_elapsed)

    write_umap_coords(Path(args.export_coords), rows, coords)
    logger.info("UMAP-coördinaten geschreven naar %s", args.export_coords)

    if args.export_reducer:
        reducer_path = Path(args.export_reducer)
        reducer_path.parent.mkdir(parents=True, exist_ok=True)
        # compress=3: joblib's zlib-compressie op de gepickelde reducer (o.a.
        # de meegepickelde ~768k x 1024 trainingsvectoren) -- dichte
        # float-arrays comprimeren niet spectaculair, maar schroeft een
        # ongecomprimeerde dump van 10+ GiB wel terug naar een werkbare
        # omvang. Geen refit nodig om dit te testen/aan te passen, zie
        # scripts/recompress_umap_reducer.py.
        joblib.dump(reducer, reducer_path, compress=3)
        logger.info("UMAP-reducer geschreven naar %s", reducer_path)

    if embed_elapsed is not None:
        logger.info(
            "timing: embeddings %.1fs, UMAP %.1fs, totaal %.1fs",
            embed_elapsed, umap_elapsed, embed_elapsed + umap_elapsed,
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
