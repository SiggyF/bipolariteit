from pipeline.match_argument_spans import (
    build_running_index,
    find_quote_span,
    match_debate,
    normalize_text,
    parse_vtt,
)

SAMPLE_VTT = """WEBVTT
X-TIMESTAMP-MAP=LOCAL:00:00:00.000,MPEGTS:154697828979600

05:00:00.000 --> 05:00:02.000
Voorzitter. De minister stond vrijdag

05:00:02.100 --> 05:00:04.500
breed lachend het einde aan te kondigen.

05:00:04.600 --> 05:00:06.000
Dat is een compleet ander zinnetje.
"""


def _row(id_, quote_text, published_at, activiteit_aanvangstijd="2026-07-01T13:35:26"):
    return {
        "id": id_,
        "quote_text": quote_text,
        "published_at": published_at,
        "activiteit_aanvangstijd": activiteit_aanvangstijd,
    }


def test_normalize_text_strips_punctuation_and_lowercases():
    assert normalize_text("Voorzitter. De minister stond vrijdag!") == "voorzitter de minister stond vrijdag"


def test_parse_vtt_extracts_cues_with_multiline_text_joined():
    cues = parse_vtt(SAMPLE_VTT)
    assert len(cues) == 3
    assert cues[0]["start"] == 5 * 3600
    assert cues[0]["end"] == 5 * 3600 + 2
    assert cues[0]["text"] == "Voorzitter. De minister stond vrijdag"


def test_find_quote_span_across_cue_boundary():
    cues = parse_vtt(SAMPLE_VTT)
    running_text, offsets = build_running_index(cues)
    span = find_quote_span(
        "De minister stond vrijdag breed lachend het einde aan te kondigen.",
        running_text,
        offsets,
        cues,
    )
    assert span == (cues[0]["start"], cues[1]["end"])


def test_find_quote_span_returns_none_when_not_verbatim():
    cues = parse_vtt(SAMPLE_VTT)
    running_text, offsets = build_running_index(cues)
    assert find_quote_span("dit staat nergens in de ondertitels", running_text, offsets, cues) is None


def test_match_debate_calibrates_using_median_offset():
    # Alle drie argumenten publiceren 10s na activiteit_aanvangstijd; de
    # ruwe cue-tijden lopen op (5h+10, +20, +30), dus de kalibratie
    # (mediaan van raw - expected) wordt 5h+10 -- niet gewoon 5h, want de
    # mediaan schuift mee met de middelste van de drie samples.
    cues = [
        {"start": 5 * 3600 + 10, "end": 5 * 3600 + 12, "text": "Eerste zin hier"},
        {"start": 5 * 3600 + 20, "end": 5 * 3600 + 22, "text": "Tweede zin hier"},
        {"start": 5 * 3600 + 30, "end": 5 * 3600 + 32, "text": "Derde zin hier"},
    ]
    rows = [
        _row(1, "Eerste zin hier", "2026-07-01T13:35:36"),
        _row(2, "Tweede zin hier", "2026-07-01T13:35:36"),
        _row(3, "Derde zin hier", "2026-07-01T13:35:36"),
    ]
    spans = match_debate(cues, rows)
    assert set(spans) == {1, 2, 3}
    # calibratie = mediaan van (raw_start - expected_offset) over de drie
    # argumenten = mediaan(5h, 5h+10, 5h+20) = 5h+10
    assert spans[1] == (0, 2)
    assert spans[2] == (10, 12)
    assert spans[3] == (20, 22)


def test_match_debate_returns_empty_below_minimum_matches():
    cues = [{"start": 100, "end": 102, "text": "Enige zin hier"}]
    rows = [_row(1, "Enige zin hier", "2026-07-01T13:35:36")]
    assert match_debate(cues, rows) == {}


def test_match_debate_skips_arguments_that_do_not_match_verbatim():
    cues = [
        {"start": 10, "end": 12, "text": "Eerste zin hier"},
        {"start": 20, "end": 22, "text": "Tweede zin hier"},
        {"start": 30, "end": 32, "text": "Derde zin hier"},
    ]
    rows = [
        _row(1, "Eerste zin hier", "2026-07-01T13:35:26"),
        _row(2, "Tweede zin hier", "2026-07-01T13:35:26"),
        _row(3, "Derde zin hier", "2026-07-01T13:35:26"),
        _row(4, "compleet ongerelateerde tekst", "2026-07-01T13:35:26"),
    ]
    spans = match_debate(cues, rows)
    assert set(spans) == {1, 2, 3}
