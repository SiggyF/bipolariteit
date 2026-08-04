"""Tests voor de URL-bouw en selectieheuristieken van de Tweede Kamer-crawler."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "crawlers" / "tweede_kamer"))

from tweede_kamer import odata  # noqa: E402


def test_vragenuur_is_a_plenaire_vergadering():
    # "Vragenuur" begint niet met "Plenair" maar vindt wel plenair plaats;
    # zonder deze uitzondering zoeken we een commissievergadering die er die
    # dag niet is en missen we het vragenuur volledig.
    assert odata.vergadering_soort_for_activiteit("Vragenuur") == "Plenair"
    assert odata.vergadering_soort_for_activiteit("Plenair debat (debat)") == "Plenair"
    assert odata.vergadering_soort_for_activiteit("Commissiedebat") == "Commissie"


def test_max_top_stays_within_the_api_limit():
    # Boven 250 antwoordt de API met HTTP 400 en laat Scrapy de respons vallen:
    # een crawl zonder resultaten en zonder duidelijke foutmelding.
    assert odata.MAX_TOP == 250
