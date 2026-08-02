"""
Draait Stage 2 (tagging, incl. de nieuwe reden-per-tag) via agy (Docker) i.p.v.
het lokale LLM -- schrijft écht naar de DB (derived + llm tags, arguments.tagged_at),
zelfde contract als pipeline/tag_arguments.py. Bedoeld voor een gerichte batch
ter validatie/quota-kalibratie, niet de volle taggingrun.

Gebruik:
    PYTHONPATH=. uv run python scripts/agy_run_tagging_batch.py --topic stikstof --limit 20
"""

import argparse
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from pipeline.db import db
from pipeline.tag_arguments import (
    PROMPT_VERSION,
    _build_prompt,
    _extract_json,
    _validate_tags,
    assign_derived_tags,
    build_tag_catalogue,
    fetch_untagged_arguments,
    insert_llm_tags,
    load_valid_tags,
)

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
    topic_row = conn.execute("SELECT id, name FROM topics WHERE slug = ?", (args.topic,)).fetchone()
    topic_id, topic_name = topic_row["id"], topic_row["name"]

    valid_tags = load_valid_tags(conn)
    tag_catalogue, tag_json_skeleton = build_tag_catalogue(conn)

    arguments = fetch_untagged_arguments(conn, topic_id, args.limit, args.min_id)
    if not arguments:
        print("Geen ongetagde argumenten.")
        return

    print(f"Model: {args.model} | {len(arguments)} argumenten\n")

    total_derived = total_llm = total_errors = 0
    latencies = []

    for arg in arguments:
        derived = assign_derived_tags(conn, arg["id"], arg["document_id"], arg["actor_id"], dry_run=True)
        total_derived += len(derived)

        prompt = _build_prompt(
            topic_name, arg["actor_name"], arg["actor_party"], arg["stance"], arg["typology"],
            arg["quote_text"], arg["quote_context"], tag_catalogue, tag_json_skeleton,
        )
        start = time.monotonic()
        try:
            stdout, stderr = run_agy(prompt, args.model)
            if not stdout:
                raise ValueError(f"leeg antwoord (stderr: {stderr[:200]})")
            parsed = _extract_json(stdout)
            accepted = _validate_tags(parsed, valid_tags)
        except Exception as exc:
            elapsed = time.monotonic() - start
            print(f"[arg {arg['id']:>5}] {arg['actor_name']:<25} FOUT na {elapsed:5.1f}s: {exc}")
            total_errors += 1
            continue
        elapsed = time.monotonic() - start
        latencies.append(elapsed)

        with conn:
            assign_derived_tags(conn, arg["id"], arg["document_id"], arg["actor_id"], dry_run=False)
            insert_llm_tags(conn, arg["id"], accepted)
            conn.execute(
                "UPDATE arguments SET tagged_at = ?, tag_prompt_version = ?, tag_model = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), PROMPT_VERSION, args.model, arg["id"]),
            )

        total_llm += len(accepted)
        print(f"[arg {arg['id']:>5}] {arg['actor_name']:<25} {elapsed:5.1f}s | derived: {len(derived)} | llm: {[s for s, _ in accepted]}")

    conn.close()
    print()
    print(f"Klaar: {len(arguments)} argumenten, {total_errors} fout(en), {total_derived} derived tags, {total_llm} llm tags.")
    if latencies:
        avg = sum(latencies) / len(latencies)
        print(f"Latency: gem={avg:.1f}s min={min(latencies):.1f}s max={max(latencies):.1f}s")


if __name__ == "__main__":
    main()
