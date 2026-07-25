"""
Draait de door agy_prepare_batch_prompts.py gebouwde prompts één voor één
door `agy` in de Docker-container (docker/agy/Dockerfile), en schrijft de
ruwe JSON-antwoorden weg -- bedoeld als quota-kalibratie (gebruiker meet
/usage voor en na deze run) en als kwaliteitssteekproef op het gekozen model.

Vereist: `docker build -t bipolariteit-agy docker/agy` en een eenmalige
interactieve login (zie docs/handoff.md, sectie "Antigravity CLI (agy) in
Docker").

Gebruik:
    PYTHONPATH=. uv run python scripts/agy_run_batch.py \
        --topic stikstof --model gemini-3.6-flash-low \
        --output data/export/agy_batch_test_results.md
"""

import argparse
import subprocess
import time
from pathlib import Path

from pipeline.db import db
from pipeline.extract_arguments import _build_prompt

from agy_prepare_batch_prompts import DOC_IDS

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
    parser.add_argument("--model", default="gemini-3.6-flash-low")
    parser.add_argument("--output", default="data/export/agy_batch_test_results.md")
    args = parser.parse_args()

    conn = db.connect()
    topic_row = conn.execute(
        "SELECT id, name, description FROM topics WHERE slug = ?", (args.topic,)
    ).fetchone()
    topic_id, topic_name, topic_description = topic_row["id"], topic_row["name"], topic_row["description"]

    docs = conn.execute(
        f"""SELECT d.id, d.content, a.name AS actor_name, a.party AS actor_party
            FROM documents d JOIN actors a ON a.id = d.actor_id
            WHERE d.topic_id = ? AND d.id IN ({','.join('?' * len(DOC_IDS))})
            ORDER BY d.id""",
        (topic_id, *DOC_IDS),
    ).fetchall()

    print(f"Model: {args.model} | {len(docs)} documenten\n")
    with open(args.output, "w") as f:
        for doc in docs:
            prompt = _build_prompt(topic_name, topic_description, doc["actor_name"], doc["actor_party"], doc["content"])
            start = time.monotonic()
            stdout, stderr = run_agy(prompt, args.model)
            elapsed = time.monotonic() - start
            print(f"[doc {doc['id']:>5}] {doc['actor_name']:<25} {elapsed:5.1f}s")
            f.write(f"=== document {doc['id']} ({doc['actor_name']}) | {elapsed:.1f}s ===\n")
            f.write(stdout if stdout else f"(leeg antwoord, stderr: {stderr[:500]})")
            f.write("\n\n")

    print(f"\nKlaar. Resultaten -> {args.output}")


if __name__ == "__main__":
    main()
