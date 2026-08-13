"""
Stage 1 LLM-extractie: leest gesegmenteerde sprekerbeurten uit `documents`
en extraheert per beurt 0..n politieke argumenten (+ claims) via een lokaal
LLM (LM Studio, OpenAI-compatibele API).

Gebruik (eerst een kleine steekproef, NIET meteen de volle batch, zie
docs/handoff.md):
    uv run python -m pipeline.extract_arguments --topic stikstof --limit 15
    uv run python -m pipeline.extract_arguments --topic stikstof --limit 15 --model google/gemma-4-e4b
    uv run python -m pipeline.extract_arguments --topic stikstof --limit 15 --dry-run

Reeds verwerkte documenten worden overgeslagen via `documents.extraction_attempted_at`
(gezet zodra een document door de LLM is gestuurd, ook als dat 0 arguments
opleverde -- zelfde patroon als `arguments.tagged_at` in tag_arguments.py),
dus herhaald draaien is veilig en de volle batch kan onderbroken/herstart
worden zonder dubbel werk.

Documenten van vóór [verwerking].vanaf in data/politieke-periodes.toml
worden overgeslagen: we analyseren de huidige en de vorige Kamer. Die
documenten blijven gewoon in de database staan; met --vanaf kan een oudere
periode alsnog bewust verwerkt worden.
"""

import argparse
import hashlib
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

import requests

from pipeline.db import db
from pipeline.llm_log import record_llm_call
from pipeline.periodes import PeriodeIndex

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = (Path(__file__).parent / "prompts" / "extract_argument.md").read_text()
PROMPT_VERSION = hashlib.sha256(PROMPT_TEMPLATE.encode()).hexdigest()[:12]

BATCH_PROMPT_TEMPLATE = (Path(__file__).parent / "prompts" / "extract_argument_batch.md").read_text()
BATCH_PROMPT_VERSION = hashlib.sha256(BATCH_PROMPT_TEMPLATE.encode()).hexdigest()[:12]

VALID_STANCE = {"pro", "contra", "unclear", "ander_onderwerp"}
VALID_TYPOLOGY = {"factual", "moral", "economic", "legal", "other"}

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _build_prompt(topic_name, topic_description, actor_name, actor_party, content, debate_context="Tweede Kamer-debat"):
    """debate_context: het soort debat waar de sprekerbeurt uit komt (bv.
    "Tweede Kamer-debat" in productie). Default blijft de Kamerdebat-
    framing zodat alle bestaande aanroepen ongewijzigd werken; het
    evalharnas (pipeline/eval/benchmark_elecdebate.py) geeft hier een eigen
    waarde voor mee, want ELECDEBATE60TO16 is geen Kamerdebat."""
    actor_party_suffix = f" ({actor_party})" if actor_party else ""
    return PROMPT_TEMPLATE.format(
        topic=topic_name,
        topic_description=topic_description or topic_name,
        actor_name=actor_name,
        actor_party_suffix=actor_party_suffix,
        content=content,
        debate_context=debate_context,
    )


def _build_batch_prompt(topic_name, topic_description, docs):
    """docs: iterable van dicts/Rows met id, actor_name, actor_party, content."""
    blocks = []
    for doc in docs:
        actor_party_suffix = f" ({doc['actor_party']})" if doc["actor_party"] else ""
        blocks.append(
            f"--- document_id={doc['id']} — spreker: {doc['actor_name']}{actor_party_suffix} ---\n"
            f'"""\n{doc["content"]}\n"""'
        )
    return BATCH_PROMPT_TEMPLATE.format(
        topic=topic_name,
        topic_description=topic_description or topic_name,
        documents_block="\n\n".join(blocks),
    )


def _extract_json(raw_text):
    """Model moet kale JSON teruggeven, maar sommige modellen wikkelen het
    toch in een ```json-codeblok ondanks de instructie -- die strippen we
    hier voor de zekerheid."""
    fence_match = _JSON_FENCE_RE.search(raw_text)
    candidate = fence_match.group(1) if fence_match else raw_text.strip()
    return json.loads(candidate)


class LLMResponse(NamedTuple):
    content: str
    usage: dict
    finish_reason: str | None


def _extract_arguments(parsed):
    """Sommige modellen geven de argumentenlijst kaal terug in plaats van
    ingepakt in {"arguments": [...]}, zoals de prompt vraagt."""
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        return parsed.get("arguments", [])
    raise ValueError(f"onverwachte JSON-vorm: {type(parsed).__name__}")


def call_llm(base_url, model, prompt, reasoning_effort, timeout, max_tokens):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }
    if reasoning_effort:
        payload["reasoning_effort"] = reasoning_effort

    resp = requests.post(f"{base_url}/chat/completions", json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    choice = data["choices"][0]
    content = choice["message"].get("content", "")
    usage = data.get("usage", {})
    finish_reason = choice.get("finish_reason")
    return LLMResponse(content, usage, finish_reason)


def _validate_argument(arg):
    if not isinstance(arg, dict):
        raise ValueError(f"argument is geen object maar {type(arg).__name__}")
    if arg.get("stance") not in VALID_STANCE:
        raise ValueError(f"ongeldige stance: {arg.get('stance')!r}")
    if arg.get("typology") not in VALID_TYPOLOGY:
        raise ValueError(f"ongeldige typology: {arg.get('typology')!r}")
    if not arg.get("quote_text"):
        raise ValueError("quote_text ontbreekt of is leeg")
    # Zonder onderwerp is 'ander_onderwerp' net zo weinig zeggend als 'unclear' --
    # de hele reden voor dit label is dat je kunt zien wát het ruime net binnenhaalt.
    if arg["stance"] == "ander_onderwerp" and not arg.get("ander_onderwerp"):
        raise ValueError("stance 'ander_onderwerp' zonder ingevuld veld ander_onderwerp")


def insert_argument(conn, document_id, topic_id, actor_id, arg, model):
    conn.execute(
        """INSERT INTO arguments
           (document_id, topic_id, actor_id, stance, typology, quote_text, quote_context, extracted_at, prompt_version, extraction_model, ander_onderwerp)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            document_id,
            topic_id,
            actor_id,
            arg["stance"],
            arg["typology"],
            arg["quote_text"],
            arg.get("quote_context"),
            datetime.now(timezone.utc).isoformat(),
            PROMPT_VERSION,
            model,
            arg.get("ander_onderwerp"),
        ),
    )
    argument_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    for claim in arg.get("claims") or []:
        if not claim.get("claim_text"):
            continue
        conn.execute(
            "INSERT INTO claims (argument_id, claim_text, attributed_source_text) VALUES (?, ?, ?)",
            (argument_id, claim["claim_text"], claim.get("attributed_source_text")),
        )
    return argument_id


# De ingest matcht ruim (keyword ergens in de activiteit, niet alleen in de
# titel, zie ingest_tk.py:250-259) -- dat trekt debatten binnen die het
# keyword maar incidenteel noemen op een heel andere as (bv. arbeidsmigratie,
# faunabeheer/wolf, ruimtelijke ordening bij asiel). TOPIC_TITLE_KEYWORDS
# dwingt bij extractie af dat de titel zelf over het onderwerp gaat, om die
# ander_onderwerp-ruis te verminderen. Topics die hier niet in staan (abortus,
# stikstof) krijgen geen titelfilter -- hun ingest-net is al smal genoeg.
TOPIC_TITLE_KEYWORDS = {
    "asiel": ["asiel", "vreemdeling", "migratie", "immigratie"],
    # "energie" en "klimaat" zijn zelf al breed (kernenergie, energiedragers,
    # klimaatakkoord, ...) maar ook sterk polyseem in gewoon Nederlands
    # ("investeringsklimaat", "vestigingsklimaat", ministerienaam "Klimaat en
    # Groene Groei" in een heel ander debat) -- dat trok bv. "Instellingswet
    # Adviescollege toetsing regeldruk" en "Mestbeleid" binnen zonder dat
    # het debat zelf over energie/klimaat ging. Extra termen dekken
    # deelonderwerpen die zelf geen "energie"/"klimaat" in de titel dragen
    # (Gasmarkt en leveringszekerheid, Netcongestie, Mijnbouw/Groningen, CCS,
    # Fit for 55, RES en wind op zee, warmtetransitie).
    "energietransitie": [
        "energie", "klimaat", "waterstof", "saldering", "elektriciteit",
        "gas", "warmte", "duurzaam", "netcongestie", "mijnbouw", "ccs",
        "fit for 55", "res en wind",
    ],
}

# Procedurele activiteitsoorten bevatten geen inhoudelijke standpunten
# (agendabeheer resp. stemuitslagen), dus altijd uitsluiten, ongeacht topic.
EXCLUDED_ACTIVITEIT_SOORTEN = ["Regeling van werkzaamheden", "Stemmingen"]


def fetch_pending_documents(conn, topic_slug, limit, min_id=0, vanaf=None):
    """`vanaf` is een ISO-datum; oudere documenten blijven in de database maar
    komen hier niet uit. Default is [verwerking].vanaf uit
    data/politieke-periodes.toml -- we analyseren de huidige en de vorige
    Kamer, en dat scheelt aanzienlijk LLM-werk."""
    if vanaf is None:
        vanaf = PeriodeIndex().drempel

    conditions = [
        "t.slug = ?",
        "d.id >= ?",
        "d.published_at >= ?",
        "d.extraction_attempted_at IS NULL",
        "d.is_voorzitter_turn = 0",
        f"d.activiteit_soort NOT IN ({','.join('?' * len(EXCLUDED_ACTIVITEIT_SOORTEN))})",
    ]
    params = [topic_slug, min_id, vanaf, *EXCLUDED_ACTIVITEIT_SOORTEN]

    title_keywords = TOPIC_TITLE_KEYWORDS.get(topic_slug, [])
    if title_keywords:
        conditions.append("(" + " OR ".join("LOWER(d.title) LIKE ?" for _ in title_keywords) + ")")
        params.extend(f"%{keyword.lower()}%" for keyword in title_keywords)

    params.append(limit)
    return conn.execute(
        f"""SELECT d.id, d.content, d.actor_id, a.name AS actor_name, a.party AS actor_party
            FROM documents d
            JOIN actors a ON a.id = d.actor_id
            JOIN topics t ON t.id = d.topic_id
            WHERE {' AND '.join(conditions)}
            ORDER BY d.id
            LIMIT ?""",
        params,
    ).fetchall()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", required=True, help="topic-slug, bv. stikstof")
    parser.add_argument("--limit", type=int, default=15, help="max aantal documenten deze run (default 15)")
    parser.add_argument("--min-id", type=int, default=0, help="alleen documenten met id >= deze waarde")
    parser.add_argument("--model", default="qwen/qwen3.6-27b")
    parser.add_argument("--base-url", default="http://localhost:1234/v1")
    parser.add_argument(
        "--reasoning-effort",
        default="none",
        help="LM Studio reasoning_effort ('none' om denkstappen uit te schakelen; leeg om het veld weg te laten)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=4000,
        help="max_tokens per document (default 4000; 2000 kapte lange Kamerbeurten af)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=400.0,
        help="request-timeout in seconden per document (default 400: 4000 tokens tegen ~16 tok/s "
             "duurt ruim 250s, dus 120s was structureel te krap voor lange beurten)",
    )
    parser.add_argument(
        "--vanaf",
        default=None,
        help="ISO-datum; overschrijft [verwerking].vanaf uit data/politieke-periodes.toml "
             "(voor een bewuste backfill van een oudere periode)",
    )
    parser.add_argument("--dry-run", action="store_true", help="niets naar de database schrijven, alleen printen")
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

    documents = fetch_pending_documents(conn, args.topic, args.limit, args.min_id, args.vanaf)
    if not documents:
        logger.info("Geen openstaande documenten (al verwerkt, of geen documenten voor deze topic).")
        return

    logger.info(
        "Model: %s | reasoning_effort=%r | prompt_version=%s | %d documenten",
        args.model, args.reasoning_effort, PROMPT_VERSION, len(documents),
    )

    total_arguments = 0
    total_claims = 0
    total_errors = 0
    latencies = []

    for doc in documents:
        prompt = _build_prompt(topic_name, topic_description, doc["actor_name"], doc["actor_party"], doc["content"])
        start = time.monotonic()
        started_at = datetime.now(timezone.utc).isoformat()
        try:
            raw_content, usage, finish_reason = call_llm(
                args.base_url, args.model, prompt, args.reasoning_effort, args.timeout, args.max_tokens
            )
            if finish_reason == "length":
                # Afgekapt antwoord levert ongeldige JSON op; melden waaróm het misging,
                # anders lijkt het op een willekeurige parse-fout.
                raise ValueError(f"antwoord afgekapt op max_tokens={args.max_tokens} (verhoog --max-tokens)")
            parsed = _extract_json(raw_content)
            arguments = _extract_arguments(parsed)
        except Exception as exc:
            elapsed = time.monotonic() - start
            logger.error("[doc %5d] %-25s FOUT na %5.1fs: %s", doc["id"], doc["actor_name"], elapsed, exc)
            total_errors += 1
            if not args.dry_run:
                record_llm_call(
                    conn, stage="extraction", topic_id=topic_id, document_id=doc["id"], model=args.model,
                    prompt_version=PROMPT_VERSION, started_at=started_at, duration_s=elapsed,
                    status="error", error_message=str(exc),
                )
            continue
        elapsed = time.monotonic() - start
        latencies.append(elapsed)
        if not args.dry_run:
            record_llm_call(
                conn, stage="extraction", topic_id=topic_id, document_id=doc["id"], model=args.model,
                prompt_version=PROMPT_VERSION, started_at=started_at, duration_s=elapsed,
                response=raw_content, status="ok", usage=usage,
            )

        n_valid = 0
        n_claims = 0

        if not args.dry_run:
            with conn:
                for arg in arguments:
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
        else:
            for arg in arguments:
                try:
                    _validate_argument(arg)
                except ValueError as exc:
                    logger.warning("[doc %5d]   overgeslagen argument: %s", doc["id"], exc)
                    continue
                n_claims += len(arg.get("claims") or [])
                n_valid += 1

        reasoning_tokens = usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        logger.info(
            "[doc %5d] %-25s %5.1fs | %d argument(en), %d claim(s) | tokens: %d (reasoning: %d)",
            doc["id"], doc["actor_name"], elapsed, n_valid, n_claims, completion_tokens, reasoning_tokens,
        )
        total_arguments += n_valid
        total_claims += n_claims

    conn.close()

    logger.info("Klaar: %d documenten verwerkt, %d fout(en).", len(documents), total_errors)
    logger.info("Totaal: %d argumenten, %d claims.", total_arguments, total_claims)
    if latencies:
        avg = sum(latencies) / len(latencies)
        logger.info("Latency: gem=%.1fs min=%.1fs max=%.1fs", avg, min(latencies), max(latencies))
        est_full = avg * 3949 / 3600
        logger.info("Geschatte doorlooptijd volle batch (3949 docs) tegen dit gemiddelde: %.1f uur", est_full)
    if args.dry_run:
        logger.info("(--dry-run: niets weggeschreven naar de database)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
