"""Zet de canonieke ElecDeb60to20-brondata (data/raw/elecdebate60to16/,
opgehaald via het Makefile daar; zie docs/eval-elecdebate.md) om naar het
genormaliseerde JSONL-tussenformaat van pipeline/eval/schema.py.

Drie bronbestanden, elk uit pierpaologoffredo/ElecDeb60to20:
- full_speeches_new.csv: één rij per sprekersbeurt (datum, spreker, tekst).
  Dit is de eenheid die een EvalRecord wordt -- vergelijkbaar met een rij in
  onze eigen `documents`-tabel.
- final_relation_graph.csv: Support/Attack/Equivalent-relaties tussen
  Claim/Premise-componenten (Dependent -> Governor). We gebruiken alleen de
  Support-relaties waarvan de Governor een Claim is: dat is precies een
  standpunt MET onderbouwing, dezelfde eenheid als wat onze eigen extractie
  als "argument" beschouwt (zie docs/eval-elecdebate.md, "Definitieverschil
  argument"). Een kale Claim zonder Support-relatie wordt bewust NIET
  meegenomen: onze extractie zou zo'n kale stellingname ook afwijzen
  ("geen onderbouwing = geen argument").
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


def _find_span(text: str, snippet: str) -> tuple[int, int] | None:
    idx = text.find(snippet)
    if idx == -1:
        return None
    return idx, idx + len(snippet)


def _drop_nested_fallacies(fallacy_tuples: set[tuple[int, int, str]]) -> set[tuple[int, int, str]]:
    """De brondata annoteert soms dezelfde drogreden op twee granulariteiten
    -- bv. een volledige twee-zinsuiting én, als aparte rij, alleen de
    tweede zin ("I want us to invest in you. I want us to invest in your
    future." vs. losstaand "I want us to invest in your future.", beide
    Appeal to Emotion). Dat levert een geïsoleerde, zwakker ogende deelzin
    op als los "gouden" voorbeeld terwijl het dezelfde fallacie is. Behoudt
    per (label, positie) alleen de langste variant als een kortere span
    volledig binnen een langere met hetzelfde label valt."""
    tuples = list(fallacy_tuples)
    return {
        (start, end, label)
        for start, end, label in tuples
        if not any(
            (s2, e2) != (start, end) and s2 <= start and end <= e2 and (e2 - s2) > (end - start)
            for s2, e2, l2 in tuples if l2 == label
        )
    }


def _parse_date(date_str: str, sep: str) -> tuple[int, int, int] | None:
    """DD<sep>MM<sep>YYYY -> (dag, maand, jaar), of None. Losstaand van
    zero-padding (bv. "9/10/2016" en "09-10-2016" geven hetzelfde resultaat)."""
    parts = date_str.split(sep)
    if len(parts) != 3:
        return None
    try:
        day, month, year = (int(p) for p in parts)
    except ValueError:
        return None
    return day, month, year


def load_speeches(path: Path) -> list[dict]:
    """full_speeches_new.csv se `date`-kolom is DD/MM/YYYY."""
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    speeches = []
    for r in rows:
        date = _parse_date(r["date"], "/")
        speeches.append({
            "speaker": r["speaker"],
            "date": date,
            "year": str(date[2]) if date else None,
            "text": r["concatenated_speech"],
        })
    return speeches


def load_relations(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_fallacies(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def _index_by_speaker_date(speeches: list[dict]) -> dict:
    index = defaultdict(list)
    for i, s in enumerate(speeches):
        if s["date"] is not None:
            index[(s["speaker"], s["date"])].append(i)
    return index


def _index_by_speaker_year(speeches: list[dict]) -> dict:
    index = defaultdict(list)
    for i, s in enumerate(speeches):
        index[(s["speaker"], s["year"])].append(i)
    return index


def build_records(speeches: list[dict], relations: list[dict], fallacies: list[dict], years: set[str] | None) -> list[dict]:
    by_speaker_date = _index_by_speaker_date(speeches)
    by_speaker_year = _index_by_speaker_year(speeches)

    spans_by_speech: dict[int, set] = defaultdict(set)
    fallacies_by_speech: dict[int, set] = defaultdict(set)

    # Eén argument = claim + ALLE premisses die 'm steunen, samengevoegd tot
    # ÉÉN span (min start, max end) -- niet losse claim- en premisse-spans,
    # anders krijg je precies de kale-stellingname/onderbouwing-zonder-claim
    # fragmenten die onze eigen extractie ook zou afwijzen. Groeperen op
    # (beurt, letterlijke governor-tekst): meerdere Support-rijen met
    # dezelfde Governor zijn meerdere premisses voor diezelfde claim.
    argument_groups: dict[tuple[int, str], dict] = {}

    n_relation_not_found = n_relation_ambiguous = n_relation_cross_speaker = 0
    for row in relations:
        if row["RelationType"] != "Support" or row["G_type"] != "Claim":
            continue
        if row["Speaker1"] != row["Speaker2"]:
            # Relatie loopt over sprekersbeurten heen (bv. een premisse van
            # spreker A die een claim van spreker B aanvalt/steunt) -- valt
            # buiten onze per-beurt EvalRecord-eenheid.
            n_relation_cross_speaker += 1
            continue
        year = row["Year"]
        if years is not None and year not in years:
            continue

        speaker = row["Speaker1"]
        date = _parse_date(row["long_date"], "-")
        candidates = by_speaker_date.get((speaker, date), []) if date else []
        if not candidates:
            candidates = by_speaker_year.get((speaker, year), [])

        dependent, governor = row["Dependent"], row["Governor"]
        matches = [i for i in candidates if dependent in speeches[i]["text"] and governor in speeches[i]["text"]]
        if not matches:
            n_relation_not_found += 1
            continue
        if len(matches) > 1:
            n_relation_ambiguous += 1
        idx = matches[0]
        text = speeches[idx]["text"]
        dep_span = _find_span(text, dependent)
        gov_span = _find_span(text, governor)

        key = (idx, governor)
        group = argument_groups.setdefault(key, {"idx": idx, "starts": [], "ends": []})
        group["starts"].extend([dep_span[0], gov_span[0]])
        group["ends"].extend([dep_span[1], gov_span[1]])

    for group in argument_groups.values():
        spans_by_speech[group["idx"]].add((min(group["starts"]), max(group["ends"])))

    n_fallacy_not_found = n_fallacy_ambiguous = 0
    for row in fallacies:
        year = row["Year"]
        if years is not None and year not in years:
            continue
        speaker, text = row["Speaker"], row["text"]
        date = _parse_date(row["real_date"], " ")
        candidates = by_speaker_date.get((speaker, date), []) if date else []
        if not candidates:
            candidates = by_speaker_year.get((speaker, year), [])
        matches = [i for i in candidates if text in speeches[i]["text"]]
        if not matches:
            n_fallacy_not_found += 1
            continue
        if len(matches) > 1:
            n_fallacy_ambiguous += 1
        idx = matches[0]
        start, end = _find_span(speeches[idx]["text"], text)
        fallacies_by_speech[idx].add((start, end, row["fallacy"]))

    print(f"  claim+onderbouwing-relaties: {n_relation_not_found} niet gevonden, "
          f"{n_relation_ambiguous} ambigu (eerste match gebruikt), "
          f"{n_relation_cross_speaker} sprekersoverschrijdend (overgeslagen)")
    print(f"  drogredenen: {n_fallacy_not_found} niet gevonden, {n_fallacy_ambiguous} ambigu (eerste match gebruikt)")

    touched = set(spans_by_speech) | set(fallacies_by_speech)
    return [
        {
            "text": speeches[i]["text"],
            "speaker": speeches[i]["speaker"] or None,
            "spans": [{"start": s, "end": e} for s, e in sorted(spans_by_speech.get(i, set()))],
            "fallacies": [
                {"start": s, "end": e, "label": label}
                for s, e, label in sorted(_drop_nested_fallacies(fallacies_by_speech.get(i, set())))
            ],
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
    relations = load_relations(RAW_DIR / "final_relation_graph.csv")
    fallacies = load_fallacies(RAW_DIR / "fallacy_second_version.csv")

    records = build_records(speeches, relations, fallacies, years)

    out_path = RAW_DIR / "test.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    jaren_suffix = f" (jaren: {sorted(years)})" if years else " (alle jaren)"
    print(f"{len(records)} records -> {out_path}{jaren_suffix}")


if __name__ == "__main__":
    main()
