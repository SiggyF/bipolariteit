"""
Ad-hoc modelvergelijking: draait een vaste set documenten (topic stikstof)
door een gegeven model, zonder de extraction_attempted_at skip-filter
(puur leesactie, schrijft niets naar de DB). Standaard id 40-54 -- het
exacte sample uit de eerdere qwen/qwen3.6-27b testrun in docs/handoff.md --
maar een eigen lijst kan meegegeven worden om specifieke (bv. door een
reviewer aangewezen) documenten te hertesten.

Gebruik:
    uv run python scripts/compare_models.py <model>
    uv run python scripts/compare_models.py <model> --doc-ids 56,95,103,150
"""
import sys
import time

from pipeline.db import db
from pipeline.extract_arguments import _build_prompt, _extract_json, _validate_argument, call_llm

DEFAULT_DOC_IDS = list(range(40, 55))


def main():
    model = sys.argv[1]
    doc_ids = DEFAULT_DOC_IDS
    if len(sys.argv) > 2 and sys.argv[2] == "--doc-ids":
        doc_ids = [int(x) for x in sys.argv[3].split(",")]

    conn = db.connect()
    topic_row = conn.execute("SELECT id, name, description FROM topics WHERE slug = 'stikstof'").fetchone()
    topic_id, topic_name, topic_description = topic_row["id"], topic_row["name"], topic_row["description"]

    docs = conn.execute(
        f"""SELECT d.id, d.content, a.name AS actor_name, a.party AS actor_party
            FROM documents d JOIN actors a ON a.id = d.actor_id
            WHERE d.topic_id = ? AND d.id IN ({','.join('?' * len(doc_ids))})
            ORDER BY d.id""",
        (topic_id, *doc_ids),
    ).fetchall()

    print(f"Model: {model} | {len(docs)} documenten\n")
    total_args = total_claims = total_errors = 0
    latencies = []

    for doc in docs:
        prompt = _build_prompt(topic_name, topic_description, doc["actor_name"], doc["actor_party"], doc["content"])
        start = time.monotonic()
        try:
            raw, usage = call_llm("http://localhost:1234/v1", model, prompt, "none", 120.0)
            parsed = _extract_json(raw)
        except Exception as exc:
            elapsed = time.monotonic() - start
            print(f"[doc {doc['id']:>5}] {doc['actor_name']:<25} FOUT na {elapsed:5.1f}s: {exc}")
            total_errors += 1
            continue
        elapsed = time.monotonic() - start
        latencies.append(elapsed)

        arguments = parsed.get("arguments", [])
        valid = []
        for arg in arguments:
            try:
                _validate_argument(arg)
                valid.append(arg)
            except ValueError as exc:
                print(f"[doc {doc['id']:>5}]   overgeslagen: {exc}")

        n_claims = sum(len(a.get("claims") or []) for a in valid)
        total_args += len(valid)
        total_claims += n_claims
        reasoning = usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0)
        print(f"[doc {doc['id']:>5}] {doc['actor_name']:<25} {elapsed:5.1f}s | {len(valid)} arg(en), {n_claims} claim(s) | reasoning_tokens={reasoning}")
        for a in valid:
            print(f"           - ({a['stance']}/{a['typology']}) {a['quote_text'][:140]!r}")

    print()
    print(f"Klaar: {len(docs)} docs, {total_errors} fout(en), {total_args} argumenten, {total_claims} claims.")
    if latencies:
        avg = sum(latencies) / len(latencies)
        print(f"Latency: gem={avg:.1f}s min={min(latencies):.1f}s max={max(latencies):.1f}s | geschat volle batch (3949 docs): {avg*3949/3600:.1f}u")


if __name__ == "__main__":
    main()
