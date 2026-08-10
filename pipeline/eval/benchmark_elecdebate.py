"""CLI-runner voor het ELECDEBATE60TO16-evalharnas (issue #62). Draait de
bestaande productieprompts (pipeline/extract_arguments.py,
pipeline/tag_arguments.py) ongewijzigd tegen genormaliseerde eval-records,
puur lezend -- geen DB-writes, zelfde patroon als scripts/compare_models.py.

Scope (zie docs/eval-elecdebate.md voor de motivatie): alleen argument-
herkenning (span-overlap) en de 2 drogreden-tags met een echte tegenhanger
in data/tags.toml (label_mapping.FALLACY_TAG_MAP) worden gescoord. Stance,
typology en de overige 4 ELECDEBATE-fallacy-typen worden bewust niet
vergeleken.

Extractie en tagging worden ONAFHANKELIJK van elkaar gescoord: tagging
draait op de gouden drogreden-citaten van de dataset zelf (evaluate_tagging),
niet op wat onze eigen extractie heeft gevonden (evaluate_extraction) --
anders werkt een extractiefout door in de tag-score en meet die niet meer
de tagkwaliteit op zich. "Span" (start/end-tekenposities) is alleen relevant
voor de EXTRACTIE-as: daar vergelijken we of onze extractie dezelfde
tekstgrenzen vindt als de dataset. Tagging kent geen eigen spandetectie --
net als de productie-tagprompt (tag_arguments.py) classificeert het een
compleet, al afgebakend citaat in één keer; de start/end uit de dataset
gebruiken we hier alleen om dat citaat uit de brontekst te snijden, niet om
te scoren.

Elke run bouwt VOORT op de vorige: data/export/eval/<dataset>.json bevat
welke record-indices al gescoord zijn (`evaluated_indices`), en --limit
selecteert steeds de eerstvolgende, nog niet gescoorde records i.p.v.
telkens dezelfde eerste N -- zelfde idee als extraction_attempted_at/
tagged_at in de productiepipeline (extract_arguments.py/tag_arguments.py),
maar zonder DB: de voortgang staat in de export zelf. Resultaten
(tp/fp/fn-tellingen, items) worden opgeteld bij de vorige run, niet
overschreven. Bij een ander model dan de vorige run (of --fresh) begint de
telling opnieuw -- modellen door elkaar optellen zou een misleidend
gemiddelde geven.

Kanttekening: de recordvolgorde in <dataset>.jsonl moet stabiel blijven
(zelfde `--years`, ongewijzigde brondata) wil index-gebaseerde voortgang
kloppen; bij een andere `--years`-selectie of bijgewerkte brondata kan
record-index N iets anders zijn gaan betekenen dan bij de vorige run.

Schrijft naast het stdout-rapport ook data/export/eval/<dataset>.json weg
(samenvatting + per-voorbeeld items), voor de /validatie-rapportage-pagina
in de frontend.

Gebruik (of via `make validate`, zie root-Makefile):
    uv run python -m pipeline.eval.benchmark_elecdebate <pad-naar-jsonl> <model>
    uv run python -m pipeline.eval.benchmark_elecdebate <pad-naar-jsonl> <model> --limit 20 --base-url http://localhost:1234/v1
    uv run python -m pipeline.eval.benchmark_elecdebate <pad-naar-jsonl> <model> --fresh
"""

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from pipeline.db import db
from pipeline.eval.label_mapping import FALLACY_TAG_MAP
from pipeline.eval.load_elecdebate import load_jsonl
from pipeline.eval.metrics import PrecisionRecallF1, aggregate, label_set_prf, span_overlap_prf
from pipeline.eval.schema import EvalRecord, Span
from pipeline.extract_arguments import _build_prompt as build_extract_prompt
from pipeline.extract_arguments import _extract_arguments, _extract_json as extract_json, _validate_argument
from pipeline.extract_arguments import call_llm as call_extract_llm
from pipeline.tag_arguments import _build_prompt as build_tag_prompt
from pipeline.tag_arguments import _extract_json as extract_tag_json, _validate_tags
from pipeline.tag_arguments import build_tag_catalogue, call_llm as call_tag_llm, load_valid_tags

logger = logging.getLogger(__name__)

EXPORT_DIR = Path(__file__).parent.parent.parent / "data" / "export" / "eval"

# extract_argument.md verwachtte tot voor kort altijd "Tweede Kamer-debat"
# (hardcoded) -- feitelijk onjuist voor deze dataset (Amerikaanse
# presidentsverkiezingsdebatten) en dus verwarrend voor het model. Dat stond
# in de weg van "we hergebruiken de productieprompt ongewijzigd": het was
# geen keuze om het te laten staan, het kon simpelweg niet anders zonder de
# prompt aan te passen. Nu geparametriseerd (_build_prompt's
# debate_context-argument, default blijft "Tweede Kamer-debat" voor
# productie) zodat het evalharnas een eigen, kloppende waarde meegeeft.
DEBATE_CONTEXT = "Amerikaans presidentsverkiezingsdebat"

TOPIC_NAME = "Amerikaans verkiezingsdebat"
# Eerdere versie deed alsof er één vaste pro/contra-as voor het hele debat
# bestond ("Generieke pro/contra-as: steunt de spreker het beleid..."), maar
# die is er niet: elk argument kan over een ander specifiek beleidsonderwerp
# gaan (NAFTA nu, Iran zo), dus doen alsof er één as is is net zo misleidend
# als er geen omschrijving geven. Nu eerlijk: leid de as per argument af.
TOPIC_DESCRIPTION = (
    "Dit debat behandelt uiteenlopende specifieke beleidskwesties (bijvoorbeeld "
    "economie, immigratie, buitenlands beleid) die per fragment kunnen "
    "verschillen -- er is dus geen vaste pro/contra-as voor het hele debat. "
    "Bepaal per argument zelf waar het inhoudelijk over gaat, en leid de "
    "pro/contra-richting daaruit af: steunt de spreker het besproken beleid "
    "(pro), of bekritiseert/verwerpt de spreker het (contra)?"
)

# Placeholder stance/typology voor de tagging-eval: de tag-prompt verwacht
# ze als context (zie pipeline/prompts/tag_argument.md), maar we vergelijken
# ze niet (zie docs/eval-elecdebate.md) -- geldige, neutrale waarden uit
# extract_arguments.VALID_STANCE/VALID_TYPOLOGY volstaan.
_PLACEHOLDER_STANCE = "unclear"
_PLACEHOLDER_TYPOLOGY = "other"


def _find_span(content: str, quote_text: str) -> Span | None:
    idx = content.find(quote_text)
    if idx == -1:
        return None
    return Span(idx, idx + len(quote_text))


def _overlaps(a: Span, b: Span) -> bool:
    return a.start < b.end and b.start < a.end


def evaluate_extraction(record: EvalRecord, model, base_url, timeout):
    """Draait alleen de extractiestap. Retourneert (span_prf, items) --
    items is een simpele per-span classificatie (gevonden/gemist/
    hallucinatie) voor menselijke inspectie, los van de tekenniveau-PRF die
    de samenvatting voedt."""
    prompt = build_extract_prompt(
        TOPIC_NAME, TOPIC_DESCRIPTION, record.speaker or "onbekend", None, record.text, debate_context=DEBATE_CONTEXT,
    )
    response = call_extract_llm(base_url, model, prompt, "none", timeout, 4000)
    parsed = extract_json(response.content)
    arguments = _extract_arguments(parsed)

    predicted_spans = []
    for arg in arguments:
        try:
            _validate_argument(arg)
        except ValueError as exc:
            logger.warning("  overgeslagen ongeldig argument: %s", exc)
            continue
        span = _find_span(record.text, arg["quote_text"])
        if span is None:
            logger.warning("  quote_text niet teruggevonden in brontekst, overgeslagen voor span-scoring")
        else:
            predicted_spans.append(span)

    span_prf = span_overlap_prf(predicted_spans, record.spans, len(record.text))

    items = []
    for gold in record.spans:
        found = any(_overlaps(gold, pred) for pred in predicted_spans)
        items.append({
            "speaker": record.speaker,
            "text": record.text[gold.start:gold.end],
            "outcome": "gevonden" if found else "gemist",
        })
    for pred in predicted_spans:
        if not any(_overlaps(pred, gold) for gold in record.spans):
            items.append({
                "speaker": record.speaker,
                "text": record.text[pred.start:pred.end],
                "outcome": "hallucinatie",
            })

    return span_prf, items


def evaluate_tagging(record: EvalRecord, model, base_url, timeout, tag_catalogue, tag_skeleton, valid_tags):
    """Tagt de GOUDEN drogreden-citaten van de dataset zelf (niet onze eigen
    extractie) -- zo blijft deze score onafhankelijk van extractiefouten:
    een gemiste extractie mag de tag-score niet laten meezakken (en
    omgekeerd). Elk citaat wordt als geheel geclassificeerd, precies zoals
    de productie-tagprompt met een compleet argument-citaat werkt -- geen
    eigen spandetectie hier. Retourneert (lijst van per-citaat
    label_set_prf, items, n_tag_errors)."""
    results = []
    items = []
    n_errors = 0
    for fallacy_span in record.fallacies:
        # fallacy_span.start/.end zijn de tekenposities zoals de brondataset
        # ze opslaat -- gebruikt om precies dit citaat uit record.text te
        # snijden, verder speelt de positie geen rol meer in deze functie.
        quote_text = record.text[fallacy_span.start:fallacy_span.end]
        expected = {FALLACY_TAG_MAP[fallacy_span.label]} if fallacy_span.label in FALLACY_TAG_MAP else set()
        try:
            tag_prompt = build_tag_prompt(
                TOPIC_NAME, record.speaker or "onbekend", None,
                _PLACEHOLDER_STANCE, _PLACEHOLDER_TYPOLOGY, quote_text, None,
                tag_catalogue, tag_skeleton,
            )
            tag_content, _usage = call_tag_llm(base_url, model, tag_prompt, "none", timeout)
            tag_parsed = extract_tag_json(tag_content)
            accepted = _validate_tags(tag_parsed, valid_tags)
            predicted = {sleutel for sleutel, _reden in accepted if sleutel in FALLACY_TAG_MAP.values()}
        except Exception as exc:
            logger.warning("  tagging mislukt: %s", exc)
            n_errors += 1
            continue
        results.append(label_set_prf(predicted, expected))

        if expected and expected <= predicted:
            outcome = "correct"
        elif expected:
            outcome = "gemist"
        elif predicted:
            outcome = "onterecht"
        else:
            continue  # noch verwacht, noch voorspeld -- geen toegevoegde waarde om te tonen
        items.append({
            "speaker": record.speaker,
            "quote_text": quote_text,
            "verwacht": sorted(expected),
            "voorspeld": sorted(predicted),
            "outcome": outcome,
        })

    return results, items, n_errors


def select_unevaluated(records: list[EvalRecord], evaluated_indices: set[int], limit: int) -> list[tuple[int, EvalRecord]]:
    """Volgende `limit` records (met hun index in `records`) die nog niet in
    `evaluated_indices` zitten, in volgorde."""
    selected = []
    for i, record in enumerate(records):
        if len(selected) >= limit:
            break
        if i in evaluated_indices:
            continue
        selected.append((i, record))
    return selected


def run(indexed_records: list[tuple[int, EvalRecord]], model, base_url, timeout=120.0):
    """Scoort precies de meegegeven (index, record)-paren -- de aanroeper
    bepaalt via select_unevaluated welke dat zijn."""
    conn = db.connect()
    tag_catalogue, tag_skeleton = build_tag_catalogue(conn)
    valid_tags = load_valid_tags(conn)

    span_results = []
    fallacy_results = []
    extraction_items = []
    tagging_items = []
    n_extract_errors = 0
    n_tag_errors = 0
    new_indices = []

    for n, (i, record) in enumerate(indexed_records):
        new_indices.append(i)
        try:
            span_prf, record_extraction_items = evaluate_extraction(record, model, base_url, timeout)
            span_results.append(span_prf)
            extraction_items.extend(record_extraction_items)
        except Exception as exc:
            logger.warning("[record %d] extractie mislukt: %s", i, exc)
            n_extract_errors += 1

        record_fallacy_results, record_tagging_items, record_tag_errors = evaluate_tagging(
            record, model, base_url, timeout, tag_catalogue, tag_skeleton, valid_tags
        )
        fallacy_results.extend(record_fallacy_results)
        tagging_items.extend(record_tagging_items)
        n_tag_errors += record_tag_errors
        logger.info("[record %d/%d, index %d] klaar (%d gouden drogreden-citaten getagd)",
                    n + 1, len(indexed_records), i, len(record_fallacy_results))

    return {
        "new_indices": new_indices,
        "n_extract_errors": n_extract_errors,
        "n_tag_errors": n_tag_errors,
        "span_overlap": aggregate(span_results),
        "fallacy_tags": aggregate(fallacy_results),
        "extraction_items": extraction_items,
        "tagging_items": tagging_items,
    }


def print_report(model, merged, total_records):
    n_scored = len(merged["evaluated_indices"])
    print(f"Model: {model} | {n_scored}/{total_records} records ooit gescoord "
          f"({merged['n_extract_errors']} extractiefouten, {merged['n_tag_errors']} tagfouten totaal)\n")
    span = merged["span_overlap"]
    print(f"Argumentherkenning (tekenniveau span-overlap): "
          f"precision={span.precision:.2f} recall={span.recall:.2f} f1={span.f1:.2f} "
          f"(tp={span.true_positives} fp={span.false_positives} fn={span.false_negatives})")
    fallacy = merged["fallacy_tags"]
    print(f"Drogreden-tags ({', '.join(FALLACY_TAG_MAP.values())}): "
          f"precision={fallacy.precision:.2f} recall={fallacy.recall:.2f} f1={fallacy.f1:.2f} "
          f"(tp={fallacy.true_positives} fp={fallacy.false_positives} fn={fallacy.false_negatives})")


def _prf_to_dict(r: PrecisionRecallF1) -> dict:
    return {
        "precision": round(r.precision, 3), "recall": round(r.recall, 3), "f1": round(r.f1, 3),
        "tp": r.true_positives, "fp": r.false_positives, "fn": r.false_negatives,
    }


def _prf_from_dict(d: dict) -> PrecisionRecallF1:
    """Reconstrueert een PrecisionRecallF1 puur voor de tp/fp/fn-tellingen
    (precision/recall/f1 worden altijd herberekend via aggregate(), nooit
    los ingelezen) -- zo kan een vorige run gecombineerd worden met een
    nieuwe via dezelfde aggregate()-functie die ook meerdere records
    binnen één run samenvoegt."""
    return PrecisionRecallF1(0.0, 0.0, 0.0, d["tp"], d["fp"], d["fn"])


def load_previous(export_path: Path, model: str, fresh: bool) -> dict:
    """Eerder geaccumuleerde voortgang voor dit dataset+model, of een lege
    staat als er niets is, --fresh is gevraagd, of het model afwijkt van de
    vorige run (modellen door elkaar optellen zou een misleidend gemiddelde
    geven -- dan begint de telling voor dit model opnieuw)."""
    empty = {
        "evaluated_indices": set(), "n_extract_errors": 0, "n_tag_errors": 0,
        "span_overlap": PrecisionRecallF1(0.0, 0.0, 0.0, 0, 0, 0),
        "fallacy_tags": PrecisionRecallF1(0.0, 0.0, 0.0, 0, 0, 0),
        "extraction_items": [], "tagging_items": [],
    }
    if fresh or not export_path.exists():
        return empty
    try:
        prev = json.loads(export_path.read_text())
    except (json.JSONDecodeError, OSError):
        return empty
    if prev.get("model") != model:
        logger.info("Vorige run gebruikte een ander model (%s -> %s), telling begint opnieuw voor dit model.",
                    prev.get("model"), model)
        return empty
    return {
        "evaluated_indices": set(prev.get("evaluated_indices", [])),
        "n_extract_errors": prev.get("n_extract_errors", 0),
        "n_tag_errors": prev.get("n_tag_errors", 0),
        "span_overlap": _prf_from_dict(prev["summary"]["argument_detection"]),
        "fallacy_tags": _prf_from_dict(prev["summary"]["fallacy_tags"]),
        "extraction_items": prev.get("extraction_items", []),
        "tagging_items": prev.get("tagging_items", []),
    }


def merge(previous: dict, new: dict) -> dict:
    return {
        "evaluated_indices": sorted(set(previous["evaluated_indices"]) | set(new["new_indices"])),
        "n_extract_errors": previous["n_extract_errors"] + new["n_extract_errors"],
        "n_tag_errors": previous["n_tag_errors"] + new["n_tag_errors"],
        "span_overlap": aggregate([previous["span_overlap"], new["span_overlap"]]),
        "fallacy_tags": aggregate([previous["fallacy_tags"], new["fallacy_tags"]]),
        "extraction_items": previous["extraction_items"] + new["extraction_items"],
        "tagging_items": previous["tagging_items"] + new["tagging_items"],
    }


def write_export(dataset: str, model: str, merged: dict, total_records: int) -> Path:
    """Schrijft data/export/eval/<dataset>.json -- vast pad, overschreven per
    run maar met CUMULATIEVE inhoud (zie module-docstring): bevat
    evaluated_indices zodat een volgende run weet welke records al gedaan
    zijn, i.p.v. steeds dezelfde eerste --limit records te herscoren."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    export = {
        "dataset": dataset,
        "model": model,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_records": len(merged["evaluated_indices"]),
        "total_records": total_records,
        "evaluated_indices": merged["evaluated_indices"],
        "n_extract_errors": merged["n_extract_errors"],
        "n_tag_errors": merged["n_tag_errors"],
        "summary": {
            "argument_detection": _prf_to_dict(merged["span_overlap"]),
            "fallacy_tags": _prf_to_dict(merged["fallacy_tags"]),
        },
        "extraction_items": merged["extraction_items"],
        "tagging_items": merged["tagging_items"],
    }
    out_path = EXPORT_DIR / f"{dataset}.json"
    out_path.write_text(json.dumps(export, ensure_ascii=False, indent=2))
    return out_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl_path", help="pad naar genormaliseerde JSONL (zie pipeline/eval/schema.py)")
    parser.add_argument("model")
    parser.add_argument("--dataset", default="elecdebate60to16", help="datasetnaam voor de export (default: %(default)s)")
    parser.add_argument("--limit", type=int, default=15, help="max aantal NIEUWE records deze run (default 15)")
    parser.add_argument("--fresh", action="store_true", help="negeer eerder geaccumuleerde voortgang en begin opnieuw")
    parser.add_argument("--base-url", default="http://localhost:1234/v1")
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    records = load_jsonl(args.jsonl_path)
    export_path = EXPORT_DIR / f"{args.dataset}.json"
    previous = load_previous(export_path, args.model, args.fresh)

    indexed_records = select_unevaluated(records, previous["evaluated_indices"], args.limit)
    if not indexed_records:
        print(f"Alle {len(records)} records al gescoord voor model {args.model} -- geen nieuwe steekproef "
              f"(gebruik --fresh om opnieuw te beginnen).\n")
        merged = merge(previous, {"new_indices": [], "n_extract_errors": 0, "n_tag_errors": 0,
                                   "span_overlap": PrecisionRecallF1(0.0, 0.0, 0.0, 0, 0, 0),
                                   "fallacy_tags": PrecisionRecallF1(0.0, 0.0, 0.0, 0, 0, 0),
                                   "extraction_items": [], "tagging_items": []})
        print_report(args.model, merged, len(records))
        return

    new = run(indexed_records, args.model, args.base_url, args.timeout)
    merged = merge(previous, new)
    print_report(args.model, merged, len(records))
    out_path = write_export(args.dataset, args.model, merged, len(records))
    print(f"\nExport geschreven naar {out_path} ({len(merged['evaluated_indices'])}/{len(records)} records ooit gescoord)")


if __name__ == "__main__":
    main()
