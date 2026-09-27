from pipeline.match_argument_spans import build_running_index, find_quote_span, parse_vtt
from pipeline.match_tag_spans import cues_in_window, find_fragment_span, match_debate_tags

# Bewust een fragment ("breed lachend") dat AL VOORKOMT in een cue vóór de
# eigenlijke argument-spanne (04:00:00) -- als match_tag_spans het venster
# niet zou beperken tot de eigen argument-quote, zou een debat-brede
# zoektocht dat eerdere, verkeerde voorkomen pakken (zelfde risico als in
# #106/#109 beschreven bij een debat-brede fragment-zoektocht).
SAMPLE_VTT = """WEBVTT

04:00:00.000 --> 04:00:03.000
Ergens anders zei een ander lid ook breed lachend dat het einde nadert.

05:00:00.000 --> 05:00:02.000
Voorzitter. De minister stond vrijdag

05:00:02.100 --> 05:00:04.500
breed lachend het einde aan te kondigen.

05:00:04.600 --> 05:00:06.000
Dat is een compleet ander zinnetje.
"""

ARGUMENT_QUOTE = "De minister stond vrijdag breed lachend het einde aan te kondigen."


def _row(tag_id, quote_fragment, argument_id=1, quote_text=ARGUMENT_QUOTE, argument_start=100.0, argument_end=110.0):
    return {
        "tag_id": tag_id,
        "quote_fragment": quote_fragment,
        "argument_id": argument_id,
        "quote_text": quote_text,
        "argument_start": argument_start,
        "argument_end": argument_end,
    }


def test_cues_in_window_filters_to_overlapping_cues_only():
    cues = parse_vtt(SAMPLE_VTT)
    # cues[1]/[2] zijn de "Voorzitter..."/"breed lachend..."-cues.
    window = cues_in_window(cues, cues[1]["start"], cues[2]["end"])
    assert window == [cues[1], cues[2]]


def test_find_fragment_span_matches_single_part_fragment_within_window():
    cues = parse_vtt(SAMPLE_VTT)
    window = cues_in_window(cues, cues[1]["start"], cues[2]["end"])
    assert find_fragment_span("breed lachend", window) == (cues[2]["start"], cues[2]["end"])


def test_find_fragment_span_returns_none_when_not_verbatim():
    cues = parse_vtt(SAMPLE_VTT)
    window = cues_in_window(cues, cues[1]["start"], cues[2]["end"])
    assert find_fragment_span("dit staat er niet", window) is None


def test_find_fragment_span_matches_multi_part_ellipsis_fragment_across_cue_boundary():
    cues = parse_vtt(SAMPLE_VTT)
    window = cues_in_window(cues, cues[1]["start"], cues[2]["end"])
    span = find_fragment_span("De minister stond vrijdag... het einde aan te kondigen.", window)
    assert span == (cues[1]["start"], cues[2]["end"])


def test_match_debate_tags_calibrates_fragment_relative_to_argument_start():
    cues = parse_vtt(SAMPLE_VTT)
    running_text, offsets = build_running_index(cues)
    raw_argument_start, _raw_argument_end = find_quote_span(ARGUMENT_QUOTE, running_text, offsets, cues)
    calibration = raw_argument_start - 100.0  # argument_start hieronder

    rows = [_row(tag_id=1, quote_fragment="breed lachend")]
    spans = match_debate_tags(cues, rows)

    expected_start = cues[2]["start"] - calibration
    expected_end = cues[2]["end"] - calibration
    assert spans == {1: (expected_start, expected_end)}


def test_match_debate_tags_ignores_duplicate_fragment_outside_argument_window():
    # Zonder de venster-restrictie zou "breed lachend" ook matchen op
    # cues[0] (04:00:00, ruim een uur vóór de argument-spanne) -- dat zou een
    # kalibratie van duizenden seconden opleveren i.p.v. iets vlak bij
    # argument_start (100.0). Het geaccepteerde resultaat moet dus dicht bij
    # de argument-spanne liggen, niet bij die vroege, verkeerde occurrence.
    cues = parse_vtt(SAMPLE_VTT)
    rows = [_row(tag_id=1, quote_fragment="breed lachend")]
    spans = match_debate_tags(cues, rows)
    start, end = spans[1]
    assert 90.0 <= start <= end <= 120.0


def test_match_debate_tags_skips_tag_when_argument_quote_no_longer_matches_verbatim():
    cues = parse_vtt(SAMPLE_VTT)
    rows = [_row(tag_id=1, quote_fragment="breed lachend", quote_text="dit staat nergens in de ondertitels")]
    spans = match_debate_tags(cues, rows)
    assert spans == {}


def test_match_debate_tags_leaves_tag_out_when_fragment_itself_does_not_match():
    cues = parse_vtt(SAMPLE_VTT)
    rows = [_row(tag_id=1, quote_fragment="dit fragment staat er niet")]
    spans = match_debate_tags(cues, rows)
    assert spans == {}


def test_match_debate_tags_shares_calibration_across_tags_of_the_same_argument():
    cues = parse_vtt(SAMPLE_VTT)
    rows = [
        _row(tag_id=1, quote_fragment="breed lachend"),
        _row(tag_id=2, quote_fragment="het einde aan te kondigen"),
    ]
    spans = match_debate_tags(cues, rows)
    assert set(spans.keys()) == {1, 2}
