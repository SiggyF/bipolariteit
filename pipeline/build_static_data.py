"""
Exporteert de SQLite-inhoud naar de gecommitte JSON die de Astro-frontend
bouwt (`data/export/topics-index.json` + `data/export/topics/<slug>.json`).
Puur een export -- geen LLM-calls, geen schrijfacties naar de DB.

Exporteert Stage 1-argumenten (pro/contra/unclear) inclusief tags, en Stage 2
(redactie-balanscheck per document, opposition-links tussen argumenten).
Bewust één platte `arguments`-lijst zonder voorgeaggregeerde cijfers: alles
wat af te leiden is (stance-kolommen, statistieken per partij, tags per
partij) leidt de frontend zelf af, zodat filteren nooit een grafiek en een
kolom uit de pas kan laten lopen.
`prompt_version` wordt meegeëxporteerd per argument zodat zichtbaar is welke
extractieprompt een argument opleverde -- de DB bevat nu een mix van vóór-
en na-Gemini-review-fix geëxtraheerde argumenten.

Exporteert alleen vanaf [verwerking].vanaf in data/politieke-periodes.toml
(de huidige en vorige kamerperiode); oudere argumenten blijven in de database
maar komen niet in de JSON en dus niet op de site.

Gebruik:
    uv run python -m pipeline.build_static_data
"""

import argparse
import json
import logging
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

import pandas as pd
import prince

from pipeline.db import db
from pipeline.extract_arguments import PROMPT_VERSION as EXTRACT_PROMPT_VERSION
from pipeline.extract_arguments import _build_prompt as _build_extraction_prompt
from pipeline.match_argument_spans import expected_event_type
from pipeline.periodes import PeriodeIndex
from pipeline.redactie_check import PROMPT_TEMPLATE as REDACTIE_PROMPT_TEMPLATE
from pipeline.redactie_check import PROMPT_VERSION as REDACTIE_PROMPT_VERSION
from pipeline.redactie_check import _format_arguments_block
from pipeline.tag_arguments import PROMPT_VERSION as TAG_PROMPT_VERSION
from pipeline.tag_arguments import _build_prompt as _build_tagging_prompt
from pipeline.tag_arguments import build_tag_catalogue

logger = logging.getLogger(__name__)

EXPORT_DIR = Path(__file__).parent.parent / "data" / "export"
_AMSTERDAM = ZoneInfo("Europe/Amsterdam")


def _speaker_event_url(video_url, published_at, anchor_at=None, turn_type=None, is_voorzitter_turn=False):
    """Debat Direct ondersteunt een deep link naar het moment dat een
    specifieke spreker/interruptie/voorzitter begint
    (?event=<eventType><ISO8601-tijdstip+offset>), naast de generieke
    .../video-link naar het begin van het hele debat.

    eventType (via expected_event_type, pipeline/match_argument_spans.py)
    hing hier tot issue #148-vervolg altijd hardgecodeerd vast op "speaker" --
    voor een interruptie (turn_type="interrumpant") bestaat er in de
    events-API geen "speaker"-event op dat tijdstip, dus Debat Direct kon geen
    match vinden en sprong terug naar het begin van het debat. Geverifieerd
    live: hetzelfde tijdstip met eventType "interrupter" i.p.v. "speaker"
    seekt wel naar de juiste beurt.

    anchor_at (documents.speaker_event_anchor_at, al tz-aware) heeft de
    voorkeur boven published_at: het is het drift-vrije Tier-1-anker uit de
    debatdirect events-API (pipeline/match_argument_spans.py calibrate_debate),
    terwijl published_at (VLOS-markeertijdbegin) voor sommige beurten uren kan
    afwijken van de werkelijke spreektijd. published_at zelf is naive lokale
    tijd zonder offset -- Europe/Amsterdam-lokalisatie geeft automatisch de
    juiste +01:00/+02:00 DST-offset i.p.v. een hardgecodeerde regel. anchor_at
    is NULL voor beurten zonder Tier-1-anker; dan blijft published_at de
    enige (beste-poging) bron."""
    if not video_url or not (anchor_at or published_at):
        return None
    base = video_url[: -len("/video")] if video_url.endswith("/video") else video_url
    dt = datetime.fromisoformat(anchor_at) if anchor_at else datetime.fromisoformat(published_at).replace(tzinfo=_AMSTERDAM)
    event_type = expected_event_type(turn_type, is_voorzitter_turn)
    event = quote(dt.strftime("%Y-%m-%dT%H:%M:%S%z"), safe="")
    return f"{base}?event={event_type}{event}"


def _thumbnail_url(video_url, published_at, start_seconds):
    """Bouwt een still-URL via Debat Direct's eigen scrub-bar-thumbnail-
    endpoint (zie docs/tk-data-sources-overview.md 5e) op het moment waarop
    dit argument wordt uitgesproken. Dat is inhoudelijk representatiever dan
    Debat Direct's eigen default (`startedAt + 45s`, zonder enige relatie tot
    de inhoud -- idem 5e), omdat het echt het moment van een spreekbeurt over
    dit topic pakt i.p.v. een willekeurig punt vlak na het begin van het debat.
    `locationId` (het zaal-pad-segment) zit niet los in de database, alleen
    verwerkt in `video_url` (opgebouwd in `enrich_video_url.py`), dus parsen
    we 'm terug uit die URL i.p.v. 'm apart op te slaan."""
    if not video_url or not published_at or start_seconds is None:
        return None
    parts = video_url.split("/")
    if len(parts) < 6:
        return None
    location_id = parts[5]
    dt = datetime.fromisoformat(published_at).replace(tzinfo=_AMSTERDAM) + timedelta(seconds=start_seconds)
    return f"https://livestreaming-thumb.b67buv2.tweedekamer.nl/{location_id}/1080/{dt.strftime('%Y-%m-%d')}/{dt.strftime('%H:%M:%S%z')}.jpg"


def _topic_image_url(arguments):
    """Still van het eerste argument in dit topic met een gematchte
    videospanne (start_seconds), als representatief beeld voor de topic-tegel
    op de homepage. Bewust geen "beste"/langste-argument-selectie -- dat is
    een aparte redactionele keuze die nog niet gemaakt is (zie issue #111)."""
    for argument in arguments:
        document = argument["document"]
        url = _thumbnail_url(document["video_url"], document["published_at"], argument["start_seconds"])
        if url:
            return url
    return None


def fetch_redactie_reviews(conn, topic_id):
    """document_id -> {pass_status, notes}. Nooit een oordeel over of een
    argument feitelijk klopt, alleen de corpus-brede pro/contra-balans op
    het moment dat het document verwerkt is -- zie schema.sql/redactie_check.py."""
    rows = conn.execute(
        """SELECT rr.document_id, rr.pass_status, rr.notes
           FROM redactie_reviews rr
           JOIN documents d ON d.id = rr.document_id
           WHERE d.topic_id = ?""",
        (topic_id,),
    ).fetchall()
    return {row["document_id"]: {"pass_status": row["pass_status"], "notes": row["notes"]} for row in rows}


def fetch_oppositions(conn, topic_id):
    """argument_id -> lijst van tegenargumenten (symmetrisch: zowel vanaf
    argument_a als argument_b bekeken), voor het tonen van een link tussen
    een argument en zijn tegenhanger(s) in de frontend. Nooit een oordeel
    over wie gelijk heeft -- alleen de relatie zelf (direct_rebuttal/thematic)."""
    rows = conn.execute(
        """SELECT ao.argument_a_id, ao.argument_b_id, ao.relation_type, ao.confidence
           FROM argument_oppositions ao
           JOIN arguments a ON a.id = ao.argument_a_id
           WHERE a.topic_id = ?""",
        (topic_id,),
    ).fetchall()

    oppositions_by_argument = {}
    for row in rows:
        a_id, b_id = row["argument_a_id"], row["argument_b_id"]
        entry = {"relation_type": row["relation_type"], "confidence": row["confidence"]}
        oppositions_by_argument.setdefault(a_id, []).append({"argument_id": b_id, **entry})
        oppositions_by_argument.setdefault(b_id, []).append({"argument_id": a_id, **entry})
    return oppositions_by_argument


def fetch_arguments(conn, topic_id, periode_index):
    rows = conn.execute(
        """SELECT ar.id, ar.stance, ar.typology, ar.quote_text, ar.quote_context,
                  ar.prompt_version, ar.start_seconds, ar.end_seconds,
                  ac.name AS actor_name, ac.party AS actor_party,
                  d.id AS document_id, d.url AS document_url, d.video_url, d.published_at,
                  d.tweedekamer_activiteit_url, d.speaker_role_title, d.raw_video_url,
                  d.speaker_event_anchor_at, d.turn_type, d.is_voorzitter_turn
           FROM arguments ar
           JOIN actors ac ON ac.id = ar.actor_id
           JOIN documents d ON d.id = ar.document_id
           WHERE ar.topic_id = ?
             AND d.published_at >= ?
             AND ar.stance != 'ander_onderwerp'
           ORDER BY ar.id""",
        (topic_id, periode_index.drempel),
    ).fetchall()

    claims_by_argument = {}
    for claim in conn.execute(
        """SELECT c.argument_id, c.claim_text, c.attributed_source_text
           FROM claims c JOIN arguments ar ON ar.id = c.argument_id
           WHERE ar.topic_id = ?""",
        (topic_id,),
    ).fetchall():
        claims_by_argument.setdefault(claim["argument_id"], []).append(
            {"claim_text": claim["claim_text"], "attributed_source_text": claim["attributed_source_text"]}
        )

    tags_by_argument = {}
    for tag in conn.execute(
        """SELECT at.argument_id, t.sleutel, t.beschrijving, t.labelgroep,
                  lg.perspectief, at.created_by, at.reden
           FROM argument_tags at
           JOIN tags t ON t.sleutel = at.tag_sleutel
           JOIN labelgroepen lg ON lg.naam = t.labelgroep
           JOIN arguments ar ON ar.id = at.argument_id
           WHERE ar.topic_id = ?
             AND t.active = 1 AND lg.active = 1""",
        (topic_id,),
    ).fetchall():
        tags_by_argument.setdefault(tag["argument_id"], []).append(
            {
                "sleutel": tag["sleutel"],
                "beschrijving": tag["beschrijving"],
                "labelgroep": tag["labelgroep"],
                "perspectief": tag["perspectief"],
                "created_by": tag["created_by"],
                "reden": tag["reden"],
            }
        )

    redactie_by_document = fetch_redactie_reviews(conn, topic_id)
    oppositions_by_argument = fetch_oppositions(conn, topic_id)

    arguments = []
    for row in rows:
        arguments.append(
            {
                "id": row["id"],
                "stance": row["stance"],
                "typology": row["typology"],
                "quote_text": row["quote_text"],
                "quote_context": row["quote_context"],
                "prompt_version": row["prompt_version"],
                # Zin-precies gematchte videospanne (pipeline/match_argument_spans.py),
                # of NULL als quote_text niet (succesvol) tegen de ondertitels gematcht
                # kon worden -- de frontend valt dan terug op video_offset_seconds.
                "start_seconds": row["start_seconds"],
                "end_seconds": row["end_seconds"],
                "actor": {
                    "name": row["actor_name"],
                    "party": row["actor_party"],
                    "role_title": row["speaker_role_title"],
                },
                "document": {
                    "id": row["document_id"],
                    "url": row["document_url"],
                    "video_url": row["video_url"],
                    # Naive lokale tijd (VLOS markeertijdbegin), zonder offset --
                    # de frontend gebruikt alleen het datumdeel, voor het datumfilter.
                    "published_at": row["published_at"],
                    "speaker_video_url": _speaker_event_url(
                        row["video_url"],
                        row["published_at"],
                        row["speaker_event_anchor_at"],
                        row["turn_type"],
                        row["is_voorzitter_turn"],
                    ),
                    "tweedekamer_activiteit_url": row["tweedekamer_activiteit_url"],
                    "redactie_review": redactie_by_document.get(row["document_id"]),
                    # Het afspeelbare HLS-manifest (pipeline/fetch_subtitles.py); NULL
                    # zolang de detail-API nog niet (succesvol) bevraagd is voor dit debat.
                    "raw_video_url": row["raw_video_url"],
                },
                # Kamer- en regeringsperiode van de publicatiedatum: staats-
                # rechtelijke context waarop de frontend kan filteren zonder
                # zelf datumgrenzen te kennen (data/politieke-periodes.toml).
                "periode": periode_index.voor(row["published_at"]),
                "claims": claims_by_argument.get(row["id"], []),
                "tags": tags_by_argument.get(row["id"], []),
                "oppositions": oppositions_by_argument.get(row["id"], []),
            }
        )
    return arguments


def fetch_party_tag_counts(conn, topic_id, drempel):
    """(party, tag_sleutel, tag_beschrijving, labelgroep) -> count, alleen
    LLM-toegekende, actieve tags -- de 3 deterministische labelgroepen
    (Actor Type/Issue Arena/Parlementaire Context) zijn bij TK-data vrijwel
    altijd hetzelfde voor elk argument en dragen dus geen onderscheidend
    signaal bij aan "welke partij hoort bij welk type argument"."""
    rows = conn.execute(
        """SELECT a.party AS party, t.sleutel, t.beschrijving, t.labelgroep, COUNT(*) AS n
           FROM argument_tags at
           JOIN arguments ar ON ar.id = at.argument_id
           JOIN actors a ON a.id = ar.actor_id
           JOIN tags t ON t.sleutel = at.tag_sleutel
           JOIN documents d ON d.id = ar.document_id
           WHERE ar.topic_id = ? AND at.created_by = 'llm' AND t.active = 1
             AND a.party IS NOT NULL
             AND d.published_at >= ?
           GROUP BY a.party, t.sleutel""",
        (topic_id, drempel),
    ).fetchall()
    return rows


def build_correspondence_analysis(rows, min_party_total=3, min_tag_total=2):
    """Correspondentieanalyse (via `prince`, hetzelfde gevestigde techniek-
    familie als HOMALS/MCA maar dan voor een simpele tweeweg-tabel) op de
    partij x tag-contingentietabel: projecteert partijen én tags in dezelfde
    2D-ruimte, zodat een partij dicht bij de tags staat die het vaakst met
    die partij samen voorkomen. Alleen bruikbaar met genoeg data; retourneert
    None als de tabel na filtering te klein is voor een zinnige analyse."""
    df = pd.DataFrame(
        [(row["party"], row["sleutel"], row["n"]) for row in rows],
        columns=["party", "sleutel", "n"],
    )
    party_totals = df.groupby("party")["n"].sum()
    tag_totals = df.groupby("sleutel")["n"].sum()
    keep_parties = party_totals[party_totals >= min_party_total].index
    keep_tags = tag_totals[tag_totals >= min_tag_total].index
    df = df[df["party"].isin(keep_parties) & df["sleutel"].isin(keep_tags)]

    if df["party"].nunique() < 3 or df["sleutel"].nunique() < 3:
        return None

    table = df.pivot_table(index="party", columns="sleutel", values="n", aggfunc="sum", fill_value=0)
    tag_meta = {row["sleutel"]: (row["beschrijving"], row["labelgroep"]) for row in rows}

    ca = prince.CA(n_components=2, random_state=42)
    ca = ca.fit(table)
    row_coords = ca.row_coordinates(table)
    col_coords = ca.column_coordinates(table)
    inertia_pct = [round(v, 1) for v in ca.percentage_of_variance_[:2]]

    return {
        "inertia_pct": inertia_pct,
        "parties": [
            {"party": party, "x": float(row_coords.loc[party, 0]), "y": float(row_coords.loc[party, 1]), "n": int(party_totals[party])}
            for party in table.index
        ],
        "tags": [
            {
                "sleutel": sleutel,
                "beschrijving": tag_meta[sleutel][0],
                "labelgroep": tag_meta[sleutel][1],
                "x": float(col_coords.loc[sleutel, 0]),
                "y": float(col_coords.loc[sleutel, 1]),
                "n": int(tag_totals[sleutel]),
            }
            for sleutel in table.columns
        ],
    }


def fetch_pipeline_status(conn, topic_row, drempel):
    """Ruwe voortgangscijfers per stap van de pipeline (crawlen -> Stage 1
    extractie -> tagging -> Stage 2 redactie-check), voor de publieke
    /status-pagina. Puur telwerk, geen kwaliteitsoordeel.

    Telt alleen binnen de verwerkingsdrempel, anders zou de voortgangsbalk
    blijven hangen op documenten die we bewust niet verwerken."""
    topic_id = topic_row["id"]

    documents_total, extraction_attempted = conn.execute(
        """SELECT COUNT(*), COUNT(extraction_attempted_at)
           FROM documents WHERE topic_id = ? AND published_at >= ?""",
        (topic_id, drempel),
    ).fetchone()

    arguments_total, arguments_tagged = conn.execute(
        """SELECT COUNT(*), COUNT(ar.tagged_at) FROM arguments ar
           JOIN documents d ON d.id = ar.document_id
           WHERE ar.topic_id = ? AND d.published_at >= ?""",
        (topic_id, drempel),
    ).fetchone()

    # Argumenten die de LLM als 'ander onderwerp' bestempelde vallen buiten de
    # export (ze horen niet bij dit topic), maar de telling en de onderwerpen
    # zelf blijven zichtbaar -- anders is niet te zien wat het ruime
    # ingest-criterium binnenhaalt.
    ander_onderwerp_rows = conn.execute(
        """SELECT ar.ander_onderwerp AS onderwerp, COUNT(*) AS aantal FROM arguments ar
           JOIN documents d ON d.id = ar.document_id
           WHERE ar.topic_id = ? AND d.published_at >= ? AND ar.stance = 'ander_onderwerp'
           GROUP BY ar.ander_onderwerp ORDER BY aantal DESC""",
        (topic_id, drempel),
    ).fetchall()

    documents_with_redactie = conn.execute(
        """SELECT COUNT(DISTINCT rr.document_id)
           FROM redactie_reviews rr JOIN documents d ON d.id = rr.document_id
           WHERE d.topic_id = ? AND d.published_at >= ?""",
        (topic_id, drempel),
    ).fetchone()[0]

    return {
        "slug": topic_row["slug"],
        "name": topic_row["name"],
        "vanaf": drempel,
        "documents_total": documents_total,
        "documents_extracted": extraction_attempted,
        "arguments_total": arguments_total,
        "arguments_tagged": arguments_tagged,
        "documents_redactie_checked": documents_with_redactie,
        "arguments_ander_onderwerp": sum(row["aantal"] for row in ander_onderwerp_rows),
        "ander_onderwerp_top": [
            {"onderwerp": row["onderwerp"], "aantal": row["aantal"]} for row in ander_onderwerp_rows[:10]
        ],
    }


def fetch_llm_call_stats(conn, topic_id):
    """Geaggregeerde aantal/tijd-cijfers per (stage, model) uit `llm_calls`,
    voor de publieke /status-pagina -- puur telwerk, zelfde stijl als
    fetch_pipeline_status hierboven. Dekt de hele geschiedenis (geen
    datumdrempel): dit gaat over pipeline-doorlooptijd, niet over welke
    argumenten getoond worden."""
    rows = conn.execute(
        """SELECT stage, model,
                  COUNT(*) AS n_calls,
                  SUM(duration_s) AS total_duration_s,
                  AVG(duration_s) AS avg_duration_s,
                  SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) AS n_errors,
                  SUM(COALESCE(completion_tokens, 0)) AS total_completion_tokens,
                  MIN(started_at) AS first_call_at,
                  MAX(started_at) AS last_call_at
           FROM llm_calls
           WHERE topic_id = ?
           GROUP BY stage, model
           ORDER BY stage, model""",
        (topic_id,),
    ).fetchall()
    return [dict(row) for row in rows]


_STAGE_CURRENT_PROMPT_VERSION = {
    "extraction": EXTRACT_PROMPT_VERSION,
    "tagging": TAG_PROMPT_VERSION,
    "redactie": REDACTIE_PROMPT_VERSION,
}


def _reconstruct_prompt(conn, call, topic_name, topic_description):
    """Bouwt de prompt-tekst van één llm_calls-rij terug op, met de
    _build_prompt-functie van de bijbehorende stage-module en de nu nog
    bestaande document/argument-data (zie schema.sql: prompt-tekst zelf
    wordt niet opgeslagen). Retourneert None als het brondocument/-argument
    inmiddels weg is."""
    if call["stage"] == "extraction":
        doc = conn.execute(
            """SELECT d.content, a.name AS actor_name, a.party AS actor_party
               FROM documents d JOIN actors a ON a.id = d.actor_id
               WHERE d.id = ?""",
            (call["document_id"],),
        ).fetchone()
        if doc is None:
            return None
        return _build_extraction_prompt(
            topic_name, topic_description, doc["actor_name"], doc["actor_party"], doc["content"]
        )

    if call["stage"] == "tagging":
        arg = conn.execute(
            """SELECT ar.stance, ar.typology, ar.quote_text, ar.quote_context,
                      a.name AS actor_name, a.party AS actor_party
               FROM arguments ar JOIN actors a ON a.id = ar.actor_id
               WHERE ar.id = ?""",
            (call["argument_id"],),
        ).fetchone()
        if arg is None:
            return None
        tag_catalogue, tag_json_skeleton = build_tag_catalogue(conn)
        return _build_tagging_prompt(
            topic_name, arg["actor_name"], arg["actor_party"], arg["stance"], arg["typology"],
            arg["quote_text"], arg["quote_context"], tag_catalogue, tag_json_skeleton,
        )

    if call["stage"] == "redactie":
        doc = conn.execute(
            """SELECT a.name AS actor_name, a.party AS actor_party
               FROM documents d JOIN actors a ON a.id = d.actor_id
               WHERE d.id = ?""",
            (call["document_id"],),
        ).fetchone()
        if doc is None:
            return None
        new_args = conn.execute(
            """SELECT id, stance, quote_text FROM arguments
               WHERE document_id = ? AND stance IN ('pro', 'contra') ORDER BY id""",
            (call["document_id"],),
        ).fetchall()
        candidate_ids = json.loads(call["prompt_vars"])["candidate_argument_ids"] if call["prompt_vars"] else []
        candidates = []
        if candidate_ids:
            placeholders = ",".join("?" * len(candidate_ids))
            candidates = conn.execute(
                f"""SELECT ar.id, ar.quote_text, a.name AS actor_name, a.party AS actor_party
                    FROM arguments ar JOIN actors a ON a.id = ar.actor_id
                    WHERE ar.id IN ({placeholders})""",
                candidate_ids,
            ).fetchall()
        actor_party_suffix = f" ({doc['actor_party']})" if doc["actor_party"] else ""
        return REDACTIE_PROMPT_TEMPLATE.format(
            topic=topic_name,
            actor_name=doc["actor_name"],
            actor_party_suffix=actor_party_suffix,
            new_arguments_block=_format_arguments_block(new_args),
            candidates_block=_format_arguments_block(candidates),
        )

    return None


def fetch_recent_llm_calls(conn, topic_row, limit=300):
    """Meest recente `limit` LLM-calls van dit topic, mét gereconstrueerde
    prompt-tekst -- voor de publieke "prompts teruglezen"-pagina. Bewust
    begrensd (niet de hele `llm_calls`-tabel, die kan tienduizenden rijen
    hebben): reconstructie kost per rij een paar extra queries, en de export
    wordt in git gecommit (zie module-docstring)."""
    topic_id, topic_name, topic_description = topic_row["id"], topic_row["name"], topic_row["description"]
    rows = conn.execute(
        """SELECT id, stage, document_id, argument_id, model, prompt_version, prompt_vars,
                  response, status, error_message, started_at, duration_s,
                  prompt_tokens, completion_tokens, reasoning_tokens
           FROM llm_calls
           WHERE topic_id = ?
           ORDER BY id DESC
           LIMIT ?""",
        (topic_id, limit),
    ).fetchall()

    calls = []
    for row in rows:
        call = dict(row)
        try:
            call["prompt"] = _reconstruct_prompt(conn, call, topic_name, topic_description)
        except Exception:
            logger.warning("llm_calls id=%s: kon prompt niet reconstrueren", call["id"])
            call["prompt"] = None
        call["prompt_outdated"] = call["prompt_version"] != _STAGE_CURRENT_PROMPT_VERSION.get(call["stage"])
        del call["prompt_vars"]
        calls.append(call)
    return calls


def fetch_sprekerbeurten(conn, topic_id, periode_index):
    """Platte lijst van alle kwalificerende sprekerbeurten voor dit topic,
    INCLUSIEF beurten zonder geëxtraheerde arguments (issue #155) -- nodig
    als volledige noemer voor tekstvolume-gebaseerde ratio's (bv. argumenten
    per 1000 tekens), want `arguments` bevat alleen beurten die minstens één
    argument opleverden. Zelfde documentfilter als
    scripts/experiment_verbositeit.py's fetch_documenten(). Bewust geen
    content zelf -- alleen de kleine text_stats-JSON, uitgepakt naar platte
    velden zodat de frontend niet zelf JSON-in-JSON hoeft te parsen."""
    rows = conn.execute(
        """SELECT d.id, length(d.content) AS char_count, d.text_stats,
                  ac.name AS actor_name, ac.party AS actor_party
           FROM documents d
           JOIN actors ac ON ac.id = d.actor_id
           WHERE d.topic_id = ?
             AND d.is_voorzitter_turn = 0
             AND d.actor_id IS NOT NULL
             AND d.content IS NOT NULL AND length(d.content) > 0
             AND d.published_at >= ?
             AND d.text_stats IS NOT NULL""",
        (topic_id, periode_index.drempel),
    ).fetchall()
    result = []
    for row in rows:
        stats = json.loads(row["text_stats"])
        result.append(
            {
                "id": row["id"],
                "actor": {"name": row["actor_name"], "party": row["actor_party"]},
                "char_count": row["char_count"],
                **stats,
            }
        )
    return result


def build_topic_export(conn, topic_row, periode_index):
    """Eén platte argumentenlijst, geen voorgeaggregeerde cijfers. De frontend
    leidt statistieken, tags-per-partij en de stance-kolommen zelf af uit deze
    lijst, zodat een gefilterde weergave niet uit de pas kan lopen met de
    grafieken ernaast (dat was precies de bug: kolommen filterden wel, de
    voorberekende `stats`/`tags_per_party` niet). De correspondentieanalyse
    blijft server-side -- die heeft een SVD nodig; client-side herberekenen
    staat in #3."""
    arguments = fetch_arguments(conn, topic_row["id"], periode_index)
    tag_rows = fetch_party_tag_counts(conn, topic_row["id"], periode_index.drempel)
    return {
        "slug": topic_row["slug"],
        "name": topic_row["name"],
        "description": topic_row["description"],
        "arguments": arguments,
        "argument_count": len(arguments),
        "sprekerbeurten": fetch_sprekerbeurten(conn, topic_row["id"], periode_index),
        "tag_correspondence": build_correspondence_analysis(tag_rows),
        "image_url": _topic_image_url(arguments),
    }


def main():
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()

    conn = db.connect()
    periode_index = PeriodeIndex()
    all_topic_rows = conn.execute("SELECT id, slug, name, description FROM topics").fetchall()

    topics_dir = EXPORT_DIR / "topics"
    topics_dir.mkdir(parents=True, exist_ok=True)
    llm_calls_dir = EXPORT_DIR / "llm_calls"
    llm_calls_dir.mkdir(parents=True, exist_ok=True)

    index = []
    status = {"generated_at": datetime.now(_AMSTERDAM).isoformat(timespec="seconds"), "topics": []}
    for topic_row in all_topic_rows:
        export = build_topic_export(conn, topic_row, periode_index)
        out_path = topics_dir / f"{topic_row['slug']}.json"
        out_path.write_text(json.dumps(export, ensure_ascii=False, indent=2))
        stances = Counter(a["stance"] for a in export["arguments"])
        logger.info(
            "%s: %d argumenten (pro=%d, contra=%d, unclear=%d) -> %s",
            topic_row["slug"], export["argument_count"],
            stances["pro"], stances["contra"], stances["unclear"], out_path,
        )
        topic_status = fetch_pipeline_status(conn, topic_row, periode_index.drempel)
        topic_status["llm_calls_by_model"] = fetch_llm_call_stats(conn, topic_row["id"])
        status["topics"].append(topic_status)

        llm_calls_export = {
            "generated_at": status["generated_at"],
            "topic": topic_row["slug"],
            "calls": fetch_recent_llm_calls(conn, topic_row),
        }
        llm_calls_path = llm_calls_dir / f"{topic_row['slug']}.json"
        llm_calls_path.write_text(json.dumps(llm_calls_export, ensure_ascii=False, indent=2))
        logger.info("%s: %d llm_calls (recent) -> %s", topic_row["slug"], len(llm_calls_export["calls"]), llm_calls_path)

        index.append(
            {
                "slug": topic_row["slug"],
                "name": topic_row["name"],
                "description": topic_row["description"],
                "argument_count": export["argument_count"],
                "image_url": export["image_url"],
            }
        )

    index_path = EXPORT_DIR / "topics-index.json"
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2))
    logger.info("Index -> %s", index_path)

    status_path = EXPORT_DIR / "status.json"
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2))
    logger.info("Status -> %s", status_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
