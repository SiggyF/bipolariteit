"""Precision/recall/F1-metrieken voor het ELECDEBATE-evalharnas (issue #62).
Span-overlap is tekenniveau (geen exacte match vereist -- politieke
transcripten hebben net iets andere zinsgrenzen dan onze extractie);
fallacy-metrics vergelijken per record welke van de gemapte tags
(label_mapping.FALLACY_TAG_MAP) voorspeld vs. gouden zijn."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PrecisionRecallF1:
    precision: float
    recall: float
    f1: float
    true_positives: int
    false_positives: int
    false_negatives: int


def _prf(tp: int, fp: int, fn: int) -> PrecisionRecallF1:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return PrecisionRecallF1(precision, recall, f1, tp, fp, fn)


def _char_positions(spans, text_length):
    covered = set()
    for span in spans:
        covered.update(range(max(0, span.start), min(text_length, span.end)))
    return covered


def span_overlap_prf(predicted_spans, gold_spans, text_length) -> PrecisionRecallF1:
    """Tekenniveau precision/recall/F1 tussen voorspelde en gouden spans."""
    predicted = _char_positions(predicted_spans, text_length)
    gold = _char_positions(gold_spans, text_length)
    tp = len(predicted & gold)
    fp = len(predicted - gold)
    fn = len(gold - predicted)
    return _prf(tp, fp, fn)


def label_set_prf(predicted_labels, gold_labels) -> PrecisionRecallF1:
    """Precision/recall/F1 tussen voorspelde en gouden labels (bv.
    tag-sleutels) binnen één record."""
    predicted = set(predicted_labels)
    gold = set(gold_labels)
    tp = len(predicted & gold)
    fp = len(predicted - gold)
    fn = len(gold - predicted)
    return _prf(tp, fp, fn)


def aggregate(results: list[PrecisionRecallF1]) -> PrecisionRecallF1:
    """Micro-aggregatie (som van tp/fp/fn over alle records) i.p.v. het
    gemiddelde van per-record F1's nemen -- robuuster tegen records zonder
    enige span/tag, waar een per-record F1 ongedefinieerd of misleidend is."""
    tp = sum(r.true_positives for r in results)
    fp = sum(r.false_positives for r in results)
    fn = sum(r.false_negatives for r in results)
    return _prf(tp, fp, fn)
