"""
Haalt de officiële genummerde Kamerstukdossiers (onderwerpen) op uit het
Tweede Kamer Open Data Gegevensmagazijn (OData v4).

Slaat de dossiers op als JSON (`data/export/tk_kamerstukdossiers.json`) met:
- `nummer`: het officiële dossiernummer (bv. 32813, 19637, 33576).
- `titel`: de officiële onderwerpstitel.

Gebruik:
    uv run python scripts/fetch_tk_dossiers.py data/export/tk_kamerstukdossiers.json --limit 2000
"""

import json
import logging
from pathlib import Path

import click
import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0/Kamerstukdossier"


def fetch_dossiers(limit: int) -> list[dict]:
    dossiers = []
    skip = 0
    batch_size = 250

    while len(dossiers) < limit:
        url = f"{BASE_URL}?$filter=Verwijderd eq false&$select=Nummer,Titel&$orderby=GewijzigdOp desc&$top={batch_size}&$skip={skip}"
        logger.info("Ophalen van batch (skip=%d, totaal=%d)...", skip, len(dossiers))
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("value", [])
        if not items:
            break

        for item in items:
            if item.get("Titel") and item.get("Nummer"):
                dossiers.append({
                    "nummer": item["Nummer"],
                    "titel": item["Titel"].strip(),
                })
            if len(dossiers) >= limit:
                break

        skip += len(items)

    # Ontdubbelen op dossiernummer
    seen = set()
    unique_dossiers = []
    for d in dossiers:
        if d["nummer"] not in seen:
            seen.add(d["nummer"])
            unique_dossiers.append(d)

    return unique_dossiers


@click.command()
@click.argument("output_path", type=click.Path(dir_okay=False, path_type=Path), default=Path("data/export/tk_kamerstukdossiers.json"))
@click.option("--limit", type=int, default=2000, help="Maximaal aantal dossiers om op te halen (default: 2000).")
def main(output_path: Path, limit: int):
    """Haal de officiële lijst met genummerde TK-onderwerpen (Kamerstukdossiers) op."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    dossiers = fetch_dossiers(limit)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(dossiers, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Succesvol %d unieke genummerde dossiers opgeslagen in: %s", len(dossiers), output_path)


if __name__ == "__main__":
    main()
