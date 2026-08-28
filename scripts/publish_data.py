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

Naast het pushen naar bipolariteit-data zet dit script ook de resterende
hoofdrepo-wijzigingen (submodule-pointer + eventuele export-json's buiten
de submodule) op een eigen branch, opent er een PR voor in
SiggyF/bipolariteit en merged die meteen -- data-only PR's, dus geen
losse reviewstap nodig (zie #222). Draait daarom alleen vanaf de
main-branch van de hoofdrepo.
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

REPO = Path(__file__).resolve().parent.parent
SUBMODULE = REPO / "data" / "export" / "gepubliceerd"
DATA_REPO = "bipolariteit/bipolariteit-data"
DATA_BRANCH = "main"


def git(*args: str, cwd: Path = SUBMODULE) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def open_main_repo_pr() -> int:
    """Rond de derde stap af die na publicatie altijd bleef liggen: de
    submodule-pointer (`data/export/gepubliceerd`) en/of de export-json's
    buiten de submodule zijn na publicatie gewijzigd in de hoofdrepo, maar
    nooit gecommit. Zet ze op een eigen branch, open er een PR voor en
    merge die meteen -- puur gegenereerde data, geen reviewstap nodig
    (zie #222).
    """
    status = git("status", "--porcelain", "--", "data/export", cwd=REPO)
    files = [line[3:] for line in status.stdout.splitlines() if line.strip()]
    if not files:
        return 0

    logger.info("%d gewijzigd bestand(en) in de hoofdrepo (%s):", len(files), REPO)
    for file in files:
        logger.info("  %s", file)

    original_branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=REPO, capture_output=True, text=True
    ).stdout.strip()
    branch_name = f"data/publish-data-{datetime.now():%Y%m%d-%H%M%S}"

    checkout = git("checkout", "-b", branch_name, cwd=REPO)
    if checkout.returncode != 0:
        logger.error("git checkout -b %s faalde: %s", branch_name, checkout.stderr)
        return checkout.returncode

    try:
        add = git("add", "--", *files, cwd=REPO)
        if add.returncode != 0:
            logger.error("git add faalde: %s", add.stderr)
            return add.returncode

        commit = git(
            "commit", "-m", "data: submodule-pointer en export-data bijwerken na publish-data", cwd=REPO
        )
        if commit.returncode != 0:
            logger.error("git commit faalde: %s", commit.stderr)
            return commit.returncode

        push = git("push", "-u", "origin", branch_name, cwd=REPO)
        if push.returncode != 0:
            logger.error("git push faalde: %s", push.stderr)
            return push.returncode

        pr = subprocess.run(
            [
                "gh",
                "pr",
                "create",
                "--title",
                "data: submodule-pointer en export-data bijwerken na publish-data",
                "--body",
                "Automatisch geopend door `scripts/publish_data.py` na `make publish-data` "
                "(submodule al gepubliceerd naar bipolariteit-data; dit zet de resterende "
                "hoofdrepo-wijzigingen erbij, zie #222).",
            ],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        if pr.returncode != 0:
            logger.error("gh pr create faalde: %s", pr.stderr)
            return pr.returncode

        pr_url = pr.stdout.strip()
        logger.info("PR geopend: %s", pr_url)

        merge = subprocess.run(
            ["gh", "pr", "merge", pr_url, "--merge"], cwd=REPO, capture_output=True, text=True
        )
        if merge.returncode != 0:
            logger.error(
                "gh pr merge faalde: %s -- PR staat nog open, merge %s handmatig", merge.stderr, pr_url
            )
            return merge.returncode

        logger.info("PR gemerged: %s", pr_url)
        return 0
    finally:
        git("checkout", original_branch, cwd=REPO)
        pull = git("pull", "origin", original_branch, cwd=REPO)
        if pull.returncode != 0:
            logger.warning("git pull na merge faalde: %s -- lokale %s kan achterlopen", pull.stderr, original_branch)


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

    main_repo_branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=REPO, capture_output=True, text=True
    ).stdout.strip()
    if main_repo_branch != "main":
        logger.error(
            "hoofdrepo staat op branch '%s', niet 'main' -- checkout eerst main "
            "(publiceren vanaf een andere branch levert een verkeerde submodule-pointer-PR op)",
            main_repo_branch,
        )
        return 1

    status = git("status", "--porcelain")
    files = [line[3:] for line in status.stdout.splitlines() if line.strip()]
    if not files:
        logger.info("geen wijzigingen in %s -- niets te publiceren", SUBMODULE)
        if args.dry_run:
            return 0
        return open_main_repo_pr()

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
    return open_main_repo_pr()


if __name__ == "__main__":
    sys.exit(main())
