"""Tests voor pipeline/eval/metrics.py (issue #62)."""

from pipeline.eval.metrics import aggregate, label_set_prf, span_overlap_prf
from pipeline.eval.schema import Span


def test_span_overlap_prf_perfect_match():
    predicted = [Span(0, 10)]
    gold = [Span(0, 10)]
    result = span_overlap_prf(predicted, gold, text_length=20)
    assert result.precision == 1.0
    assert result.recall == 1.0
    assert result.f1 == 1.0


def test_span_overlap_prf_partial_overlap():
    predicted = [Span(0, 10)]
    gold = [Span(5, 15)]
    result = span_overlap_prf(predicted, gold, text_length=20)
    assert result.true_positives == 5  # tekens 5..9
    assert result.false_positives == 5  # tekens 0..4
    assert result.false_negatives == 5  # tekens 10..14


def test_span_overlap_prf_no_spans_either_side():
    result = span_overlap_prf([], [], text_length=20)
    assert result.precision == 0.0
    assert result.recall == 0.0
    assert result.f1 == 0.0
    assert result.true_positives == 0


def test_label_set_prf():
    result = label_set_prf({"Drogreden-Ad-Hominem", "Drogreden-Stropop"}, {"Drogreden-Ad-Hominem"})
    assert result.true_positives == 1
    assert result.false_positives == 1
    assert result.false_negatives == 0


def test_aggregate_sums_across_records():
    r1 = span_overlap_prf([Span(0, 10)], [Span(0, 10)], text_length=20)
    r2 = span_overlap_prf([], [Span(0, 5)], text_length=20)
    combined = aggregate([r1, r2])
    assert combined.true_positives == 10
    assert combined.false_negatives == 5
    assert combined.false_positives == 0
