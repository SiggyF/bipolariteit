"""
Eenmalige backfill: vult documents.text_stats voor rijen die al vóór deze
kolom bestonden zijn geïmporteerd (issue #155). Alleen rijen met
text_stats IS NULL worden bijgewerkt, dus een her-run is goedkoop/
idempotent. Zelfde sprekerbeurt-filter als pipeline/extract_arguments.py en
scripts/experiment_verbositeit.py's fetch_documenten: geen voorzitterbeurten,
wel een actor, wel content.

Gebruik:
    uv run python scripts/backfill_document_tekststatistieken.py [--dry-run] [--batch-size 500]
"""

import argparse
import json
import logging

from pipeline.db import db
from pipeline.text_stats import compute_document_stats

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

_FILTER = """
    text_stats IS NULL
    AND is_voorzitter_turn = 0
    AND actor_id IS NOT NULL
    AND content IS NOT NULL AND length(content) > 0
"""


def fetch_pending(conn, batch_size):
    return conn.execute(
        f"SELECT id, content FROM documents WHERE {_FILTER} LIMIT ?",
        (batch_size,),
    ).fetchall()


def backfill(dry_run=False, batch_size=500):
    conn = db.connect(db.DEFAULT_DB_PATH)
    try:
        if dry_run:
            (kandidaten,) = conn.execute(f"SELECT COUNT(*) FROM documents WHERE {_FILTER}").fetchone()
            logger.info("Dry-run: %d documenten zouden bijgewerkt worden.", kandidaten)
            return

        total = 0
        while True:
            rows = fetch_pending(conn, batch_size)
            if not rows:
                break
            for row in rows:
                stats = compute_document_stats(row["content"])
                conn.execute(
                    "UPDATE documents SET text_stats = ? WHERE id = ?",
                    (json.dumps(stats), row["id"]),
                )
                total += 1
            conn.commit()
            logger.info("Batch verwerkt, cumulatief %d documenten.", total)
        logger.info("Klaar: %d documenten bijgewerkt.", total)
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()
    backfill(dry_run=args.dry_run, batch_size=args.batch_size)
