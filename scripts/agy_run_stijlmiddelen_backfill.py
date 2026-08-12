"""
Backfill van de labelgroep "Stijlmiddelen" (issue #67) op argumenten die al
vóór deze labelgroep bestond volledig getagd waren (`tagged_at IS NOT NULL`).
Draait via agy (Docker/Gemini), met een SMALLE catalogus die alleen de 5
Stijlmiddelen-tags bevat -- geen volledige hertagging, bestaande tags blijven
onaangeroerd (`insert_llm_tags` is additief, INSERT OR IGNORE).

Idempotent via `arguments.stijl_tagged_at`: gezet na elke poging, ook als
dat 0 stijltags opleverde (0 is een geldige uitkomst voor een "kies nul of
meer"-labelgroep, dus "geen Stijl-tag aanwezig" alleen is geen betrouwbaar
signaal dat een argument nog gecontroleerd moet worden).

Gebruik (eerst een kleine steekproef, NIET meteen de volle batch):
    PYTHONPATH=. uv run python scripts/agy_run_stijlmiddelen_backfill.py --topic stikstof --limit 20
"""

import argparse
import json
import time
from datetime import datetime, timezone

from pipeline.db import db
from pipeline.tag_arguments import (
    _build_prompt,
    _extract_json,
    _validate_tags,
    insert_llm_tags,
    load_all_active_tags_by_labelgroep,
    load_valid_tags,
)
from scripts.agy_run_tagging_batch import run_agy

STIJLMIDDELEN_LABELGROEP = "Stijlmiddelen"
STIJLMIDDELEN_FIELD = "stijlmiddelen"


def build_stijlmiddelen_catalogue(conn):
    grouped = load_all_active_tags_by_labelgroep(conn)
    info = grouped[STIJLMIDDELEN_LABELGROEP]
    lines = [f"### {STIJLMIDDELEN_LABELGROEP} ({info['beschrijving']}) -- kies nul of meer"]
    for sleutel, beschrijving in info["tags"]:
        lines.append(f"- {sleutel}: {beschrijving}")
    skeleton = {STIJLMIDDELEN_FIELD: [{"sleutel": "<TAG_SLEUTEL>", "reden": "<korte argument-specifieke onderbouwing>"}]}
    return "\n".join(lines).strip(), json.dumps(skeleton, ensure_ascii=False, indent=2)


def fetch_backfill_candidates(conn, topic_id, limit, min_id=0):
    return conn.execute(
        """SELECT ar.id, ar.stance, ar.typology, ar.quote_text, ar.quote_context,
                  act.name AS actor_name, act.party AS actor_party
           FROM arguments ar
           JOIN actors act ON act.id = ar.actor_id
           WHERE ar.topic_id = ? AND ar.id >= ?
             AND ar.tagged_at IS NOT NULL
             AND ar.stijl_tagged_at IS NULL
           ORDER BY ar.id
           LIMIT ?""",
        (topic_id, min_id, limit),
    ).fetchall()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", default="stikstof")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--min-id", type=int, default=0)
    parser.add_argument("--model", default="gemini-3.6-flash-low")
    args = parser.parse_args()

    conn = db.connect()
    topic_row = conn.execute("SELECT id, name FROM topics WHERE slug = ?", (args.topic,)).fetchone()
    topic_id, topic_name = topic_row["id"], topic_row["name"]

    valid_tags = {STIJLMIDDELEN_FIELD: load_valid_tags(conn)[STIJLMIDDELEN_FIELD]}
    tag_catalogue, tag_json_skeleton = build_stijlmiddelen_catalogue(conn)

    arguments = fetch_backfill_candidates(conn, topic_id, args.limit, args.min_id)
    if not arguments:
        print("Geen kandidaten (alles al gecontroleerd, of geen getagde argumenten voor deze topic).")
        return

    print(f"Model: {args.model} | {len(arguments)} argumenten\n")

    total_tags = total_errors = 0
    latencies = []

    for arg in arguments:
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
            insert_llm_tags(conn, arg["id"], accepted)
            conn.execute(
                "UPDATE arguments SET stijl_tagged_at = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), arg["id"]),
            )

        total_tags += len(accepted)
        print(f"[arg {arg['id']:>5}] {arg['actor_name']:<25} {elapsed:5.1f}s | stijl: {[s for s, _ in accepted]}")

    conn.close()
    print()
    print(f"Klaar: {len(arguments)} argumenten, {total_errors} fout(en), {total_tags} stijltags toegekend.")
    if latencies:
        avg = sum(latencies) / len(latencies)
        print(f"Latency: gem={avg:.1f}s min={min(latencies):.1f}s max={max(latencies):.1f}s")


if __name__ == "__main__":
    main()
