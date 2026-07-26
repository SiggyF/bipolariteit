"""
Eenmalige backfill voor bewindspersonen (Minister/Staatssecretaris) die als
spreker geen <fractie> hebben (ze spreken op dat moment niet namens een
Kamerfractie) -- ze kregen daardoor actors.party = NULL en toonden in de
frontend geen partij/naam-context. Twee losse stappen, geen LLM:

1. documents.speaker_role_title vullen uit de brondata (<spreker><functie>,
   zie ingest_tk._speaker_role_title) voor bestaande documenten die al vóór
   deze kolom bestonden zijn geïmporteerd -- zelfde patroon als
   backfill_activiteit_tijden.py/backfill_voorzitter_turns.py.
2. actors.party vullen voor de bewindspersonen wiens partij traceerbaar is
   via de Tweede Kamer OData Persoon-API (Persoon -> FractieZetelPersoon ->
   FractieZetel -> Fractie.Afkorting), geverifieerd op 2026-07-26:

   - Femke Marije Wiersma -> BBB (huidige zetel, Van 2025-11-12, TotEnMet NULL)
   - Silvio Erkens -> VVD (zetel t/m 2026-02-22, daarna minister zonder zetel)
   - Christianne van der Wal(-Zeggelink) -> VVD (zetel t/m 2025-03-25)
   - Mark Harbers -> VVD (twee zetelperiodes, laatste t/m 2022-01-09)

   Bewust NIET geraden voor Dick Schoof, Jean Rummenie, Piet Adema en Jaimi
   van Essen: geen Persoon-record met Kamerlidschap/Fractiegeschiedenis
   gevonden in de OData API (Schoof is in werkelijkheid ook partijloos
   minister-president) -- hun party blijft NULL, wat hier feitelijk correct
   is, geen hiaat. speaker_role_title (stap 1) toont voor hen alsnog de
   functie, dus ze blijven niet content-loos in de UI.

Gebruik:
    uv run python scripts/backfill_minister_info.py --topic stikstof [--dry-run]
"""

import argparse
import json
import logging
import xml.etree.ElementTree as ET

from pipeline.db import db
from pipeline.ingest.ingest_tk import NS, find_matching_activiteiten, find_speaking_turns, _speaker_role_title
from pipeline.paths import RAW_DIR_TWEEDE_KAMER as RAW_DIR

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Zie de docstring hierboven voor de OData-verificatie per naam/partij.
MINISTER_PARTY = {
    "Femke Marije Wiersma": "BBB",
    "Silvio Erkens": "VVD",
    "Christianne van der Wal-Zeggelink": "VVD",
    "Christianne van der Wal": "VVD",
    "Mark Harbers": "VVD",
}


def backfill_role_titles(conn, topic_keyword, dry_run=False):
    updated = 0
    skipped_no_meta = 0
    for xml_path in sorted(RAW_DIR.glob("*.xml")):
        meta_path = xml_path.with_suffix(".json")
        if not meta_path.exists():
            skipped_no_meta += 1
            continue
        root = ET.parse(xml_path).getroot()

        for activiteit in find_matching_activiteiten(root, topic_keyword):
            for turn_el, spreker_el, _ in find_speaking_turns(activiteit):
                role_title = _speaker_role_title(spreker_el)
                if not role_title:
                    continue
                external_id = turn_el.attrib.get("objectid")
                if not external_id:
                    continue

                row = conn.execute(
                    "SELECT id, speaker_role_title FROM documents WHERE external_id = ?",
                    (external_id,),
                ).fetchone()
                if not row or row["speaker_role_title"]:
                    continue

                if dry_run:
                    updated += 1
                    continue
                conn.execute(
                    "UPDATE documents SET speaker_role_title = ? WHERE id = ?",
                    (role_title, row["id"]),
                )
                updated += 1

    logger.info(
        "speaker_role_title: %d documenten %s (%d bestanden zonder metadata overgeslagen).",
        updated, "zouden bijgewerkt worden" if dry_run else "bijgewerkt", skipped_no_meta,
    )


def backfill_minister_party(conn, dry_run=False):
    updated = 0
    for name, party in MINISTER_PARTY.items():
        rows = conn.execute(
            "SELECT id FROM actors WHERE name = ? AND party IS NULL", (name,)
        ).fetchall()
        for row in rows:
            if not dry_run:
                conn.execute("UPDATE actors SET party = ? WHERE id = ?", (party, row["id"]))
            updated += 1
            logger.info("  actor %d (%s) -> party=%s", row["id"], name, party)
    logger.info("actors.party: %d rijen %s.", updated, "zouden bijgewerkt worden" if dry_run else "bijgewerkt")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = db.connect(db.DEFAULT_DB_PATH)
    try:
        backfill_role_titles(conn, args.topic, dry_run=args.dry_run)
        backfill_minister_party(conn, dry_run=args.dry_run)
        if not args.dry_run:
            conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
