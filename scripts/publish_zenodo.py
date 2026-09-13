"""Publiceer (als Zenodo-draft) een nieuwe versie van de volle-dataset-
tegelpyramide van de plenaire kaart.

Gebruik:

    uv run python scripts/publish_zenodo.py
    uv run python scripts/publish_zenodo.py --dry-run
    uv run python scripts/publish_zenodo.py --files data/export/plenair-map/plenair-map-full.pmtiles

`data/export/plenair-map/plenair-map-full.pmtiles` (~1,25 GiB, issue #281)
en `plenair-map-full.json` (~119 MiB) zijn te groot voor git/GitHub
(100 MB-harde-limiet) en horen niet in `data/export/gepubliceerd/`
(`scripts/publish_data.py`'s jsDelivr-route is voor de kleine JSON-/tags-
data die de site verder gebruikt -- niet voor pmtiles, dat sinds issue #316
altijd naar Hugging Face gaat, zowel de kleine `plenair-map.pmtiles`
(`make publish-tiles`) als deze volle-dataset-variant hieronder). Zie
docs/release.md: Zenodo is bewust gekozen voor dit soort grote,
archiefachtige data (DOI/versionering), niet voor de "overschrijf de
huidige data"-flow die zowel `publish-data` (jsDelivr) als
`publish-huggingface`/`publish-tiles` (Hugging Face) gebruiken.

`make tiles-full` bundelt de tegelpyramide + companion-bestanden al in
`data/export/plenair-map/bundel/` (gitignored) -- default hier is gewoon
"alles wat daarin staat publiceren", zodat deze twee stappen niet los van
elkaar uit de pas kunnen lopen over welke bestanden erbij horen.

Maakt een NIEUWE VERSIE aan onder het bestaande concept-record (niet een los
nieuw record -- zelfde archief als de eerdere Zenodo-publicatie, zie
docs/handoff.md 2026-08-29-sessie: https://doi.org/10.5281/zenodo.22181704)
en upload de bestanden erin, als DRAFT. Publiceren zelf (onomkeerbaar, eigen
DOI per versie) blijft een bewuste, handmatige stap in de Zenodo-UI -- zelfde
patroon als de vorige archivering en als `scripts/publish_data.py`'s
hoofdrepo-PR (geen automatische onomkeerbare stappen).

Vereist ZENODO_TOKEN (zie .devcontainer/.env.local).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

import requests

from pipeline.paths import REPO_ROOT

logger = logging.getLogger(__name__)

ZENODO_API = "https://zenodo.org/api"
# Zelfde concept-record als pipeline/plenary_map/cluster.py's
# ZENODO_CONCEPT_RECID -- blijft stabiel over alle versies heen.
ZENODO_CONCEPT_RECID = "22181704"

DEFAULT_BUNDLE_DIR = REPO_ROOT / "data" / "export" / "plenair-map" / "bundel"


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def find_latest_deposition_id(token: str) -> int:
    """Meest recente deposition-id onder het bestaande concept-record.

    Via de deposit-API (niet de publieke records-API) omdat die ook
    niet-gepubliceerde/eigen versies teruggeeft. Kiest zelf de meest recente
    op basis van `modified` i.p.v. op een API-side sort-parameter te
    vertrouwen (Zenodo's exacte sleutelnamen daarvoor zijn niet stabiel
    gedocumenteerd)."""
    resp = requests.get(
        f"{ZENODO_API}/deposit/depositions",
        params={"q": f"conceptrecid:{ZENODO_CONCEPT_RECID}", "all_versions": "true", "size": 50},
        headers=_headers(token),
        timeout=30,
    )
    resp.raise_for_status()
    hits = resp.json()
    if not hits:
        raise RuntimeError(f"geen bestaande deposition gevonden onder concept {ZENODO_CONCEPT_RECID}")
    latest = max(hits, key=lambda d: d["modified"])
    return latest["id"]


def create_new_version(token: str, latest_id: int) -> dict:
    resp = requests.post(
        f"{ZENODO_API}/deposit/depositions/{latest_id}/actions/newversion",
        headers=_headers(token),
        timeout=30,
    )
    resp.raise_for_status()
    draft_url = resp.json()["links"]["latest_draft"]
    draft = requests.get(draft_url, headers=_headers(token), timeout=30)
    draft.raise_for_status()
    return draft.json()


def remove_stale_files(token: str, deposition: dict, filenames: set[str]) -> None:
    """Een nieuwe versie start als kopie van de vorige (incl. bestanden) --
    gelijknamige oude bestanden eerst verwijderen, anders krijg je twee
    entries met dezelfde naam in de nieuwe versie."""
    for f in deposition.get("files", []):
        if f["filename"] in filenames:
            resp = requests.delete(f["links"]["self"], headers=_headers(token), timeout=30)
            if resp.status_code not in (204, 404):
                resp.raise_for_status()
            logger.info("oud bestand verwijderd uit draft: %s", f["filename"])


def upload_file(token: str, bucket_url: str, path: Path) -> None:
    size_mb = path.stat().st_size / 1024 / 1024
    logger.info("upload %s (%.1f MiB) naar %s", path.name, size_mb, bucket_url)
    with path.open("rb") as fh:
        # Geen timeout: dit kan bij ~1,25 GiB over een gewone verbinding lang
        # duren, en `data=fh` streamt het bestand (geen volledige inhoud in
        # geheugen) -- een timeout zou hier alleen een trage-maar-gezonde
        # upload voortijdig afbreken.
        resp = requests.put(f"{bucket_url}/{path.name}", data=fh, headers=_headers(token), timeout=None)
    resp.raise_for_status()
    logger.info("klaar: %s", path.name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--files",
        nargs="+",
        type=Path,
        default=None,
        help=f"te uploaden bestanden (default: alles in {DEFAULT_BUNDLE_DIR}, zie `make tiles-full`)",
    )
    parser.add_argument("--dry-run", action="store_true", help="toon wat er zou gebeuren, maak geen Zenodo-draft aan")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if args.files is None:
        if not DEFAULT_BUNDLE_DIR.is_dir():
            logger.error(
                "%s bestaat niet -- draai eerst `make tiles-full` om de bundel te vullen",
                DEFAULT_BUNDLE_DIR,
            )
            return 1
        args.files = sorted(f for f in DEFAULT_BUNDLE_DIR.iterdir() if f.is_file())
        if not args.files:
            logger.error("%s is leeg -- draai eerst `make tiles-full`", DEFAULT_BUNDLE_DIR)
            return 1

    missing = [str(f) for f in args.files if not f.is_file()]
    if missing:
        logger.error("bestand(en) niet gevonden: %s", ", ".join(missing))
        return 1

    total_mb = sum(f.stat().st_size for f in args.files) / 1024 / 1024
    logger.info("%d bestand(en), %.1f MiB totaal:", len(args.files), total_mb)
    for f in args.files:
        logger.info("  %s (%.1f MiB)", f, f.stat().st_size / 1024 / 1024)

    if args.dry_run:
        logger.info("dry-run, geen Zenodo-aanroepen gedaan")
        return 0

    token = os.environ.get("ZENODO_TOKEN")
    if not token:
        logger.error("ontbrekende omgevingsvariabele ZENODO_TOKEN -- zie .devcontainer/.env.local")
        return 1

    latest_id = find_latest_deposition_id(token)
    logger.info("meest recente deposition onder concept %s: %s", ZENODO_CONCEPT_RECID, latest_id)

    deposition = create_new_version(token, latest_id)
    deposition_id = deposition["id"]
    bucket_url = deposition["links"]["bucket"]
    logger.info("nieuwe draft-versie aangemaakt: deposition %s", deposition_id)

    remove_stale_files(token, deposition, {f.name for f in args.files})

    for f in args.files:
        upload_file(token, bucket_url, f)

    html_url = deposition["links"].get("html", f"https://zenodo.org/deposit/{deposition_id}")
    logger.info("klaar -- controleer/vul metadata aan en publiceer handmatig: %s", html_url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
