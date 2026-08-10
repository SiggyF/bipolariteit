"""Tests voor de pure hulpfuncties in pipeline/eval/benchmark_elecdebate.py
(issue #62). De volledige runner (evaluate_extraction/evaluate_tagging/run) roept een LLM en de
database aan en wordt daarom niet hier maar handmatig geverifieerd, zie
docs/eval-elecdebate.md."""

import json

from pipeline.eval.benchmark_elecdebate import _find_span, _overlaps, write_export
import pipeline.eval.benchmark_elecdebate as benchmark_elecdebate
from pipeline.eval.metrics import PrecisionRecallF1
from pipeline.eval.schema import Span


def test_find_span_locates_exact_substring():
    content = "Mijn tegenstander is een leugenaar. Bovendien is zijn plan slecht."
    assert _find_span(content, "Bovendien is zijn plan slecht.") == Span(36, 66)


def test_find_span_returns_none_when_not_found():
    content = "Een tekst zonder het gezochte citaat."
    assert _find_span(content, "dit citaat komt hier niet in voor") is None


def test_overlaps_true_for_partial_overlap():
    assert _overlaps(Span(0, 10), Span(5, 15)) is True


def test_overlaps_false_for_disjoint_spans():
    assert _overlaps(Span(0, 10), Span(10, 20)) is False


def test_overlaps_true_when_one_contains_the_other():
    assert _overlaps(Span(0, 20), Span(5, 10)) is True


def test_write_export_writes_expected_shape(tmp_path, monkeypatch):
    monkeypatch.setattr(benchmark_elecdebate, "EXPORT_DIR", tmp_path)
    stats = {
        "n_records": 3,
        "n_extract_errors": 0,
        "n_tag_errors": 0,
        "span_overlap": PrecisionRecallF1(0.5, 0.5, 0.5, 5, 5, 5),
        "fallacy_tags": PrecisionRecallF1(1.0, 0.2, 0.33, 1, 0, 4),
        "extraction_items": [{"speaker": "TEST", "text": "een citaat", "outcome": "gevonden"}],
        "tagging_items": [{"speaker": "TEST", "quote_text": "een citaat", "verwacht": ["Drogreden-Ad-Hominem"], "voorspeld": [], "outcome": "gemist"}],
    }

    out_path = write_export("test-dataset", "test-model", stats)

    assert out_path == tmp_path / "test-dataset.json"
    written = json.loads(out_path.read_text())
    assert written["dataset"] == "test-dataset"
    assert written["model"] == "test-model"
    assert written["summary"]["argument_detection"]["f1"] == 0.5
    assert written["summary"]["fallacy_tags"]["tp"] == 1
    assert written["extraction_items"] == stats["extraction_items"]
    assert written["tagging_items"] == stats["tagging_items"]
