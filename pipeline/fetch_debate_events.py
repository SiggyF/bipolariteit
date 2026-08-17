"""
Haalt de events-array van Debat Direct's debat-detail-API op en cachet die
op disk, per debat (documents.debatdirect_id, zie pipeline/enrich_video_url.py).
Voorbereidende stap voor het exact per-sprekerbeurt kalibreren van
arguments.start_seconds/end_seconds (zie pipeline/match_argument_spans.py,
docs/tk-data-sources-overview.md 5f) -- dat kalibreren zelf gebeurt in een
latere stap, dit script haalt alleen op.

`events[]` bevat per beurtwissel een `eventStart` (ISO8601-wandklok) en
`eventType` (bv. "speaker"/"interrupter"/"chairman") plus een `objectId`
die byte-identiek is aan de `objectid`-attribute op VLOS `<spreker>` in onze
eigen brondata (zie docs/tk-data-sources-overview.md 5f) -- dat maakt een
exact, drift-vrij anker per sprekerbeurt mogelijk, in tegenstelling tot de
WebVTT-ondertitelklok (zie pipeline/fetch_subtitles.py).

Geen Akamai-CDN-throttle nodig hier (die geldt alleen voor het `.vtt`-CDN-pad
uit fetch_subtitles.py, niet voor dit JSON-endpoint) -- kopieer die logica dus
niet naar dit script. Wel een korte, eigen sleep tussen requests uit
hoffelijkheid richting de API.

Cachet naar data/debate_events/<debatdirect_id>.json (niet ingecheckt, zie
.gitignore) en slaat een debat over waarvoor die file al bestaat -- geen
database-boekhouding nodig, het bestand zelf is de idempotentie-vlag.

Gebruik:
    uv run python -m pipeline.fetch_debate_events [--topic stikstof] [--force]
"""

import argparse
import json
import logging
import time

import requests

from pipeline.db import db
from pipeline.debatdirect_api import fetch_debate_detail
from pipeline.paths import REPO_ROOT

logger = logging.getLogger(__name__)

DEBATE_EVENTS_DIR = REPO_ROOT / "data" / "debate_events"

# Lichte hoffelijkheids-pauze tussen opeenvolgende requests -- geen bekende
# cache-bug op dit endpoint (zie moduledocstring), dus geen throttle-logica
# nodig zoals bij fetch_subtitles.py.
_SLEEP_BETWEEN_REQUESTS_SECONDS = 0.5


def fetch_pending_debates(conn, topic_id):
    """Distincte debatdirect_id's binnen dit topic."""
    rows = conn.execute(
        """SELECT DISTINCT debatdirect_id
           FROM documents
           WHERE topic_id = ? AND debatdirect_id IS NOT NULL
           ORDER BY debatdirect_id""",
        (topic_id,),
    ).fetchall()
    return [row["debatdirect_id"] for row in rows]


def fetch(topic_keyword, force=False):
    conn = db.connect()
    topic_row = conn.execute("SELECT id FROM topics WHERE slug = ?", (topic_keyword,)).fetchone()
    if topic_row is None:
        raise SystemExit(f"onbekende topic-slug: {topic_keyword}")
    try:
        _fetch_topic(conn, topic_row["id"], force=force)
    finally:
        conn.close()


def fetch_all(force=False):
    conn = db.connect()
    try:
        topic_rows = conn.execute("SELECT id, slug FROM topics ORDER BY slug").fetchall()
        for topic_row in topic_rows:
            logger.info("=== topic: %s ===", topic_row["slug"])
            _fetch_topic(conn, topic_row["id"], force=force)
    finally:
        conn.close()


def _fetch_topic(conn, topic_id, force=False):
    debates = fetch_pending_debates(conn, topic_id)
    if not debates:
        logger.info("Geen documenten met een debatdirect_id.")
        return

    DEBATE_EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    fetched, cached, failed = 0, 0, 0

    for debatdirect_id in debates:
        cache_path = DEBATE_EVENTS_DIR / f"{debatdirect_id}.json"
        if not force and cache_path.exists():
            cached += 1
            continue

        try:
            detail = fetch_debate_detail(session, debatdirect_id)
            time.sleep(_SLEEP_BETWEEN_REQUESTS_SECONDS)
        except requests.RequestException as exc:
            logger.error("Ophalen mislukt voor debat %s: %s", debatdirect_id, exc)
            failed += 1
            continue

        started_at = detail.get("startedAt")
        events = detail.get("events")
        if not started_at or events is None:
            logger.warning("Debat %s mist startedAt/events, overgeslagen.", debatdirect_id)
            failed += 1
            continue

        cache_path.write_text(json.dumps({"startedAt": started_at, "events": events}))
        fetched += 1
        logger.info("Opgeslagen: %s (%d events)", cache_path.relative_to(REPO_ROOT), len(events))

    logger.info(
        "Klaar: %d opgehaald, %d al gecached, %d mislukt (van %d debatten).",
        fetched, cached, failed, len(debates),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", help="topic-slug, bv. stikstof (default: alle topics)")
    parser.add_argument("--force", action="store_true", help="ook debatten met een bestaande cache-file opnieuw ophalen")
    args = parser.parse_args()
    if args.topic:
        fetch(args.topic, force=args.force)
    else:
        fetch_all(force=args.force)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
