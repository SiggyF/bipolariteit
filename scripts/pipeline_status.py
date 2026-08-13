"""
Doorlopend overzicht van openstaand pipeline-werk per topic: dit vervangt het
handmatig bijhouden van "wat is de volgende stap" in docs/handoff.md met een
herhaalbare query. Bedoeld om vóór elke sessie te draaien.

Voor elk topic, vier categorieën:
- extractie: documenten nog niet verwerkt, of verwerkt met een verouderde
  extract_argument.md-promptversie (PROMPT_VERSION in pipeline/extract_arguments.py)
- tagging: arguments nog niet getagd, of getagd met een verouderde
  tag_argument.md-promptversie
- redactie: documenten met arguments maar nog geen redactie_reviews-rij, of
  gereviewd met een verouderde redactie_bias_check.md-promptversie
- (topic zelf: ontbrekende description blokkeert extractie hard, zie
  extract_arguments.py -- hier gewoon gemeld, niet hard gefaald)

Een "verouderde promptversie" betekent: het bestaande record heeft een
prompt_version die niet gelijk is aan de huidige hash van het promptbestand
op disk. Dit maakt promptwijzigingen automatisch zichtbaar als heropend werk,
zonder dat iemand een los logboek moet bijwerken.

Gebruik:
    uv run python scripts/pipeline_status.py
    uv run python scripts/pipeline_status.py --topic stikstof
"""

import argparse
import logging

from pipeline.db import db
from pipeline.extract_arguments import (
    EXCLUDED_ACTIVITEIT_SOORTEN,
    PROMPT_VERSION as EXTRACT_PROMPT_VERSION,
    TOPIC_TITLE_KEYWORDS,
)
from pipeline.periodes import PeriodeIndex
from pipeline.redactie_check import PROMPT_VERSION as REDACTIE_PROMPT_VERSION
from pipeline.tag_arguments import PROMPT_VERSION as TAG_PROMPT_VERSION

logger = logging.getLogger(__name__)


def _count(conn, query, params=()):
    return conn.execute(query, params).fetchone()[0]


def _count_pending_extraction(conn, topic_id, topic_slug, vanaf):
    """Zelfde filters als fetch_pending_documents in extract_arguments.py,
    anders telt dit mee wat make extract nooit oppakt (documenten van vóór
    de kamerperiode-drempel, procedurele activiteitsoorten, titelfilter)."""
    conditions = [
        "topic_id = ?",
        "extraction_attempted_at IS NULL",
        "is_voorzitter_turn = 0",
        "published_at >= ?",
        f"activiteit_soort NOT IN ({','.join('?' * len(EXCLUDED_ACTIVITEIT_SOORTEN))})",
    ]
    params = [topic_id, vanaf, *EXCLUDED_ACTIVITEIT_SOORTEN]

    title_keywords = TOPIC_TITLE_KEYWORDS.get(topic_slug, [])
    if title_keywords:
        conditions.append("(" + " OR ".join("LOWER(title) LIKE ?" for _ in title_keywords) + ")")
        params.extend(f"%{keyword.lower()}%" for keyword in title_keywords)

    return _count(conn, f"SELECT COUNT(*) FROM documents WHERE {' AND '.join(conditions)}", params)


def topic_status(conn, topic_id, topic_slug, vanaf):
    total_documents = _count(conn, "SELECT COUNT(*) FROM documents WHERE topic_id = ?", (topic_id,))
    voorzitter_turns = _count(
        conn, "SELECT COUNT(*) FROM documents WHERE topic_id = ? AND is_voorzitter_turn = 1", (topic_id,)
    )
    pending_extraction = _count_pending_extraction(conn, topic_id, topic_slug, vanaf)
    outdated_extraction = _count(
        conn,
        """SELECT COUNT(*) FROM documents
           WHERE topic_id = ? AND extraction_attempted_at IS NOT NULL
             AND (extraction_prompt_version IS NULL OR extraction_prompt_version != ?)""",
        (topic_id, EXTRACT_PROMPT_VERSION),
    )

    total_arguments = _count(conn, "SELECT COUNT(*) FROM arguments WHERE topic_id = ?", (topic_id,))
    pending_tagging = _count(
        conn, "SELECT COUNT(*) FROM arguments WHERE topic_id = ? AND tagged_at IS NULL", (topic_id,)
    )
    outdated_tagging = _count(
        conn,
        """SELECT COUNT(*) FROM arguments
           WHERE topic_id = ? AND tagged_at IS NOT NULL
             AND (tag_prompt_version IS NULL OR tag_prompt_version != ?)""",
        (topic_id, TAG_PROMPT_VERSION),
    )

    pending_redactie = _count(
        conn,
        """SELECT COUNT(DISTINCT d.id) FROM documents d
           JOIN arguments ar ON ar.document_id = d.id
           LEFT JOIN redactie_reviews rr ON rr.document_id = d.id
           WHERE d.topic_id = ? AND rr.id IS NULL""",
        (topic_id,),
    )
    outdated_redactie = _count(
        conn,
        """SELECT COUNT(*) FROM redactie_reviews rr
           JOIN documents d ON d.id = rr.document_id
           WHERE d.topic_id = ? AND (rr.prompt_version IS NULL OR rr.prompt_version != ?)""",
        (topic_id, REDACTIE_PROMPT_VERSION),
    )

    # video_url-enrichment (pipeline/enrich_video_url.py) draait mee in
    # `make export`, maar wordt hier ook los geteld: anders valt een topic
    # waarvoor de enrichment nog nooit draaide (bv. net toegevoegd) pas op
    # als iemand toevallig de export-output leest (zie issue #83).
    pending_video = _count(
        conn,
        """SELECT COUNT(*) FROM documents
           WHERE topic_id = ? AND video_url IS NULL AND activiteit_aanvangstijd IS NOT NULL""",
        (topic_id,),
    )

    return {
        "documents": total_documents,
        "voorzitter_turns": voorzitter_turns,
        "pending_extraction": pending_extraction,
        "outdated_extraction": outdated_extraction,
        "arguments": total_arguments,
        "pending_tagging": pending_tagging,
        "outdated_tagging": outdated_tagging,
        "pending_redactie": pending_redactie,
        "outdated_redactie": outdated_redactie,
        "pending_video": pending_video,
    }


def fetch_topics(conn, topic_slug=None):
    if topic_slug:
        rows = conn.execute("SELECT id, slug, name, description FROM topics WHERE slug = ?", (topic_slug,)).fetchall()
        if not rows:
            raise SystemExit(f"onbekende topic-slug: {topic_slug}")
        return rows
    return conn.execute("SELECT id, slug, name, description FROM topics ORDER BY slug").fetchall()


def print_report(conn, topics):
    vanaf = PeriodeIndex().drempel
    logger.info(
        "Huidige promptversies: extract=%s tag=%s redactie=%s",
        EXTRACT_PROMPT_VERSION, TAG_PROMPT_VERSION, REDACTIE_PROMPT_VERSION,
    )
    logger.info("Verwerkingsdrempel (publicatiedatum): vanaf %s", vanaf)
    for topic in topics:
        status = topic_status(conn, topic["id"], topic["slug"], vanaf)
        missing_description = " ⚠️ GEEN description (extractie faalt hard)" if not topic["description"] else ""
        logger.info("")
        logger.info("=== %s (%s)%s ===", topic["name"], topic["slug"], missing_description)
        logger.info(
            "  documenten: %d totaal | %d nog niet geëxtraheerd | %d met verouderde extractie-prompt | %d voorzitter-beurten (overgeslagen)",
            status["documents"], status["pending_extraction"], status["outdated_extraction"], status["voorzitter_turns"],
        )
        logger.info(
            "  arguments:  %d totaal | %d nog niet getagd | %d met verouderde tag-prompt",
            status["arguments"], status["pending_tagging"], status["outdated_tagging"],
        )
        logger.info(
            "  redactie:   %d documenten nog niet gecontroleerd | %d reviews met verouderde prompt",
            status["pending_redactie"], status["outdated_redactie"],
        )
        logger.info(
            "  video_url:  %d documenten nog zonder video_url (make enrich-video TOPIC=%s)",
            status["pending_video"], topic["slug"],
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", help="alleen dit topic-slug tonen (default: alle topics)")
    args = parser.parse_args()

    conn = db.connect()
    topics = fetch_topics(conn, args.topic)
    print_report(conn, topics)
    conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
