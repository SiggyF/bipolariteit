"""
Verkenning vóór een crawl: hoeveel Tweede Kamer-activiteiten levert een
kandidaat-trefwoord op, en van welke debatsoort?

Bedoeld om de omvang en de ruis van een nieuw topic te kennen vóórdat er
LLM-credits aan verbrand worden. Telt alleen activiteiten vanaf de
verwerkingsdrempel (data/politieke-periodes.toml, [verwerking].vanaf) -- alles
daarvoor komt sowieso niet in de export terecht.

Doet zelf HTTP (in tegenstelling tot de spider), want dit is een eenmalige
telling en geen crawl: geen items, geen pipelines, geen ruwe bestanden.

Gebruik:
    uv run python scripts/probe_topic_keywords.py asiel migratie asielbeleid
"""

import argparse
import collections
import logging
import sys
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
# odata.py woont in het crawler-pakket; dat is de enige plek met de
# URL-bouwlogica, dus importeren in plaats van hier een tweede versie te maken.
sys.path.insert(0, str(REPO_ROOT / "crawlers" / "tweede_kamer"))

from pipeline import periodes  # noqa: E402
from tweede_kamer import odata  # noqa: E402

logger = logging.getLogger(__name__)

PAGE_SIZE = 250


def fetch_activiteiten(keyword, vanaf):
    """Alle niet-verwijderde activiteiten met het trefwoord in het onderwerp,
    vanaf de verwerkingsdrempel. Volgt @odata.nextLink tot het einde."""
    filter_expr = (
        f"contains(Onderwerp,'{keyword}') and Verwijderd eq false "
        f"and Datum ge {vanaf}T00:00:00Z"
    )
    url = odata.build_url("Activiteit", filter=filter_expr, orderby="Datum desc", top=PAGE_SIZE)
    activiteiten = []
    while url:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        body = response.json()
        activiteiten.extend(body.get("value", []))
        url = body.get("@odata.nextLink")
    return activiteiten


def report(keyword, activiteiten):
    per_soort = collections.Counter(a.get("Soort") or "(geen soort)" for a in activiteiten)
    logger.info("%s: %d activiteiten", keyword, len(activiteiten))
    for soort, aantal in per_soort.most_common():
        logger.info("    %4d  %s", aantal, soort)
    logger.info("  recentste onderwerpen:")
    for activiteit in activiteiten[:10]:
        datum = (activiteit.get("Datum") or "")[:10]
        logger.info("    %s  %s", datum, activiteit.get("Onderwerp"))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("keywords", nargs="+", help="kandidaat-trefwoorden, bv. asiel migratie")
    args = parser.parse_args()

    _kamerperiodes, _regeringsperiodes, vanaf = periodes.laad_periodes()
    logger.info("Verwerkingsdrempel: vanaf %s", vanaf)
    for keyword in args.keywords:
        report(keyword, fetch_activiteiten(keyword, vanaf))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
