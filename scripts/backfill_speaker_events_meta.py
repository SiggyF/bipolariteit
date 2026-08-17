"""
Eenmalige backfill: vult documents.speaker_person_id/turn_type voor rijen die
al vóór deze kolommen bestonden zijn geïmporteerd. ingest_tk.py's
document_exists-dedup zorgt ervoor dat een simpele her-run van de ingest deze
bestaande rijen nooit update, dus dit is een aparte, direct-UPDATE-stap over
dezelfde brondata (data/raw/tweede_kamer/**/*.xml).

Topic-onafhankelijk, bewust géén --topic-filter: eerdere versie matchte via
find_matching_activiteiten(root, topic_keyword) en miste zo documenten die
alleen via --also-keyword/--also-dir bij de oorspronkelijke ingest zijn
meegenomen (bv. topic energietransitie, --also-keyword klimaat/waterstof/...,
niet ergens gedocumenteerd). Topic-matching is hier ook niet nodig: een
document bestaat al of niet in de DB, dus deze versie werkt gewoon élke turn
in élk XML-bestand bij waarvan het external_id al een documents-rij heeft --
dat dekt alle topics in één scan, zonder de keyword-matching van de ingest te
hoeven reproduceren.

Gebruik:
    uv run python scripts/backfill_speaker_events_meta.py [--dry-run]
"""

import argparse
import logging
import xml.etree.ElementTree as ET

from pipeline.db import db
from pipeline.ingest.ingest_tk import NS, _local
from pipeline.paths import RAW_DIR_TWEEDE_KAMER as RAW_DIR

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def backfill(dry_run=False):
    conn = db.connect(db.DEFAULT_DB_PATH)
    try:
        updated = 0
        for xml_path in sorted(RAW_DIR.glob("**/*.xml")):
            root = ET.parse(xml_path).getroot()

            for turn_el in root.iter():
                spreker_el = turn_el.find(NS + "spreker")
                tekst_el = turn_el.find(NS + "tekst")
                if spreker_el is None or tekst_el is None:
                    continue
                external_id = turn_el.attrib.get("objectid")
                speaker_person_id = spreker_el.attrib.get("objectid")
                turn_type = _local(turn_el.tag)
                if not external_id or not speaker_person_id:
                    continue
                if dry_run:
                    row = conn.execute(
                        "SELECT id, speaker_person_id FROM documents WHERE external_id = ?",
                        (external_id,),
                    ).fetchone()
                    if row and row["speaker_person_id"] is None:
                        updated += 1
                    continue
                cur = conn.execute(
                    """
                    UPDATE documents
                    SET speaker_person_id = ?, turn_type = ?
                    WHERE external_id = ? AND speaker_person_id IS NULL
                    """,
                    (speaker_person_id, turn_type, external_id),
                )
                updated += cur.rowcount

        if dry_run:
            logger.info("Dry-run: %d documenten zouden bijgewerkt worden.", updated)
        else:
            conn.commit()
            logger.info("Klaar: %d documenten bijgewerkt.", updated)
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    backfill(dry_run=args.dry_run)
