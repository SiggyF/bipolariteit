"""
Vult arguments.start_seconds/end_seconds, per sprekerbeurt geankerd op de
debatdirect events-API (docs/tk-data-sources-overview.md 5f) en verfijnd met
de gecachete WebVTT-ondertitel-cues (pipeline/fetch_subtitles.py), zoals
gespecificeerd in docs/design/videoplayer/README.md ("Spannes verrijken").

Vult daarnaast documents.speaker_event_anchor_at (issue #148-vervolg) met
hetzelfde Tier-1-anker, maar dan als absolute wall-clock-tijd i.p.v.
videoseconden: het drift-vrije alternatief voor documents.published_at dat
build_static_data.py e.a. gebruiken voor de externe "video op dit
moment"-deep-link naar Debat Direct (?event=speaker<ISO8601>).
published_at (VLOS-markeertijd) bleek voor sommige beurten uren af te wijken
van de werkelijke spreektijd, waardoor die link naar het begin van het debat
sprong i.p.v. naar de juiste beurt.

Twee tiers per sprekerbeurt (VLOS-`<woordvoerder>`/`<interrumpant>`, één
document per beurt):

1. **Tier 1 (primair)**: een exact, drift-vrij anker uit de debatdirect
   events-API (pipeline/fetch_debate_events.py), gekoppeld via
   `documents.speaker_person_id` (TK-Persoon-GUID, byte-identiek aan
   events[].objectId) + verwacht eventType (`expected_event_type`) +
   dichtstbijzijnde tijdstip binnen een venster (`find_turn_anchor`).
2. **Tier 2 (verfijning/fallback)**: binnen een geankerde beurt verfijnt een
   VTT-quote-match de exacte positie van elk argument (`match_turn_with_anchor`,
   gekalibreerd op déze beurt, niet op een mediaan voor het hele debat). Voor
   beurten zonder Tier-1-anker (geen events-cache, of geen matchend event
   binnen het venster) blijft de oorspronkelijke aanpak intact: één mediane
   VTT-kalibratie over het hele debat (`match_debate`) -- dus geen regressie
   voor debatten waarvoor de events-API niets oplevert.

Levert een VTT-match binnen een geankerde beurt niets op (VLOS-transcriptie en
live-ondertiteling kunnen verschillen), dan valt die beurt terug op het
Tier-1-anker zelf plus een spreektempo-schatting van de duur
(`estimate_duration_seconds`) -- de al langer gedocumenteerde maar nooit
gebouwde `video_offset_seconds`-fallback, nu wél geïmplementeerd nu er een
betrouwbaar beurt-anker bestaat. Alleen wanneer noch een Tier-1-anker, noch
een debat-brede Tier-2-kalibratie lukt, blijft een argument ongematcht
(`start_seconds`/`end_seconds` NULL).

Idempotent via arguments.start_seconds IS NULL; --force matcht opnieuw.

Gebruik:
    uv run python -m pipeline.match_argument_spans --topic stikstof [--dry-run] [--force]
"""

import argparse
import json
import logging
import re
import statistics
from bisect import bisect_right
from datetime import datetime, timedelta

from pipeline.db import db
from pipeline.fetch_debate_events import DEBATE_EVENTS_DIR
from pipeline.fetch_subtitles import SUBTITLES_DIR

logger = logging.getLogger(__name__)

_CUE_RE = re.compile(
    r"(\d\d):(\d\d):(\d\d)\.(\d\d\d) --> (\d\d):(\d\d):(\d\d)\.(\d\d\d)\n(.*?)(?=\n\n|\Z)",
    re.S,
)
_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")

# Een kalibratie steunend op te weinig spreekbeurten is onbetrouwbaar (één
# toevallige woordelijke overlap zegt weinig over de klok-offset van het hele
# debat). Telt spreekbeurten met minstens één match, niet losse argumenten --
# meerdere argumenten in dezelfde beurt leveren maar één kalibratiepunt op.
# Geldt alleen voor het Tier-2-only-fallbackpad (match_debate) -- voor
# Tier-1-geankerde beurten speelt TURN_ANCHOR_WINDOW_SECONDS dezelfde
# beschermende rol.
MIN_MATCHES_FOR_CALIBRATION = 3

# Zie het uitgebreide commentaar bij het gebruik in match_debate() (#108):
# steekproef over ~800 debatten gaf een mediane spreiding van ~130s tussen
# de per-beurt kalibratiepunten, met twee uitschieters (1741s/8777s) die
# aantoonbaar een onbetrouwbare published_at rond een schorsing hebben --
# niet een kapotte video. 800s ligt ruim boven de rest (max ~630s) en ruim
# onder beide uitschieters.
MAX_CALIBRATION_SPREAD_SECONDS = 800

# Venster waarbinnen een debatdirect-event nog als hetzelfde beurt-begin
# geldt (zie find_turn_anchor). Ruim genoeg voor de grove published_at-schatting
# die als zoekcentrum dient, streng genoeg om nooit een verkeerde latere beurt
# van dezelfde spreker te pakken (zie pilotonderzoek issue #130).
TURN_ANCHOR_WINDOW_SECONDS = 180

# Spreektempo-schatting voor de anker-zonder-VTT-match-fallback, zelfde
# concept als arguments-timed.json/docs/design/videoplayer/README.md
# ("Spannes verrijken"): ~2,4 woorden/sec.
SPEAKING_WORDS_PER_SECOND = 2.4
MIN_ESTIMATED_DURATION_SECONDS = 1.0

# VLOS-brontekst begint elke beurt met een sprekerlabel dat zelf niet
# uitgesproken is (bv. "Mevrouw Van der Plas (BBB): ", "De voorzitter: ") --
# de live-ondertiteling bevat dat label niet, dus zonder dit te strippen zou
# de beurt-openingstekst nooit in de VTT te vinden zijn. Sprekerlabels zijn
# altijd kort en gevolgd door een dubbele punt vlak aan het begin.
_SPEAKER_LABEL_RE = re.compile(r"^[^:\n]{1,80}:\s*")
TURN_OPENING_WORD_COUNT = 10


def _ts_to_seconds(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_vtt(text):
    """Lijst van {start, end, text} in de VTT's eigen klok (seconden), in
    documentvolgorde. `text` is de ruwe cue-tekst (nog niet genormaliseerd)."""
    cues = []
    for match in _CUE_RE.finditer(text):
        h1, m1, s1, ms1, h2, m2, s2, ms2, cue_text = match.groups()
        cues.append(
            {
                "start": _ts_to_seconds(h1, m1, s1, ms1),
                "end": _ts_to_seconds(h2, m2, s2, ms2),
                "text": cue_text.replace("\n", " ").strip(),
            }
        )
    return cues


def normalize_text(text):
    """Lowercase, geen leestekens -- alleen a-z/0-9, enkele spaties. Bewust
    ruw (geen lemmatisering/stemming): de aanname is woordelijke overlap
    tussen VLOS-quote en live-ondertiteling, geen semantische match."""
    return _NORMALIZE_RE.sub(" ", text.lower()).strip()


def build_running_index(cues):
    """Genormaliseerde tekst van alle cues aaneengeregen (met een spatie
    ertussen, zodat een quote die over een cue-grens loopt toch als
    aaneengesloten tekst matcht), plus de cumulatieve lengte na elke cue om
    een character-offset terug te kunnen herleiden naar een cue-index."""
    parts = []
    cue_end_offsets = []
    offset = 0
    for cue in cues:
        normalized = normalize_text(cue["text"])
        parts.append(normalized)
        offset += len(normalized) + 1  # +1 voor de spatie die join() toevoegt
        cue_end_offsets.append(offset)
    return " ".join(parts), cue_end_offsets


def find_quote_span(quote_text, running_text, cue_end_offsets, cues):
    """(start_seconds, end_seconds) op de VTT's eigen klok, of None als de
    genormaliseerde quote niet woordelijk terug te vinden is."""
    needle = normalize_text(quote_text)
    if not needle:
        return None
    char_start = running_text.find(needle)
    if char_start == -1:
        return None
    char_end = char_start + len(needle) - 1

    start_cue = bisect_right(cue_end_offsets, char_start)
    end_cue = bisect_right(cue_end_offsets, char_end)
    if start_cue >= len(cues) or end_cue >= len(cues):
        return None
    return cues[start_cue]["start"], cues[end_cue]["end"]


def fetch_candidate_arguments(conn, topic_id, force):
    span_filter = "" if force else "AND ar.start_seconds IS NULL"
    return conn.execute(
        f"""SELECT ar.id, ar.document_id, ar.quote_text, d.debatdirect_id, d.published_at,
                   d.activiteit_aanvangstijd, d.speaker_person_id, d.turn_type, d.is_voorzitter_turn,
                   d.content AS turn_content
            FROM arguments ar
            JOIN documents d ON d.id = ar.document_id
            WHERE ar.topic_id = ? AND d.debatdirect_id IS NOT NULL {span_filter}
            ORDER BY d.debatdirect_id, ar.id""",
        (topic_id,),
    ).fetchall()


def _expected_offset_seconds(published_at, activiteit_aanvangstijd):
    """Grove schatting van de spreekbeurt-start t.o.v. het debatbegin --
    zelfde `video_offset_seconds`-concept als arguments-timed.json, hier
    gebruikt als kalibratie-anker in het Tier-2-only-fallbackpad."""
    if not published_at or not activiteit_aanvangstijd:
        return None
    return (datetime.fromisoformat(published_at) - datetime.fromisoformat(activiteit_aanvangstijd)).total_seconds()


def match_debate(cues, rows):
    """rows: argumenten van één debat (zelfde debatdirect_id). Retourneert
    {argument_id: (start_seconds, end_seconds)} in videoseconden, alleen voor
    argumenten die zowel matchten als binnen een kalibreerbaar debat vielen.

    Dit is het Tier-2-only-fallbackpad: één mediane kalibratie-offset over
    het hele debat, gebruikt voor beurten zonder Tier-1-anker (zie
    calibrate_debate) -- ongewijzigd t.o.v. de oorspronkelijke aanpak, dus
    geen regressie voor debatten waarvoor de events-API niets oplevert."""
    running_text, cue_end_offsets = build_running_index(cues)

    raw_matches = {}  # argument_id -> (raw_start, raw_end)
    # Meerdere argumenten kunnen in dezelfde spreekbeurt vallen (zelfde
    # published_at, dus dezelfde `expected`-waarde), maar hun quote begint op
    # verschillende posities bínnen die beurt -- raw_start - expected loopt
    # dus op naarmate een quote later in de beurt valt. Alleen de laagste
    # diff per beurt (de quote die het dichtst bij het begin van de beurt
    # ligt) is een bruikbaar kalibratiepunt; de mediaan van de rest ligt
    # systematisch te hoog (zie #106 -- gaf spannes die tientallen seconden
    # te vroeg lagen).
    min_diff_per_turn = {}
    for row in rows:
        span = find_quote_span(row["quote_text"], running_text, cue_end_offsets, cues)
        if span is None:
            continue
        raw_matches[row["id"]] = span

        expected = _expected_offset_seconds(row["published_at"], row["activiteit_aanvangstijd"])
        if expected is not None:
            diff = span[0] - expected
            if expected not in min_diff_per_turn or diff < min_diff_per_turn[expected]:
                min_diff_per_turn[expected] = diff

    calibration_samples = list(min_diff_per_turn.values())
    if len(calibration_samples) < MIN_MATCHES_FOR_CALIBRATION:
        return {}

    # De spreiding tussen de per-beurt kalibratiepunten hoort klein te zijn
    # (mediaan ~130s over ~800 onderzochte debatten) -- het HLS-manifest zelf
    # is altijd één doorlopende, ononderbroken opname die exact de volledige
    # wandklok-duur van de activiteit beslaat, ook over een schorsing heen
    # (bevestigd via ffprobe, zie #108: geen ontbrekend stuk video, geen
    # #EXT-X-DISCONTINUITY). Een grote spreiding betekent dus niet dat de
    # video hapert, maar dat `published_at` voor een deel van de argumenten
    # de echte schorsingsduur niet correct weerspiegelt -- een fout in de
    # VLOS-brondata, niet in deze matching. Beter dan blind een mediaan
    # tussen twee onverenigbare clusters te kiezen (die dan voor beide kanten
    # fout is, met zelfs negatieve start_seconds tot gevolg): het hele debat
    # ongekalibreerd laten, dezelfde "nooit gokken"-aanpak als bij een
    # ontbrekende ondertitel-match.
    if max(calibration_samples) - min(calibration_samples) > MAX_CALIBRATION_SPREAD_SECONDS:
        logger.warning(
            "Kalibratiepunten wijken te veel af (spreiding %.0fs > %.0fs) -- "
            "vermoedelijk onbetrouwbare published_at rond een schorsing, debat overgeslagen.",
            max(calibration_samples) - min(calibration_samples),
            MAX_CALIBRATION_SPREAD_SECONDS,
        )
        return {}

    calibration = statistics.median(calibration_samples)
    return {
        argument_id: (raw_start - calibration, raw_end - calibration)
        for argument_id, (raw_start, raw_end) in raw_matches.items()
    }


def load_events(events_json):
    """events_json: geparste inhoud van data/debate_events/<id>.json
    ({"startedAt": ..., "events": [...]}). Retourneert (started_at, events)
    met events als lijst van {"video_seconds", "eventType", "objectId"} --
    eventStart - startedAt is hier al één keer vooraf omgerekend naar
    videoseconden, zodat find_turn_anchor alleen nog met getallen hoeft te
    vergelijken."""
    started_at = datetime.fromisoformat(events_json["startedAt"])
    events = []
    for e in events_json.get("events", []):
        event_type = e.get("eventType")
        object_id = e.get("objectId")
        event_start_raw = e.get("eventStart")
        if not event_type or not object_id or not event_start_raw:
            continue
        event_start = datetime.fromisoformat(event_start_raw)
        events.append(
            {
                "video_seconds": (event_start - started_at).total_seconds(),
                "eventType": event_type,
                "objectId": object_id,
            }
        )
    return started_at, events


def expected_event_type(turn_type, is_voorzitter_turn):
    """Welk debatdirect-eventType bij deze VLOS-beurt hoort. Voorzitterbeurten
    (structureel nog steeds een <woordvoerder>-element) blijken in de
    events-API uitsluitend als 'chairman' voor te komen, nooit 'speaker' --
    geverifieerd op c1663929-... (zie docs/tk-data-sources-overview.md 5f)."""
    if turn_type == "interrumpant":
        return "interrupter"
    if is_voorzitter_turn:
        return "chairman"
    return "speaker"


def expected_turn_seconds(published_at, started_at):
    """published_at (VLOS markeertijdbegin, mogelijk zonder tijdzone) omgezet
    naar videoseconden t.o.v. started_at (het video-t=0-anker uit de
    events-API) -- het zoekcentrum voor find_turn_anchor, niet het
    uiteindelijke resultaat."""
    if not published_at:
        return None
    target = datetime.fromisoformat(published_at)
    if target.tzinfo is None:
        target = target.replace(tzinfo=started_at.tzinfo)
    return (target - started_at).total_seconds()


def find_turn_anchor(events, speaker_person_id, event_type, expected_seconds, window_seconds=TURN_ANCHOR_WINDOW_SECONDS):
    """Dichtstbijzijnde event met matchend objectId + eventType binnen
    `window_seconds` van `expected_seconds`, in videoseconden. None als er
    geen kandidaat is, of de dichtstbijzijnde toch te ver weg ligt (voorkomt
    dat een andere, latere beurt van dezelfde spreker per ongeluk als anker
    voor déze beurt gebruikt wordt)."""
    if speaker_person_id is None or expected_seconds is None:
        return None
    candidates = [e for e in events if e["objectId"] == speaker_person_id and e["eventType"] == event_type]
    if not candidates:
        return None
    best = min(candidates, key=lambda e: abs(e["video_seconds"] - expected_seconds))
    if abs(best["video_seconds"] - expected_seconds) > window_seconds:
        return None
    return best["video_seconds"]


def estimate_duration_seconds(quote_text):
    """Spreektempo-schatting van de duur van een quote (zelfde concept als
    arguments-timed.json), gebruikt als een geankerde beurt geen enkele
    VTT-match oplevert."""
    word_count = len(quote_text.split())
    return max(word_count / SPEAKING_WORDS_PER_SECOND, MIN_ESTIMATED_DURATION_SECONDS)


def turn_opening_needle(turn_content, word_count=TURN_OPENING_WORD_COUNT):
    """Eerste `word_count` woorden van een sprekerbeurt, ná het sprekerlabel
    (zie _SPEAKER_LABEL_RE) -- bruikbaar als VTT-matching-needle om te bepalen
    waar de beurt zélf begint, i.t.t. waar een specifiek argument daarbinnen
    begint (zie match_turn_with_anchor). None als er te weinig tekst overblijft
    om een betrouwbare match op te baseren."""
    if not turn_content:
        return None
    stripped = _SPEAKER_LABEL_RE.sub("", turn_content, count=1)
    words = stripped.split()[:word_count]
    if len(words) < 4:
        return None
    return " ".join(words)


def match_turn_with_anchor(cues, running_text, cue_end_offsets, turn_anchor_seconds, turn_rows, turn_content=None):
    """Eén sprekerbeurt met een Tier-1-anker (turn_anchor_seconds, in
    videoseconden). VTT-matches binnen de beurt verfijnen de exacte positie
    van elk argument, gekalibreerd op déze beurt (niet op een mediaan voor
    het hele debat).

    Kalibratiereferentie is bij voorkeur de beurt-openingstekst zelf
    (turn_opening_needle(turn_content)) -- niet het eerste gématchte
    ARGUMENT: een beurt begint vaak met tekst die geen eigen argument is (bv.
    "Voorzitter, dank u wel." of een langere inleidende reactie vóórdat het
    eerste geëxtraheerde argument begint). Zou je in plaats daarvan het eerste
    gématchte argument op het anker vastzetten, dan verdwijnt die inleiding
    stilzwijgend uit de berekening en komt *elk* argument in die beurt
    stelselmatig te vroeg te liggen, met precies de duur van die inleiding
    (in de praktijk enkele tot enkele tientallen seconden, zie issue #130).

    Lukt het niet om de beurt-opening zelf te vinden (VLOS-transcriptie en
    live-ondertiteling kunnen verschillen), dan valt dit terug op het eerste
    gématchte argument als kalibratiereferentie -- minder precies, maar beter
    dan de beurt overslaan.

    Levert geen enkele quote in de beurt een VTT-match op (ook de opening
    niet), dan valt de hele beurt terug op het anker zelf plus een
    spreektempo-schatting van de duur (estimate_duration_seconds) -- de
    eerder aspirational, nooit gebouwde video_offset_seconds-fallback."""
    raw_matches = {}
    for row in turn_rows:
        span = find_quote_span(row["quote_text"], running_text, cue_end_offsets, cues)
        if span is not None:
            raw_matches[row["id"]] = span

    if raw_matches:
        opening_needle = turn_opening_needle(turn_content)
        opening_span = find_quote_span(opening_needle, running_text, cue_end_offsets, cues) if opening_needle else None
        reference_raw_start = opening_span[0] if opening_span is not None else min(start for start, _end in raw_matches.values())
        calibration = reference_raw_start - turn_anchor_seconds
        return {
            argument_id: (start - calibration, end - calibration)
            for argument_id, (start, end) in raw_matches.items()
        }

    return {
        row["id"]: (turn_anchor_seconds, turn_anchor_seconds + estimate_duration_seconds(row["quote_text"]))
        for row in turn_rows
    }


def calibrate_debate(cues, debate_rows, events_json=None):
    """Eén debat (rows = argumenten met dezelfde debatdirect_id), side-effect-
    vrij (geen DB/disk-IO -- events_json is al ingelezen door de aanroeper).
    Retourneert (spans, anchors):
    - spans: {argument_id: (start_seconds, end_seconds)}
    - anchors: {document_id: wall-clock ISO8601-string van het Tier-1-anker}
      voor beurten die een events-API-anker kregen -- dit is het drift-vrije
      alternatief voor documents.published_at (zie _speaker_event_url in
      build_static_data.py/export_argument_doc.py/build_confrontatie_export.py,
      issue #148-vervolg: "video op dit moment" sprong naar het begin omdat
      published_at rond sommige beurten uren kan afwijken van de werkelijke
      spreektijd).

    events_json=None reproduceert exact match_debate()'s gedrag (Tier-2-only,
    debat-brede mediaan) -- de niet-regressie-garantie voor debatten zonder
    events-cache. Met events_json: elke beurt (gegroepeerd op document_id)
    krijgt eerst een Tier-1-poging (find_turn_anchor); lukt die niet, dan valt
    alleen díe beurt terug op het Tier-2-debat-brede pad, niet het hele
    debat -- en blijft er voor die beurt geen anchors-entry over."""
    if events_json is None:
        return match_debate(cues, debate_rows), {}

    running_text, cue_end_offsets = build_running_index(cues)
    started_at, events = load_events(events_json)

    rows_by_turn = {}
    for row in debate_rows:
        rows_by_turn.setdefault(row["document_id"], []).append(row)

    spans = {}
    anchors = {}
    unanchored_rows = []
    for turn_rows in rows_by_turn.values():
        first = turn_rows[0]
        event_type = expected_event_type(first["turn_type"], first["is_voorzitter_turn"])
        expected_seconds = expected_turn_seconds(first["published_at"], started_at)
        anchor = find_turn_anchor(events, first["speaker_person_id"], event_type, expected_seconds)
        if anchor is None:
            unanchored_rows.extend(turn_rows)
            continue
        anchors[first["document_id"]] = (started_at + timedelta(seconds=anchor)).isoformat()
        spans.update(
            match_turn_with_anchor(cues, running_text, cue_end_offsets, anchor, turn_rows, turn_content=first["turn_content"])
        )

    if unanchored_rows:
        spans.update(match_debate(cues, unanchored_rows))

    return spans, anchors


def match(topic_keyword, dry_run=False, force=False):
    conn = db.connect()
    topic_row = conn.execute("SELECT id FROM topics WHERE slug = ?", (topic_keyword,)).fetchone()
    if topic_row is None:
        raise SystemExit(f"onbekende topic-slug: {topic_keyword}")
    try:
        _match_topic(conn, topic_row["id"], dry_run=dry_run, force=force)
    finally:
        conn.close()


def match_all(dry_run=False, force=False):
    conn = db.connect()
    try:
        topic_rows = conn.execute("SELECT id, slug FROM topics ORDER BY slug").fetchall()
        for topic_row in topic_rows:
            logger.info("=== topic: %s ===", topic_row["slug"])
            _match_topic(conn, topic_row["id"], dry_run=dry_run, force=force)
    finally:
        conn.close()


def _match_topic(conn, topic_id, dry_run=False, force=False):
    rows = fetch_candidate_arguments(conn, topic_id, force)
    if not rows:
        logger.info("Geen argumenten met een debatdirect_id en (nog) geen span.")
        return

    rows_by_debate = {}
    for row in rows:
        rows_by_debate.setdefault(row["debatdirect_id"], []).append(row)

    matched, uncalibrated, no_subtitles, total = 0, 0, 0, len(rows)
    for debatdirect_id, debate_rows in rows_by_debate.items():
        cache_path = SUBTITLES_DIR / f"{debatdirect_id}.vtt"
        if not cache_path.exists():
            no_subtitles += len(debate_rows)
            logger.warning("Geen ondertitel-cache voor debat %s (%d argumenten overgeslagen).", debatdirect_id, len(debate_rows))
            continue

        cues = parse_vtt(cache_path.read_text())

        events_path = DEBATE_EVENTS_DIR / f"{debatdirect_id}.json"
        events_json = json.loads(events_path.read_text()) if events_path.exists() else None
        spans, anchors = calibrate_debate(cues, debate_rows, events_json)

        if not spans and len(debate_rows) > 0:
            uncalibrated += len(debate_rows)

        matched += len(spans)
        if not dry_run:
            if spans:
                conn.executemany(
                    "UPDATE arguments SET start_seconds = ?, end_seconds = ? WHERE id = ?",
                    [(start, end, argument_id) for argument_id, (start, end) in spans.items()],
                )
            if anchors:
                # Drift-vrij alternatief voor documents.published_at (zie
                # calibrate_debate hierboven) -- gebruikt door
                # _speaker_event_url voor de "video op dit moment"-link.
                conn.executemany(
                    "UPDATE documents SET speaker_event_anchor_at = ? WHERE id = ?",
                    [(anchor_at, document_id) for document_id, anchor_at in anchors.items()],
                )
            if force:
                # --force herbeoordeelt ook argumenten met een bestaande span; als
                # een debat nu (anders dan een eerdere run) niet meer kalibreert
                # -- bv. de nieuwe spreiding-check in #108 -- moet die oude,
                # inmiddels onbetrouwbaar geachte span ook echt verdwijnen i.p.v.
                # stilzwijgend blijven staan.
                stale_ids = [row["id"] for row in debate_rows if row["id"] not in spans]
                if stale_ids:
                    conn.executemany(
                        "UPDATE arguments SET start_seconds = NULL, end_seconds = NULL WHERE id = ?",
                        [(argument_id,) for argument_id in stale_ids],
                    )
                # Zelfde reden als hierboven, nu voor het Tier-1-anker per beurt.
                stale_document_ids = {row["document_id"] for row in debate_rows} - anchors.keys()
                if stale_document_ids:
                    conn.executemany(
                        "UPDATE documents SET speaker_event_anchor_at = NULL WHERE id = ?",
                        [(document_id,) for document_id in stale_document_ids],
                    )

    if not dry_run:
        conn.commit()

    logger.info(
        "Klaar: %d/%d argumenten gematcht+gekalibreerd, %d in te weinig-matches-debatten, %d zonder ondertitel-cache.",
        matched, total, uncalibrated, no_subtitles,
    )
    if dry_run:
        logger.info("(--dry-run: niets weggeschreven naar de database)")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", help="topic-slug, bv. stikstof (default: alle topics)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="ook argumenten met een bestaande span opnieuw matchen")
    args = parser.parse_args()
    if args.topic:
        match(args.topic, dry_run=args.dry_run, force=args.force)
    else:
        match_all(dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
