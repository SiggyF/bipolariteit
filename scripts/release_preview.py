"""Publiceer een getagde preview-release naar Cloudflare Workers.

Gebruik:

    uv run python scripts/release_preview.py v0.3.0
    uv run python scripts/release_preview.py v0.3.0 --dry-run

De tag wordt omgezet naar een hostnaam van de vorm
`<tag>-preview.bipolariteit.org`. Bewust één niveau onder het domein: het
gratis Universal SSL-certificaat van Cloudflare dekt `*.bipolariteit.org`,
maar niets dieper dan dat.

Het script gaat ervan uit dat `frontend/dist` al gebouwd is (`make build`).
De GitHub Action doet dat vlak hiervoor; lokaal moet je het zelf doen.

Vereist in de omgeving: CLOUDFLARE_API_TOKEN en CLOUDFLARE_ACCOUNT_ID.
Zie docs/release.md voor het opzetten daarvan.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

REPO = Path(__file__).resolve().parent.parent
DIST = REPO / "frontend" / "dist"
SJABLOON = REPO / "deploy" / "wrangler.template.jsonc"
GEGENEREERD = REPO / "wrangler.generated.jsonc"

DOMEIN = "bipolariteit.org"
ACHTERVOEGSEL = "-preview"
NAAM_PREFIX = "bipolariteit-"

# Een DNS-label mag maximaal 63 tekens zijn, en een Worker-naam ook. De
# Worker-naam is de langste van de twee (prefix + slug + achtervoegsel), dus
# die bepaalt de ruimte die de slug overhoudt.
MAX_SLUG = 63 - len(NAAM_PREFIX) - len(ACHTERVOEGSEL)


def slug_van_tag(tag: str) -> str:
	"""Zet een git-tag om naar een geldig DNS-label.

	Punten en schuine strepen zijn niet toegestaan in een label (een punt zou
	er zelfs een extra niveau van maken, en dáár reikt het certificaat niet),
	dus die worden streepjes: `v0.2.0-status-and-filters` ->
	`v0-2-0-status-and-filters`.
	"""
	slug = tag.strip().lower()
	slug = re.sub(r"[^a-z0-9]+", "-", slug)
	slug = slug.strip("-")

	if not slug:
		raise ValueError(f"tag {tag!r} levert een lege hostnaam op")
	if len(slug) > MAX_SLUG:
		afgekapt = slug[:MAX_SLUG].rstrip("-")
		logger.warning(
			"tag %r is te lang voor een hostnaam (%d > %d tekens), afgekapt tot %r",
			tag,
			len(slug),
			MAX_SLUG,
			afgekapt,
		)
		slug = afgekapt
	if slug[0].isdigit():
		# Toegestaan in DNS, maar een Worker-naam moet met een letter beginnen;
		# de prefix vangt dat al op. Alleen loggen zodat het niet verrast.
		logger.debug("slug %r begint met een cijfer", slug)

	return slug


def schrijf_robots(dist: Path) -> None:
	"""Zet een robots.txt die alles weert in de build.

	De preview is niet met een wachtwoord afgeschermd -- de URL is het enige
	dat hem beschermt. Indexering is dan het lek dat je niet meer terugdraait,
	dus zowel robots.txt als de `X-Robots-Tag`-header uit deploy/worker.js.
	"""
	robots = dist / "robots.txt"
	robots.write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
	logger.info("robots.txt geschreven (alles geweerd) naar %s", robots)


def render_config(naam: str, hostnaam: str) -> Path:
	sjabloon = SJABLOON.read_text(encoding="utf-8")
	config = sjabloon.replace("__NAAM__", naam).replace("__HOSTNAAM__", hostnaam)
	GEGENEREERD.write_text(config, encoding="utf-8")
	logger.info("wrangler-config geschreven naar %s", GEGENEREERD)
	return GEGENEREERD


def main(argv: list[str] | None = None) -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("tag", help="git-tag, bijvoorbeeld v0.3.0")
	parser.add_argument(
		"--dry-run",
		action="store_true",
		help="toon de hostnaam en de config, maar deploy niet",
	)
	args = parser.parse_args(argv)

	logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

	slug = slug_van_tag(args.tag)
	hostnaam = f"{slug}{ACHTERVOEGSEL}.{DOMEIN}"
	naam = f"{NAAM_PREFIX}{slug}{ACHTERVOEGSEL}"

	logger.info("tag %s -> https://%s (worker %s)", args.tag, hostnaam, naam)

	if not DIST.is_dir() or not (DIST / "index.html").is_file():
		logger.error(
			"%s bestaat niet of bevat geen index.html -- draai eerst `make build`",
			DIST,
		)
		return 1

	schrijf_robots(DIST)
	config = render_config(naam, hostnaam)

	if args.dry_run:
		logger.info("dry-run, niet gedeployd. Config:\n%s", config.read_text())
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

	logger.info("klaar: https://%s", hostnaam)
	logger.info(
		"het certificaat kan een paar minuten nodig hebben; tot die tijd kan "
		"de browser een beveiligingswaarschuwing tonen"
	)
	return 0


if __name__ == "__main__":
	sys.exit(main())
