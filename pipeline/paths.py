from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    """Walk upward until we find the repo's pyproject.toml, rather than
    counting a fixed number of parent directories (fragile if this file
    ever moves)."""
    for candidate in [start, *start.parents]:
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise RuntimeError(f"kon pyproject.toml (repo root) niet vinden vanaf {start}")


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
RAW_DIR_TWEEDE_KAMER = REPO_ROOT / "data" / "raw" / "tweede_kamer"
