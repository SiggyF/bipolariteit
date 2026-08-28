"""Publiceer data/export/gepubliceerd/ naar de publieke bipolariteit-data-repo.

Gebruik:

    make export-public-data   # frontend/scripts/export_public_data.ts, ververst data/export/gepubliceerd/
    make publish-data          # export-public-data + dit script

    uv run python scripts/publish_data.py
    uv run python scripts/publish_data.py --dry-run

data/export/gepubliceerd/ is een git submodule op de publieke repo
bipolariteit/bipolariteit-data (zie .gitmodules) -- de hoofdrepo
(SiggyF/bipolariteit) blijft private. jsDelivr's GitHub-CDN
(cdn.jsdelivr.net/gh/bipolariteit/bipolariteit-data@main/...) serveert er
client-side uit, met CORS voor alle origins.

Losgekoppeld van de release-workflows: data-publicatie heeft een eigen
cadans (verandert alleen als de dataset zelf verandert), niet die van een
frontend-release. Zie docs/release.md.
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

REPO = Path(__file__).resolve().parent.parent
SUBMODULE = REPO / "data" / "export" / "gepubliceerd"
DATA_REPO = "bipolariteit/bipolariteit-data"
DATA_BRANCH = "main"


def git(*args: str, cwd: Path = SUBMODULE) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def warn_about_pending_main_repo_changes() -> None:
    """Waarschuw als de hoofdrepo na publicatie nog los werk heeft: de
    submodule-pointer (`data/export/gepubliceerd`) en/of de export-json's
    buiten de submodule. Dat blijft altijd een aparte, bewuste commit/PR in
    SiggyF/bipolariteit -- dit script commit/pusht daar zelf niets (zie #222).
    """
    status = git("status", "--porcelain", "--", "data/export", cwd=REPO)
    files = [line[3:] for line in status.stdout.splitlines() if line.strip()]
    if not files:
        return

    logger.warning(
        "%d gewijzigd bestand(en) in de hoofdrepo (%s) nog niet gecommit -- "
        "maak hiervoor een aparte PR (submodule-pointer + eventuele export-json's):",
        len(files),
        REPO,
    )
    for file in files:
        logger.warning("  %s", file)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="toon de git-status van de submodule, maar commit/push niet",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if not SUBMODULE.is_dir() or not (SUBMODULE / ".git").exists():
        logger.error(
            "%s is geen geïnitialiseerde submodule -- draai eerst `git submodule update --init`",
            SUBMODULE,
        )
        return 1

    status = git("status", "--porcelain")
    files = [line[3:] for line in status.stdout.splitlines() if line.strip()]
    if not files:
        logger.info("geen wijzigingen in %s -- niets te publiceren", SUBMODULE)
        warn_about_pending_main_repo_changes()
        return 0

    logger.info("%d gewijzigd bestand(en) in %s:", len(files), SUBMODULE)
    for file in files:
        logger.info("  %s", file)

    if args.dry_run:
        logger.info("dry-run, niet gecommit/gepusht")
        return 0

    git("add", "-A")
    commit = git("commit", "-m", "Ververs geëxporteerde data")
    if commit.returncode != 0:
        logger.error("git commit faalde: %s", commit.stderr)
        return commit.returncode

    push = git("push")
    if push.returncode != 0:
        logger.error("git push faalde: %s", push.stderr)
        return push.returncode

    for file in files:
        purge_url = f"https://purge.jsdelivr.net/gh/{DATA_REPO}@{DATA_BRANCH}/{file}"
        response = requests.get(purge_url, timeout=30)
        if response.ok:
            logger.info("jsDelivr-cache geleegd voor %s", file)
        else:
            logger.warning("jsDelivr-purge voor %s gaf status %s (niet fataal)", file, response.status_code)

    logger.info("klaar: gepubliceerd naar https://github.com/%s", DATA_REPO)
    warn_about_pending_main_repo_changes()
    return 0


if __name__ == "__main__":
    sys.exit(main())
