"""
Regex-kandidatenscan voor Stijl-Godwin (issue #321): zoekt argumenten wier
quote_text/quote_context WOII/nazi-Duitsland-vocabulaire bevat, als
voorselectie vóór een LLM-beoordeling via pipeline/tag_single.py. Bewust
ruim (hoge recall, lage precisie is prima -- het LLM beoordeelt per
kandidaat alsnog of het echt een Godwin-vergelijking is, dit script haalt
alleen de kansloze meerderheid eruit).

Woordgrens-regex i.p.v. SQL LIKE: substring-matches als '%azi%' vangen ook
"Brazilië"/"Aziatische"/"Azië" -- zie de ruwe SQL-proefscan die dit opleverde
tijdens het bouwen van dit script.

Gebruik:
    uv run python -m scripts.find_godwin_candidates --output /pad/naar/kandidaten.txt
    uv run python -m scripts.find_godwin_candidates --print  # eerst even bekijken, niets wegschrijven
"""

import argparse
import re
from pathlib import Path

from pipeline.db import db

# Woordgrens-patronen, hoofdletterongevoelig. Bewust géén kale 'azi'
# (Brazilië/Aziatische/Azië) en géén kale 'bezetting' (COA-bezettingsgraad
# is het overgrote deel van de treffers, niets met WOII te maken).
PATTERNS = [
    r"\bnazi[a-z']*\b",
    r"\bhitler\b",
    r"\bderde\s+rijk\b",
    r"\bnaziregime\b",
    r"\bnazi-duitsland\b",
    r"\bholocaust\b",
    r"\bauschwitz\b",
    r"\bgoebbels\b",
    r"\bjodenvervolg\w*\b",
    r"\bconcentratiekamp\w*\b",
    r"\bkristallnacht\b",
    r"\bfascist\w*\b",
    r"\bfascisme\b",
    r"\btweede\s+wereldoorlog\b",
    r"\bwoii\b",
    r"\bwo2\b",
    r"\bgodwin\b",
    # Euphemismen/indirecte verwijzingen naar Hitler/het naziregime, en
    # aanpalende WOII-aanloopvocabulaire (Chamberlain/Sudetenland/appeasement
    # = de Godwin-variant die specifiek naar 1938 verwijst i.p.v. de oorlog
    # zelf) -- ontbraken in de eerste ronde (zie ook #321-discussie).
    r"\bman\s+met\s+de\s+snor\b",
    r"\bf[üu]hrer\b",
    r"\bbruinhemden\b",
    r"\bendl[öo]sung\b",
    r"\banne\s+frank\b",
    r"\bchamberlain\b",
    r"\bsudetenland\b",
    r"\bappeasement\b",
    r"\bmunchen[-\s]akkoord\b",
    r"\bjaren\s+dertig\b",
    r"\b1938\b",
    r"\bkristalnacht\b",  # alternatieve NL-spelling naast Kristallnacht
]
COMBINED = re.compile("|".join(PATTERNS), re.IGNORECASE)


def find_candidates(conn):
    rows = conn.execute(
        """SELECT ar.id, ar.topic_id, tp.slug AS topic_slug, act.name AS actor_name,
                  ar.quote_text, ar.quote_context
           FROM arguments ar
           JOIN topics tp ON tp.id = ar.topic_id
           JOIN actors act ON act.id = ar.actor_id
           ORDER BY ar.id"""
    ).fetchall()
    candidates = []
    for row in rows:
        haystack = row["quote_text"] + " " + (row["quote_context"] or "")
        match = COMBINED.search(haystack)
        if match:
            candidates.append((row, match.group(0)))
    return candidates


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", default=None, help="pad voor een --ids-file (één argument-id per regel)")
    parser.add_argument("--print", dest="do_print", action="store_true", help="print elke kandidaat (spreker, treffer, quote) naar stdout")
    args = parser.parse_args()

    conn = db.connect()
    candidates = find_candidates(conn)

    print(f"{len(candidates)} kandidaten gevonden (van {conn.execute('SELECT COUNT(*) AS n FROM arguments').fetchone()['n']} argumenten totaal).")

    if args.do_print or not args.output:
        for row, matched in candidates:
            print(f"[{row['id']:>5}] {row['topic_slug']:<16} {row['actor_name']:<25} treffer={matched!r}")
            print(f"        {row['quote_text'][:160]}")

    if args.output:
        lines = [f"# {len(candidates)} regex-kandidaten voor Stijl-Godwin (scripts/find_godwin_candidates.py)"]
        for row, matched in candidates:
            lines.append(f"{row['id']}  # {row['topic_slug']} | {row['actor_name']} | treffer={matched!r}")
        Path(args.output).write_text("\n".join(lines) + "\n")
        print(f"Weggeschreven naar {args.output}")


if __name__ == "__main__":
    main()
