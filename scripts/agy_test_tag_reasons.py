"""
Eenmalige test: laat agy (Docker, zie docs/handoff.md) een paar argumenten
taggen met de nieuwe "reden per tag"-prompt, om te controleren of de reden
daadwerkelijk argument-specifiek is (niet een kale herhaling van de
tag-beschrijving) voordat dit op schaal gebruikt wordt. Schrijft niets naar
de DB -- puur leesactie + printen.

Gebruik:
    PYTHONPATH=. uv run python scripts/agy_test_tag_reasons.py --doc-ids 21,22
"""

import argparse
import subprocess
from pathlib import Path

from pipeline.db import db
from pipeline.tag_arguments import _build_prompt, _extract_json, _validate_tags, build_tag_catalogue, load_valid_tags

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
    parser.add_argument("--arg-ids", default="21")
    parser.add_argument("--model", default="gemini-3.6-flash-low")
    args = parser.parse_args()
    arg_ids = [int(x) for x in args.arg_ids.split(",")]

    conn = db.connect()
    topic_row = conn.execute("SELECT id, name FROM topics WHERE slug = ?", (args.topic,)).fetchone()
    topic_id, topic_name = topic_row["id"], topic_row["name"]

    valid_tags = load_valid_tags(conn)
    tag_catalogue, tag_json_skeleton = build_tag_catalogue(conn)

    rows = conn.execute(
        f"""SELECT ar.id, ar.stance, ar.typology, ar.quote_text, ar.quote_context,
                   a.name AS actor_name, a.party AS actor_party
            FROM arguments ar JOIN actors a ON a.id = ar.actor_id
            WHERE ar.id IN ({','.join('?' * len(arg_ids))})""",
        arg_ids,
    ).fetchall()

    for row in rows:
        prompt = _build_prompt(
            topic_name, row["actor_name"], row["actor_party"], row["stance"], row["typology"],
            row["quote_text"], row["quote_context"], tag_catalogue, tag_json_skeleton,
        )
        print(f"=== argument {row['id']} ===")
        print(row["quote_text"][:200])
        print()
        stdout, stderr = run_agy(prompt, args.model)
        if not stdout:
            print("LEEG ANTWOORD, stderr:", stderr[:500])
            continue
        try:
            parsed = _extract_json(stdout)
            accepted = _validate_tags(parsed, valid_tags)
        except Exception as exc:
            print("PARSE-FOUT:", exc)
            print("ruwe output:", stdout[:1000])
            continue
        for sleutel, reden in accepted:
            print(f"  - {sleutel}: {reden}")
        print()


if __name__ == "__main__":
    main()
