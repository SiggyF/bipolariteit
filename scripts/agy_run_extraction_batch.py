"""
Draait Stage 1 (extractie) via agy (Docker) i.p.v. het lokale LLM -- schrijft
echt naar de DB (arguments, claims, documents.extraction_attempted_at),
zelfde contract als pipeline/extract_arguments.py. Bedoeld voor batchwise
extractie met agy als primaire backend naast/i.p.v. de lokale qwen-pipeline
(zie docs/handoff.md).

Gebruik:
    PYTHONPATH=. uv run python scripts/agy_run_extraction_batch.py --topic stikstof --limit 377
"""

import argparse
import logging
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from pipeline.db import db
from pipeline.extract_arguments import (
    PROMPT_VERSION,
    _build_prompt,
    _extract_json,
    _validate_argument,
    fetch_pending_documents,
    insert_argument,
)

logger = logging.getLogger(__name__)

# Buiten de repo (bevat een live OAuth-token, nooit in een git-repo laten
# staan): éénmalig aangemaakt via `docker run -it --rm -v ...` login, zie
# docs/handoff.md.
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", default="stikstof")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--min-id", type=int, default=0)
    parser.add_argument("--model", default="gemini-3.6-flash-low")
    args = parser.parse_args()

    conn = db.connect()
    topic_row = conn.execute("SELECT id, name, description FROM topics WHERE slug = ?", (args.topic,)).fetchone()
    if topic_row is None:
        raise SystemExit(f"onbekende topic-slug: {args.topic}")
    topic_id, topic_name, topic_description = topic_row["id"], topic_row["name"], topic_row["description"]
    if not topic_description:
        raise SystemExit(
            f"topic '{args.topic}' heeft geen description (pro/contra-narratief) -- "
            "zet dit eerst via UPDATE topics SET description = ... (zie docs/handoff.md)"
        )

    documents = fetch_pending_documents(conn, topic_id, args.limit, args.min_id)
    if not documents:
        logger.info("Geen openstaande documenten (al verwerkt, of geen documenten voor deze topic).")
        return

    logger.info("Model: %s | prompt_version=%s | %d documenten", args.model, PROMPT_VERSION, len(documents))

    total_arguments = total_claims = total_errors = 0
    latencies = []

    for doc in documents:
        prompt = _build_prompt(topic_name, topic_description, doc["actor_name"], doc["actor_party"], doc["content"])
        start = time.monotonic()
        try:
            stdout, stderr = run_agy(prompt, args.model)
            if not stdout:
                raise ValueError(f"leeg antwoord (stderr: {stderr[:200]})")
            parsed = _extract_json(stdout)
        except Exception as exc:
            elapsed = time.monotonic() - start
            logger.error("[doc %5d] %-25s FOUT na %5.1fs: %s", doc["id"], doc["actor_name"], elapsed, exc)
            total_errors += 1
            continue
        elapsed = time.monotonic() - start
        latencies.append(elapsed)

        with conn:
            for arg in parsed.get("arguments", []):
                try:
                    _validate_argument(arg)
                except ValueError as exc:
                    logger.warning("[doc %5d]   overgeslagen argument: %s", doc["id"], exc)
                    continue
                n_claims += len(arg.get("claims") or [])
                insert_argument(conn, doc["id"], topic_id, doc["actor_id"], arg, args.model)
                n_valid += 1

            conn.execute(
                "UPDATE documents SET extraction_attempted_at = ?, extraction_prompt_version = ?, extraction_model = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), PROMPT_VERSION, args.model, doc["id"]),
            )

        logger.info(
            "[doc %5d] %-25s %5.1fs | %d argument(en), %d claim(s)",
            doc["id"], doc["actor_name"], elapsed, n_valid, n_claims,
        )
        total_arguments += n_valid
        total_claims += n_claims

    conn.close()

    logger.info("Klaar: %d documenten verwerkt, %d fout(en).", len(documents), total_errors)
    logger.info("Totaal: %d argumenten, %d claims.", total_arguments, total_claims)
    if latencies:
        avg = sum(latencies) / len(latencies)
        logger.info("Latency: gem=%.1fs min=%.1fs max=%.1fs", avg, min(latencies), max(latencies))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
