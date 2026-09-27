"""
Haalt de volledige TK OData Kamerstukdossier-collectie op (7825 records op
2026-09-27, dus in zijn geheel te downloaden) en vult de kamerstukdossiers-
lookuptabel (pipeline/db/schema.sql), i.p.v. losse lookups per dossiernummer
te doen (zie #183/#348). Eenmalig/periodiek uit te voeren, niet per topic of
per crawl.

Gebruik:
    uv run python -m scripts.db.fetch_kamerstukdossiers
"""

import json
import logging
import time
import urllib.parse
import urllib.request

from pipeline.db import db

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

_BASE = "https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0"
_HEADERS = {"User-Agent": "bipolariteit-tk-crawler/0.1 (contact: f.baart@gmail.com; onderzoeksproject)"}
_PAGE_SIZE = 250


def _dossiernummer(nummer, toevoeging):
    return f"{nummer}-{toevoeging}" if toevoeging else str(nummer)


def fetch_all_dossiers():
    """Pagineert door de hele Kamerstukdossier-collectie via $orderby=Nummer +
    $top/$skip (de server staat geen $top>250 toe). $orderby zorgt voor
    aaneensluitende, niet-overlappende pagina's -- geverifieerd tijdens het
    uitzoekwerk voor #348 (pagina 1: 17050-28737, pagina 2: 28741-30579, geen
    gaten/duplicaten)."""
    skip = 0
    while True:
        params = {
            "$top": _PAGE_SIZE,
            "$skip": skip,
            "$orderby": "Nummer",
            "$select": "Nummer,Toevoeging,Titel,Afgesloten",
        }
        url = f"{_BASE}/Kamerstukdossier?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read())
        items = body.get("value", [])
        if not items:
            break
        yield from items
        skip += _PAGE_SIZE
        time.sleep(0.2)  # geen agressieve polling tegen een publieke overheids-API


def main():
    conn = db.connect()
    try:
        n_totaal = 0
        n_zonder_nummer = 0
        for item in fetch_all_dossiers():
            nummer = item.get("Nummer")
            if nummer is None:
                n_zonder_nummer += 1
                continue
            toevoeging = item.get("Toevoeging")
            conn.execute(
                """
                INSERT INTO kamerstukdossiers (dossiernummer, nummer, toevoeging, titel, afgesloten)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (dossiernummer) DO UPDATE SET
                    titel = excluded.titel, afgesloten = excluded.afgesloten
                """,
                (_dossiernummer(nummer, toevoeging), nummer, toevoeging, item.get("Titel"), int(bool(item.get("Afgesloten")))),
            )
            n_totaal += 1
        conn.commit()
        logger.info("Klaar: %d dossiers opgeslagen, %d zonder Nummer overgeslagen.", n_totaal, n_zonder_nummer)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
