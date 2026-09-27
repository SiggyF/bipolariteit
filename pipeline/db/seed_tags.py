"""
Laadt de argument-taxonomie uit config/tags.toml in de labelgroepen- en
tags-tabellen. Idempotent en veilig om te herhalen na een edit door de
onderzoeker aan tags.toml: elke run zet eerst alles inactief en activeert
vervolgens alles wat nog in het bestand staat (zie schema.sql-commentaar bij
`labelgroepen`/`tags`). Nooit clear+reinsert -- argument_tags houdt levende
foreign keys naar tags vast.

Gebruik:
    uv run python -m pipeline.db.seed_tags
    uv run python -m pipeline.db.seed_tags --dry-run
"""

import argparse
import tomllib
from pathlib import Path

from pipeline.db import db
from pipeline.taxonomy import selectie_for

TAGS_TOML_PATH = Path(__file__).parent.parent.parent / "config" / "tags.toml"


def load_taxonomy(path: Path = TAGS_TOML_PATH) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


def seed_tags(conn, taxonomy: dict, dry_run: bool = False) -> tuple[int, int]:
    n_labelgroepen = 0
    n_tags = 0
    seen_sleutels = set()

    if not dry_run:
        conn.execute("UPDATE labelgroepen SET active = 0")
        conn.execute("UPDATE tags SET active = 0")

    for perspectief in taxonomy["perspectieven"]:
        for labelgroep in perspectief["labelgroepen"]:
            naam = labelgroep["naam"]
            selectie = selectie_for(naam)
            if not dry_run:
                conn.execute(
                    """INSERT INTO labelgroepen (naam, perspectief, beschrijving, selectie, active)
                       VALUES (?, ?, ?, ?, 1)
                       ON CONFLICT(naam) DO UPDATE SET
                         perspectief = excluded.perspectief,
                         beschrijving = excluded.beschrijving,
                         selectie = excluded.selectie,
                         active = 1""",
                    (naam, perspectief["naam"], labelgroep["beschrijving"], selectie),
                )
            n_labelgroepen += 1

            for tag in labelgroep["tags"]:
                sleutel = tag["sleutel"]
                if sleutel in seen_sleutels:
                    raise ValueError(f"dubbele sleutel in tags.toml: {sleutel!r}")
                seen_sleutels.add(sleutel)
                if not dry_run:
                    conn.execute(
                        """INSERT INTO tags (sleutel, labelgroep, beschrijving, active)
                           VALUES (?, ?, ?, 1)
                           ON CONFLICT(sleutel) DO UPDATE SET
                             labelgroep = excluded.labelgroep,
                             beschrijving = excluded.beschrijving,
                             active = 1""",
                        (sleutel, naam, tag["beschrijving"]),
                    )
                n_tags += 1

    if not dry_run:
        conn.commit()
    return n_labelgroepen, n_tags


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = db.connect()
    taxonomy = load_taxonomy()
    n_lg, n_tags = seed_tags(conn, taxonomy, dry_run=args.dry_run)

    if not args.dry_run:
        n_inactive_lg = conn.execute("SELECT COUNT(*) FROM labelgroepen WHERE active = 0").fetchone()[0]
        n_inactive_tags = conn.execute("SELECT COUNT(*) FROM tags WHERE active = 0").fetchone()[0]
        if n_inactive_lg or n_inactive_tags:
            print(
                f"Let op: {n_inactive_lg} labelgroep(en) en {n_inactive_tags} tag(s) "
                "zijn nu inactief (niet meer in tags.toml aanwezig)."
            )

    verb = "Zou seeden" if args.dry_run else "Geseed"
    print(f"{verb}: {n_lg} labelgroepen, {n_tags} tags.")
    conn.close()


if __name__ == "__main__":
    main()
