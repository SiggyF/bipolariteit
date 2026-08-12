"""
Backfill van de labelgroep "Stijlmiddelen" (issue #67) op argumenten die al
vóór deze labelgroep bestond volledig getagd waren (`tagged_at IS NOT NULL`).
Draait via agy (Docker/Gemini), met een SMALLE catalogus die alleen de 5
Stijlmiddelen-tags bevat -- geen volledige hertagging, bestaande tags blijven
onaangeroerd (`insert_llm_tags` is additief, INSERT OR IGNORE).

Batcht meerdere argumenten (--batch-size, default 50) in één prompt/call --
de catalogus-tekst hoeft dan maar één keer per batch verstuurd te worden
i.p.v. per argument, naar het patroon van
pipeline/prompts/extract_argument_batch.md (dat bestaat al voor extractie,
dit is de tag-variant). Geretourneerde argument_id's worden gevalideerd
tegen de aangeleverde batch -- hallucinaties worden overgeslagen, niet
vertrouwd (zelfde patroon als prompts/redactie_bias_check.md).

Idempotent via `arguments.stijl_tagged_at`: gezet na elke poging, ook als
dat 0 stijltags opleverde (0 is een geldige uitkomst voor een "kies nul of
meer"-labelgroep, dus "geen Stijl-tag aanwezig" alleen is geen betrouwbaar
signaal dat een argument nog gecontroleerd moet worden).

Gebruik (eerst een kleine steekproef, NIET meteen de volle batch):
    PYTHONPATH=. uv run python scripts/agy_run_stijlmiddelen_backfill.py --topic stikstof --limit 20
"""

import argparse
import json
import logging
import time
from datetime import datetime, timezone

from pipeline.db import db
from pipeline.tag_arguments import (
    _extract_json,
    _validate_tags,
    insert_llm_tags,
    load_all_active_tags_by_labelgroep,
    load_valid_tags,
)
from scripts.agy_run_tagging_batch import run_agy

logger = logging.getLogger(__name__)

STIJLMIDDELEN_LABELGROEP = "Stijlmiddelen"
STIJLMIDDELEN_FIELD = "stijlmiddelen"

BATCH_PROMPT_TEMPLATE = """Je labelt meerdere, al afzonderlijk geëxtraheerde politieke argumenten over "{topic}" op stijlmiddelen, los van elkaar. Elk argument hieronder is een apart, zelfstandig fragment met een eigen `argument_id` -- vermeng nooit citaten tussen argumenten.

Belangrijk:
- Jij beoordeelt nooit of het argument klopt, terecht is, of overtuigend is.
- Ken alleen tags toe die je uit onderstaande lijst kiest, letterlijk overgenomen (exacte sleutel, geen parafrase, geen nieuwe tags verzinnen).
- Een lege lijst mag als geen enkel stijlmiddel van toepassing is.
- Elke toegekende tag krijgt een `reden`: één korte zin die uitlegt waarom DEZE tag op DIT specifieke argument van toepassing is.

Taxonomie:
{tag_catalogue}

De argumenten:

{arguments_block}

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok eromheen. Geef voor élk argument hierboven precies één object terug, ook als de lijst leeg is, in dezelfde volgorde als de argument_ids hierboven. Formaat:

```
{{"arguments": [
  {{
    "argument_id": <id>,
    "stijlmiddelen": [
      {{"sleutel": "<TAG_SLEUTEL>", "reden": "<korte argument-specifieke onderbouwing>"}}
    ]
  }}
]}}
```
"""


def build_stijlmiddelen_catalogue(conn):
    grouped = load_all_active_tags_by_labelgroep(conn)
    info = grouped[STIJLMIDDELEN_LABELGROEP]
    lines = [f"### {STIJLMIDDELEN_LABELGROEP} ({info['beschrijving']}) -- kies nul of meer"]
    for sleutel, beschrijving in info["tags"]:
        lines.append(f"- {sleutel}: {beschrijving}")
    return "\n".join(lines).strip()


def _build_batch_prompt(topic_name, tag_catalogue, batch):
    blocks = []
    for arg in batch:
        blocks.append(
            f'--- argument_id={arg["id"]} ---\n"""\n{arg["quote_text"]}\n"""'
        )
    return BATCH_PROMPT_TEMPLATE.format(
        topic=topic_name, tag_catalogue=tag_catalogue, arguments_block="\n\n".join(blocks),
    )


def fetch_backfill_candidates(conn, topic_id, limit, min_id=0):
    return conn.execute(
        """SELECT ar.id, ar.quote_text
           FROM arguments ar
           WHERE ar.topic_id = ? AND ar.id >= ?
             AND ar.tagged_at IS NOT NULL
             AND ar.stijl_tagged_at IS NULL
           ORDER BY ar.id
           LIMIT ?""",
        (topic_id, min_id, limit),
    ).fetchall()


def _chunk(items, size):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", default="stikstof")
    parser.add_argument("--limit", type=int, default=20, help="max aantal kandidaten deze run (default 20)")
    parser.add_argument("--batch-size", type=int, default=50, help="argumenten per LLM-call (default 50)")
    parser.add_argument("--min-id", type=int, default=0)
    parser.add_argument("--model", default="gemini-3.6-flash-low")
    args = parser.parse_args()

    conn = db.connect()
    topic_row = conn.execute("SELECT id, name FROM topics WHERE slug = ?", (args.topic,)).fetchone()
    topic_id, topic_name = topic_row["id"], topic_row["name"]

    valid_tags = {STIJLMIDDELEN_FIELD: load_valid_tags(conn)[STIJLMIDDELEN_FIELD]}
    tag_catalogue = build_stijlmiddelen_catalogue(conn)

    arguments = fetch_backfill_candidates(conn, topic_id, args.limit, args.min_id)
    if not arguments:
        logger.info("Geen kandidaten (alles al gecontroleerd, of geen getagde argumenten voor deze topic).")
        return

    batches = list(_chunk(arguments, args.batch_size))
    logger.info("Model: %s | %d argumenten in %d batch(es) van max %d", args.model, len(arguments), len(batches), args.batch_size)

    total_tags = total_errors = total_hallucinated = 0
    latencies = []

    for batch in batches:
        by_id = {arg["id"]: arg for arg in batch}
        prompt = _build_batch_prompt(topic_name, tag_catalogue, batch)
        start = time.monotonic()
        try:
            stdout, stderr = run_agy(prompt, args.model)
            if not stdout:
                raise ValueError(f"leeg antwoord (stderr: {stderr[:200]})")
            parsed = _extract_json(stdout)
            results = parsed.get("arguments", []) if isinstance(parsed, dict) else parsed
        except Exception as exc:
            elapsed = time.monotonic() - start
            logger.error("[batch %d argumenten] FOUT na %5.1fs: %s", len(batch), elapsed, exc)
            total_errors += len(batch)
            continue
        elapsed = time.monotonic() - start
        latencies.append(elapsed)

        seen_ids = set()
        for item in results:
            argument_id = item.get("argument_id")
            if argument_id not in by_id:
                total_hallucinated += 1
                logger.warning("  genegeerd: argument_id %r zat niet in de aangeleverde batch", argument_id)
                continue
            seen_ids.add(argument_id)
            accepted = _validate_tags({STIJLMIDDELEN_FIELD: item.get(STIJLMIDDELEN_FIELD, [])}, valid_tags)
            with conn:
                insert_llm_tags(conn, argument_id, accepted)
                conn.execute(
                    "UPDATE arguments SET stijl_tagged_at = ? WHERE id = ?",
                    (datetime.now(timezone.utc).isoformat(), argument_id),
                )
            total_tags += len(accepted)
            logger.info("[arg %5d] %5.1fs (batch) | stijl: %s", argument_id, elapsed, [s for s, _ in accepted])

        missing = set(by_id) - seen_ids
        if missing:
            logger.warning("  %d argument(en) niet teruggekomen in het antwoord, niet gemarkeerd: %s", len(missing), sorted(missing))

    conn.close()
    logger.info(
        "Klaar: %d argumenten, %d fout(en), %d hallucinatie(s) genegeerd, %d stijltags toegekend.",
        len(arguments), total_errors, total_hallucinated, total_tags,
    )
    if latencies:
        avg = sum(latencies) / len(latencies)
        logger.info("Latency per batch: gem=%.1fs min=%.1fs max=%.1fs", avg, min(latencies), max(latencies))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
