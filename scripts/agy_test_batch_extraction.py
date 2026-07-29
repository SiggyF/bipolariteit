"""
Validatietest voor gebundelde (multi-document) extractieprompts via agy:
draait dezelfde 20 doc-ids als de eerdere quota-kalibratie
(agy_prepare_batch_prompts.DEFAULT_DOC_IDS), maar nu N per agy-call in plaats
van 1 per call, om te zien of het model documenten door elkaar haalt en of
het tokens/calls bespaart t.o.v. de bekende resultaten in
data/export/agy_batch_test_results.md.

Schrijft geen data naar de database -- puur een kwaliteitscheck.

Gebruik:
    PYTHONPATH=. uv run python scripts/agy_test_batch_extraction.py --group-size 5
"""

import argparse
import json
import logging
import subprocess
import time
from pathlib import Path

from pipeline.db import db
from pipeline.extract_arguments import BATCH_PROMPT_VERSION, _build_batch_prompt, _extract_json, _validate_argument

logger = logging.getLogger(__name__)

DEFAULT_DOC_IDS = [37, 40, 41, 42, 45, 50, 51, 56, 101, 107, 116, 122, 129, 133, 150, 167, 169, 175, 192, 218]

AGY_GEMINI_CONFIG_DIR = str(Path.home() / ".bipolariteit" / "agy_gemini_config")


def run_agy(prompt, model):
    result = subprocess.run(
        [
            "docker", "run", "--rm",
            "-v", f"{AGY_GEMINI_CONFIG_DIR}:/home/agy/.gemini",
            "bipolariteit-agy",
            "agy", "--print", prompt,
            "--model", model,
            "--sandbox",
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    return result.stdout.strip(), result.stderr.strip()


def chunk(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", default="stikstof")
    parser.add_argument("--model", default="gemini-3.6-flash-low")
    parser.add_argument("--group-size", type=int, default=5)
    parser.add_argument("--output", default="data/export/agy_batch_test_multidoc_results.md")
    args = parser.parse_args()

    conn = db.connect()
    topic_row = conn.execute("SELECT id, name, description FROM topics WHERE slug = ?", (args.topic,)).fetchone()
    topic_id, topic_name, topic_description = topic_row["id"], topic_row["name"], topic_row["description"]

    docs = conn.execute(
        f"""SELECT d.id, d.content, a.name AS actor_name, a.party AS actor_party
            FROM documents d JOIN actors a ON a.id = d.actor_id
            WHERE d.topic_id = ? AND d.id IN ({','.join('?' * len(DEFAULT_DOC_IDS))})
            ORDER BY d.id""",
        (topic_id, *DEFAULT_DOC_IDS),
    ).fetchall()
    docs_by_id = {d["id"]: d for d in docs}

    logger.info("Model: %s | batch_prompt_version=%s | %d documenten in groepen van %d", args.model, BATCH_PROMPT_VERSION, len(docs), args.group_size)

    total_calls = 0
    total_args = 0
    total_mismatches = 0
    total_missing_docs = 0
    latencies = []

    with open(args.output, "w") as f:
        for group in chunk(docs, args.group_size):
            group_ids = [d["id"] for d in group]
            prompt = _build_batch_prompt(topic_name, topic_description, group)
            start = time.monotonic()
            stdout, stderr = run_agy(prompt, args.model)
            elapsed = time.monotonic() - start
            total_calls += 1
            latencies.append(elapsed)

            f.write(f"=== groep {group_ids} | {elapsed:.1f}s ===\n{stdout}\n\n")

            try:
                parsed = _extract_json(stdout)
                results_by_id = {r["document_id"]: r.get("arguments", []) for r in parsed.get("documents", [])}
            except Exception as exc:
                logger.error("groep %s: FOUT bij parsen: %s", group_ids, exc)
                total_mismatches += len(group_ids)
                continue

            missing = set(group_ids) - set(results_by_id)
            if missing:
                logger.error("groep %s: ontbrekende document_id(s) in antwoord: %s", group_ids, missing)
                total_missing_docs += len(missing)

            for doc_id in group_ids:
                doc = docs_by_id[doc_id]
                arguments = results_by_id.get(doc_id, [])
                n_ok = 0
                for arg in arguments:
                    try:
                        _validate_argument(arg)
                    except ValueError as exc:
                        logger.warning("[doc %5d] ongeldig argument: %s", doc_id, exc)
                        continue
                    if arg["quote_text"] not in doc["content"]:
                        logger.error("[doc %5d] QUOTE NIET GEVONDEN IN BRONTEKST (mogelijk cross-document bleed): %r", doc_id, arg["quote_text"][:120])
                        total_mismatches += 1
                        continue
                    n_ok += 1
                total_args += n_ok
                logger.info("[doc %5d] %-25s %d argument(en) (van %d), quote-check OK", doc_id, doc["actor_name"], n_ok, len(arguments))

    conn.close()
    logger.info(
        "Klaar: %d calls voor %d documenten (%.1f docs/call), %d argumenten totaal, %d quote-mismatches, %d ontbrekende docs in antwoorden.",
        total_calls, len(docs), len(docs) / total_calls, total_args, total_mismatches, total_missing_docs,
    )
    if latencies:
        avg = sum(latencies) / len(latencies)
        logger.info("Latency per call: gem=%.1fs min=%.1fs max=%.1fs (%.1fs/doc effectief)", avg, min(latencies), max(latencies), sum(latencies) / len(docs))
    logger.info("Ruwe output -> %s (vergelijk handmatig met data/export/agy_batch_test_results.md)", args.output)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
