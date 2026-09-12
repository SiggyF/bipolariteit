"""Publiceer de tegelpyramide-bundel van de plenaire kaart als live data naar
een publieke Hugging Face-dataset-repo.

Gebruik:

    uv run python scripts/publish_huggingface.py
    uv run python scripts/publish_huggingface.py --dry-run
    uv run python scripts/publish_huggingface.py --files data/export/plenair-map-full.pmtiles

Zelfde bundel als `scripts/publish_zenodo.py` (`data/export/zenodo/`, gevuld
door `make tiles-full`) -- de twee publiceerstappen delen zo altijd dezelfde
bestandenlijst. Het verschil zit in de bestemming, niet in de inhoud: Zenodo
is het archief (DOI/versionering, handmatig gepubliceerd, zie
`publish_zenodo.py`), Hugging Face is de live-databron -- bestanden hier
worden direct overschreven op de dataset-repo, zonder aparte publiceerstap,
zelfde "overschrijf de huidige data"-flow als `scripts/publish_data.py`'s
jsDelivr-route. Dit is mogelijk sinds CORS + HTTP Range bevestigd zijn te
werken op HF's dataset-CDN voor bestanden van deze grootte (zie issue #293) --
iets wat jsDelivr/git niet aankan boven de 100 MB-limiet.

Vereist HUGGINGFACE_TOKEN (zie .devcontainer/.env.local) met schrijfrechten
op de doelrepo.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from huggingface_hub import HfApi

from pipeline.paths import REPO_ROOT

logger = logging.getLogger(__name__)

DEFAULT_BUNDLE_DIR = REPO_ROOT / "data" / "export" / "zenodo"
DEFAULT_REPO_ID = "SiggyF/bipolariteit-pmtiles"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--files",
        nargs="+",
        type=Path,
        default=None,
        help=f"te uploaden bestanden (default: alles in {DEFAULT_BUNDLE_DIR}, zie `make tiles-full`)",
    )
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID, help=f"HF dataset-repo (default: {DEFAULT_REPO_ID})")
    parser.add_argument("--dry-run", action="store_true", help="toon wat er zou gebeuren, upload niets")
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
    logger.info("repo: %s -- %d bestand(en), %.1f MiB totaal:", args.repo_id, len(args.files), total_mb)
    for f in args.files:
        logger.info("  %s (%.1f MiB)", f, f.stat().st_size / 1024 / 1024)

    if args.dry_run:
        logger.info("dry-run, geen Hugging Face-aanroepen gedaan")
        return 0

    token = os.environ.get("HUGGINGFACE_TOKEN")
    if not token:
        logger.error("ontbrekende omgevingsvariabele HUGGINGFACE_TOKEN -- zie .devcontainer/.env.local")
        return 1

    api = HfApi(token=token)
    api.create_repo(repo_id=args.repo_id, repo_type="dataset", private=False, exist_ok=True)

    for f in args.files:
        logger.info("upload %s ...", f.name)
        api.upload_file(path_or_fileobj=f, path_in_repo=f.name, repo_id=args.repo_id, repo_type="dataset")
        logger.info("klaar: %s", f.name)

    logger.info(
        "klaar -- live op https://huggingface.co/datasets/%s (resolve-URL per bestand: "
        "https://huggingface.co/datasets/%s/resolve/main/<bestandsnaam>)",
        args.repo_id, args.repo_id,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
