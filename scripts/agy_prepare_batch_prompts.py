"""
Bouwt de echte extractieprompts (dezelfde _build_prompt als extract_arguments.py
gebruikt) voor een gekozen set documenten, en schrijft ze naar één bestand --
bedoeld om via agy (Antigravity CLI, Docker) te draaien als validatie/tweede-
beoordeling van de lokale qwen-extracties (zie docs/handoff.md, besluit: agy
wordt niet voor de volle batch gebruikt, alleen voor steekproefvalidatie).

Schrijft alleen weg, doet geen LLM-calls.

Gebruik:
    PYTHONPATH=. uv run python scripts/agy_prepare_batch_prompts.py \
        --topic stikstof --output data/export/batch-experiment/agy_batch_test_prompts.md
    PYTHONPATH=. uv run python scripts/agy_prepare_batch_prompts.py \
        --topic stikstof --doc-ids 56,95,103,150
"""

import argparse

from pipeline.db import db
from pipeline.extract_arguments import _build_prompt

DEFAULT_DOC_IDS = [37, 40, 41, 42, 45, 50, 51, 56, 101, 107, 116, 122, 129, 133, 150, 167, 169, 175, 192, 218]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", default="stikstof")
    parser.add_argument("--output", default="data/export/batch-experiment/agy_batch_test_prompts.md")
    parser.add_argument("--doc-ids", default=None, help="komma-gescheiden document-ids, bv. 56,95,103,150")
    args = parser.parse_args()
    doc_ids = [int(x) for x in args.doc_ids.split(",")] if args.doc_ids else DEFAULT_DOC_IDS

    conn = db.connect()
    topic_row = conn.execute(
        "SELECT id, name, description FROM topics WHERE slug = ?", (args.topic,)
    ).fetchone()
    if topic_row is None:
        raise SystemExit(f"onbekende topic-slug: {args.topic}")
    topic_id, topic_name, topic_description = topic_row["id"], topic_row["name"], topic_row["description"]

    docs = conn.execute(
        f"""SELECT d.id, d.content, a.name AS actor_name, a.party AS actor_party
            FROM documents d JOIN actors a ON a.id = d.actor_id
            WHERE d.topic_id = ? AND d.id IN ({','.join('?' * len(doc_ids))})
            ORDER BY d.id""",
        (topic_id, *doc_ids),
    ).fetchall()

    total_chars = 0
    with open(args.output, "w") as f:
        for doc in docs:
            prompt = _build_prompt(topic_name, topic_description, doc["actor_name"], doc["actor_party"], doc["content"])
            total_chars += len(prompt)
            f.write(f"=== document {doc['id']} ({doc['actor_name']}) ===\n")
            f.write(prompt)
            f.write("\n\n")

    print(f"Klaar: {len(docs)} documenten, {total_chars} tekens totaal -> {args.output}")


if __name__ == "__main__":
    main()
