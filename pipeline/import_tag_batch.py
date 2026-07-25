"""
Verwerkt het geplakte antwoord van een externe chat-LLM (bv. Gemini) op een
batch-document uit pipeline/prepare_tag_batch.py: valideert per argument
tegen de huidige (actieve) tags-tabel en schrijft geaccepteerde tags weg als
created_by='llm', net als pipeline/tag_arguments.py zou doen.

Gebruik:
    uv run python -m pipeline.import_tag_batch --topic stikstof --input /pad/naar/antwoord.txt
    uv run python -m pipeline.import_tag_batch --topic stikstof --input /pad/naar/antwoord.txt --dry-run
"""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from pipeline.db import db
from pipeline.tag_arguments import _validate_tags, load_valid_tags

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _extract_json(raw_text):
    fence_match = _JSON_FENCE_RE.search(raw_text)
    candidate = fence_match.group(1) if fence_match else raw_text.strip()
    return json.loads(candidate)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", required=True, help="topic-slug, bv. stikstof")
    parser.add_argument("--input", required=True, help="pad naar het geplakte Gemini-antwoord")
    parser.add_argument("--dry-run", action="store_true", help="niets naar de database schrijven, alleen printen")
    args = parser.parse_args()

    raw_text = Path(args.input).read_text()
    parsed = _extract_json(raw_text)

    conn = db.connect()
    valid_tags = load_valid_tags(conn)

    total_accepted = 0
    total_errors = 0
    now = datetime.now(timezone.utc).isoformat()

    for arg_id_str, tag_fields in parsed.items():
        try:
            argument_id = int(arg_id_str)
        except ValueError:
            print(f"overgeslagen: ongeldig argument-id in antwoord: {arg_id_str!r}")
            total_errors += 1
            continue

        row = conn.execute("SELECT id FROM arguments WHERE id = ?", (argument_id,)).fetchone()
        if row is None:
            print(f"[arg {argument_id:>5}] overgeslagen: bestaat niet in deze database")
            total_errors += 1
            continue

        accepted = _validate_tags(tag_fields, valid_tags)
        print(f"[arg {argument_id:>5}] llm: {[sleutel for sleutel, _reden in accepted]}")
        total_accepted += len(accepted)

        if not args.dry_run:
            for sleutel, reden in accepted:
                conn.execute(
                    """INSERT OR IGNORE INTO argument_tags (argument_id, tag_sleutel, created_by, confidence, reden, assigned_at)
                       VALUES (?, ?, 'llm', NULL, ?, ?)""",
                    (argument_id, sleutel, reden, now),
                )
            conn.execute("UPDATE arguments SET tagged_at = ? WHERE id = ?", (now, argument_id))

    if not args.dry_run:
        conn.commit()
    conn.close()

    print()
    print(f"Klaar: {len(parsed)} argumenten verwerkt, {total_errors} fout(en), {total_accepted} tags geaccepteerd.")
    if args.dry_run:
        print("(--dry-run: niets weggeschreven naar de database)")


if __name__ == "__main__":
    main()
