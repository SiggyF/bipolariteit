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


def test_match_debate_calibrates_on_earliest_quote_per_turn():
    # Beurt A heeft drie argumenten (zelfde published_at, expected 10s) met
    # oplopende rauwe cue-tijden (5h+10, +20, +30) -- alleen de eerste ligt
    # vlak bij het begin van de beurt, dus alleen die diff (5h) telt mee als
    # kalibratiepunt; de latere twee zouden de mediaan 10-20s te hoog trekken
    # als ze los meetelden (zie #106). Beurt B en C leveren elk één quote op
    # die wél precies aan het begin van hun beurt valt, dus alle drie de
    # beurten wijzen dezelfde kalibratieconstante (5h) aan.
    cues = [
        {"start": 5 * 3600 + 10, "end": 5 * 3600 + 12, "text": "Eerste zin hier"},
        {"start": 5 * 3600 + 20, "end": 5 * 3600 + 22, "text": "Tweede zin hier"},
        {"start": 5 * 3600 + 30, "end": 5 * 3600 + 32, "text": "Derde zin hier"},
        {"start": 5 * 3600 + 40, "end": 5 * 3600 + 42, "text": "Vierde zin hier"},
        {"start": 5 * 3600 + 70, "end": 5 * 3600 + 72, "text": "Vijfde zin hier"},
    ]
    rows = [
        _row(1, "Eerste zin hier", "2026-07-01T13:35:36"),
        _row(2, "Tweede zin hier", "2026-07-01T13:35:36"),
        _row(3, "Derde zin hier", "2026-07-01T13:35:36"),
        _row(4, "Vierde zin hier", "2026-07-01T13:36:06"),
        _row(5, "Vijfde zin hier", "2026-07-01T13:36:36"),
    ]
    spans = match_debate(cues, rows)
    assert set(spans) == {1, 2, 3, 4, 5}
    # calibratie = mediaan van de laagste diff per beurt = 5h (alle drie
    # beurten wijzen dezelfde constante aan)
    assert spans[1] == (10, 12)
    assert spans[2] == (20, 22)
    assert spans[3] == (30, 32)
    assert spans[4] == (40, 42)
    assert spans[5] == (70, 72)


def test_match_debate_requires_minimum_number_of_turns_not_matches():
    # Vijf argumenten, maar allemaal in dezelfde spreekbeurt -- dat levert
    # maar één kalibratiepunt op (niet vijf), dus onder
    # MIN_MATCHES_FOR_CALIBRATION en dus geen kalibratie.
    cues = [
        {"start": 10, "end": 12, "text": "Eerste zin hier"},
        {"start": 20, "end": 22, "text": "Tweede zin hier"},
        {"start": 30, "end": 32, "text": "Derde zin hier"},
        {"start": 40, "end": 42, "text": "Vierde zin hier"},
        {"start": 50, "end": 52, "text": "Vijfde zin hier"},
    ]
    rows = [
        _row(1, "Eerste zin hier", "2026-07-01T13:35:36"),
        _row(2, "Tweede zin hier", "2026-07-01T13:35:36"),
        _row(3, "Derde zin hier", "2026-07-01T13:35:36"),
        _row(4, "Vierde zin hier", "2026-07-01T13:35:36"),
        _row(5, "Vijfde zin hier", "2026-07-01T13:35:36"),
    ]
    assert match_debate(cues, rows) == {}


def test_match_debate_skips_debate_with_implausible_calibration_spread():
    # Drie spreekbeurten, ver uit elkaar in de tijd, waarvan er twee een
    # vergelijkbare diff opleveren (~100s) en één een diff die daar >800s
    # van afwijkt (zie #108: een spreiding dat groot komt niet doordat de
    # video hapert -- die is altijd doorlopend, geverifieerd via ffprobe --
    # maar doordat published_at ergens onbetrouwbaar is, bv. rond een
    # schorsing). Beter geen kalibratie dan een mediaan tussen twee
    # onverenigbare clusters die voor geen van beide klopt.
    cues = [
        {"start": 100, "end": 102, "text": "Eerste zin hier"},
        {"start": 1150, "end": 1152, "text": "Tweede zin hier"},
        {"start": 3200, "end": 3202, "text": "Derde zin hier"},
    ]
    rows = [
        _row(1, "Eerste zin hier", "2026-07-01T13:35:26"),  # expected 0s, diff 100
        _row(2, "Tweede zin hier", "2026-07-01T13:52:06"),  # expected 1000s, diff 150
        _row(3, "Derde zin hier", "2026-07-01T14:08:46"),  # expected 2000s, diff 1200
    ]
    assert match_debate(cues, rows) == {}


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
        _row(2, "Tweede zin hier", "2026-07-01T13:35:36"),
        _row(3, "Derde zin hier", "2026-07-01T13:35:46"),
        _row(4, "compleet ongerelateerde tekst", "2026-07-01T13:35:26"),
    ]
    spans = match_debate(cues, rows)
    assert set(spans) == {1, 2, 3}
