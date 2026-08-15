"""
Beantwoordt de openstaande vraag in issue #108 ("is de kalibratie-drift van
1 debat of van meerdere?") door de kalibratie-spreiding (zie `match_debate()`
in pipeline/match_argument_spans.py) voor élk gecached debat te berekenen,
niet alleen voor een steekproef zoals PR #114 ad-hoc deed.

Puur leesoperatie: geen netwerktoegang, geen schrijfacties naar de database.
Hergebruikt de matching/kalibratie-logica uit match_argument_spans.py zodat
dit script nooit uit de pas kan lopen met wat de productie-pipeline doet.

Gebruik:
    uv run python -m scripts.audit_calibration_spread [--threshold 800] [--top 20]
"""

import argparse
import logging
import statistics

from pipeline.db import db
from pipeline.fetch_subtitles import SUBTITLES_DIR
from pipeline.match_argument_spans import (
    MIN_MATCHES_FOR_CALIBRATION,
    _expected_offset_seconds,
    build_running_index,
    find_quote_span,
    parse_vtt,
)

logger = logging.getLogger(__name__)


def fetch_debates(conn):
    """Eén rij per debatdirect_id met een titel/datum voor leesbare output."""
    return conn.execute(
        """SELECT d.debatdirect_id, t.slug AS topic_slug, MIN(d.activiteit_aanvangstijd) AS aanvang
           FROM documents d JOIN topics t ON t.id = d.topic_id
           WHERE d.debatdirect_id IS NOT NULL
           GROUP BY d.debatdirect_id, t.slug
           ORDER BY d.debatdirect_id"""
    ).fetchall()


def fetch_arguments(conn, debatdirect_id):
    return conn.execute(
        """SELECT ar.quote_text, d.published_at, d.activiteit_aanvangstijd
           FROM arguments ar JOIN documents d ON d.id = ar.document_id
           WHERE d.debatdirect_id = ?""",
        (debatdirect_id,),
    ).fetchall()


def calibration_spread(cues, rows):
    """Spreiding (max-min) van de per-beurt kalibratiepunten, of None als er
    te weinig gematchte quotes zijn om iets over te zeggen (zelfde drempel
    als match_debate())."""
    running_text, cue_end_offsets = build_running_index(cues)

    samples = []
    for row in rows:
        span = find_quote_span(row["quote_text"], running_text, cue_end_offsets, cues)
        if span is None:
            continue
        expected = _expected_offset_seconds(row["published_at"], row["activiteit_aanvangstijd"])
        if expected is not None:
            samples.append(span[0] - expected)

    if len(samples) < MIN_MATCHES_FOR_CALIBRATION:
        return None, len(samples)
    return max(samples) - min(samples), len(samples)


def audit(conn):
    results = []
    debates = fetch_debates(conn)
    no_cache = 0
    too_few_matches = 0
    for debate in debates:
        cache_path = SUBTITLES_DIR / f"{debate['debatdirect_id']}.vtt"
        if not cache_path.exists():
            no_cache += 1
            continue

        cues = parse_vtt(cache_path.read_text())
        rows = fetch_arguments(conn, debate["debatdirect_id"])
        spread, n_matches = calibration_spread(cues, rows)
        if spread is None:
            too_few_matches += 1
            continue

        results.append(
            {
                "debatdirect_id": debate["debatdirect_id"],
                "topic_slug": debate["topic_slug"],
                "aanvang": debate["aanvang"],
                "spread": spread,
                "n_matches": n_matches,
            }
        )

    results.sort(key=lambda r: r["spread"], reverse=True)
    return results, no_cache, too_few_matches


def print_report(results, no_cache, too_few_matches, threshold, top):
    spreads = [r["spread"] for r in results]
    logger.info(
        "%d debatten met kalibreerbare spreiding, %d zonder ondertitel-cache overgeslagen, "
        "%d met te weinig matches (< %d) overgeslagen.",
        len(results), no_cache, too_few_matches, MIN_MATCHES_FOR_CALIBRATION,
    )
    if spreads:
        logger.info(
            "Spreiding: mediaan %.0fs, gemiddeld %.0fs, max %.0fs.",
            statistics.median(spreads), statistics.mean(spreads), max(spreads),
        )

    flagged = [r for r in results if r["spread"] > threshold]
    logger.info("")
    logger.info("=== %d debatten boven de %ds-drempel ===", len(flagged), threshold)
    for r in flagged:
        logger.info(
            "  %s  topic=%-12s aanvang=%s  spread=%.0fs  (%d matches)",
            r["debatdirect_id"], r["topic_slug"], r["aanvang"], r["spread"], r["n_matches"],
        )

    logger.info("")
    logger.info("=== top %d ongeacht drempel ===", top)
    for r in results[:top]:
        logger.info(
            "  %s  topic=%-12s aanvang=%s  spread=%.0fs  (%d matches)",
            r["debatdirect_id"], r["topic_slug"], r["aanvang"], r["spread"], r["n_matches"],
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--threshold", type=float, default=800, help="drempel in seconden (default: 800, zie #114)")
    parser.add_argument("--top", type=int, default=20, help="aantal debatten in de top-lijst (default: 20)")
    args = parser.parse_args()

    conn = db.connect()
    try:
        results, no_cache, too_few_matches = audit(conn)
    finally:
        conn.close()

    print_report(results, no_cache, too_few_matches, args.threshold, args.top)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
