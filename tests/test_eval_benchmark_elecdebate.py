"""Tests voor de pure hulpfuncties in pipeline/eval/benchmark_elecdebate.py
(issue #62). De volledige runner (evaluate_extraction/evaluate_tagging/run) roept een LLM en de
database aan en wordt daarom niet hier maar handmatig geverifieerd, zie
docs/eval-elecdebate.md."""

import json

from pipeline.eval.benchmark_elecdebate import (
    _attach_tags_to_extraction_items, _context_window, _find_span, _overlaps,
    load_previous, merge, select_unevaluated, write_export,
)
import pipeline.eval.benchmark_elecdebate as benchmark_elecdebate
from pipeline.eval.metrics import PrecisionRecallF1
from pipeline.eval.schema import EvalRecord, Span


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


def test_context_window_includes_surrounding_text():
    text = "Eerste zin hier. Het woord is een drogreden. Laatste zin hier."
    start = text.index("drogreden")
    end = start + len("drogreden")
    context = _context_window(text, start, end, radius=50)
    assert "Eerste zin" in context
    assert "Laatste zin" in context
    assert "drogreden" in context


def test_context_window_marks_truncation_with_ellipsis():
    text = "a" * 500 + " target " + "b" * 500
    start = text.index("target")
    end = start + len("target")
    context = _context_window(text, start, end, radius=50)
    assert context.startswith("…")
    assert context.endswith("…")


def test_context_window_no_ellipsis_when_covers_whole_text():
    text = "Kort tekstje met een woord erin."
    start = text.index("woord")
    end = start + len("woord")
    context = _context_window(text, start, end, radius=1000)
    assert context == text
    assert "…" not in context


def test_attach_tags_to_extraction_items_copies_overlapping_tags():
    extraction_items = [
        {"start": 0, "end": 20, "outcome": "gevonden"},
        {"start": 50, "end": 60, "outcome": "gemist"},
    ]
    tagging_items = [
        {"start": 5, "end": 10, "verwacht": ["Debatzet-Persoon-Aanspreken"], "voorspeld": []},
    ]

    _attach_tags_to_extraction_items(extraction_items, tagging_items)

    assert extraction_items[0]["verwacht"] == ["Debatzet-Persoon-Aanspreken"]
    assert extraction_items[0]["voorspeld"] == []
    assert extraction_items[1]["verwacht"] == []
    assert extraction_items[1]["voorspeld"] == []


def test_attach_tags_to_extraction_items_no_llm_call_needed():
    """Zuiver een in-memory merge -- geen call_llm-mocking nodig, bewijst
    dat dit puur weergavelogica is, geen extra evaluatie."""
    extraction_items = [{"start": 0, "end": 5, "outcome": "gevonden"}]
    _attach_tags_to_extraction_items(extraction_items, tagging_items=[])
    assert extraction_items[0]["verwacht"] == []
    assert extraction_items[0]["voorspeld"] == []


def _sample_merged():
    return {
        "evaluated_indices": [0, 1, 2],
        "n_extract_errors": 0,
        "n_tag_errors": 0,
        "span_overlap": PrecisionRecallF1(0.5, 0.5, 0.5, 5, 5, 5),
        "fallacy_tags": PrecisionRecallF1(1.0, 0.2, 0.33, 1, 0, 4),
        "extraction_items": [{"speaker": "TEST", "text": "een citaat", "outcome": "gevonden"}],
        "tagging_items": [{"speaker": "TEST", "quote_text": "een citaat", "verwacht": ["Debatzet-Persoon-Aanspreken"], "voorspeld": [], "outcome": "gemist"}],
    }


def test_write_export_writes_expected_shape(tmp_path, monkeypatch):
    monkeypatch.setattr(benchmark_elecdebate, "EXPORT_DIR", tmp_path)
    merged = _sample_merged()

    out_path = write_export("test-dataset", "test-model", merged, total_records=10)

    assert out_path == tmp_path / "test-dataset.json"
    written = json.loads(out_path.read_text())
    assert written["dataset"] == "test-dataset"
    assert written["model"] == "test-model"
    assert written["n_records"] == 3
    assert written["total_records"] == 10
    assert written["evaluated_indices"] == [0, 1, 2]
    assert written["summary"]["argument_detection"]["f1"] == 0.5
    assert written["summary"]["fallacy_tags"]["tp"] == 1
    assert written["extraction_items"] == merged["extraction_items"]
    assert written["tagging_items"] == merged["tagging_items"]


def test_select_unevaluated_skips_already_scored_indices():
    records = [EvalRecord(text=f"tekst {i}", speaker=None) for i in range(5)]
    selected = select_unevaluated(records, evaluated_indices={0, 2}, limit=10)
    assert [i for i, _ in selected] == [1, 3, 4]


def test_select_unevaluated_respects_limit():
    records = [EvalRecord(text=f"tekst {i}", speaker=None) for i in range(5)]
    selected = select_unevaluated(records, evaluated_indices=set(), limit=2)
    assert [i for i, _ in selected] == [0, 1]


def test_select_unevaluated_with_limit_zero_selects_nothing():
    records = [EvalRecord(text=f"tekst {i}", speaker=None) for i in range(5)]
    selected = select_unevaluated(records, evaluated_indices=set(), limit=0)
    assert selected == []


def test_load_previous_resumes_when_dataset_and_model_match(tmp_path, monkeypatch):
    monkeypatch.setattr(benchmark_elecdebate, "EXPORT_DIR", tmp_path)
    write_export("test-dataset", "test-model", _sample_merged(), total_records=10)
    export_path = tmp_path / "test-dataset.json"

    previous = load_previous(export_path, "test-model", fresh=False)

    assert previous["evaluated_indices"] == {0, 1, 2}
    assert previous["span_overlap"].true_positives == 5


def test_load_previous_resets_on_model_mismatch(tmp_path, monkeypatch):
    monkeypatch.setattr(benchmark_elecdebate, "EXPORT_DIR", tmp_path)
    write_export("test-dataset", "test-model", _sample_merged(), total_records=10)
    export_path = tmp_path / "test-dataset.json"

    previous = load_previous(export_path, "a-different-model", fresh=False)

    assert previous["evaluated_indices"] == set()


def test_load_previous_resets_when_fresh_requested(tmp_path, monkeypatch):
    monkeypatch.setattr(benchmark_elecdebate, "EXPORT_DIR", tmp_path)
    write_export("test-dataset", "test-model", _sample_merged(), total_records=10)
    export_path = tmp_path / "test-dataset.json"

    previous = load_previous(export_path, "test-model", fresh=True)

    assert previous["evaluated_indices"] == set()


def test_merge_combines_indices_and_sums_counts():
    previous = {
        "evaluated_indices": {0, 1},
        "n_extract_errors": 1,
        "n_tag_errors": 0,
        "span_overlap": PrecisionRecallF1(0.0, 0.0, 0.0, 3, 1, 2),
        "fallacy_tags": PrecisionRecallF1(0.0, 0.0, 0.0, 1, 0, 1),
        "extraction_items": [{"outcome": "gevonden"}],
        "tagging_items": [],
    }
    new = {
        "new_indices": [2, 3],
        "n_extract_errors": 0,
        "n_tag_errors": 1,
        "span_overlap": PrecisionRecallF1(0.0, 0.0, 0.0, 2, 0, 1),
        "fallacy_tags": PrecisionRecallF1(0.0, 0.0, 0.0, 0, 1, 0),
        "extraction_items": [{"outcome": "gemist"}],
        "tagging_items": [{"outcome": "onterecht"}],
    }

    merged = merge(previous, new)

    assert merged["evaluated_indices"] == [0, 1, 2, 3]
    assert merged["n_extract_errors"] == 1
    assert merged["n_tag_errors"] == 1
    assert merged["span_overlap"].true_positives == 5
    assert merged["span_overlap"].false_positives == 1
    assert merged["fallacy_tags"].false_positives == 1
    assert merged["extraction_items"] == [{"outcome": "gevonden"}, {"outcome": "gemist"}]
