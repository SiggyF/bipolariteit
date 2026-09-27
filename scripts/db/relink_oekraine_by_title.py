"""Herstelt de topic-koppeling voor 'oekraine' op basis van de daadwerkelijke
debattitel, in plaats van het eerdere brede resultaat (678 documenten,
waarvan er 674 als titel "Vragenuur" hadden en inhoudelijk niets met
Oekraine/Rusland/NAVO te maken hadden -- zie sessie 2026-09-12).

Voert eerst altijd een telling uit (zoals bij --dry-run) zodat de omvang
zichtbaar is voordat er iets wordt weggeschreven; gebruik --apply om de
UPDATE's daadwerkelijk uit te voeren.

Wat dit doet:
1. Ontkoppelt documenten die nu topic_id=oekraine hebben maar geen titelmatch
   hebben EN geen "echt" argument (stance != ander_onderwerp) hebben opgeleverd.
   (22 documenten met titelmatch of een echt argument blijven dus gewoon
   gekoppeld, ook als hun titel zelf niet in TITLE_KEYWORDS voorkomt.)
2. Koppelt documenten met een titelmatch die nu topic_id IS NULL hebben, of
   abusievelijk bij een ander topic (asiel/energietransitie) hangen -- zulke
   overlap is een bekende beperking van de huidige single-value topic_id-kolom,
   zie issue #299. Bestaande getagde argumenten van dat andere topic blijven
   gewoon staan (arguments.topic_id is een denormalized snapshot, wordt niet
   met terugwerkende kracht aangepast).
3. Zet extraction_attempted_at terug op NULL voor documenten die van een
   ander topic naar oekraine verhuizen, zodat ze alsnog voor de oekraine-
   context worden geextraheerd (dat veld is topic-onafhankelijk, dus staat
   voor deze documenten al op een waarde van hun vorige topic).

Gebruik:
    uv run python scripts/db/relink_oekraine_by_title.py           # dry-run
    uv run python scripts/db/relink_oekraine_by_title.py --apply   # schrijft weg
"""

import argparse

from pipeline.db import db

TITLE_KEYWORDS = ["oekra", "navo", "rusland", "poetin"]
EXCLUDE_TITLE_KEYWORDS = ["irak", "iran", "isra"]


def build_title_match(alias: str = "d") -> tuple[str, list[str]]:
    include = " OR ".join(f"LOWER({alias}.title) LIKE ?" for _ in TITLE_KEYWORDS)
    exclude = " AND ".join(f"LOWER({alias}.title) NOT LIKE ?" for _ in EXCLUDE_TITLE_KEYWORDS)
    condition = f"({include}) AND {exclude}"
    params = [f"%{kw}%" for kw in TITLE_KEYWORDS] + [f"%{kw}%" for kw in EXCLUDE_TITLE_KEYWORDS]
    return condition, params


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="schrijf de wijzigingen weg (default: alleen tellen)")
    args = parser.parse_args()

    conn = db.connect()
    topic_row = conn.execute("SELECT id FROM topics WHERE slug = 'oekraine'").fetchone()
    if topic_row is None:
        raise SystemExit("topic 'oekraine' bestaat niet, eerst aanmaken met scripts/db/add_topic.py")
    topic_id = topic_row["id"]

    title_match, title_params = build_title_match("d")

    to_unlink = conn.execute(
        f"""SELECT COUNT(*) c FROM documents d
            WHERE d.topic_id = ? AND NOT ({title_match})
              AND NOT EXISTS (
                SELECT 1 FROM arguments ar WHERE ar.document_id = d.id AND ar.stance != 'ander_onderwerp'
              )""",
        [topic_id, *title_params],
    ).fetchone()["c"]

    to_link = conn.execute(
        f"""SELECT COUNT(*) c FROM documents d
            WHERE d.topic_id IS NOT ? AND ({title_match})""",
        [topic_id, *title_params],
    ).fetchone()["c"]

    to_reset_attempted = conn.execute(
        f"""SELECT COUNT(*) c FROM documents d
            WHERE d.topic_id IS NOT NULL AND d.topic_id != ? AND ({title_match})
              AND d.extraction_attempted_at IS NOT NULL""",
        [topic_id, *title_params],
    ).fetchone()["c"]

    print(f"te ontkoppelen (geen titelmatch, geen echt argument): {to_unlink}")
    print(f"te koppelen (titelmatch, nu elders of NULL): {to_link}")
    print(f"  waarvan extraction_attempted_at wordt gereset (kwam van ander topic): {to_reset_attempted}")

    if not args.apply:
        print("\n(dry-run -- gebruik --apply om dit daadwerkelijk uit te voeren)")
        return

    with conn:
        cur = conn.execute(
            f"""UPDATE documents AS d SET topic_id = NULL
                WHERE d.topic_id = ? AND NOT ({title_match})
                  AND NOT EXISTS (
                    SELECT 1 FROM arguments ar WHERE ar.document_id = d.id AND ar.stance != 'ander_onderwerp'
                  )""",
            [topic_id, *title_params],
        )
        print("ontkoppeld:", cur.rowcount)

        cur = conn.execute(
            f"""UPDATE documents AS d SET extraction_attempted_at = NULL
                WHERE d.topic_id IS NOT NULL AND d.topic_id != ? AND ({title_match})
                  AND d.extraction_attempted_at IS NOT NULL""",
            [topic_id, *title_params],
        )
        print("extraction_attempted_at gereset:", cur.rowcount)

        cur = conn.execute(
            f"""UPDATE documents AS d SET topic_id = ?
                WHERE d.topic_id IS NOT ? AND ({title_match})""",
            [topic_id, topic_id, *title_params],
        )
        print("gekoppeld aan oekraine:", cur.rowcount)


if __name__ == "__main__":
    main()
