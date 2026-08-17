from pipeline.match_argument_spans import (
    build_running_index,
    calibrate_debate,
    estimate_duration_seconds,
    expected_event_type,
    expected_turn_seconds,
    find_quote_span,
    find_turn_anchor,
    load_events,
    match_debate,
    match_turn_with_anchor,
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


def _row(
    id_,
    quote_text,
    published_at,
    activiteit_aanvangstijd="2026-07-01T13:35:26",
    document_id=None,
    speaker_person_id=None,
    turn_type="woordvoerder",
    is_voorzitter_turn=0,
):
    return {
        "id": id_,
        "document_id": document_id if document_id is not None else id_,
        "quote_text": quote_text,
        "published_at": published_at,
        "activiteit_aanvangstijd": activiteit_aanvangstijd,
        "speaker_person_id": speaker_person_id,
        "turn_type": turn_type,
        "is_voorzitter_turn": is_voorzitter_turn,
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


# --- Tier 1: events-API-anker per beurt (issue #130) ---


def test_load_events_converts_event_start_to_video_seconds_relative_to_started_at():
    events_json = {
        "startedAt": "2026-07-01T13:00:00",
        "events": [
            {"eventStart": "2026-07-01T13:16:40", "eventType": "speaker", "objectId": "guid-a"},
            {"eventStart": "2026-07-01T13:33:20", "eventType": "interrupter", "objectId": "guid-b"},
        ],
    }
    started_at, events = load_events(events_json)
    assert started_at.isoformat() == "2026-07-01T13:00:00"
    assert events == [
        {"video_seconds": 1000.0, "eventType": "speaker", "objectId": "guid-a"},
        {"video_seconds": 2000.0, "eventType": "interrupter", "objectId": "guid-b"},
    ]


def test_load_events_skips_incomplete_entries():
    events_json = {
        "startedAt": "2026-07-01T13:00:00",
        "events": [
            {"eventStart": "2026-07-01T13:16:40", "eventType": "speaker"},  # geen objectId
            {"eventType": "speaker", "objectId": "guid-a"},  # geen eventStart
        ],
    }
    _started_at, events = load_events(events_json)
    assert events == []


def test_expected_event_type_maps_interrumpant_and_voorzitter_to_debatdirect_types():
    assert expected_event_type("interrumpant", is_voorzitter_turn=0) == "interrupter"
    assert expected_event_type("interrumpant", is_voorzitter_turn=1) == "interrupter"
    assert expected_event_type("woordvoerder", is_voorzitter_turn=1) == "chairman"
    assert expected_event_type("woordvoerder", is_voorzitter_turn=0) == "speaker"


def test_expected_turn_seconds_attaches_started_at_timezone_to_naive_published_at():
    from datetime import datetime, timedelta, timezone

    started_at = datetime(2026, 7, 1, 13, 0, 0, tzinfo=timezone(timedelta(hours=2)))
    assert expected_turn_seconds("2026-07-01T13:16:40", started_at) == 1000.0


def test_expected_turn_seconds_returns_none_without_published_at():
    from datetime import datetime

    assert expected_turn_seconds(None, datetime(2026, 7, 1, 13, 0, 0)) is None


_EVENTS = [
    {"video_seconds": 1000.0, "eventType": "speaker", "objectId": "guid-a"},
    {"video_seconds": 2000.0, "eventType": "interrupter", "objectId": "guid-b"},
    {"video_seconds": 3000.0, "eventType": "speaker", "objectId": "guid-a"},  # latere beurt, zelfde spreker
]


def test_find_turn_anchor_picks_nearest_matching_candidate_within_window():
    assert find_turn_anchor(_EVENTS, "guid-a", "speaker", expected_seconds=1010) == 1000.0
    # dichter bij de latere beurt van dezelfde spreker -- moet die pakken, niet de eerste
    assert find_turn_anchor(_EVENTS, "guid-a", "speaker", expected_seconds=2990) == 3000.0


def test_find_turn_anchor_returns_none_outside_window():
    assert find_turn_anchor(_EVENTS, "guid-a", "speaker", expected_seconds=1200, window_seconds=180) is None


def test_find_turn_anchor_ignores_type_mismatch():
    assert find_turn_anchor(_EVENTS, "guid-a", "interrupter", expected_seconds=1000) is None


def test_find_turn_anchor_returns_none_without_speaker_person_id_or_expected_seconds():
    assert find_turn_anchor(_EVENTS, None, "speaker", expected_seconds=1000) is None
    assert find_turn_anchor(_EVENTS, "guid-a", "speaker", expected_seconds=None) is None


def test_estimate_duration_seconds_uses_speaking_tempo_with_a_floor():
    assert estimate_duration_seconds("een twee drie vier vijf zes zeven acht") == 8 / 2.4
    assert estimate_duration_seconds("kort") == 1.0  # floor, anders 1/2.4 < 1


def test_match_turn_with_anchor_calibrates_relative_to_the_anchor_not_a_debate_median():
    cues = [
        {"start": 1005, "end": 1007, "text": "Eerste zin hier"},
        {"start": 1015, "end": 1017, "text": "Tweede zin hier"},
    ]
    running_text, offsets = build_running_index(cues)
    rows = [
        _row(1, "Eerste zin hier", published_at=None, document_id=10),
        _row(2, "Tweede zin hier", published_at=None, document_id=10),
    ]
    spans = match_turn_with_anchor(cues, running_text, offsets, turn_anchor_seconds=1000, turn_rows=rows)
    assert spans == {1: (1000, 1002), 2: (1010, 1012)}


def test_match_turn_with_anchor_falls_back_to_anchor_plus_estimated_duration_without_vtt_match():
    cues = [{"start": 1005, "end": 1007, "text": "Compleet ongerelateerde tekst"}]
    running_text, offsets = build_running_index(cues)
    rows = [_row(1, "een twee drie vier vijf", published_at=None, document_id=10)]
    spans = match_turn_with_anchor(cues, running_text, offsets, turn_anchor_seconds=1000, turn_rows=rows)
    assert spans == {1: (1000, 1000 + 5 / 2.4)}


def test_calibrate_debate_without_events_reproduces_match_debate_exactly():
    # Non-regressie: events_json=None (geen fetch-debate-events-cache voor dit
    # debat) moet precies hetzelfde resultaat geven als de oude, ongewijzigde
    # match_debate() -- geen enkele gedragsverandering voor debatten waarvoor
    # de events-API niets oplevert.
    cues = [
        {"start": 5 * 3600 + 10, "end": 5 * 3600 + 12, "text": "Eerste zin hier"},
        {"start": 5 * 3600 + 20, "end": 5 * 3600 + 22, "text": "Tweede zin hier"},
        {"start": 5 * 3600 + 30, "end": 5 * 3600 + 32, "text": "Derde zin hier"},
    ]
    rows = [
        _row(1, "Eerste zin hier", "2026-07-01T13:35:26"),
        _row(2, "Tweede zin hier", "2026-07-01T13:35:36"),
        _row(3, "Derde zin hier", "2026-07-01T13:35:46"),
    ]
    assert calibrate_debate(cues, rows, events_json=None) == match_debate(cues, rows)


def test_calibrate_debate_anchors_each_turn_independently_recovers_from_single_turn_vtt_drift():
    # Reproduceert het scenario uit #130/#108: de rauwe VTT-klok van beurt B
    # is (bv. door een subtitel-systeemreset rond een schorsing) 2000s
    # weggedreven van de werkelijke videotijd, terwijl beurt A/C een normale
    # ~5s tikvertraging hebben. published_at (en dus activiteit_aanvangstijd-
    # afgeleide "expected") blijft voor alle drie beurten wél betrouwbaar.
    #
    # Tier-2-only (de oude aanpak): de per-beurt-diffs (5, 5, 2005) hebben een
    # spreiding >MAX_CALIBRATION_SPREAD_SECONDS, dus match_debate() geeft {}
    # terug -- het hele debat blijft ongekalibreerd, ook beurt A/C die prima
    # hadden gekund.
    #
    # Tier 1 (events-API-anker): elke beurt wordt onafhankelijk gekalibreerd
    # tegen zijn eigen, drift-vrije wandklok-anker, dus alle drie beurten
    # krijgen alsnog een correcte, exacte spanne.
    cues = [
        {"start": 1005, "end": 1007, "text": "Eerste zin hier"},
        {"start": 2005, "end": 2007, "text": "Tweede zin hier"},
        {"start": 6005, "end": 6007, "text": "Derde zin hier"},
    ]
    rows = [
        _row(1, "Eerste zin hier", "2026-07-01T13:16:40", "2026-07-01T13:00:00", document_id=1, speaker_person_id="guid-a"),
        _row(2, "Tweede zin hier", "2026-07-01T13:33:20", "2026-07-01T13:00:00", document_id=3, speaker_person_id="guid-c"),
        _row(3, "Derde zin hier", "2026-07-01T14:06:40", "2026-07-01T13:00:00", document_id=2, speaker_person_id="guid-b"),
    ]
    events_json = {
        "startedAt": "2026-07-01T13:00:00",
        "events": [
            {"eventStart": "2026-07-01T13:16:40", "eventType": "speaker", "objectId": "guid-a"},
            {"eventStart": "2026-07-01T13:33:20", "eventType": "speaker", "objectId": "guid-c"},
            {"eventStart": "2026-07-01T14:06:40", "eventType": "speaker", "objectId": "guid-b"},
        ],
    }

    assert match_debate(cues, rows) == {}

    spans = calibrate_debate(cues, rows, events_json)
    assert spans == {1: (1000, 1002), 2: (2000, 2002), 3: (4000, 4002)}


def test_calibrate_debate_falls_back_to_debate_wide_median_for_unanchored_turns():
    # Een events-cache bestaat wel voor dit debat, maar één beurt heeft geen
    # matchend event (bv. de spreker sprak vlak buiten de events-log) -- die
    # beurt moet dan nog steeds via het oude Tier-2-debat-brede pad een span
    # kunnen krijgen, samen met de andere, wél-onmatchte argumenten die ook
    # geen Tier-1-anker hebben.
    cues = [
        {"start": 5 * 3600 + 10, "end": 5 * 3600 + 12, "text": "Eerste zin hier"},
        {"start": 5 * 3600 + 20, "end": 5 * 3600 + 22, "text": "Tweede zin hier"},
        {"start": 5 * 3600 + 30, "end": 5 * 3600 + 32, "text": "Derde zin hier"},
    ]
    rows = [
        _row(1, "Eerste zin hier", "2026-07-01T13:35:26", document_id=1, speaker_person_id="guid-onbekend"),
        _row(2, "Tweede zin hier", "2026-07-01T13:35:36", document_id=2, speaker_person_id="guid-onbekend"),
        _row(3, "Derde zin hier", "2026-07-01T13:35:46", document_id=3, speaker_person_id="guid-onbekend"),
    ]
    events_json = {"startedAt": "2026-07-01T13:00:00", "events": []}  # geen enkel event matcht

    spans = calibrate_debate(cues, rows, events_json)
    assert spans == match_debate(cues, rows)
    assert set(spans) == {1, 2, 3}
