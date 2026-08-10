"""Zet de canonieke ElecDeb60to20-brondata (data/raw/elecdebate60to16/,
opgehaald via het Makefile daar; zie docs/eval-elecdebate.md) om naar het
genormaliseerde JSONL-tussenformaat van pipeline/eval/schema.py.

Drie bronbestanden, elk uit pierpaologoffredo/ElecDeb60to20:
- full_speeches_new.csv: één rij per sprekersbeurt (datum, spreker, tekst).
  Dit is de eenheid die een EvalRecord wordt -- vergelijkbaar met een rij in
  onze eigen `documents`-tabel.
- full_components.csv: elke geannoteerde claim/premise-zin, ONGEACHT of hij
  ook een drogreden is (44k+ rijen) -- alleen een `Year`-kolom, geen
  spreker/datum, dus een zin wordt gezocht binnen alle beurten van dat jaar.
- fallacy_second_version.csv: drogreden-annotaties MET spreker+datum, dus
  hier kan wel exact op (jaar, spreker) gematcht worden voor we op tekst
  zoeken.

Zoeken gebeurt op tekstsubstring (zelfde aanpak als _find_span elders in het
evalharnas). Bij meerdere kandidaat-beurten wordt de eerste gebruikt en het
aantal ambigue/niet-gevonden matches gerapporteerd -- geen giswerk, wel
zichtbaar hoeveel er niet uniek op te lossen was.

Gebruik:
    uv run python scripts/convert_elecdebate.py
    uv run python scripts/convert_elecdebate.py --years all
"""

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

RAW_DIR = Path(__file__).parent.parent / "data" / "raw" / "elecdebate60to16"
DEFAULT_YEARS = {"2016", "2020"}

ARGUMENT_COMPONENT_TAGS = {"Claim", "Premise"}


def _find_span(text: str, snippet: str) -> tuple[int, int] | None:
    idx = text.find(snippet)
    if idx == -1:
        return None
    return idx, idx + len(snippet)


def _year_of(date: str) -> str | None:
    """full_speeches_new.csv se `date`-kolom is DD/MM/YYYY."""
    parts = date.split("/")
    return parts[-1] if len(parts) == 3 else None


def load_speeches(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [{"speaker": r["speaker"], "year": _year_of(r["date"]), "text": r["concatenated_speech"]} for r in rows]


def load_components(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_fallacies(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def build_records(speeches: list[dict], components: list[dict], fallacies: list[dict], years: set[str] | None) -> list[dict]:
    by_year: dict[str, list[int]] = defaultdict(list)
    for i, s in enumerate(speeches):
        by_year[s["year"]].append(i)

    spans_by_speech: dict[int, set] = defaultdict(set)
    fallacies_by_speech: dict[int, set] = defaultdict(set)

    n_component_not_found = n_component_ambiguous = 0
    for row in components:
        year = row["Year"]
        if years is not None and year not in years:
            continue
        sentence = row["Sentence"]
        candidates = [i for i in by_year.get(year, []) if sentence in speeches[i]["text"]]
        if not candidates:
            n_component_not_found += 1
            continue
        if len(candidates) > 1:
            n_component_ambiguous += 1
        span = _find_span(speeches[candidates[0]]["text"], sentence)
        spans_by_speech[candidates[0]].add(span)

    n_fallacy_not_found = n_fallacy_ambiguous = 0
    for row in fallacies:
        year = row["Year"]
        if years is not None and year not in years:
            continue
        speaker, text = row["Speaker"], row["text"]
        candidates = [i for i in by_year.get(year, []) if speeches[i]["speaker"] == speaker and text in speeches[i]["text"]]
        if not candidates:
            n_fallacy_not_found += 1
            continue
        if len(candidates) > 1:
            n_fallacy_ambiguous += 1
        idx = candidates[0]
        start, end = _find_span(speeches[idx]["text"], text)
        fallacies_by_speech[idx].add((start, end, row["fallacy"]))

    print(f"  componenten: {n_component_not_found} niet gevonden, {n_component_ambiguous} ambigu (eerste match gebruikt)")
    print(f"  drogredenen: {n_fallacy_not_found} niet gevonden, {n_fallacy_ambiguous} ambigu (eerste match gebruikt)")

    touched = set(spans_by_speech) | set(fallacies_by_speech)
    return [
        {
            "text": speeches[i]["text"],
            "speaker": speeches[i]["speaker"] or None,
            "spans": [{"start": s, "end": e} for s, e in sorted(spans_by_speech.get(i, set()))],
            "fallacies": [{"start": s, "end": e, "label": label} for s, e, label in sorted(fallacies_by_speech.get(i, set()))],
        }
        for i in sorted(touched)
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--years", default=",".join(sorted(DEFAULT_YEARS)),
        help="komma-gescheiden debatjaren, of 'all' voor de volledige dataset (default: %(default)s)",
    )
    args = parser.parse_args()
    years = None if args.years == "all" else set(args.years.split(","))

    speeches = load_speeches(RAW_DIR / "full_speeches_new.csv")
    components = load_components(RAW_DIR / "full_components.csv")
    fallacies = load_fallacies(RAW_DIR / "fallacy_second_version.csv")

    records = build_records(speeches, components, fallacies, years)

    out_path = RAW_DIR / "test.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    jaren_suffix = f" (jaren: {sorted(years)})" if years else " (alle jaren)"
    print(f"{len(records)} records -> {out_path}{jaren_suffix}")


if __name__ == "__main__":
    main()
