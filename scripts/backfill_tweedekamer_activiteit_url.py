"""
Eenmalige backfill van `documents.tweedekamer_activiteit_url` voor documenten
die al vóór deze kolom bestond zijn geïngest (zie docs/tk-data-sources-overview.md
sectie 11 -- Activiteit.Nummer -> publieke tweedekamer.nl-detailpagina).

Nieuwe crawls vullen deze kolom al rechtstreeks (crawlers/tweede_kamer/tweede_kamer/pipelines.py).
Dit script is alleen nodig voor de bestaande documenten die van vóór die wijziging dateren.

Werkwijze: per raw metadata-JSON-bestand (data/raw/tweede_kamer/*.json, één per
Verslag -- niet gecommit, alleen lokaal aanwezig) staat al een `activiteit_id`
(OData GUID). Voor elke unieke Verslag wordt de bijbehorende Activiteit één keer
opgehaald (Nummer + Soort), de URL opgebouwd, en toegepast op alle documenten
met `raw_ref` gelijk aan die Verslag-XML (join via `documents.raw_ref`, niet via
een los activiteit_id-veld -- dat wordt nergens in `documents` opgeslagen).

Gebruik:
    uv run python scripts/backfill_tweedekamer_activiteit_url.py [--dry-run]
"""

import argparse
import json
import logging

import requests

from pipeline.db import db
from pipeline.paths import RAW_DIR_TWEEDE_KAMER as RAW_DIR

logger = logging.getLogger(__name__)

ODATA_BASE = "https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0"


def activiteit_website_url(nummer, soort):
    """Zelfde logica als crawlers/tweede_kamer/tweede_kamer/odata.py:activiteit_website_url
    -- bewust gedupliceerd i.p.v. cross-package geïmporteerd (het scrapy-project
    en de pipeline hebben elk hun eigen sys.path-root, zie docs/plan.md)."""
    if not nummer:
        return None
    if soort and soort.startswith("Plenair"):
        return f"https://www.tweedekamer.nl/debat_en_vergadering/plenaire_vergaderingen/details/activiteit?id={nummer}"
    if soort and "Commissie" in soort:
        return f"https://www.tweedekamer.nl/debat_en_vergadering/commissievergaderingen/details?id={nummer}"
    return None


def fetch_activiteit(activiteit_id):
    resp = requests.get(f"{ODATA_BASE}/Activiteit/{activiteit_id}", timeout=30)
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="niets naar de database schrijven, alleen printen")
    args = parser.parse_args()

    meta_files = sorted(RAW_DIR.glob("*.json"))
    if not meta_files:
        logger.info("Geen raw metadata-bestanden gevonden in %s.", RAW_DIR)
        return

    conn = db.connect()
    total_updated = 0

    for meta_path in meta_files:
        metadata = json.loads(meta_path.read_text())
        activiteit_id = metadata.get("activiteit_id")
        verslag_id = metadata.get("verslag_id")
        raw_ref = f"{verslag_id}.xml"
        if not activiteit_id:
            logger.warning("%s: geen activiteit_id in metadata, overgeslagen.", meta_path.name)
            continue

        activiteit = fetch_activiteit(activiteit_id)
        url = activiteit_website_url(activiteit.get("Nummer"), activiteit.get("Soort"))
        logger.info(
            "%s: Activiteit %s (Nummer=%s, Soort=%s) -> %s",
            meta_path.name, activiteit_id, activiteit.get("Nummer"), activiteit.get("Soort"), url,
        )
        if not url:
            continue

        if not args.dry_run:
            cur = conn.execute(
                "UPDATE documents SET tweedekamer_activiteit_url = ? WHERE raw_ref = ? AND tweedekamer_activiteit_url IS NULL",
                (url, raw_ref),
            )
            conn.commit()
            total_updated += cur.rowcount
        else:
            count = conn.execute(
                "SELECT COUNT(*) FROM documents WHERE raw_ref = ? AND tweedekamer_activiteit_url IS NULL",
                (raw_ref,),
            ).fetchone()[0]
            total_updated += count

    conn.close()
    logger.info("Klaar: %d documenten bijgewerkt%s.", total_updated, " (dry-run, niets weggeschreven)" if args.dry_run else "")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
