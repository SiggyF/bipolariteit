"""
Vult arguments.start_seconds/end_seconds door quote_text zin-precies te
matchen tegen de gecachete WebVTT-ondertitel-cues (pipeline/fetch_subtitles.py),
zoals aangetoond in de PoC (docs/poc/video-eigen-player/, zie ook
docs/tk-data-sources-overview.md 5b/5c) en gespecificeerd in
docs/design/videoplayer/README.md ("Spannes verrijken").

Twee stappen per debat:
1. **Matchen**: quote_text van elk argument opzoeken als aaneengesloten,
   genormaliseerde tekst in de cues (een quote kan over meerdere cues lopen,
   dus lopende tekst i.p.v. cue-voor-cue-vensters). Levert per match een
   tijdspanne op de VTT's eigen, niet bij nul beginnende klok
   (X-TIMESTAMP-MAP, zie 5c) -- nog niet bruikbaar als videoseconden.
2. **Calibreren**: die klok wordt per debat omgezet naar seconden-sinds-
   videobegin door 'm te vergelijken met de al bekende, grovere schatting
   (document.published_at t.o.v. de debat-aanvangstijd -- hetzelfde
   `video_offset_seconds`-concept als in arguments-timed.json). De mediane
   afwijking over alle gematchte quotes in dat debat is de kalibratie-
   constante; één afwijkende match trekt die dankzij de mediaan niet scheef.

Quotes die niet woordelijk in de ondertitels voorkomen (VLOS-transcriptie en
live-ondertiteling kunnen verschillen, zie de PoC-caveat) blijven simpelweg
ongematcht -- geen gok, de frontend valt voor die argumenten terug op
video_offset_seconds plus een vaste duur (zie het datacontract in schema.sql).

Idempotent via arguments.start_seconds IS NULL; --force matcht opnieuw.

Gebruik:
    uv run python -m pipeline.match_argument_spans --topic stikstof [--dry-run] [--force]
"""

import argparse
import logging
import re
import statistics
from bisect import bisect_right
from datetime import datetime

from pipeline.db import db
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
MIN_MATCHES_FOR_CALIBRATION = 3


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
        f"""SELECT ar.id, ar.quote_text, d.debatdirect_id, d.published_at, d.activiteit_aanvangstijd
            FROM arguments ar
            JOIN documents d ON d.id = ar.document_id
            WHERE ar.topic_id = ? AND d.debatdirect_id IS NOT NULL {span_filter}
            ORDER BY d.debatdirect_id, ar.id""",
        (topic_id,),
    ).fetchall()


def _expected_offset_seconds(published_at, activiteit_aanvangstijd):
    """Grove schatting van de spreekbeurt-start t.o.v. het debatbegin --
    zelfde `video_offset_seconds`-concept als arguments-timed.json, hier
    gebruikt als kalibratie-anker in plaats van als eindresultaat."""
    if not published_at or not activiteit_aanvangstijd:
        return None
    return (datetime.fromisoformat(published_at) - datetime.fromisoformat(activiteit_aanvangstijd)).total_seconds()


def match_debate(cues, rows):
    """rows: argumenten van één debat (zelfde debatdirect_id). Retourneert
    {argument_id: (start_seconds, end_seconds)} in videoseconden, alleen voor
    argumenten die zowel matchten als binnen een kalibreerbaar debat vielen."""
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

    calibration = statistics.median(calibration_samples)
    return {
        argument_id: (raw_start - calibration, raw_end - calibration)
        for argument_id, (raw_start, raw_end) in raw_matches.items()
    }


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
        spans = match_debate(cues, debate_rows)
        if not spans and len(debate_rows) > 0:
            uncalibrated += len(debate_rows)

        matched += len(spans)
        if not dry_run and spans:
            conn.executemany(
                "UPDATE arguments SET start_seconds = ?, end_seconds = ? WHERE id = ?",
                [(start, end, argument_id) for argument_id, (start, end) in spans.items()],
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
