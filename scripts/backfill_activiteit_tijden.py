"""
Eenmalige backfill: vult documents.activiteit_aanvangstijd/-eindtijd voor
rijen die al vóór deze kolommen bestonden zijn geïmporteerd. ingest_tk.py's
document_exists-dedup zorgt ervoor dat een simpele her-run van de ingest
deze bestaande rijen nooit update, dus dit is een aparte, direct-UPDATE-stap
over dezelfde brondata (data/raw/tweede_kamer/*.xml).

Gebruik:
    uv run python scripts/backfill_activiteit_tijden.py --topic stikstof [--dry-run]
"""

import argparse
import json
import logging
import xml.etree.ElementTree as ET

from pipeline.db import db
from pipeline.ingest.ingest_tk import NS, find_matching_activiteiten, find_speaking_turns
from pipeline.paths import RAW_DIR_TWEEDE_KAMER as RAW_DIR

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def backfill(topic_keyword, dry_run=False):
    conn = db.connect(db.DEFAULT_DB_PATH)
    try:
        updated = 0
        skipped_no_meta = 0
        for xml_path in sorted(RAW_DIR.glob("*.xml")):
            meta_path = xml_path.with_suffix(".json")
            if not meta_path.exists():
                skipped_no_meta += 1
                continue
            metadata = json.loads(meta_path.read_text())
            root = ET.parse(xml_path).getroot()

            for activiteit in find_matching_activiteiten(root, topic_keyword):
                aanvangstijd = activiteit.findtext(NS + "aanvangstijd") or metadata.get("activiteit_datum")
                eindtijd = activiteit.findtext(NS + "eindtijd")
                if not aanvangstijd:
                    continue
                for turn_el, _, _ in find_speaking_turns(activiteit):
                    external_id = turn_el.attrib.get("objectid")
                    if not external_id:
                        continue
                    if dry_run:
                        row = conn.execute(
                            "SELECT id, activiteit_aanvangstijd FROM documents WHERE external_id = ?",
                            (external_id,),
                        ).fetchone()
                        if row and row["activiteit_aanvangstijd"] is None:
                            updated += 1
                        continue
                    cur = conn.execute(
                        """
                        UPDATE documents
                        SET activiteit_aanvangstijd = ?, activiteit_eindtijd = ?
                        WHERE external_id = ? AND activiteit_aanvangstijd IS NULL
                        """,
                        (aanvangstijd, eindtijd, external_id),
                    )
                    updated += cur.rowcount

        if dry_run:
            logger.info("Dry-run: %d documenten zouden bijgewerkt worden (%d bestanden zonder metadata overgeslagen).", updated, skipped_no_meta)
        else:
            conn.commit()
            logger.info("Klaar: %d documenten bijgewerkt (%d bestanden zonder metadata overgeslagen).", updated, skipped_no_meta)
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    backfill(args.topic, dry_run=args.dry_run)
