"""Publiceer de publieke site naar www.bipolariteit.org.

Gebruik:

    uv run python scripts/release_www.py
    uv run python scripts/release_www.py --dry-run

In tegenstelling tot scripts/release_preview.py (één Worker per tag, met
`X-Robots-Tag: noindex`) is dit een vaste hostnaam en één vaste Worker
(`bipolariteit-www`), en blijft de site indexeerbaar: er wordt geen
robots.txt geschreven die crawlers weert.

Het script gaat ervan uit dat `frontend/dist` al gebouwd is, met
PUBLIC_RELEASE_OFFICIEEL=true meegegeven aan de build -- gebruik daarom
`make release-www` en niet dit script rechtstreeks.

Vereist in de omgeving: CLOUDFLARE_API_TOKEN en CLOUDFLARE_ACCOUNT_ID.
Zie docs/release.md voor het opzetten daarvan.
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

REPO = Path(__file__).resolve().parent.parent
DIST = REPO / "frontend" / "dist"
SJABLOON = REPO / "deploy" / "wrangler.www.template.jsonc"
GEGENEREERD = REPO / "wrangler.generated.jsonc"

HOSTNAAM = "www.bipolariteit.org"
NAAM = "bipolariteit-www"


def render_config(naam: str) -> Path:
    sjabloon = SJABLOON.read_text(encoding="utf-8")
    config = sjabloon.replace("__NAAM__", naam)
    GEGENEREERD.write_text(config, encoding="utf-8")
    logger.info("wrangler-config geschreven naar %s", GEGENEREERD)
    return GEGENEREERD


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="toon de config, maar deploy niet",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    logger.info("https://%s (worker %s)", HOSTNAAM, NAAM)

    if not DIST.is_dir() or not (DIST / "index.html").is_file():
        logger.error(
            "%s bestaat niet of bevat geen index.html -- draai eerst `make build`",
            DIST,
        )
        return 1

    config = render_config(NAAM)

    if args.dry_run:
        logger.info(
            "dry-run, niet gedeployd. Config:\n%s",
            config.read_text(encoding="utf-8"),
        )
        return 0

    ontbreekt = [
        naam_var
        for naam_var in ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID")
        if not os.environ.get(naam_var)
    ]
    if ontbreekt:
        logger.error(
            "ontbrekende omgevingsvariabele(n): %s -- zie docs/release.md",
            ", ".join(ontbreekt),
        )
        return 1

    commando = [
        "npx",
        "--yes",
        "wrangler@4",
        "deploy",
        "--config",
        str(config),
    ]
    logger.info("uitvoeren: %s", " ".join(commando))
    resultaat = subprocess.run(commando, cwd=REPO)
    if resultaat.returncode != 0:
        logger.error("wrangler deploy faalde met code %s", resultaat.returncode)
        return resultaat.returncode

    logger.info("klaar: https://%s", HOSTNAAM)
    return 0


if __name__ == "__main__":
    sys.exit(main())
