"""
Bouwt één groot review-document van alle Stage-1-geëxtraheerde argumenten
(quote/context/stance/typology/actor) voor menselijke of externe-LLM
(Gemini) validatie van de extractiekwaliteit -- bedoeld als aanvulling op
de losse steekproef uit docs/handoff.md ("Tag-kwaliteitscontrole"), maar
dan voor Stage 1 (extract_arguments.py) i.p.v. Stage 2 (tag_arguments.py).

Schrijft alleen weg, doet geen LLM-calls en verandert niets aan de DB.

Gebruik:
    PYTHONPATH=. uv run python scripts/build_extraction_review_doc.py \
        --topic stikstof --output data/export/extractie_review_stikstof.md
"""

import argparse

from pipeline.db import db

INSTRUCTIONS = """Je bent een tweede beoordelaar voor Stage 1 van een argument-extractiepipeline \
(politieke Tweede Kamer-debatten, onderwerp "{topic}"). Een lokaal LLM heeft per sprekerbeurt \
politieke argumenten geëxtraheerd: een letterlijk citaat (`quote_text`), een korte parafrase van \
de context (`quote_context`), een standpunt (`stance`: pro/contra/unclear t.o.v. het beleid) en een \
typologie (`typology`: factual/moral/economic/legal/other).

Beoordeel per argument kritisch, puur op basis van de tekst:
1. **Is dit daadwerkelijk een argument** (een standpunt met een onderbouwing/reden), of is het \
   procedurele tekst, een kale vraag, of een fragment zonder argumentatieve inhoud dat niet had \
   moeten worden geëxtraheerd?
2. **Klopt de `stance`?** Zou jij dit ook pro/contra/unclear noemen t.o.v. het beleid?
3. **Klopt de `typology`?** Past de gekozen categorie (factual/moral/economic/legal/other), of zou \
   een andere beter passen?
4. **Is het citaat volledig en samenhangend**, of is het een afgeknipt fragment van een groter punt \
   dat beter als één argument had moeten worden geëxtraheerd?

Je oordeelt nooit over de politieke juistheid of overtuigingskracht van het argument zelf -- alleen \
over de kwaliteit van de extractie. Geef per argument een kort oordeel (1 regel volstaat als alles \
klopt; leg uit bij een probleem). Als een groep argumenten stelselmatig hetzelfde soort fout \
vertoont, mag je dat aan het eind samenvatten i.p.v. het per argument te herhalen.

---

"""


def build_document(topic_name, rows):
    blocks = [INSTRUCTIONS.format(topic=topic_name)]
    for r in rows:
        party_suffix = f" ({r['actor_party']})" if r["actor_party"] else ""
        context_line = f"\nContext: {r['quote_context']}" if r["quote_context"] else ""
        blocks.append(
            f"### Argument {r['id']} (document {r['document_id']})\n"
            f"Spreker: {r['actor_name']}{party_suffix} | stance: {r['stance']} | typology: {r['typology']}\n"
            f'"""\n{r["quote_text"]}\n"""{context_line}\n'
        )
    return "\n".join(blocks)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--min-id", type=int, default=0, help="alleen arguments met id >= deze waarde")
    args = parser.parse_args()

    conn = db.connect()
    topic_row = conn.execute("SELECT id, name FROM topics WHERE slug = ?", (args.topic,)).fetchone()
    if topic_row is None:
        raise SystemExit(f"onbekende topic-slug: {args.topic}")
    topic_id, topic_name = topic_row["id"], topic_row["name"]

    rows = conn.execute(
        """SELECT a.id, a.document_id, a.stance, a.typology, a.quote_text, a.quote_context,
                  ac.name AS actor_name, ac.party AS actor_party
           FROM arguments a
           JOIN actors ac ON ac.id = a.actor_id
           WHERE a.topic_id = ? AND a.id >= ?
           ORDER BY a.id""",
        (topic_id, args.min_id),
    ).fetchall()
    conn.close()

    if not rows:
        print("Geen argumenten gevonden voor deze topic/min-id.")
        return

    document = build_document(topic_name, rows)
    with open(args.output, "w") as f:
        f.write(document)

    word_count = len(document.split())
    print(f"Klaar: {len(rows)} argumenten geschreven naar {args.output}")
    print(f"Woordenaantal: {word_count} (~{word_count // 500} pagina's bij ~500 woorden/pagina)")


if __name__ == "__main__":
    main()
