"""Tests voor de validatie van door de LLM teruggegeven argumenten."""

import sqlite3
from pathlib import Path

import pytest

from pipeline.extract_arguments import _validate_argument, fetch_pending_documents

SCHEMA_PATH = Path(__file__).parent.parent / "pipeline" / "db" / "schema.sql"

GELDIG = {
    "stance": "pro",
    "typology": "factual",
    "quote_text": "Er zijn te weinig opvangplekken, dus de keten loopt vast.",
}


def test_valid_argument_passes():
    _validate_argument(dict(GELDIG))


def test_unknown_stance_is_rejected():
    with pytest.raises(ValueError, match="ongeldige stance"):
        _validate_argument({**GELDIG, "stance": "voor"})


def test_ander_onderwerp_requires_the_subject_it_is_actually_about():
    # Zonder onderwerp is dit label net zo weinig zeggend als 'unclear' -- de hele
    # reden ervoor is zichtbaar maken wát het ruime ingest-criterium binnenhaalt.
    with pytest.raises(ValueError, match="ander_onderwerp"):
        _validate_argument({**GELDIG, "stance": "ander_onderwerp"})

    _validate_argument({**GELDIG, "stance": "ander_onderwerp", "ander_onderwerp": "arbeidsmigratie"})


def _fresh_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text())
    return conn


def _seed_pending_document(conn, document_id, topic_id, topic_slug, published_at, title="Een debat"):
    """Minimale rij-keten (topic/source/actor/document) voor één nog niet
    geëxtraheerd document -- gebruikt door de multi-topic (topic_slug=None,
    issue #391) tests."""
    conn.execute(
        "INSERT OR IGNORE INTO topics (id, slug, name, description) VALUES (?, ?, ?, 'een narratief')",
        (topic_id, topic_slug, topic_slug.capitalize()),
    )
    conn.execute(
        "INSERT OR IGNORE INTO sources (id, type, name, retrieved_at) VALUES (1, 'tweede_kamer', 'TK', '2026-01-01T00:00:00Z')"
    )
    conn.execute(
        "INSERT OR IGNORE INTO actors (id, name, type, party) VALUES (1, 'Actor Een', 'person', 'Partij X')"
    )
    conn.execute(
        """INSERT INTO documents (id, source_id, topic_id, actor_id, title, content, published_at, activiteit_soort)
           VALUES (?, 1, ?, 1, ?, 'inhoud', ?, 'Plenair debat')""",
        (document_id, topic_id, title, published_at),
    )


def test_fetch_pending_documents_without_topic_merges_all_topics_newest_first():
    """issue #391: zonder topic_slug (None) moet de queue over alle topics
    heen lopen, met het meest recente documents.published_at eerst --
    ongeacht topic."""
    conn = _fresh_conn()
    _seed_pending_document(conn, document_id=1, topic_id=1, topic_slug="stikstof", published_at="2026-01-01T00:00:00Z")
    _seed_pending_document(conn, document_id=2, topic_id=2, topic_slug="abortus", published_at="2026-06-01T00:00:00Z")
    _seed_pending_document(conn, document_id=3, topic_id=1, topic_slug="stikstof", published_at="2026-03-01T00:00:00Z")

    rows = fetch_pending_documents(conn, None, limit=10, vanaf="2000-01-01")

    assert [row["id"] for row in rows] == [2, 3, 1]
    assert [row["topic_slug"] for row in rows] == ["abortus", "stikstof", "stikstof"]


def test_fetch_pending_documents_without_topic_respects_limit_across_topics():
    conn = _fresh_conn()
    _seed_pending_document(conn, document_id=1, topic_id=1, topic_slug="stikstof", published_at="2026-01-01T00:00:00Z")
    _seed_pending_document(conn, document_id=2, topic_id=2, topic_slug="abortus", published_at="2026-06-01T00:00:00Z")

    rows = fetch_pending_documents(conn, None, limit=1, vanaf="2000-01-01")

    assert [row["id"] for row in rows] == [2]


def test_fetch_pending_documents_without_topic_skips_topics_without_description():
    conn = _fresh_conn()
    _seed_pending_document(conn, document_id=1, topic_id=1, topic_slug="stikstof", published_at="2026-01-01T00:00:00Z")
    conn.execute("UPDATE topics SET description = NULL WHERE id = 1")
    _seed_pending_document(conn, document_id=2, topic_id=2, topic_slug="abortus", published_at="2026-06-01T00:00:00Z")

    rows = fetch_pending_documents(conn, None, limit=10, vanaf="2000-01-01")

    assert [row["id"] for row in rows] == [2]


def test_fetch_pending_documents_without_topic_applies_per_topic_title_keyword_filter():
    """TOPIC_TITLE_KEYWORDS blijft per topic gelden in de alle-topics-modus --
    asiel vereist een titel-keyword-match, stikstof (geen entry) niet."""
    conn = _fresh_conn()
    conn.execute(
        "INSERT INTO topics (id, slug, name, description) VALUES (1, 'stikstof', 'Stikstof', 'een narratief')"
    )
    conn.execute(
        "INSERT INTO topics (id, slug, name, description) VALUES (2, 'asiel', 'Asiel', 'een narratief')"
    )
    conn.execute(
        "INSERT INTO sources (id, type, name, retrieved_at) VALUES (1, 'tweede_kamer', 'TK', '2026-01-01T00:00:00Z')"
    )
    conn.execute(
        "INSERT INTO actors (id, name, type, party) VALUES (1, 'Actor Een', 'person', 'Partij X')"
    )
    conn.execute(
        """INSERT INTO documents (id, source_id, topic_id, actor_id, title, content, published_at, activiteit_soort)
           VALUES (1, 1, 1, 1, 'Mestbeleid', 'inhoud', '2026-01-01T00:00:00Z', 'Plenair debat')"""
    )
    conn.execute(
        """INSERT INTO documents (id, source_id, topic_id, actor_id, title, content, published_at, activiteit_soort)
           VALUES (2, 1, 2, 1, 'Asielopvang in de regio', 'inhoud', '2026-02-01T00:00:00Z', 'Plenair debat')"""
    )
    conn.execute(
        """INSERT INTO documents (id, source_id, topic_id, actor_id, title, content, published_at, activiteit_soort)
           VALUES (3, 1, 2, 1, 'Mestbeleid', 'inhoud', '2026-03-01T00:00:00Z', 'Plenair debat')"""
    )

    rows = fetch_pending_documents(conn, None, limit=10, vanaf="2000-01-01")

    assert [row["id"] for row in rows] == [2, 1]
