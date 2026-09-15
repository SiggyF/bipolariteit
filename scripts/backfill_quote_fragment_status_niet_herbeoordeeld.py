"""
Eenmalige backfill: markeert bestaande `argument_tags`-rijen die vóór de
`niet_herbeoordeeld`-status bestonden expliciet als zodanig, i.p.v. ze voor
altijd op `quote_fragment_status IS NULL` te laten staan.

Aanleiding: `--backfill-quote-fragment` (pipeline/tag_arguments.py) zet
quote_fragment_status alleen op de (argument_id, tag_sleutel)-paren die het
LLM-antwoord ook echt weer voorstelt. Een pre-bestaande llm-tag die een
eerdere --backfill-quote-fragment-run niet opnieuw voorstelde (bv. het model
koos een andere sleutel binnen dezelfde labelgroep) bleef daardoor voor
altijd `quote_fragment_status IS NULL` -- ononderscheidbaar van een tag die
nooit door enige quote_fragment-bewuste pass is aangeraakt, en dus voor
altijd een (nooit-convergerende) kandidaat voor een volgende
--backfill-quote-fragment-aanroep.

Nieuwe reprocessing-runs zetten dit voortaan zelf (main()'s process_result()
markeert na elke geslaagde --backfill-quote-fragment-aanroep alle resterende
onopgeloste llm-tags van dat argument als 'niet_herbeoordeeld') -- dit
script is puur de eenmalige inhaalslag voor argumenten die al vóór die
codewijziging zijn hergetagd.

Gebruik:
    uv run python scripts/backfill_quote_fragment_status_niet_herbeoordeeld.py [--dry-run]
"""

import argparse
import logging

from pipeline.db import db
from pipeline.tag_arguments import PROMPT_VERSION

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def backfill(conn, dry_run=False):
    rows = conn.execute(
        """SELECT id FROM argument_tags
           WHERE created_by = 'llm' AND quote_fragment_status IS NULL
             AND argument_id IN (SELECT id FROM arguments WHERE tag_prompt_version = ?)""",
        (PROMPT_VERSION,),
    ).fetchall()
    if not dry_run:
        conn.execute(
            """UPDATE argument_tags SET quote_fragment_status = 'niet_herbeoordeeld'
               WHERE created_by = 'llm' AND quote_fragment_status IS NULL
                 AND argument_id IN (SELECT id FROM arguments WHERE tag_prompt_version = ?)""",
            (PROMPT_VERSION,),
        )
        conn.commit()
    return len(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="niets wegschrijven, alleen het aantal tellen")
    args = parser.parse_args()

    conn = db.connect()
    n = backfill(conn, dry_run=args.dry_run)
    logger.info(
        "%s %d argument_tags-rijen naar quote_fragment_status='niet_herbeoordeeld' (tag_prompt_version=%s).",
        "Zou" if args.dry_run else "Gezet:", n, PROMPT_VERSION,
    )
    conn.close()


if __name__ == "__main__":
    main()
