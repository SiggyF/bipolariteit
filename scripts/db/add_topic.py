"""
Voegt bewust een nieuwe curated topic toe (of werkt de description van een
bestaande bij) -- de tegenhanger van `pipeline.ingest.ingest_tk.get_topic()`,
die sinds de opschoning van energie/energiedrager/klimaat/saldering/waterstof/
migratie/Vragenuur (2026-09-12) geen nieuwe topic-rij meer stilzwijgend
aanmaakt. Een nieuw topic is nu altijd een bewuste, aparte stap via dit
script, met een description die vanuit een los, leesbaar/diffbaar bestand
komt (zie config/topic-descriptions/) i.p.v. een string in de commandline.

Gebruik:
    uv run python scripts/db/add_topic.py --slug oekraine --name "Oekraïne" \\
        --description-file config/topic-descriptions/oekraine.md

Bestaat de slug al? Dan wordt alleen de description bijgewerkt (upsert),
handig om een concept-tekst iteratief te verfijnen vóórdat er geëxtraheerd
wordt.
"""

import argparse

from pipeline.db import db


def add_topic(slug, name, description):
    conn = db.connect()
    with conn:
        row = conn.execute("SELECT id FROM topics WHERE slug = ?", (slug,)).fetchone()
        if row:
            conn.execute("UPDATE topics SET name = ?, description = ? WHERE slug = ?", (name, description, slug))
            print(f"topic '{slug}' (id {row['id']}) bijgewerkt.")
        else:
            cur = conn.execute(
                "INSERT INTO topics (slug, name, description) VALUES (?, ?, ?)", (slug, name, description)
            )
            print(f"topic '{slug}' aangemaakt, id {cur.lastrowid}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--slug", required=True, help="topic-slug, bv. oekraine")
    parser.add_argument("--name", required=True, help="weergavenaam, bv. Oekraïne")
    parser.add_argument(
        "--description-file", required=True,
        help="pad naar een tekstbestand met de pro/contra-description (zie config/topic-descriptions/)",
    )
    args = parser.parse_args()
    description = open(args.description_file).read().strip()
    add_topic(args.slug, args.name, description)


if __name__ == "__main__":
    main()
