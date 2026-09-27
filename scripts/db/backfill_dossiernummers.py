"""
Backfill voor activiteit_nummer/motie_dossiernummer (documents) en
activiteit_dossiernummers (issue #183/#348): loopt éénmalig over alle al
gecrawlde VLOS-XML-bestanden die door bestaande documents-rijen gerefereerd
worden (documents.raw_ref) en vult de nieuwe kolommen/tabel met terugwerkende
kracht, zonder opnieuw te crawlen. Nieuwe ingest-runs (pipeline/ingest/ingest_tk.py)
vullen deze velden al vanaf nu vanzelf.

Gebruik:
    uv run python -m scripts.db.backfill_dossiernummers
"""

import logging
import xml.etree.ElementTree as ET
from pathlib import Path

from pipeline.db import db
from pipeline.ingest.ingest_tk import (
    NS,
    _local,
    _turn_motie_dossiernummer,
    find_speaking_turns,
    upsert_activiteit_dossiernummers,
)
from pipeline.paths import RAW_DIR_TWEEDE_KAMER as RAW_DIR

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def _resolve_xml_path(raw_ref):
    """Sommige oudere documents-rijen hebben een raw_ref zonder topic-submap
    (uit een periode vóór die submap-conventie), terwijl het bestand
    zelf inmiddels wél in een submap van RAW_DIR staat. UUID-bestandsnamen
    zijn praktisch garant uniek, dus een rglob op de kale bestandsnaam is hier
    een veilige fallback, geen gok."""
    direct = RAW_DIR / raw_ref
    if direct.exists():
        return direct
    return next(RAW_DIR.rglob(Path(raw_ref).name), None)


def backfill_file(conn, raw_ref):
    xml_path = _resolve_xml_path(raw_ref)
    if xml_path is None:
        logger.warning("XML-bestand ontbreekt, overgeslagen: %s", raw_ref)
        return 0

    try:
        root = ET.parse(xml_path).getroot()
    except ET.ParseError as e:
        logger.warning("kon %s niet parsen (%s), overgeslagen", raw_ref, e)
        return 0

    updated = 0
    for activiteit in root.iter(NS + "activiteit"):
        activiteit_nummer = activiteit.findtext(NS + "parlisid")
        upsert_activiteit_dossiernummers(conn, activiteit_nummer, activiteit)

        for turn_el, _spreker_el, _tekst_el in find_speaking_turns(activiteit):
            external_id = turn_el.attrib.get("objectid")
            if not external_id:
                continue
            motie_dossiernummer = _turn_motie_dossiernummer(turn_el)
            cur = conn.execute(
                """
                UPDATE documents
                SET activiteit_nummer = ?, motie_dossiernummer = ?
                WHERE source_id IN (SELECT id FROM sources WHERE type = 'tweede_kamer')
                  AND external_id = ?
                  AND raw_ref = ?
                  AND (activiteit_nummer IS NULL OR activiteit_nummer != ?)
                """,
                (activiteit_nummer, motie_dossiernummer, external_id, raw_ref, activiteit_nummer),
            )
            updated += cur.rowcount

    return updated


def main():
    conn = db.connect()
    try:
        raw_refs = [
            row["raw_ref"]
            for row in conn.execute(
                "SELECT DISTINCT raw_ref FROM documents WHERE raw_ref IS NOT NULL"
            ).fetchall()
        ]
        logger.info("Backfill over %d bestanden...", len(raw_refs))
        totaal_updated = 0
        for i, raw_ref in enumerate(raw_refs, start=1):
            totaal_updated += backfill_file(conn, raw_ref)
            if i % 500 == 0:
                conn.commit()
                logger.info("  %d/%d bestanden verwerkt (%d documents-rijen bijgewerkt)", i, len(raw_refs), totaal_updated)
        conn.commit()

        dossier_count = conn.execute("SELECT COUNT(*) AS n FROM activiteit_dossiernummers").fetchone()["n"]
        motie_count = conn.execute(
            "SELECT COUNT(*) AS n FROM documents WHERE motie_dossiernummer IS NOT NULL"
        ).fetchone()["n"]
        activiteit_nummer_count = conn.execute(
            "SELECT COUNT(*) AS n FROM documents WHERE activiteit_nummer IS NOT NULL"
        ).fetchone()["n"]
        logger.info(
            "Klaar: %d documents-rijen bijgewerkt, %d met activiteit_nummer, %d met motie_dossiernummer, "
            "%d (activiteit, dossier)-paren in activiteit_dossiernummers.",
            totaal_updated,
            activiteit_nummer_count,
            motie_count,
            dossier_count,
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
