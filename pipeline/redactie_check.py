"""
Stage 2 redactie-check: draait NA extract_arguments.py. Twee losse dingen per
document, geen fact-check op geen van beide:

1. Balans-check (deterministisch, geen LLM): na het bijtellen van dit document
   wordt de corpus-brede pro/contra-verhouding van het topic opnieuw berekend.
   Dit is bewust NIET "is dit ene document eenzijdig" -- elk document is hier
   één sprekersbeurt (één Kamerlid), dus dat zou vrijwel altijd "eenzijdig"
   zijn en niets onderscheidends zeggen. In plaats daarvan meet dit of het
   groeiende corpus als geheel in balans blijft; elk document is het meetpunt
   waarop die corpus-brede snapshot wordt vastgelegd.
2. Opposition-linking (LLM): kijkt of één van de nieuwe argumenten van dit
   document een bestaand argument met het tegenovergestelde standpunt direct
   weerlegt of er thematisch mee te maken heeft. Levert `argument_oppositions`-
   rijen op. Nooit een oordeel over wie gelijk heeft, alleen dat ze op hetzelfde
   punt inhaken.

Reeds verwerkte documenten (een bestaande `redactie_reviews`-rij voor dat
document) worden overgeslagen, dus herhaald draaien is veilig.

Gebruik:
    uv run python -m pipeline.redactie_check --topic stikstof --limit 15
    uv run python -m pipeline.redactie_check --topic stikstof --limit 15 --dry-run
"""

import argparse
import hashlib
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from pipeline.db import db
from pipeline.llm_log import record_llm_call

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = (Path(__file__).parent / "prompts" / "redactie_bias_check.md").read_text()
PROMPT_VERSION = hashlib.sha256(PROMPT_TEMPLATE.encode()).hexdigest()[:12]

VALID_RELATION_TYPES = {"direct_rebuttal", "thematic"}
MAX_CANDIDATES_PER_STANCE = 10

# Aandeel van de minderheidskant (min(pro,contra) / (pro+contra)) in het hele
# topic-corpus op het moment van dit document. Drempels bewust ruim: dit is
# een signaal om te herbekijken, geen harde uitsluiting.
BALANCED_MIN_MINORITY_PCT = 0.35
IMBALANCED_MIN_MINORITY_PCT = 0.15

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)
_OPPOSITE_STANCE = {"pro": "contra", "contra": "pro"}


def _extract_json(raw_text):
    fence_match = _JSON_FENCE_RE.search(raw_text)
    candidate = fence_match.group(1) if fence_match else raw_text.strip()
    return json.loads(candidate)


def call_llm(base_url, model, prompt, reasoning_effort, timeout):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 1000,
    }
    if reasoning_effort:
        payload["reasoning_effort"] = reasoning_effort

    resp = requests.post(f"{base_url}/chat/completions", json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    message = data["choices"][0]["message"]
    usage = data.get("usage", {})
    return message.get("content", ""), usage


def compute_balance(conn, topic_id, document_id):
    """Lopende pro/contra-ratio van dit topic, opgebouwd t/m dit document
    (document_id-volgorde, dezelfde volgorde als extract_arguments.py verwerkt).
    Bewust begrensd tot documenten <= document_id i.p.v. de hele, nog groeiende
    corpus te tellen -- anders levert elke run een ander getal op voor dezelfde
    rij (een LLM-batch die ondertussen doorloopt verandert de latere documenten,
    niet de vroegere), en is dit geen "deterministische snapshot per document"
    meer maar een moment-opname van de hele run."""
    row = conn.execute(
        """SELECT
               SUM(CASE WHEN ar.stance = 'pro' THEN 1 ELSE 0 END) AS pro,
               SUM(CASE WHEN ar.stance = 'contra' THEN 1 ELSE 0 END) AS contra
           FROM arguments ar
           WHERE ar.topic_id = ? AND ar.document_id <= ?""",
        (topic_id, document_id),
    ).fetchone()
    pro, contra = row["pro"] or 0, row["contra"] or 0
    total = pro + contra
    if total == 0:
        return "flag", f"Nog geen pro/contra-argumenten in het corpus (pro={pro}, contra={contra})."

    minority_pct = min(pro, contra) / total
    if minority_pct >= BALANCED_MIN_MINORITY_PCT:
        status = "balanced"
    elif minority_pct >= IMBALANCED_MIN_MINORITY_PCT:
        status = "imbalanced"
    else:
        status = "flag"
    notes = f"Corpus-breed: {pro} pro / {contra} contra (minderheidsaandeel {minority_pct:.0%})."
    return status, notes


def fetch_opposition_candidates(conn, topic_id, stance, exclude_document_id, limit):
    # Willekeurige steekproef i.p.v. "meest recente N": anders wordt elk nieuw
    # document tegen dezelfde handvol recente tegenargumenten gelegd, wat een
    # paar argumenten kunstmatig tot opposition-hub maakt (sample-artefact,
    # geen inhoudelijk patroon).
    return conn.execute(
        """SELECT ar.id, ar.quote_text, act.name AS actor_name, act.party AS actor_party
           FROM arguments ar
           JOIN actors act ON act.id = ar.actor_id
           WHERE ar.topic_id = ? AND ar.stance = ? AND ar.document_id != ?
           ORDER BY RANDOM()
           LIMIT ?""",
        (topic_id, stance, exclude_document_id, limit),
    ).fetchall()


def _format_arguments_block(rows):
    lines = []
    for row in rows:
        keys = row.keys()
        actor_name = row["actor_name"] if "actor_name" in keys else None
        actor_party = row["actor_party"] if "actor_party" in keys else None
        actor_suffix = f" ({actor_party})" if actor_party else ""
        actor_bit = f" -- {actor_name}{actor_suffix}" if actor_name else ""
        lines.append(f'- [id {row["id"]}] "{row["quote_text"]}"{actor_bit}')
    return "\n".join(lines) if lines else "(geen)"


def find_oppositions(
    conn, topic_id, document_id, dry_run,
    base_url, model, reasoning_effort, timeout, topic_name, actor_name, actor_party, new_args, candidates_by_id,
):
    if not candidates_by_id:
        return [], {}

    actor_party_suffix = f" ({actor_party})" if actor_party else ""
    prompt = PROMPT_TEMPLATE.format(
        topic=topic_name,
        actor_name=actor_name,
        actor_party_suffix=actor_party_suffix,
        new_arguments_block=_format_arguments_block(new_args),
        candidates_block=_format_arguments_block(list(candidates_by_id.values())),
    )
    start = time.monotonic()
    started_at = datetime.now(timezone.utc).isoformat()
    raw_content, usage = call_llm(base_url, model, prompt, reasoning_effort, timeout)
    parsed = _extract_json(raw_content)

    valid_new_ids = {arg["id"] for arg in new_args}
    accepted = []
    for item in parsed.get("oppositions", []):
        new_id = item.get("new_argument_id")
        existing_id = item.get("existing_argument_id")
        relation_type = item.get("relation_type")
        if new_id not in valid_new_ids:
            logger.warning("    overgeslagen: onbekend new_argument_id %r", new_id)
            continue
        if existing_id not in candidates_by_id:
            logger.warning("    overgeslagen: existing_argument_id %r zat niet in de aangeleverde kandidaten", existing_id)
            continue
        if relation_type not in VALID_RELATION_TYPES:
            logger.warning("    overgeslagen: ongeldig relation_type %r", relation_type)
            continue
        accepted.append((new_id, existing_id, relation_type, item.get("confidence")))

    if not dry_run:
        record_llm_call(
            conn, stage="redactie", topic_id=topic_id, document_id=document_id, model=model,
            prompt_version=PROMPT_VERSION, started_at=started_at, duration_s=time.monotonic() - start,
            prompt_vars={"candidate_argument_ids": list(candidates_by_id)},
            response=raw_content, status="ok", usage=usage,
        )
    return accepted, usage


def insert_oppositions(conn, oppositions):
    now_pairs = []
    for new_id, existing_id, relation_type, confidence in oppositions:
        conn.execute(
            """INSERT INTO argument_oppositions (argument_a_id, argument_b_id, relation_type, created_by, confidence)
               VALUES (?, ?, ?, 'llm', ?)""",
            (new_id, existing_id, relation_type, confidence),
        )
        now_pairs.append((new_id, existing_id, relation_type))
    return now_pairs


def fetch_pending_documents(conn, topic_id, limit, min_id=0):
    return conn.execute(
        """SELECT DISTINCT d.id, d.actor_id, act.name AS actor_name, act.party AS actor_party
           FROM documents d
           JOIN arguments ar ON ar.document_id = d.id
           JOIN actors act ON act.id = d.actor_id
           LEFT JOIN redactie_reviews rr ON rr.document_id = d.id
           WHERE d.topic_id = ?
             AND d.id >= ?
             AND d.extraction_attempted_at IS NOT NULL
             AND rr.id IS NULL
           ORDER BY d.id
           LIMIT ?""",
        (topic_id, min_id, limit),
    ).fetchall()


def fetch_document_arguments(conn, document_id):
    return conn.execute(
        "SELECT id, stance, quote_text FROM arguments WHERE document_id = ? ORDER BY id",
        (document_id,),
    ).fetchall()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", required=True, help="topic-slug, bv. stikstof")
    parser.add_argument("--limit", type=int, default=15, help="max aantal documenten deze run (default 15)")
    parser.add_argument("--min-id", type=int, default=0, help="alleen documenten met id >= deze waarde")
    parser.add_argument("--model", default="qwen/qwen3.6-27b")
    parser.add_argument("--base-url", default="http://localhost:1234/v1")
    parser.add_argument("--reasoning-effort", default="none")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--dry-run", action="store_true", help="niets naar de database schrijven, alleen printen")
    args = parser.parse_args()

    conn = db.connect()
    topic_row = conn.execute("SELECT id, name FROM topics WHERE slug = ?", (args.topic,)).fetchone()
    if topic_row is None:
        raise SystemExit(f"onbekende topic-slug: {args.topic}")
    topic_id, topic_name = topic_row["id"], topic_row["name"]

    documents = fetch_pending_documents(conn, topic_id, args.limit, args.min_id)
    if not documents:
        logger.info("Geen openstaande documenten (al gecontroleerd, of nog geen documenten met arguments voor deze topic).")
        return

    logger.info(
        "Model: %s | reasoning_effort=%r | prompt_version=%s | %d documenten",
        args.model, args.reasoning_effort, PROMPT_VERSION, len(documents),
    )

    total_oppositions = 0
    total_errors = 0
    latencies = []

    for doc in documents:
        new_args = fetch_document_arguments(conn, doc["id"])
        pass_status, notes = compute_balance(conn, topic_id, doc["id"])

        stances_present = {arg["stance"] for arg in new_args if arg["stance"] in ("pro", "contra")}
        candidates_by_id = {}
        for stance in stances_present:
            for row in fetch_opposition_candidates(conn, topic_id, _OPPOSITE_STANCE[stance], doc["id"], MAX_CANDIDATES_PER_STANCE):
                candidates_by_id[row["id"]] = row

        start = time.monotonic()
        started_at = datetime.now(timezone.utc).isoformat()
        try:
            oppositions, usage = find_oppositions(
                conn, topic_id, doc["id"], args.dry_run,
                args.base_url, args.model, args.reasoning_effort, args.timeout,
                topic_name, doc["actor_name"], doc["actor_party"],
                [dict(a) for a in new_args if a["stance"] in ("pro", "contra")],
                candidates_by_id,
            )
        except Exception as exc:
            elapsed = time.monotonic() - start
            logger.error("[doc %5d] %-25s FOUT bij opposition-check na %5.1fs: %s", doc["id"], doc["actor_name"], elapsed, exc)
            total_errors += 1
            if not args.dry_run and candidates_by_id:
                record_llm_call(
                    conn, stage="redactie", topic_id=topic_id, document_id=doc["id"], model=args.model,
                    prompt_version=PROMPT_VERSION, started_at=started_at, duration_s=elapsed,
                    prompt_vars={"candidate_argument_ids": list(candidates_by_id)},
                    status="error", error_message=str(exc),
                )
            # Document blijft pending (geen redactie_reviews-rij) zodat een
            # volgende run het opnieuw probeert -- zelfde patroon als
            # extract_arguments.py bij een mislukte LLM-call.
            continue
        elapsed = time.monotonic() - start
        if oppositions or candidates_by_id:
            latencies.append(elapsed)

        if not args.dry_run:
            inserted = insert_oppositions(conn, oppositions)
            conn.execute(
                """INSERT INTO redactie_reviews (document_id, pass_status, notes, reviewer_model, created_at, prompt_version)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (doc["id"], pass_status, notes, args.model, datetime.now(timezone.utc).isoformat(), PROMPT_VERSION),
            )
            conn.commit()
        else:
            inserted = [(n, e, r) for n, e, r, _c in oppositions]

        total_oppositions += len(inserted)
        logger.info(
            "[doc %5d] %-25s %5.1fs | balans=%s | %d kandidaten | %d opposition(s)",
            doc["id"], doc["actor_name"], elapsed, pass_status, len(candidates_by_id), len(inserted),
        )

    conn.close()

    logger.info("Klaar: %d documenten verwerkt, %d fout(en).", len(documents), total_errors)
    logger.info("Totaal: %d oppositions.", total_oppositions)
    if latencies:
        avg = sum(latencies) / len(latencies)
        logger.info("Latency: gem=%.1fs min=%.1fs max=%.1fs", avg, min(latencies), max(latencies))
    if args.dry_run:
        logger.info("(--dry-run: niets weggeschreven naar de database)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
