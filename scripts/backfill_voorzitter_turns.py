"""
Eenmalige backfill: zet documents.is_voorzitter_turn voor rijen die al vóór
deze kolom bestonden zijn geïmporteerd. ingest_tk.py's document_exists-dedup
zorgt ervoor dat een simpele her-run van de ingest deze bestaande rijen nooit
update, dus dit is een aparte, direct-UPDATE-stap over dezelfde brondata
(data/raw/tweede_kamer/*.xml).

Documenten die hierdoor alsnog als voorzitter-beurt herkend worden, kunnen al
vóór deze fix door Stage 1 verwerkt zijn (arguments toegeschreven aan de
voorzitter's eigen fractie, terwijl het procedurele tekst was -- zie
docs/handoff.md). --purge-arguments verwijdert die arguments (+ afhankelijke
claims/argument_tags/argument_oppositions) alsnog; zonder die flag rapporteert
dit script alleen hoeveel dat er zijn, zonder iets te verwijderen.

Gebruik:
    uv run python scripts/backfill_voorzitter_turns.py --topic stikstof [--dry-run] [--purge-arguments]
"""

import argparse
import json
import logging
import xml.etree.ElementTree as ET

from pipeline.db import db
from pipeline.ingest.ingest_tk import (
    NS,
    build_parent_map,
    find_matching_activiteiten,
    find_speaking_turns,
    is_voorzitter_turn,
)
from pipeline.paths import RAW_DIR_TWEEDE_KAMER as RAW_DIR

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def purge_arguments_for_document(conn, document_id):
    argument_ids = [
        row["id"] for row in conn.execute("SELECT id FROM arguments WHERE document_id = ?", (document_id,)).fetchall()
    ]
    for argument_id in argument_ids:
        conn.execute("DELETE FROM argument_tags WHERE argument_id = ?", (argument_id,))
        conn.execute("DELETE FROM claims WHERE argument_id = ?", (argument_id,))
        conn.execute(
            "DELETE FROM argument_oppositions WHERE argument_a_id = ? OR argument_b_id = ?",
            (argument_id, argument_id),
        )
    conn.execute("DELETE FROM arguments WHERE document_id = ?", (document_id,))
    return len(argument_ids)


def backfill(topic_keyword, dry_run=False, purge_arguments=False):
    conn = db.connect(db.DEFAULT_DB_PATH)
    try:
        flagged = 0
        skipped_no_meta = 0
        purged_arguments = 0
        newly_flagged_with_arguments = 0

        for xml_path in sorted(RAW_DIR.glob("*.xml")):
            meta_path = xml_path.with_suffix(".json")
            if not meta_path.exists():
                skipped_no_meta += 1
                continue
            root = ET.parse(xml_path).getroot()
            parent_map = build_parent_map(root)

            for activiteit in find_matching_activiteiten(root, topic_keyword):
                for turn_el, _, _ in find_speaking_turns(activiteit):
                    if not is_voorzitter_turn(turn_el, parent_map):
                        continue
                    external_id = turn_el.attrib.get("objectid")
                    if not external_id:
                        continue

                    row = conn.execute(
                        "SELECT id, is_voorzitter_turn FROM documents WHERE external_id = ?",
                        (external_id,),
                    ).fetchone()
                    if not row or row["is_voorzitter_turn"]:
                        continue

                    argument_count = conn.execute(
                        "SELECT COUNT(*) AS n FROM arguments WHERE document_id = ?", (row["id"],)
                    ).fetchone()["n"]
                    if argument_count:
                        newly_flagged_with_arguments += 1

                    if dry_run:
                        flagged += 1
                        continue

                    conn.execute(
                        "UPDATE documents SET is_voorzitter_turn = 1 WHERE id = ?",
                        (row["id"],),
                    )
                    flagged += 1

                    if argument_count and purge_arguments:
                        purged_arguments += purge_arguments_for_document(conn, row["id"])

        if dry_run:
            logger.info(
                "Dry-run: %d documenten zouden geflagd worden als voorzitter-beurt "
                "(%d bestanden zonder metadata overgeslagen). Daarvan hebben %d al arguments in de DB.",
                flagged, skipped_no_meta, newly_flagged_with_arguments,
            )
        else:
            conn.commit()
            logger.info(
                "Klaar: %d documenten geflagd als voorzitter-beurt (%d bestanden zonder metadata overgeslagen).",
                flagged, skipped_no_meta,
            )
            if purge_arguments:
                logger.info("Verwijderd: %d arguments (+ afhankelijke claims/tags/oppositions) uit voorzitter-beurten.", purged_arguments)
            elif newly_flagged_with_arguments:
                logger.info(
                    "%d van de geflagde documenten hadden al arguments in de DB -- niet verwijderd "
                    "(gebruik --purge-arguments om ze alsnog te verwijderen).",
                    newly_flagged_with_arguments,
                )
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--purge-arguments", action="store_true", help="Verwijder ook arguments die al uit voorzitter-beurten geëxtraheerd waren")
    args = parser.parse_args()
    backfill(args.topic, dry_run=args.dry_run, purge_arguments=args.purge_arguments)
