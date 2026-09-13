"""
Vult argument_tags.start_seconds/end_seconds voor tags met een verbatim
quote_fragment (issue #109) -- zelfde patroon als
pipeline/match_argument_spans.py, maar een niveau dieper: niet de hele
arguments.quote_text, maar het specifieke zinsdeel waarop één tag slaat.

Draait NA pipeline/tag_arguments.py (dat quote_fragment vult, gevalideerd via
classify_quote_fragment()) EN NA pipeline/match_argument_spans.py (dat de
ouder-argument-spanne arguments.start_seconds/end_seconds al gevuld moet
hebben) -- zonder een gekalibreerde argument-spanne is er niets om de
fragment-spanne aan op te hangen.

Geen aparte kalibratie-pass nodig: de kalibratieconstante van het argument
zelf (raw_argument_start - arguments.start_seconds) is al bekend en
toepasbaar op het fragment, want beide liggen op dezelfde VTT-klok. Het
fragment wordt bovendien alleen gezocht binnen de cues van de al bekende
argument-spanne (niet het hele debat) -- voorkomt dat een kort fragment
toevallig elders in het debat ook voorkomt en de verkeerde plek oplevert
(zelfde risico als bij de oorspronkelijke hypothese in #106, en zichtbaar
gemaakt door de "ambigu"-classificatie in tag_arguments.classify_quote_fragment,
die dat risico al binnen de hele quote afvangt -- dit is de video-kant
ervan).

Ondersteunt meerdelige fragments (twee zinsdelen die het model met "..."
aan elkaar plakte, zie tag_arguments._ELLIPSIS_RE/QF_GELDIG_MEERDELIG): de
spanne loopt dan van het begin van het eerste deel tot het eind van het
laatste.

Idempotent via argument_tags.start_seconds IS NULL; --force matcht opnieuw.

Gebruik:
    uv run python -m pipeline.match_tag_spans --topic energietransitie [--dry-run] [--force]
"""

import argparse
import logging
import re
from bisect import bisect_right

from pipeline.db import db
from pipeline.fetch_subtitles import SUBTITLES_DIR
from pipeline.match_argument_spans import build_running_index, find_quote_span, normalize_text, parse_vtt

logger = logging.getLogger(__name__)

# Zelfde jokerteken-regex als tag_arguments._ELLIPSIS_RE (bewust hier
# gedupliceerd i.p.v. een private naam cross-module te importeren) -- een
# wijziging aan het ene patroon moet bewust ook hier meegenomen worden.
_ELLIPSIS_RE = re.compile(r"\.\.\.|…")


def cues_in_window(cues, window_start, window_end):
    """Cues die (deels) binnen [window_start, window_end] vallen, op de
    VTT's eigen (ongekalibreerde) klok -- het venster van de al bekende
    ouder-argument-spanne, zodat een fragment niet per ongeluk buiten de
    eigen quote matcht."""
    return [c for c in cues if c["end"] >= window_start and c["start"] <= window_end]


def find_fragment_span(quote_fragment, cues):
    """(start_seconds, end_seconds) van quote_fragment binnen `cues`, op de
    VTT's eigen klok, of None als het niet verbatim terug te vinden is.
    `cues` is al beperkt tot het venster van de ouder-argument-quote (zie
    cues_in_window) -- geen debat-brede zoektocht."""
    running_text, cue_end_offsets = build_running_index(cues)

    if not _ELLIPSIS_RE.search(quote_fragment):
        return find_quote_span(quote_fragment, running_text, cue_end_offsets, cues)

    # Meerdelig fragment: elk deel apart normaliseren, "..." wordt een
    # regex-gat (.*?) ertussen -- zelfde aanpak als
    # tag_arguments.classify_quote_fragment(), nu met offsets i.p.v. een
    # kale bool, om de spanne (begin eerste deel - eind laatste deel) terug
    # te kunnen herleiden.
    delen = [normalize_text(deel) for deel in _ELLIPSIS_RE.split(quote_fragment)]
    delen = [deel for deel in delen if deel]
    if not delen:
        return None
    pattern = ".*?".join(re.escape(deel) for deel in delen)
    match = re.search(pattern, running_text)
    if match is None:
        return None
    char_start, char_end = match.start(), match.end() - 1
    start_cue = bisect_right(cue_end_offsets, char_start)
    end_cue = bisect_right(cue_end_offsets, char_end)
    if start_cue >= len(cues) or end_cue >= len(cues):
        return None
    return cues[start_cue]["start"], cues[end_cue]["end"]


def fetch_candidate_tags(conn, topic_id, force):
    """argument_tags-rijen met een quote_fragment en een al gekalibreerd
    ouder-argument, gegroepeerd (via ORDER BY) per debat dan per argument --
    alleen created_by='llm' heeft een frase-concept (zie #109, "Scope van de
    proefdraai")."""
    span_filter = "" if force else "AND at.start_seconds IS NULL"
    return conn.execute(
        f"""SELECT at.id AS tag_id, at.quote_fragment,
                   ar.id AS argument_id, ar.quote_text, ar.start_seconds AS argument_start,
                   ar.end_seconds AS argument_end, d.debatdirect_id
            FROM argument_tags at
            JOIN arguments ar ON ar.id = at.argument_id
            JOIN documents d ON d.id = ar.document_id
            WHERE ar.topic_id = ?
              AND at.created_by = 'llm'
              AND at.quote_fragment IS NOT NULL
              AND ar.start_seconds IS NOT NULL
              AND d.debatdirect_id IS NOT NULL
              {span_filter}
            ORDER BY d.debatdirect_id, ar.id, at.id""",
        (topic_id,),
    ).fetchall()


def match_debate_tags(cues, debate_rows):
    """debate_rows: argument_tags-rijen (via fetch_candidate_tags) van één
    debat. Retourneert {tag_id: (start_seconds, end_seconds)} in
    videoseconden -- alleen voor tags waarvan zowel het ouder-argument als
    het fragment zelf verbatim terugvonden werden."""
    running_text, cue_end_offsets = build_running_index(cues)

    rows_by_argument = {}
    for row in debate_rows:
        rows_by_argument.setdefault(row["argument_id"], []).append(row)

    spans = {}
    for argument_id, tag_rows in rows_by_argument.items():
        first = tag_rows[0]
        raw_argument_span = find_quote_span(first["quote_text"], running_text, cue_end_offsets, cues)
        if raw_argument_span is None:
            logger.warning(
                "    argument %d: quote_text niet meer verbatim terug te vinden -- tags overgeslagen.", argument_id
            )
            continue
        raw_argument_start, raw_argument_end = raw_argument_span
        calibration = raw_argument_start - first["argument_start"]

        window_cues = cues_in_window(cues, raw_argument_start, raw_argument_end)
        for row in tag_rows:
            frag_span = find_fragment_span(row["quote_fragment"], window_cues)
            if frag_span is None:
                continue
            raw_frag_start, raw_frag_end = frag_span
            spans[row["tag_id"]] = (raw_frag_start - calibration, raw_frag_end - calibration)

    return spans


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
    rows = fetch_candidate_tags(conn, topic_id, force)
    if not rows:
        logger.info("Geen tags met een quote_fragment, gekalibreerd ouder-argument en (nog) geen spanne.")
        return

    rows_by_debate = {}
    for row in rows:
        rows_by_debate.setdefault(row["debatdirect_id"], []).append(row)

    matched, no_subtitles, total = 0, 0, len(rows)
    for debatdirect_id, debate_rows in rows_by_debate.items():
        cache_path = SUBTITLES_DIR / f"{debatdirect_id}.vtt"
        if not cache_path.exists():
            no_subtitles += len(debate_rows)
            logger.warning("Geen ondertitel-cache voor debat %s (%d tags overgeslagen).", debatdirect_id, len(debate_rows))
            continue

        cues = parse_vtt(cache_path.read_text())
        spans = match_debate_tags(cues, debate_rows)
        matched += len(spans)

        if not dry_run and spans:
            conn.executemany(
                "UPDATE argument_tags SET start_seconds = ?, end_seconds = ? WHERE id = ?",
                [(start, end, tag_id) for tag_id, (start, end) in spans.items()],
            )
        if not dry_run and force:
            # --force herbeoordeelt ook tags met een bestaande spanne; als een
            # fragment nu niet meer matcht (bv. een ondertussen bijgewerkte
            # ondertitel-cache), moet die oude spanne ook echt verdwijnen
            # i.p.v. stilzwijgend blijven staan -- zelfde norm als
            # match_argument_spans.py.
            stale_ids = [row["tag_id"] for row in debate_rows if row["tag_id"] not in spans]
            if stale_ids:
                conn.executemany(
                    "UPDATE argument_tags SET start_seconds = NULL, end_seconds = NULL WHERE id = ?",
                    [(tag_id,) for tag_id in stale_ids],
                )

    if not dry_run:
        conn.commit()

    logger.info(
        "Klaar: %d/%d tags gematcht+gekalibreerd, %d zonder ondertitel-cache.",
        matched, total, no_subtitles,
    )
    if dry_run:
        logger.info("(--dry-run: niets weggeschreven naar de database)")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", help="topic-slug, bv. energietransitie (default: alle topics)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="ook tags met een bestaande spanne opnieuw matchen")
    args = parser.parse_args()
    if args.topic:
        match(args.topic, dry_run=args.dry_run, force=args.force)
    else:
        match_all(dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
