"""Tests voor scripts/convert_elecdebate.py (issue #62)."""

from scripts.convert_elecdebate import _drop_nested_fallacies


def test_drop_nested_fallacies_keeps_only_the_longer_span():
    """De brondata annoteert soms dezelfde drogreden op twee granulariteiten
    (bv. "I want us to invest in you. I want us to invest in your future."
    vs. losstaand "I want us to invest in your future.", beide Appeal to
    Emotion) -- de kortere, volledig binnen de langere vallende variant
    moet wegvallen."""
    tuples = {
        (414, 477, "Appeal to Emotion"),
        (442, 477, "Appeal to Emotion"),
    }
    assert _drop_nested_fallacies(tuples) == {(414, 477, "Appeal to Emotion")}


def test_drop_nested_fallacies_keeps_disjoint_spans():
    tuples = {
        (0, 10, "Ad Hominem"),
        (20, 30, "Ad Hominem"),
    }
    assert _drop_nested_fallacies(tuples) == tuples


def test_drop_nested_fallacies_keeps_nested_spans_with_different_labels():
    """Nesting is alleen een dataset-artefact bij hetzelfde label -- een
    kortere span met een ANDER label kan een echte, aparte annotatie zijn."""
    tuples = {
        (0, 50, "Appeal to Emotion"),
        (10, 20, "Ad Hominem"),
    }
    assert _drop_nested_fallacies(tuples) == tuples


def test_drop_nested_fallacies_keeps_equal_length_spans():
    """Twee exact even lange, niet-identieke spans zijn geen 'nesting' --
    alleen strikt kortere spans binnen een strikt langere vallen weg."""
    tuples = {
        (0, 10, "Ad Hominem"),
        (5, 15, "Ad Hominem"),
    }
    assert _drop_nested_fallacies(tuples) == tuples
