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

Exporteert alleen de huidige en vorige kamerperiode (zie
periodes.verwerkingsdrempel); oudere argumenten blijven in de database maar
komen niet in de JSON en dus niet op de site.

Gebruik:
    uv run python -m pipeline.build_static_data
    uv run python -m pipeline.build_static_data --topic stikstof
"""

import argparse
import json
import logging
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

import pandas as pd
import prince

from pipeline.db import db
from pipeline.periodes import PeriodeIndex

logger = logging.getLogger(__name__)

EXPORT_DIR = Path(__file__).parent.parent / "data" / "export"
_AMSTERDAM = ZoneInfo("Europe/Amsterdam")


def _speaker_event_url(video_url, published_at):
    """Debat Direct ondersteunt een deep link naar het moment dat een
    specifieke spreker begint (?event=speaker<ISO8601-tijdstip+offset>),
    naast de generieke .../video-link naar het begin van het hele debat.
    documents.published_at (VLOS markeertijdbegin) is naive lokale tijd
    zonder offset -- Europe/Amsterdam-lokalisatie geeft automatisch de
    juiste +01:00/+02:00 DST-offset i.p.v. een hardgecodeerde regel."""
    if not video_url or not published_at:
        return None
    base = video_url[: -len("/video")] if video_url.endswith("/video") else video_url
    dt = datetime.fromisoformat(published_at).replace(tzinfo=_AMSTERDAM)
    event = quote(dt.strftime("%Y-%m-%dT%H:%M:%S%z"), safe="")
    return f"{base}?event=speaker{event}"


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
                  ar.prompt_version, ac.name AS actor_name, ac.party AS actor_party,
                  d.id AS document_id, d.url AS document_url, d.video_url, d.published_at,
                  d.tweedekamer_activiteit_url, d.speaker_role_title
           FROM arguments ar
           JOIN actors ac ON ac.id = ar.actor_id
           JOIN documents d ON d.id = ar.document_id
           WHERE ar.topic_id = ?
             AND d.published_at >= ?
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
                "actor": {
                    "name": row["actor_name"],
                    "party": row["actor_party"],
                    "role_title": row["speaker_role_title"],
                },
                "document": {
                    "url": row["document_url"],
                    "video_url": row["video_url"],
                    # Naive lokale tijd (VLOS markeertijdbegin), zonder offset --
                    # de frontend gebruikt alleen het datumdeel, voor het datumfilter.
                    "published_at": row["published_at"],
                    "speaker_video_url": _speaker_event_url(row["video_url"], row["published_at"]),
                    "tweedekamer_activiteit_url": row["tweedekamer_activiteit_url"],
                    "redactie_review": redactie_by_document.get(row["document_id"]),
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
    }


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
        "tag_correspondence": build_correspondence_analysis(tag_rows),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", default=None, help="alleen deze topic-slug exporteren (default: alle topics)")
    args = parser.parse_args()

    conn = db.connect()
    periode_index = PeriodeIndex()
    if args.topic:
        topic_rows = conn.execute("SELECT id, slug, name, description FROM topics WHERE slug = ?", (args.topic,)).fetchall()
        if not topic_rows:
            raise SystemExit(f"onbekende topic-slug: {args.topic}")
    else:
        topic_rows = conn.execute("SELECT id, slug, name, description FROM topics").fetchall()

    topics_dir = EXPORT_DIR / "topics"
    topics_dir.mkdir(parents=True, exist_ok=True)

    index = []
    status = {"generated_at": datetime.now(_AMSTERDAM).isoformat(timespec="seconds"), "topics": []}
    for topic_row in topic_rows:
        export = build_topic_export(conn, topic_row, periode_index)
        status["topics"].append(fetch_pipeline_status(conn, topic_row, periode_index.drempel))
        out_path = topics_dir / f"{topic_row['slug']}.json"
        out_path.write_text(json.dumps(export, ensure_ascii=False, indent=2))
        index.append(
            {
                "slug": topic_row["slug"],
                "name": topic_row["name"],
                "description": topic_row["description"],
                "argument_count": export["argument_count"],
            }
        )
        stances = Counter(a["stance"] for a in export["arguments"])
        logger.info(
            "%s: %d argumenten (pro=%d, contra=%d, unclear=%d) -> %s",
            topic_row["slug"], export["argument_count"],
            stances["pro"], stances["contra"], stances["unclear"], out_path,
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
