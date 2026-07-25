"""
Test dat seed_tags.py de taxonomie correct en idempotent laadt, inclusief
het inactief maken van tags/labelgroepen die niet meer in tags.toml staan.
"""

import sqlite3
from pathlib import Path

from pipeline.db.seed_tags import load_taxonomy, seed_tags

SCHEMA_PATH = Path(__file__).parent.parent / "pipeline" / "db" / "schema.sql"


def _fresh_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text())
    return conn


def _count(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_seed_tags_loads_expected_counts():
    conn = _fresh_conn()
    taxonomy = load_taxonomy()
    expected_labelgroepen = sum(len(p["labelgroepen"]) for p in taxonomy["perspectieven"])
    expected_tags = sum(
        len(lg["tags"]) for p in taxonomy["perspectieven"] for lg in p["labelgroepen"]
    )

    n_lg, n_tags = seed_tags(conn, taxonomy)

    assert n_lg == expected_labelgroepen
    assert n_tags == expected_tags
    assert _count(conn, "labelgroepen") == expected_labelgroepen
    assert _count(conn, "tags") == expected_tags
    assert _count(conn, "tags WHERE active = 0") == 0


def test_seeding_twice_is_idempotent():
    conn = _fresh_conn()
    taxonomy = load_taxonomy()
    seed_tags(conn, taxonomy)
    n_tags_after_first = _count(conn, "tags")

    seed_tags(conn, taxonomy)
    n_tags_after_second = _count(conn, "tags")

    assert n_tags_after_first == n_tags_after_second
    assert _count(conn, "tags WHERE active = 0") == 0


def test_removed_tag_becomes_inactive_not_deleted():
    conn = _fresh_conn()
    taxonomy = load_taxonomy()
    seed_tags(conn, taxonomy)

    # simuleer een onderzoeker die één tag uit een labelgroep verwijdert
    trimmed = {
        "perspectieven": [
            {
                **p,
                "labelgroepen": [
                    {**lg, "tags": lg["tags"][:-1]} if lg["tags"] else lg
                    for lg in p["labelgroepen"]
                ],
            }
            for p in taxonomy["perspectieven"]
        ]
    }
    seed_tags(conn, trimmed)

    assert _count(conn, "tags") == _count(conn, "tags")  # rijen blijven bestaan
    assert _count(conn, "tags WHERE active = 0") >= 1  # maar minstens één is nu inactief


def test_dry_run_writes_nothing():
    conn = _fresh_conn()
    taxonomy = load_taxonomy()
    seed_tags(conn, taxonomy, dry_run=True)
    assert _count(conn, "labelgroepen") == 0
    assert _count(conn, "tags") == 0
