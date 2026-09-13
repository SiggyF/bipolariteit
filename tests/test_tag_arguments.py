from collections import Counter

from pipeline.tag_arguments import (
    _GEEN_TAG,
    QF_AMBIGU,
    QF_GEEN_FRAGMENT,
    QF_GELDIG,
    QF_GELDIG_MEERDELIG,
    QF_NIET_GEVONDEN,
    _coerce_tag_entry,
    _validate_tags,
    classify_quote_fragment,
)

QUOTE_TEXT = "Mensen zijn gebaat bij een stabiele overheid, en veel meer mensen zijn gebaat bij een stabiele markt."


def test_classify_quote_fragment_geen_fragment_for_none_or_empty():
    assert classify_quote_fragment(None, QUOTE_TEXT) == QF_GEEN_FRAGMENT
    assert classify_quote_fragment("  ", QUOTE_TEXT) == QF_GEEN_FRAGMENT


def test_classify_quote_fragment_geldig_for_unique_verbatim_substring():
    assert classify_quote_fragment("een stabiele overheid", QUOTE_TEXT) == QF_GELDIG


def test_classify_quote_fragment_niet_gevonden_for_paraphrase():
    assert classify_quote_fragment("een wankele regering", QUOTE_TEXT) == QF_NIET_GEVONDEN


def test_classify_quote_fragment_ambigu_for_substring_occurring_twice():
    # "gebaat bij een stabiele" komt twee keer voor (overheid/markt) -- welke
    # bedoeld is, is niet af te leiden, dus afkeuren i.p.v. gokken.
    assert classify_quote_fragment("gebaat bij een stabiele", QUOTE_TEXT) == QF_AMBIGU


def test_classify_quote_fragment_geldig_meerdelig_for_ellipsis_joined_parts():
    fragment = "Mensen zijn gebaat... veel meer mensen zijn gebaat"
    assert classify_quote_fragment(fragment, QUOTE_TEXT) == QF_GELDIG_MEERDELIG


def test_classify_quote_fragment_niet_gevonden_when_one_ellipsis_part_missing():
    fragment = "Mensen zijn gebaat... dit deel staat er niet"
    assert classify_quote_fragment(fragment, QUOTE_TEXT) == QF_NIET_GEVONDEN


def test_coerce_tag_entry_accepts_new_object_with_quote_fragment():
    entry = {"sleutel": "Stijl-Herhaling", "reden": "reden hier", "quote_fragment": "een fragment"}
    assert _coerce_tag_entry(entry) == ("Stijl-Herhaling", "reden hier", "een fragment")


def test_coerce_tag_entry_accepts_bare_string_without_quote_fragment():
    assert _coerce_tag_entry("Stijl-Herhaling") == ("Stijl-Herhaling", None, None)


def test_coerce_tag_entry_returns_geen_tag_sentinel_for_null_forms():
    assert _coerce_tag_entry({"sleutel": None}) is _GEEN_TAG
    assert _coerce_tag_entry({"sleutel": "null"}) is _GEEN_TAG


def test_coerce_tag_entry_ignores_non_string_quote_fragment():
    entry = {"sleutel": "Stijl-Herhaling", "reden": "r", "quote_fragment": 123}
    assert _coerce_tag_entry(entry) == ("Stijl-Herhaling", "r", None)


VALID_TAGS = {
    "stijlmiddelen": ("meervoud", "Stijlmiddelen", {"Stijl-Herhaling", "Stijl-Metafoor"}),
}


def test_validate_tags_keeps_quote_fragment_when_geldig():
    parsed = {
        "stijlmiddelen": [
            {"sleutel": "Stijl-Herhaling", "reden": "r", "quote_fragment": "een stabiele overheid"},
        ]
    }
    accepted = _validate_tags(parsed, VALID_TAGS, QUOTE_TEXT)
    assert accepted == [("Stijl-Herhaling", "r", "een stabiele overheid")]


def test_validate_tags_drops_quote_fragment_when_not_verbatim():
    parsed = {
        "stijlmiddelen": [
            {"sleutel": "Stijl-Herhaling", "reden": "r", "quote_fragment": "een wankele regering"},
        ]
    }
    accepted = _validate_tags(parsed, VALID_TAGS, QUOTE_TEXT)
    assert accepted == [("Stijl-Herhaling", "r", None)]


def test_validate_tags_keeps_tag_without_quote_fragment_as_whole_quote():
    parsed = {"stijlmiddelen": [{"sleutel": "Stijl-Herhaling", "reden": "r", "quote_fragment": None}]}
    accepted = _validate_tags(parsed, VALID_TAGS, QUOTE_TEXT)
    assert accepted == [("Stijl-Herhaling", "r", None)]


def test_validate_tags_updates_qf_stats_counter():
    parsed = {
        "stijlmiddelen": [
            {"sleutel": "Stijl-Herhaling", "reden": "r", "quote_fragment": "een stabiele overheid"},
            {"sleutel": "Stijl-Metafoor", "reden": "r2", "quote_fragment": "een wankele regering"},
        ]
    }
    qf_stats = Counter()
    _validate_tags(parsed, VALID_TAGS, QUOTE_TEXT, qf_stats=qf_stats)
    assert qf_stats[QF_GELDIG] == 1
    assert qf_stats[QF_NIET_GEVONDEN] == 1
