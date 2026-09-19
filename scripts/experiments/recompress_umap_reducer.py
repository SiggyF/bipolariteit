"""
Herpakt een al gefitte UMAP-reducer (pipeline/plenary_map/umap.py
--export-reducer) met joblib-compressie, zonder de dure UMAP-fit opnieuw te
draaien. Alleen nodig als een eerdere run zonder compress= is weggeschreven
(zag ooit 10+ GiB ongecomprimeerd voor de volle dataset).

Gebruik:
    uv run python scripts/experiments/recompress_umap_reducer.py \
        data/plenair-map/umap-reducer-full.joblib
"""
import argparse
from pathlib import Path

import joblib


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("reducer_path", type=Path)
    parser.add_argument("--compress", type=int, default=3, help="joblib-compressieniveau 1-9")
    args = parser.parse_args()

    before = args.reducer_path.stat().st_size
    reducer = joblib.load(args.reducer_path)
    joblib.dump(reducer, args.reducer_path, compress=args.compress)
    after = args.reducer_path.stat().st_size

    print(f"{args.reducer_path}: {before / 1e9:.2f} GB -> {after / 1e9:.2f} GB (compress={args.compress})")


if __name__ == "__main__":
    main()
