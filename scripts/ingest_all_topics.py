"""
Ingest alle topics in de database in één keer, met de extra crawl-
zoektermen per topic (TOPIC_TITLE_KEYWORDS in pipeline/extract_arguments.py)
automatisch doorgegeven als --also-dir/--also-keyword -- de tegenhanger van
scripts/crawl_all_topics.py (issue #391).

Gebruik:
    uv run python scripts/ingest_all_topics.py
"""

import logging

from pipeline.db import db
from pipeline.extract_arguments import TOPIC_TITLE_KEYWORDS
from pipeline.ingest.ingest_tk import ingest

logger = logging.getLogger(__name__)


def main():
    conn = db.connect()
    slugs = [row["slug"] for row in conn.execute("SELECT slug FROM topics ORDER BY slug").fetchall()]
    if not slugs:
        logger.warning("Geen topics in de database -- niets te ingesten.")
        return

    for slug in slugs:
        # De slug zelf hoort al bij de primaire raw_dir/<slug>/ (het eerste
        # argument van ingest()); alleen de ándere zoektermen horen als
        # also-dir/also-keyword, anders zou diezelfde map twee keer gescand
        # worden (idempotent qua DB-writes, maar overbodig werk en dubbele
        # logregels).
        extra_keywords = [k for k in TOPIC_TITLE_KEYWORDS.get(slug, []) if k != slug]
        logger.info("=== topic: %s (extra zoektermen: %s) ===", slug, extra_keywords or "geen")
        ingest(slug, also_dirs=extra_keywords, also_keywords=extra_keywords)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
