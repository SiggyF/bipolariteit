"""
Crawlt alle topics in de database in één keer, inclusief de extra crawl-
zoektermen per topic (TOPIC_TITLE_KEYWORDS in pipeline/extract_arguments.py)
-- de tegenhanger van extract/tag's "zonder TOPIC: alle topics" (issue #391)
voor de crawl-stap. Een topic zonder entry in TOPIC_TITLE_KEYWORDS wordt
gewoon op z'n eigen slug gecrawld (zoals nu al het geval is voor bv.
stikstof/abortus/oekraine); een topic MET entry (asiel, energietransitie)
wordt op elk van die zoektermen apart gecrawld, net als een handmatige
`make crawl TOPIC=<zoekterm>` per term.

Zonder --soort over DEFAULT_SOORTEN heen (i.p.v. alleen "Plenair debat
(debat)", de Makefile-default): recente politieke activiteit zit vaak in
een Tweeminutendebat of Commissiedebat, niet in een losstaand hoofddebat --
bv. "Tweeminutendebat JBZ-Raad (Vreemdelingen- en asielbeleid)" (Soort
"Plenair debat (tweeminutendebat)") en "Energie voor huishoudens" (Soort
"Commissiedebat") kwamen allebei niet mee met alleen de oude default.
Handmatig al zo gedaan voor asiel (vijf debatsoorten, zie docs/handoff.md);
dit generaliseert dat naar alle topics/zoektermen -- als één gecombineerd
`Soort eq 'a' or Soort eq 'b' or ...`-filter (odata.activiteiten_url), dus
nog steeds één scrapy-run per zoekterm, niet één per (zoekterm, soort).

Elke zoekterm is een losse scrapy-run (zelfde subprocess als het `crawl`
Makefile-target), dus een falende zoekterm stopt niet de hele batch.

Gebruik:
    uv run python scripts/crawl_all_topics.py --limit 15
"""

import argparse
import logging
import subprocess
from pathlib import Path

from pipeline.db import db
from pipeline.extract_arguments import TOPIC_TITLE_KEYWORDS

logger = logging.getLogger(__name__)

CRAWLER_DIR = Path(__file__).parent.parent / "crawlers" / "tweede_kamer"

# Zelfde vijf debatsoorten als eerder handmatig gebruikt voor asiel (docs/
# handoff.md, 2026-08-04-sessie): "Plenair debat (debat)" alleen mist het
# merendeel van de actuele activiteit, die vaak als tweeminutendebat/
# commissiedebat/wetgevingsoverleg op de agenda staat i.p.v. een losstaand
# hoofddebat.
DEFAULT_SOORTEN = (
    "Plenair debat (debat)",
    "Plenair debat (wetgeving)",
    "Plenair debat (tweeminutendebat)",
    "Commissiedebat",
    "Wetgevingsoverleg",
)


def crawl_keywords_for_slug(slug):
    return TOPIC_TITLE_KEYWORDS.get(slug, [slug])


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument(
        "--soort", default=None,
        help="beperkt tot precies dit Activiteit.Soort i.p.v. de DEFAULT_SOORTEN-lijst",
    )
    args = parser.parse_args()
    soorten = [args.soort] if args.soort else list(DEFAULT_SOORTEN)
    soort_arg = ",".join(soorten)

    conn = db.connect()
    slugs = [row["slug"] for row in conn.execute("SELECT slug FROM topics ORDER BY slug").fetchall()]
    if not slugs:
        logger.warning("Geen topics in de database -- niets te crawlen.")
        return

    # Dedupliceren -- twee topics zouden in theorie dezelfde zoekterm kunnen
    # registreren, en die zou dan anders dubbel gecrawld worden.
    seen = set()
    for slug in slugs:
        for keyword in crawl_keywords_for_slug(slug):
            if keyword in seen:
                continue
            seen.add(keyword)
            logger.info("=== crawl: topic=%s keyword=%s soorten=%s ===", slug, keyword, soort_arg)
            subprocess.run(
                [
                    "uv", "run", "scrapy", "crawl", "verslagen",
                    "-a", f"topic={keyword}", "-a", f"limit={args.limit}", "-a", f"soort={soort_arg}",
                ],
                cwd=CRAWLER_DIR, check=True,
            )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
