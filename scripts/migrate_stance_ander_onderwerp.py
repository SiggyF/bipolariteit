"""
Migratie: stance-waarde 'ander_onderwerp' toestaan en de bijbehorende
kolom toevoegen.

SQLite kan een CHECK-constraint niet met ALTER TABLE wijzigen, dus de tabel
wordt herbouwd volgens de aanbevolen volgorde (nieuwe tabel, kopiëren,
oude droppen, hernoemen). Alleen de constraint en de nieuwe kolom veranderen;
alle bestaande rijen en waarden blijven ongewijzigd.

Draai `make backup-db` voordat je dit uitvoert.

Gebruik:
    PYTHONPATH=. uv run python scripts/migrate_stance_ander_onderwerp.py [--dry-run]
"""

import argparse
import logging

from pipeline.db import db

logger = logging.getLogger(__name__)

NIEUWE_TABEL = """
CREATE TABLE arguments_migratie (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id),
    topic_id INTEGER NOT NULL REFERENCES topics(id),
    actor_id INTEGER NOT NULL REFERENCES actors(id),
    stance TEXT NOT NULL CHECK (stance IN ('pro', 'contra', 'unclear', 'ander_onderwerp')),
    typology TEXT NOT NULL CHECK (typology IN ('factual', 'moral', 'economic', 'legal', 'other')),
    quote_text TEXT NOT NULL,
    quote_context TEXT,
    extracted_at TEXT NOT NULL,
    cluster_id INTEGER,
    redactie_status TEXT CHECK (redactie_status IN ('balanced', 'imbalanced', 'flag')),
    tagged_at TEXT,
    prompt_version TEXT,
    extraction_model TEXT,
    tag_prompt_version TEXT,
    tag_model TEXT,
    ander_onderwerp TEXT
)
"""

KOLOMMEN = """id, document_id, topic_id, actor_id, stance, typology, quote_text, quote_context,
    extracted_at, cluster_id, redactie_status, tagged_at, prompt_version, extraction_model,
    tag_prompt_version, tag_model"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="alleen tellen, niets wijzigen")
    args = parser.parse_args()

    conn = db.connect()
    kolommen = {row["name"] for row in conn.execute("PRAGMA table_info(arguments)")}
    if "ander_onderwerp" in kolommen:
        logger.info("Migratie al uitgevoerd (kolom ander_onderwerp bestaat).")
        return

    voor = conn.execute("SELECT count(*) AS n FROM arguments").fetchone()["n"]
    logger.info("%d argumenten in de huidige tabel", voor)
    if args.dry_run:
        return

    # Foreign keys uit tijdens de herbouw: claims/argument_tags/argument_oppositions
    # verwijzen naar arguments(id), en die id's blijven identiek -- maar SQLite zou
    # tijdens DROP TABLE anders alsnog cascaderen of blokkeren.
    conn.execute("PRAGMA foreign_keys = OFF")
    with conn:
        conn.execute(NIEUWE_TABEL)
        conn.execute(f"INSERT INTO arguments_migratie ({KOLOMMEN}) SELECT {KOLOMMEN} FROM arguments")
        conn.execute("DROP TABLE arguments")
        conn.execute("ALTER TABLE arguments_migratie RENAME TO arguments")
        conn.execute("CREATE INDEX idx_arguments_topic_stance ON arguments(topic_id, stance)")
        conn.execute("CREATE INDEX idx_arguments_document ON arguments(document_id)")
    conn.execute("PRAGMA foreign_keys = ON")

    na = conn.execute("SELECT count(*) AS n FROM arguments").fetchone()["n"]
    schendingen = conn.execute("PRAGMA foreign_key_check").fetchall()
    logger.info("%d argumenten na migratie, %d foreign-key-schendingen", na, len(schendingen))
    if voor != na or schendingen:
        raise SystemExit("migratie niet consistent -- herstel de back-up uit ~/data/bipolariteit/")
    conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
