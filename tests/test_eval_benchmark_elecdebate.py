"""Tests voor de pure hulpfuncties in pipeline/eval/benchmark_elecdebate.py
(issue #62). De volledige runner (evaluate_extraction/evaluate_tagging/run) roept een LLM en de
database aan en wordt daarom niet hier maar handmatig geverifieerd, zie
docs/eval-elecdebate.md."""

from pipeline.eval.benchmark_elecdebate import _find_span
from pipeline.eval.schema import Span


def test_find_span_locates_exact_substring():
    content = "Mijn tegenstander is een leugenaar. Bovendien is zijn plan slecht."
    assert _find_span(content, "Bovendien is zijn plan slecht.") == Span(36, 66)


def test_find_span_returns_none_when_not_found():
    content = "Een tekst zonder het gezochte citaat."
    assert _find_span(content, "dit citaat komt hier niet in voor") is None
