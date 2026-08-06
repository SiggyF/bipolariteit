"""
Migratie: voeg de `llm_calls`-tabel toe aan een bestaande lokale database.

Puur additief (CREATE TABLE IF NOT EXISTS + indexen), dus geen tabel-herbouw
nodig zoals bij migrate_stance_ander_onderwerp.py. `make db-init` kan dit niet
zelf: die draait schema.sql via executescript(), en dat breekt op een
bestaande database bij de allereerste CREATE TABLE (zonder IF NOT EXISTS).
Dit script voert alleen het nieuwe blok uit pipeline/db/schema.sql uit.

Gebruik:
    PYTHONPATH=. uv run python scripts/migrate_add_llm_calls.py
"""

import logging

from pipeline.db import db

logger = logging.getLogger(__name__)

LLM_CALLS_TABLE = """
CREATE TABLE IF NOT EXISTS llm_calls (
    id INTEGER PRIMARY KEY,
    stage TEXT NOT NULL CHECK (stage IN ('extraction', 'tagging', 'redactie')),
    topic_id INTEGER NOT NULL REFERENCES topics(id),
    document_id INTEGER REFERENCES documents(id),
    argument_id INTEGER REFERENCES arguments(id),
    model TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    prompt_vars TEXT,
    response TEXT,
    status TEXT NOT NULL CHECK (status IN ('ok', 'error')),
    error_message TEXT,
    started_at TEXT NOT NULL,
    duration_s REAL NOT NULL,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    reasoning_tokens INTEGER
)
"""

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_llm_calls_topic_model ON llm_calls(topic_id, model)",
    "CREATE INDEX IF NOT EXISTS idx_llm_calls_stage ON llm_calls(stage)",
]


def main():
    conn = db.connect()
    conn.execute(LLM_CALLS_TABLE)
    for statement in INDEXES:
        conn.execute(statement)
    conn.commit()
    n = conn.execute("SELECT COUNT(*) AS n FROM llm_calls").fetchone()["n"]
    logger.info("llm_calls-tabel aanwezig, %d rij(en).", n)
    conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
