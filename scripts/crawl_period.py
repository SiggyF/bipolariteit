"""
Haalt de topic-onafhankelijke verslagen op (alle plenaire en commissiedebatten,
zonder trefwoordfilter) en vult daarmee bij wat nog mist (issue #270). Dit
is het eerste deel van `make crawl`; de per-topic-trefwoordcrawl
(scripts/crawl_all_topics.py) volgt daarna.

Zonder --start bepaalt het script zelf vanaf waar er iets ontbreekt: de
laatste datum die al uit de betreffende map in de database staat, min een
overlap (OVERLAP_DAYS), tot en met vandaag. Plenair en Commissie hebben elk
hun eigen map en dus hun eigen startdatum. Opnieuw ophalen is veilig: de
ruwe bestanden heten naar verslag_id (overschrijven, niet dubbelen) en de
ingest slaat bestaande sprekerbeurten over.

Gebruik:
    uv run python scripts/crawl_period.py
    uv run python scripts/crawl_period.py --start 2026-09-15 --end 2026-09-19
"""

import argparse
import logging
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path

from pipeline.db import db

logger = logging.getLogger(__name__)

CRAWLER_DIR = Path(__file__).parent.parent / "crawlers" / "tweede_kamer"

# (soort voor verslagen_periode, map onder data/raw/tweede_kamer/). Dezelfde
# vaste mappen als de eerdere handmatige crawls van 2025 tot heden.
PERIOD_DIRS = (
    ("Plenair", "_plenair_2025-heden"),
    ("Commissie", "_commissie_2025-heden"),
)

# Verslagen worden soms achteraf aangevuld of gecorrigeerd; een week
# overlap vangt dat op, en omdat ophalen idempotent is kost het alleen tijd.
OVERLAP_DAYS = 7


def latest_ingested_date(conn, dir_name):
    """Laatste published_at-datum van de documenten uit deze map, of None."""
    row = conn.execute(
        "SELECT MAX(substr(published_at, 1, 10)) FROM documents WHERE raw_ref LIKE ?",
        (f"{dir_name}/%",),
    ).fetchone()
    return row[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", help="ISO-datum; default: laatste ingeste datum per map min OVERLAP_DAYS")
    parser.add_argument("--end", help="ISO-datum; default: vandaag")
    args = parser.parse_args()
    end = args.end or date.today().isoformat()

    conn = db.connect()
    try:
        for soort, dir_name in PERIOD_DIRS:
            start = args.start
            if start is None:
                latest = latest_ingested_date(conn, dir_name)
                if latest is None:
                    parser.error(f"{dir_name} staat nog niet in de database; geef --start op")
                start = (datetime.fromisoformat(latest) - timedelta(days=OVERLAP_DAYS)).date().isoformat()
            logger.info("=== crawl periode: %s %s t/m %s -> %s ===", soort, start, end, dir_name)
            subprocess.run(
                [
                    "uv", "run", "scrapy", "crawl", "verslagen_periode",
                    "-a", f"start={start}", "-a", f"end={end}",
                    "-a", f"soort={soort}", "-a", f"topic_keyword={dir_name}",
                ],
                cwd=CRAWLER_DIR, check=True,
            )
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
