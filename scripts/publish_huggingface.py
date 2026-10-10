"""Publiceer de tegelpyramide-bundel van de plenaire kaart als live data naar
een publieke Hugging Face-dataset-repo.

Gebruik:

    uv run python scripts/publish_huggingface.py
    uv run python scripts/publish_huggingface.py --dry-run
    uv run python scripts/publish_huggingface.py --files data/export/plenair-map/plenair-map-full.pmtiles

Bestanden komen te staan onder een submap in de dataset-repo (--repo-subdir,
default "plenair-map") -- in tegenstelling tot Zenodo's platte bucket
(waar een "/" in de bestandsnaam slechts een S3-key-truc is, zie
docs/data-layout.md) ondersteunt de Hugging Face Hub-API `path_in_repo` als
een echt pad. Eén submap per dataset houdt de repo opgeruimd nu er zowel de
volle-dataset-bundel (`make publish-huggingface`) als de kleine
alledaagse pmtiles (`make publish-tiles`) in dezelfde repo terechtkomen.

Zelfde bundel als `scripts/publish_zenodo.py`
(`data/export/plenair-map/bundel/`, gevuld door `make tiles-full`) -- de
twee publiceerstappen delen zo altijd dezelfde
bestandenlijst. Het verschil zit in de bestemming, niet in de inhoud: Zenodo
is het archief (DOI/versionering, handmatig gepubliceerd, zie
`publish_zenodo.py`), Hugging Face is de live-databron -- bestanden hier
worden direct overschreven op de dataset-repo, zonder aparte publiceerstap,
zelfde "overschrijf de huidige data"-flow als `scripts/publish_data.py`'s
jsDelivr-route. Dit is mogelijk sinds CORS + HTTP Range bevestigd zijn te
werken op HF's dataset-CDN voor bestanden van deze grootte (zie issue #293) --
iets wat jsDelivr/git niet aankan boven de 100 MB-limiet.

De gefitte UMAP-reducer (`umap-reducer-*.joblib`, ruim 10 GB op de volle
dataset) gaat standaard NIET mee: de site leest hem niet (alleen
`scripts/argument_tree/transform_arguments_into_umap.py` lokaal), dus hij
hoort bij het Zenodo-archief en niet bij de live-data. Met `--include-reducer`
gaat hij toch mee.

Vereist HUGGINGFACE_TOKEN (zie .devcontainer/.env.local) met schrijfrechten
op de doelrepo.
"""

from __future__ import annotations

import argparse
import fnmatch
import logging
import os
import sys
from pathlib import Path

from huggingface_hub import HfApi

from pipeline.paths import REPO_ROOT

logger = logging.getLogger(__name__)

DEFAULT_BUNDLE_DIR = REPO_ROOT / "data" / "export" / "plenair-map" / "bundel"
DEFAULT_REPO_ID = "SiggyF/bipolariteit-pmtiles"
DEFAULT_REPO_SUBDIR = "plenair-map"
# Bestanden die niet standaard naar de live-repo gaan (zie de moduledocstring).
REDUCER_GLOB = "umap-reducer-*.joblib"


def select_bundle_files(bundle_dir: Path, include_reducer: bool = False) -> tuple[list[Path], list[Path]]:
    """Alle bestanden in de bundel, gesorteerd, en welke daarvan overgeslagen zijn."""
    files = sorted(f for f in bundle_dir.iterdir() if f.is_file())
    if include_reducer:
        return files, []
    skipped = [f for f in files if fnmatch.fnmatch(f.name, REDUCER_GLOB)]
    return [f for f in files if f not in skipped], skipped


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
    parser.add_argument(
        "--repo-subdir",
        default=DEFAULT_REPO_SUBDIR,
        help=f"submap in de dataset-repo waaronder de bestanden komen (default: {DEFAULT_REPO_SUBDIR!r}, "
        "leeg '' voor de repo-root)",
    )
    parser.add_argument(
        "--include-reducer",
        action="store_true",
        help=f"neem ook {REDUCER_GLOB} mee (standaard overgeslagen: ruim 10 GB en niet door de site gelezen)",
    )
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
        args.files, skipped = select_bundle_files(DEFAULT_BUNDLE_DIR, args.include_reducer)
        for f in skipped:
            logger.info("overgeslagen: %s (%.1f GiB, --include-reducer om mee te sturen)", f.name, f.stat().st_size / 1024**3)
        if not args.files:
            logger.error("%s is leeg -- draai eerst `make tiles-full`", DEFAULT_BUNDLE_DIR)
            return 1

    missing = [str(f) for f in args.files if not f.is_file()]
    if missing:
        logger.error("bestand(en) niet gevonden: %s", ", ".join(missing))
        return 1

    subdir = args.repo_subdir.strip("/")

    def path_in_repo(f: Path) -> str:
        return f"{subdir}/{f.name}" if subdir else f.name

    total_mb = sum(f.stat().st_size for f in args.files) / 1024 / 1024
    logger.info(
        "repo: %s%s -- %d bestand(en), %.1f MiB totaal:",
        args.repo_id, f"/{subdir}" if subdir else "", len(args.files), total_mb,
    )
    for f in args.files:
        logger.info("  %s -> %s (%.1f MiB)", f, path_in_repo(f), f.stat().st_size / 1024 / 1024)

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
        target = path_in_repo(f)
        logger.info("upload %s ...", target)
        api.upload_file(path_or_fileobj=f, path_in_repo=target, repo_id=args.repo_id, repo_type="dataset")
        logger.info(
            "klaar: %s -- live op https://huggingface.co/datasets/%s/resolve/main/%s",
            target, args.repo_id, target,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
