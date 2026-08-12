"""Controleer na een release dat er geen gevoelige bestanden publiek staan.

Gebruik:

    uv run python scripts/check_public_exposure.py www.bipolariteit.org
    uv run python scripts/check_public_exposure.py v0-3-0-preview.bipolariteit.org --skip-dist-scan

Twee controles:

1. **dist-scan** -- doorzoekt `frontend/dist` (vóór upload al opgebouwd) op
   bestandsnamen die niet in een statische build thuishoren: `.env`-bestanden,
   databases, sleutels, `.git`. De site is volledig statisch (zie
   docs/release.md), dus alles in die map wordt letterlijk publiek
   geserveerd -- wat er niet in hoort te staan, moet hier al opvallen, vóór
   wrangler het uploadt.
2. **live-probe** -- doet een HTTP-request naar een lijst bekende gevoelige
   paden op de gedeployde hostnaam en verwacht overal 404. Dit vangt ook
   dingen die de dist-scan mist, bv. omdat Cloudflare-instellingen zelf iets
   blootleggen dat niet in `frontend/dist` zit.

Geen van beide is uitputtend -- dit is een sanity-check, geen audit.
"""

from __future__ import annotations

import argparse
import fnmatch
import logging
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

REPO = Path(__file__).resolve().parent.parent
DIST = REPO / "frontend" / "dist"

# Patronen die in een statische frontend-build niets te zoeken hebben.
VERDACHTE_PATRONEN = [
    ".env",
    ".env.*",
    "*.db",
    "*.db-journal",
    "*.db-wal",
    "*.sqlite",
    "*.sqlite3",
    "*.pem",
    "*.key",
    "id_rsa*",
    "credentials*",
    "*.p12",
    ".git",
    ".claude",
    ".devcontainer",
    ".mcp.json",
    "settings.local.json",
]

# Paden die op een gedeployde site altijd 404 horen te geven.
GEVOELIGE_PADEN = [
    "/.env",
    "/.env.local",
    "/.git/config",
    "/.git/HEAD",
    "/wrangler.generated.jsonc",
    "/wrangler.toml",
    "/package.json",
    "/pipeline/db/schema.sql",
    "/data/bipolariteit.db",
    "/.aws/credentials",
    "/id_rsa",
    "/.claude/settings.json",
    "/.claude/settings.local.json",
    "/.mcp.json",
    "/.devcontainer/.env.local",
    "/.devcontainer/devcontainer.json",
]


def scan_dist(dist: Path) -> list[Path]:
    if not dist.is_dir():
        logger.error("%s bestaat niet -- draai eerst `make build`", dist)
        raise SystemExit(1)

    treffers = []
    for pad in dist.rglob("*"):
        naam = pad.name
        if any(fnmatch.fnmatch(naam, patroon) for patroon in VERDACHTE_PATRONEN):
            treffers.append(pad.relative_to(dist))
    return treffers


def controleer_bereikbaarheid(hostnaam: str) -> None:
    """Faalt hard als de hostnaam niet oplost, in plaats van dat elk pad los
    stil overgeslagen wordt.

    Een DNS-fout op één pad betekent een DNS-fout op alle paden (zelfde host),
    dus alle paden gewoon los af laten schieten geeft een misleidend groen
    eindresultaat: "geen 200'en gevonden" terwijl er in werkelijkheid geen
    enkele check heeft plaatsgevonden.
    """
    try:
        socket.getaddrinfo(hostnaam, 443)
    except OSError as exc:
        raise SystemExit(
            f"{hostnaam} lost niet op ({exc}) -- de live-probe kan zo niets "
            "controleren. Gebruik een resolver die het domein kent (bv. "
            "`--resolve` of een andere DNS-server), of los de DNS-fout eerst op."
        ) from exc


def probeer_paden(hostnaam: str) -> list[str]:
    bereikbaar = []
    for pad in GEVOELIGE_PADEN:
        url = f"https://{hostnaam}{pad}"
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310
                status = resp.status
        except urllib.error.HTTPError as exc:
            status = exc.code
        except urllib.error.URLError as exc:
            raise SystemExit(f"kon {url} niet bereiken ({exc})") from exc

        if status == 200:
            bereikbaar.append(url)
        logger.info("%s -> %s", url, status)

    return bereikbaar


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hostnaam", help="bv. www.bipolariteit.org")
    parser.add_argument(
        "--skip-dist-scan",
        action="store_true",
        help="sla de scan van frontend/dist over (bv. als die niet lokaal aanwezig is)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    controleer_bereikbaarheid(args.hostnaam)

    fout = False

    if not args.skip_dist_scan:
        treffers = scan_dist(DIST)
        if treffers:
            fout = True
            logger.error(
                "verdachte bestanden in frontend/dist (worden publiek geserveerd): %s",
                ", ".join(str(t) for t in treffers),
            )
        else:
            logger.info("dist-scan: geen verdachte bestanden in %s", DIST)

    bereikbaar = probeer_paden(args.hostnaam)
    if bereikbaar:
        fout = True
        logger.error(
            "gevoelige paden gaven 200 in plaats van 404: %s",
            ", ".join(bereikbaar),
        )
    else:
        logger.info("live-probe: alle %d gecontroleerde paden gaven geen 200", len(GEVOELIGE_PADEN))

    if fout:
        return 1

    logger.info("geen publieke blootstelling gevonden")
    return 0


if __name__ == "__main__":
    sys.exit(main())
