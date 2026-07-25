"""
Genereert één groot tekstdocument met meerdere reeds geëxtraheerde argumenten
+ de taxonomie-instructies, bedoeld om in één keer te plakken in een externe
chat-LLM (Gemini) i.p.v. het lokale LLM one-by-one te laten draaien via
pipeline/tag_arguments.py (~30s/argument). Het antwoord plak je terug in een
bestand en verwerk je met pipeline/import_tag_batch.py.

Deterministische tags (Arena-Parlement/Actor-Type/Parlementaire Context)
worden meteen al toegekend (kost niets, geen LLM nodig) -- alleen de 7
LLM-labelgroepen komen in het document terecht.

Gebruik:
    uv run python -m pipeline.prepare_tag_batch --topic stikstof --limit 40 \
        --output /pad/naar/tag_batch.md
"""

import argparse

from pipeline.db import db
from pipeline.tag_arguments import (
    assign_derived_tags,
    build_tag_catalogue,
    fetch_untagged_arguments,
)


def build_batch_document(conn, arguments, tag_catalogue, tag_json_skeleton):
    argument_blocks = []
    for arg in arguments:
        party_suffix = f" ({arg['actor_party']})" if arg["actor_party"] else ""
        context_line = f"\nContext: {arg['quote_context']}" if arg["quote_context"] else ""
        argument_blocks.append(
            f"### Argument {arg['id']}\n"
            f"Spreker: {arg['actor_name']}{party_suffix} | standpunt: {arg['stance']} | typologie: {arg['typology']}\n"
            f'"""\n{arg["quote_text"]}\n"""{context_line}'
        )

    skeleton_per_arg = tag_json_skeleton.replace("\n", "\n  ")
    example_ids = [str(a["id"]) for a in arguments[:2]] or ["<id>"]
    full_skeleton = (
        "{\n"
        + ",\n".join(f'  "{aid}": {skeleton_per_arg}' for aid in example_ids)
        + ("\n  ...\n}" if len(arguments) > 2 else "\n}")
    )

    return f"""Je labelt {len(arguments)} reeds geëxtraheerde politieke argumenten over "stikstof" met tags uit een vaste taxonomie, aangeleverd door een argumentatie-onderzoeker. Elk argument is los te behandelen.

Belangrijk:
- Jij beoordeelt nooit of een argument klopt, terecht is, of overtuigend is. Dat geldt ook voor de labelgroep "Dialectische Kwaliteit": je labelt de argumentatieve VORM (bv. "dit is een ad-hominem-constructie"), nooit of dat gebruik van die vorm hier eerlijk, onterecht of overtuigend is. Een ad hominem of ander patroon kan een volkomen redelijk punt zijn -- dat is niet aan jou om te beoordelen.
- Ken alleen tags toe die je uit onderstaande lijst kiest, letterlijk overgenomen (exacte sleutel, geen parafrase, geen nieuwe tags verzinnen).
- Bij een labelgroep die "kies precies één" zegt: kies er ook echt maar één, of `null` als geen enkele optie past.
- Bij een labelgroep die "kies nul of meer" zegt: een lege lijst `[]` mag als niets van toepassing is.
- Elke toegekende tag krijgt een `reden`: één korte zin die uitlegt waarom DEZE tag op DIT specifieke argument van toepassing is (bv. citeer of parafraseer het deel van de tekst dat het patroon laat zien). Herhaal niet de generieke tag-beschrijving uit de taxonomie hieronder -- die kent de lezer al.
- Verwerk ALLE {len(arguments)} argumenten hieronder, en alleen deze -- niet meer, niet minder.

Taxonomie:
{tag_catalogue}

Argumenten:
{chr(10).join(argument_blocks)}

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok eromheen: één object, gesleuteld op het argument-id (als string) uit de "### Argument <id>"-koppen hierboven, in dit exacte formaat per argument:

{full_skeleton}
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", required=True, help="topic-slug, bv. stikstof")
    parser.add_argument("--limit", type=int, default=40, help="max aantal argumenten in dit batch-document")
    parser.add_argument("--min-id", type=int, default=0)
    parser.add_argument("--output", required=True, help="pad waar het batch-document weggeschreven wordt")
    args = parser.parse_args()

    conn = db.connect()
    topic_row = conn.execute("SELECT id, name FROM topics WHERE slug = ?", (args.topic,)).fetchone()
    if topic_row is None:
        raise SystemExit(f"onbekende topic-slug: {args.topic}")
    topic_id = topic_row["id"]

    arguments = fetch_untagged_arguments(conn, topic_id, args.limit, args.min_id)
    if not arguments:
        print("Geen ongetagde argumenten (al verwerkt, of geen argumenten voor deze topic).")
        return

    total_derived = 0
    for arg in arguments:
        derived = assign_derived_tags(conn, arg["id"], arg["document_id"], arg["actor_id"], dry_run=False)
        total_derived += len(derived)
    conn.commit()

    tag_catalogue, tag_json_skeleton = build_tag_catalogue(conn)
    document = build_batch_document(conn, arguments, tag_catalogue, tag_json_skeleton)

    output_path = args.output
    with open(output_path, "w") as f:
        f.write(document)

    conn.close()

    print(f"Klaar: {len(arguments)} argumenten ({total_derived} afgeleide tags al toegekend, kosteloos).")
    print(f"Batch-document geschreven naar: {output_path}")
    print(f"Argument-ids in dit document: {[a['id'] for a in arguments]}")
    print("Plak de volledige inhoud van dit bestand in Gemini, plak het antwoord terug in een bestand,")
    print("en verwerk het met: uv run python -m pipeline.import_tag_batch --topic <topic> --input <pad>")


if __name__ == "__main__":
    main()
