"""
Eenmalige migratie (issue #252): zet bestaande argument_oppositions-rijen om
naar het nieuwe aif_relations/aif_relation_premises-model (AIF-
kern, zie pipeline/schemas/argument_relations.schema.json).

argument_oppositions.argument_a_id was altijd het nieuw-geextraheerde
argument dat een bestaand argument (argument_b_id) weerlegt/raakt (zie
redactie_check.py::insert_oppositions) -- in het nieuwe model is
argument_b_id dus de target (het argument dat aangevallen wordt) en
argument_a_id de premise (het argument dat aanvalt). relation_type wordt
altijd 'conflict' (argument_oppositions kende nooit een support-relatie);
de oude relation_type-waarde ('direct_rebuttal'/'thematic') verhuist naar
het nieuwe scheme-veld. weak_link is voor gemigreerde rijen altijd 0 --
dat signaal bestond nog niet toen deze rijen gemaakt werden, dus 1 zetten
zou een positief signaal verzinnen dat nooit berekend is.

Idempotent: slaat een argument_oppositions-rij over als er al een
aif_relations-rij bestaat met dezelfde target/premise/scheme-combinatie.

Gebruik:
    uv run python scripts/migrate_argument_oppositions_to_relations.py [--dry-run]
"""

import argparse
import logging

from pipeline.db import db

logger = logging.getLogger(__name__)


def fetch_oppositions(conn):
    return conn.execute(
        "SELECT argument_a_id, argument_b_id, relation_type, created_by, confidence FROM argument_oppositions"
    ).fetchall()


def relation_already_migrated(conn, target_id, premise_id, scheme):
    row = conn.execute(
        """SELECT ar.id
           FROM aif_relations ar
           JOIN aif_relation_premises arp ON arp.relation_id = ar.id
           WHERE ar.target_argument_id = ? AND arp.argument_id = ?
             AND ar.relation_type = 'conflict'
             AND (ar.scheme IS ? OR ar.scheme = ?)""",
        (target_id, premise_id, scheme, scheme),
    ).fetchone()
    return row is not None


def migrate(conn, dry_run):
    oppositions = fetch_oppositions(conn)
    migrated, skipped = 0, 0
    for row in oppositions:
        target_id = row["argument_b_id"]
        premise_id = row["argument_a_id"]
        scheme = row["relation_type"]

        if relation_already_migrated(conn, target_id, premise_id, scheme):
            skipped += 1
            continue

        if dry_run:
            migrated += 1
            continue

        cur = conn.execute(
            """INSERT INTO aif_relations
                   (relation_type, target_argument_id, scheme, weak_link, created_by, confidence)
               VALUES ('conflict', ?, ?, 0, ?, ?)""",
            (target_id, scheme, row["created_by"], row["confidence"]),
        )
        conn.execute(
            "INSERT INTO aif_relation_premises (relation_id, argument_id) VALUES (?, ?)",
            (cur.lastrowid, premise_id),
        )
        migrated += 1

    if not dry_run:
        conn.commit()
    logger.info(
        "%s%d gemigreerd, %d al aanwezig (van %d argument_oppositions-rijen totaal).",
        "[dry-run] " if dry_run else "", migrated, skipped, len(oppositions),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="alleen tellen, niets wegschrijven")
    args = parser.parse_args()

    conn = db.connect()
    try:
        migrate(conn, args.dry_run)
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
