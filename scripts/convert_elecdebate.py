"""Zet `data/raw/elecdebate60to16/pos_{train,test}_set.csv` (uit
pierpaologoffredo/FallacyDetection, zie docs/eval-elecdebate.md) om naar het
genormaliseerde JSONL-tussenformaat van pipeline/eval/schema.py.

Elke CSV-rij is één fallacieuze span (Fallacy-tekst + Label + arg_comp) binnen
een grotere paragraaf (Context). Meerdere rijen kunnen dezelfde Context delen
(meerdere fallacies in één paragraaf), dus rijen worden per Context
gegroepeerd tot één EvalRecord met meerdere spans/fallacies.

Output blijft, net als de brondata, onder data/raw/ (gitignored) staan --
dit is afgeleide inhoud van een dataset die we niet zelf herdistribueren.

Gebruik:
    uv run python scripts/convert_elecdebate.py
"""

import csv
import json
from pathlib import Path

RAW_DIR = Path(__file__).parent.parent / "data" / "raw" / "elecdebate60to16"
SPLITS = ["train", "test"]

# arg_comp-waarden die duiden op een afgebakende argumentcomponent (i.t.t.
# leeg, bv. bij een deel van de Slogans-rijen zonder claim/premise-structuur).
ARGUMENT_COMPONENT_VALUES = {"Claim", "Premise"}


def _find_span(context: str, snippet: str) -> tuple[int, int] | None:
    idx = context.find(snippet)
    if idx == -1:
        return None
    return idx, idx + len(snippet)


def convert(csv_path: Path) -> list[dict]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Sets i.p.v. lists: de brondata bevat rijen die exact dezelfde
    # (Context, Fallacy, Label)-combinatie herhalen (bv. omdat arg_comp
    # apart voor Claim én Premise geannoteerd is op dezelfde tekst) --
    # inhoudelijk dezelfde span meerdere keren opnemen voegt niets toe.
    by_context: dict[str, dict] = {}
    n_not_found = 0
    for row in rows:
        context = row["Context"]
        record = by_context.setdefault(context, {"text": context, "speaker": None, "spans": set(), "fallacies": set()})

        span = _find_span(context, row["Fallacy"])
        if span is None:
            n_not_found += 1
            continue
        start, end = span

        if row["arg_comp"] in ARGUMENT_COMPONENT_VALUES:
            record["spans"].add((start, end))
        record["fallacies"].add((start, end, row["Label"]))

    if n_not_found:
        print(f"  waarschuwing: {n_not_found} rij(en) overgeslagen, snippet niet gevonden in Context")

    return [
        {
            "text": record["text"],
            "speaker": record["speaker"],
            "spans": [{"start": start, "end": end} for start, end in sorted(record["spans"])],
            "fallacies": [{"start": start, "end": end, "label": label} for start, end, label in sorted(record["fallacies"])],
        }
        for record in by_context.values()
    ]


def main():
    for split in SPLITS:
        csv_path = RAW_DIR / f"pos_{split}_set.csv"
        if not csv_path.exists():
            print(f"{split}: {csv_path} niet gevonden, overgeslagen")
            continue
        records = convert(csv_path)
        out_path = RAW_DIR / f"{split}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"{split}: {len(records)} records -> {out_path}")


if __name__ == "__main__":
    main()
