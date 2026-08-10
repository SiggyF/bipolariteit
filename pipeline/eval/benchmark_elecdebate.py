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
draait op de gouden drogreden-spans van de dataset zelf (evaluate_tagging),
niet op wat onze eigen extractie toevallig heeft gevonden (evaluate_
extraction) -- anders werkt een extractiefout door in de tag-score en meet
die niet meer de tagkwaliteit op zich.

Gebruik:
    uv run python -m pipeline.eval.benchmark_elecdebate <pad-naar-jsonl> <model>
    uv run python -m pipeline.eval.benchmark_elecdebate <pad-naar-jsonl> <model> --base-url http://localhost:1234/v1
"""

import argparse
import logging

from pipeline.db import db
from pipeline.eval.label_mapping import FALLACY_TAG_MAP
from pipeline.eval.load_elecdebate import load_jsonl
from pipeline.eval.metrics import aggregate, label_set_prf, span_overlap_prf
from pipeline.eval.schema import EvalRecord, Span
from pipeline.extract_arguments import _build_prompt as build_extract_prompt
from pipeline.extract_arguments import _extract_arguments, _extract_json as extract_json, _validate_argument
from pipeline.extract_arguments import call_llm as call_extract_llm
from pipeline.tag_arguments import _build_prompt as build_tag_prompt
from pipeline.tag_arguments import _extract_json as extract_tag_json, _validate_tags
from pipeline.tag_arguments import build_tag_catalogue, call_llm as call_tag_llm, load_valid_tags

logger = logging.getLogger(__name__)

TOPIC_NAME = "ELECDEBATE60TO16-benchmark"
TOPIC_DESCRIPTION = (
    "Benchmark tegen Amerikaanse presidentsverkiezingsdebatten (1960-2016/2020, "
    "ELECDEBATE60TO16-dataset). Alleen argumentherkenning en drogreden-tags "
    "worden gescoord; stance en typology worden bewust niet vergeleken "
    "(zie docs/eval-elecdebate.md)."
)


def _find_span(content: str, quote_text: str) -> Span | None:
    idx = content.find(quote_text)
    if idx == -1:
        return None
    return Span(idx, idx + len(quote_text))


# Placeholder stance/typology voor de tagging-eval: de tag-prompt verwacht
# ze als context (zie pipeline/prompts/tag_argument.md), maar we vergelijken
# ze niet (zie docs/eval-elecdebate.md) -- geldige, neutrale waarden uit
# extract_arguments.VALID_STANCE/VALID_TYPOLOGY volstaan.
_PLACEHOLDER_STANCE = "unclear"
_PLACEHOLDER_TYPOLOGY = "other"


def evaluate_extraction(record: EvalRecord, model, base_url, timeout):
    """Draait alleen de extractiestap. Retourneert span_prf."""
    prompt = build_extract_prompt(TOPIC_NAME, TOPIC_DESCRIPTION, record.speaker or "onbekend", None, record.text)
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

    return span_overlap_prf(predicted_spans, record.spans, len(record.text))


def evaluate_tagging(record: EvalRecord, model, base_url, timeout, tag_catalogue, tag_skeleton, valid_tags):
    """Tagt de GOUDEN drogreden-spans van de dataset zelf (niet onze eigen
    extractie) -- zo blijft deze score onafhankelijk van extractiefouten:
    een gemiste extractie mag de tag-score niet laten meezakken (en
    omgekeerd). Retourneert (lijst van per-span label_set_prf, n_tag_errors)."""
    results = []
    n_errors = 0
    for fallacy_span in record.fallacies:
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

    return results, n_errors


def run(records, model, base_url, timeout=120.0):
    conn = db.connect()
    tag_catalogue, tag_skeleton = build_tag_catalogue(conn)
    valid_tags = load_valid_tags(conn)

    span_results = []
    fallacy_results = []
    n_extract_errors = 0
    n_tag_errors = 0

    for i, record in enumerate(records):
        try:
            span_results.append(evaluate_extraction(record, model, base_url, timeout))
        except Exception as exc:
            logger.warning("[record %d] extractie mislukt: %s", i, exc)
            n_extract_errors += 1

        record_fallacy_results, record_tag_errors = evaluate_tagging(
            record, model, base_url, timeout, tag_catalogue, tag_skeleton, valid_tags
        )
        fallacy_results.extend(record_fallacy_results)
        n_tag_errors += record_tag_errors
        logger.info("[record %d/%d] klaar (%d gouden drogreden-spans getagd)", i + 1, len(records), len(record_fallacy_results))

    return {
        "n_records": len(records),
        "n_extract_errors": n_extract_errors,
        "n_tag_errors": n_tag_errors,
        "span_overlap": aggregate(span_results),
        "fallacy_tags": aggregate(fallacy_results),
    }


def print_report(model, stats):
    print(f"Model: {model} | {stats['n_records']} records "
          f"({stats['n_extract_errors']} extractiefouten, {stats['n_tag_errors']} tagfouten)\n")
    span = stats["span_overlap"]
    print(f"Argumentherkenning (tekenniveau span-overlap): "
          f"precision={span.precision:.2f} recall={span.recall:.2f} f1={span.f1:.2f} "
          f"(tp={span.true_positives} fp={span.false_positives} fn={span.false_negatives})")
    fallacy = stats["fallacy_tags"]
    print(f"Drogreden-tags ({', '.join(FALLACY_TAG_MAP.values())}): "
          f"precision={fallacy.precision:.2f} recall={fallacy.recall:.2f} f1={fallacy.f1:.2f} "
          f"(tp={fallacy.true_positives} fp={fallacy.false_positives} fn={fallacy.false_negatives})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", help="pad naar genormaliseerde JSONL (zie pipeline/eval/schema.py)")
    parser.add_argument("model")
    parser.add_argument("--base-url", default="http://localhost:1234/v1")
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    records = load_jsonl(args.dataset)
    stats = run(records, args.model, args.base_url, args.timeout)
    print_report(args.model, stats)


if __name__ == "__main__":
    main()
