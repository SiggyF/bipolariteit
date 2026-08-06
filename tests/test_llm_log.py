"""Test dat record_llm_call een rij naar `llm_calls` schrijft, zowel bij een
geslaagde als een mislukte call, zonder de volledige prompt-tekst op te slaan
(zie pipeline/db/schema.sql)."""

import sqlite3
from pathlib import Path

from pipeline.llm_log import record_llm_call

SCHEMA_PATH = Path(__file__).parent.parent / "pipeline" / "db" / "schema.sql"


def _fresh_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text())
    conn.execute("INSERT INTO topics (id, slug, name) VALUES (1, 'stikstof', 'Stikstof')")
    conn.execute(
        "INSERT INTO sources (id, type, name, retrieved_at) VALUES (1, 'tweede_kamer', 'TK', '2026-01-01T00:00:00Z')"
    )
    conn.execute("INSERT INTO actors (id, name, type) VALUES (1, 'Test Kamerlid', 'person')")
    conn.execute(
        "INSERT INTO documents (id, source_id, topic_id, actor_id, content) VALUES (1, 1, 1, 1, 'inhoud')"
    )
    conn.execute(
        """INSERT INTO arguments (id, document_id, topic_id, actor_id, stance, typology, quote_text, extracted_at)
           VALUES (1, 1, 1, 1, 'pro', 'factual', 'quote', '2026-01-01T00:00:00Z')"""
    )
    return conn


def test_record_ok_call_stores_response_and_tokens():
    conn = _fresh_conn()
    record_llm_call(
        conn, stage="extraction", topic_id=1, document_id=1, model="test-model",
        prompt_version="abc123", started_at="2026-01-01T00:00:00Z", duration_s=1.5,
        response='{"arguments": []}', status="ok",
        usage={"prompt_tokens": 100, "completion_tokens": 20, "completion_tokens_details": {"reasoning_tokens": 5}},
    )
    row = conn.execute("SELECT * FROM llm_calls").fetchone()
    assert row["stage"] == "extraction"
    assert row["document_id"] == 1
    assert row["model"] == "test-model"
    assert row["status"] == "ok"
    assert row["response"] == '{"arguments": []}'
    assert row["prompt_tokens"] == 100
    assert row["completion_tokens"] == 20
    assert row["reasoning_tokens"] == 5
    assert row["prompt_vars"] is None


def test_record_error_call_stores_error_message():
    conn = _fresh_conn()
    record_llm_call(
        conn, stage="tagging", topic_id=1, argument_id=1, model="test-model",
        prompt_version="def456", started_at="2026-01-01T00:00:01Z", duration_s=0.2,
        status="error", error_message="timeout",
    )
    row = conn.execute("SELECT * FROM llm_calls").fetchone()
    assert row["stage"] == "tagging"
    assert row["argument_id"] == 1
    assert row["status"] == "error"
    assert row["error_message"] == "timeout"
    assert row["response"] is None


def test_prompt_vars_stored_as_json_for_redactie():
    conn = _fresh_conn()
    record_llm_call(
        conn, stage="redactie", topic_id=1, document_id=1, model="test-model",
        prompt_version="ghi789", started_at="2026-01-01T00:00:02Z", duration_s=3.0,
        prompt_vars={"candidate_argument_ids": [1, 2, 3]}, status="ok",
    )
    row = conn.execute("SELECT prompt_vars FROM llm_calls").fetchone()
    assert row["prompt_vars"] == '{"candidate_argument_ids": [1, 2, 3]}'
