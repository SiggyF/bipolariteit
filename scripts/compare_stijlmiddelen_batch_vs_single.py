"""
Kwaliteitscontrole voor scripts/agy_run_stijlmiddelen_backfill.py: pakt N
argumenten die al via de batch-aanpak zijn getagd (`stijl_tagged_at IS NOT
NULL`), haalt hun huidige Stijl-*-tags op (= de batch-uitkomst), en tagt ze
opnieuw één-voor-één (batch-size 1, dus 1 argument per LLM-call, zelfde
prompt-template als de batch-run -- alleen de batchgrootte verschilt, om het
batch-effect zelf te isoleren i.p.v. ook nog prompt-verschillen mee te meten).

Puur leesactie: schrijft NIETS naar de database (geen insert_llm_tags, geen
stijl_tagged_at-update) -- alleen een side-by-side vergelijking op het scherm.
Aanleiding: een eerder, vergelijkbaar experiment met gebundelde extractie-
prompts (docs/batch-experiment.md, sessie 2026-07-28) liet destijds op 14 van
de 20 documenten afwijkende resultaten zien t.o.v. single-call -- nooit
vastgesteld of dat door bundeling kwam of door modelvariatie. Dit script is
de same-day controlemeting die toen ontbrak, nu voor de Stijlmiddelen-tagging.

Gebruik:
    PYTHONPATH=. uv run python scripts/compare_stijlmiddelen_batch_vs_single.py --topic asiel --n 20
"""

import argparse
import logging

from pipeline.db import db
from pipeline.tag_arguments import _extract_json, _validate_tags, load_valid_tags
from scripts.agy_run_stijlmiddelen_backfill import (
    STIJLMIDDELEN_FIELD,
    _build_batch_prompt,
    build_stijlmiddelen_catalogue,
)
from scripts.agy_run_tagging_batch import run_agy

logger = logging.getLogger(__name__)


def fetch_already_batched(conn, topic_id, n):
    return conn.execute(
        """SELECT id, quote_text FROM arguments
           WHERE topic_id = ? AND stijl_tagged_at IS NOT NULL
           ORDER BY id LIMIT ?""",
        (topic_id, n),
    ).fetchall()


def fetch_stored_stijltags(conn, argument_id):
    rows = conn.execute(
        "SELECT tag_sleutel FROM argument_tags WHERE argument_id = ? AND tag_sleutel LIKE 'Stijl-%' ORDER BY tag_sleutel",
        (argument_id,),
    ).fetchall()
    return sorted(r["tag_sleutel"] for r in rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", default="stikstof")
    parser.add_argument("--n", type=int, default=20, help="aantal al-gebatchte argumenten om te vergelijken (default 20)")
    parser.add_argument("--model", default="gemini-3.6-flash-low")
    args = parser.parse_args()

    conn = db.connect()
    topic_row = conn.execute("SELECT id, name FROM topics WHERE slug = ?", (args.topic,)).fetchone()
    topic_id, topic_name = topic_row["id"], topic_row["name"]

    valid_tags = {STIJLMIDDELEN_FIELD: load_valid_tags(conn)[STIJLMIDDELEN_FIELD]}
    tag_catalogue = build_stijlmiddelen_catalogue(conn)

    arguments = fetch_already_batched(conn, topic_id, args.n)
    if not arguments:
        logger.info("Geen al-gebatchte argumenten gevonden voor topic %s.", args.topic)
        return

    logger.info("Model: %s | %d argumenten, elk los (batch-size 1) opnieuw getagd (GEEN DB-writes)", args.model, len(arguments))

    matches = mismatches = errors = 0

    for arg in arguments:
        batch_tags = fetch_stored_stijltags(conn, arg["id"])
        prompt = _build_batch_prompt(topic_name, tag_catalogue, [arg])
        try:
            stdout, stderr = run_agy(prompt, args.model)
            if not stdout:
                raise ValueError(f"leeg antwoord (stderr: {stderr[:200]})")
            parsed = _extract_json(stdout)
            results = parsed.get("arguments", []) if isinstance(parsed, dict) else parsed
            single_result = results[0] if results else {}
            accepted = _validate_tags({STIJLMIDDELEN_FIELD: single_result.get(STIJLMIDDELEN_FIELD, [])}, valid_tags)
            single_tags = sorted(s for s, _ in accepted)
        except Exception as exc:
            logger.error("[arg %5d] FOUT bij losse call: %s", arg["id"], exc)
            errors += 1
            continue

        ok = batch_tags == single_tags
        matches += ok
        mismatches += not ok
        logger.info(
            "[arg %5d] %s | batch=%s | los=%s",
            arg["id"], "GELIJK" if ok else "VERSCHIL", batch_tags, single_tags,
        )

    conn.close()
    logger.info(
        "Klaar: %d gelijk, %d verschil, %d fout(en) op %d argumenten.",
        matches, mismatches, errors, len(arguments),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
