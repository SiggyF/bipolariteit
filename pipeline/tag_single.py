"""
Gerichte hertag-pass: evalueert één specifieke tag (config/tags.toml) tegen
reeds getagde `arguments`-rijen, zonder de hele taxonomie opnieuw te
doorlopen (in tegenstelling tot tag_arguments.py, dat alleen ongetagde
argumenten pakt, en anders dan scripts/agy_run_stijlmiddelen_backfill.py,
dat een hele labelgroep in één keer afvinkt via `stijl_tagged_at` -- een
sleutel die later aan een al afgevinkte labelgroep wordt toegevoegd komt
daarmee nooit meer aan de beurt).

Bedoeld voor een taxonomie-uitbreiding ná een volledige tag-pass (bv. issue
#321 Stijl-Godwin, issue #262 Debatzet-Cirkelredenering): i.p.v. alle
argumenten opnieuw door de volle taggingprompt te halen, één gerichte vraag
per argument ("is deze ene tag hier van toepassing?"). Kandidaatselectie is
`NOT EXISTS`-gebaseerd tegen `llm_calls` (is dit argument al succesvol door
déze exacte prompt_version voor déze tag gehaald?), niet tegen
`argument_tags` -- dat laatste krijgt alleen een rij bij "van_toepassing:
true", dus zou een "nee"-uitkomst bij elke herrun opnieuw bevragen.
`prompt_version` is een hash van het template + de tag-specifieke few-shot-
voorbeelden + de taxonomie-tekst (zie compute_prompt_version()): een latere
aanscherping van de prompt (zoals de Stijl-Godwin-precisiefix in #321)
krijgt vanzelf een nieuwe versie en blokkeert dus geen herbeoordeling.
Generiek herbruikbaar voor elke nieuw toegevoegde tag, geen aparte
markerkolom per labelgroep nodig.

Schrijft uitsluitend rijen voor de opgegeven tag_sleutel weg (via
tag_arguments.insert_llm_tags, additief -- nooit bestaande argument_tags
aanraken of arguments.tagged_at wijzigen).

Gebruik:
    uv run python -m pipeline.tag_single --tag Stijl-Godwin --topic stikstof \
        --ids-file kandidaten.txt --base-url https://router.huggingface.co/v1 \
        --model Qwen/Qwen3.8-27B:ovhcloud --api-key $HUGGINGFACE_INFERENCE_TOKEN --parallel

    uv run python -m pipeline.tag_single --tag Debatzet-Cirkelredenering --all-topics \
        --base-url https://router.huggingface.co/v1 --model Qwen/Qwen3.8-27B:ovhcloud \
        --api-key $HUGGINGFACE_INFERENCE_TOKEN --parallel --limit 500
"""

import argparse
import hashlib
import json
import logging
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from dask.distributed import as_completed

from pipeline.dask_client import make_client
from pipeline.db import db
from pipeline.hf_pricing import get_baseline_pricing, price_still_matches
from pipeline.llm_client import call_llm
from pipeline.llm_log import record_llm_call
from pipeline.tag_arguments import (
    QF_AMBIGU,
    QF_GEEN_FRAGMENT,
    QF_GELDIG,
    QF_GELDIG_MEERDELIG,
    QF_NIET_GEVONDEN,
    _extract_json,
    classify_quote_fragment,
    insert_llm_tags,
)

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = (Path(__file__).parent / "prompts" / "tag_single.md").read_text()

# Optionele few-shot-voorbeelden per tag_sleutel, puur om een klein/gratis
# model over de drempel te trekken bij patronen die subtieler zijn dan de
# generieke tag-beschrijving alleen duidelijk maakt (zie issue #262: het
# model miste zonder voorbeelden een impliciete cirkel via een moreel
# zelfoordeel, terwijl het letterlijke herhaling ("X is goed want X is
# goed") wel al zonder voorbeelden herkende). Geen taxonomie-data (hoort dus
# niet in config/tags.toml) -- puur promptvoorbeelden voor dit script.
FEWSHOT_EXAMPLES = {
    "Debatzet-Cirkelredenering": [
        (
            "Ik verkondig hier waarheden. Als ik hier sta te liegen, zou het niet goed zijn.",
            {
                "van_toepassing": True,
                "reden": "De spreker leidt de waarheid van de eigen bewering af uit de eigen "
                         "deugdzaamheid ('ik lieg niet') in plaats van uit bewijs -- een impliciete "
                         "cirkel: het enige 'bewijs' voor de waarheid is de eigen claim niet te liegen.",
                "quote_fragment": None,
            },
        ),
        (
            "Dit beleid is goed, want het is goed beleid.",
            {
                "van_toepassing": True,
                "reden": "De premisse herhaalt letterlijk de conclusie zonder onafhankelijk bewijs.",
                "quote_fragment": None,
            },
        ),
        (
            "Ik sta hier overtuigd te vertellen dat dit pakket voldoende is, want de cijfers "
            "van het RIVM laten dat zien.",
            {
                "van_toepassing": False,
                "reden": None,
                "quote_fragment": None,
            },
        ),
    ],
    # Zie issue #321: een eerste ronde tegen 22 regex-kandidaten (WOII/nazi-
    # vocabulaire) leverde 18x "ja" op, maar bij nalezing bleek de meerderheid
    # géén Godwin (retorische vergelijking) te zijn -- het model triggerde ook
    # op (a) een neutrale feitelijke/historische verwijzing zonder vergelijking
    # ("de verdragen die vlak na de Tweede Wereldoorlog zijn gesloten") en (b)
    # een letterlijke beschrijving van echte actuele nazi-symboliek/-geweld
    # ("Heil Hitler"-roepende nazi's bij een rel) -- geen van beide is een
    # vergelijking, dus geen Stijl-Godwin. Voorbeelden hieronder zijn de
    # daadwerkelijke fout-positieven uit die ronde (herschreven tot de kern),
    # plus het enige echte treffer uit diezelfde ronde.
    "Stijl-Godwin": [
        (
            "De realiteit is dat de verdragen die vlak na de Tweede Wereldoorlog zijn gesloten, "
            "nooit bedoeld zijn geweest om iedereen het recht te geven zich in een Europees land "
            "naar keuze te vestigen.",
            {
                "van_toepassing": False,
                "reden": None,
                "quote_fragment": None,
            },
        ),
        (
            "We zien demonstraties die uitmondden in gewelddadige rellen met \"Heil Hitler\"-roepende "
            "nazi's, een gemeentehuis dat vernield werd, en een explosief dat afging bij een "
            "opvanglocatie.",
            {
                "van_toepassing": False,
                "reden": None,
                "quote_fragment": None,
            },
        ),
        (
            "Hoe zou Nederland eruit hebben gezien als wij in de Tweede Wereldoorlog Groningen en "
            "Drenthe hadden moeten opgeven, Duits als officiële taal hadden moeten accepteren en in "
            "onze Grondwet hadden moeten vastleggen nooit meer onze eigen bondgenoten te mogen "
            "kiezen? Die vergelijking dringt zich op als ik denk aan de 3,5 miljoen mensen in de "
            "Donbas.",
            {
                "van_toepassing": True,
                "reden": "De spreker trekt expliciet een vergelijking tussen het huidige Oekraïne-"
                         "conflict en het WOII-scenario van een bezet, opgedeeld Nederland.",
                "quote_fragment": "hoe zou Nederland eruit hebben gezien als wij in de Tweede "
                                   "Wereldoorlog Groningen en Drenthe hadden moeten opgeven",
            },
        ),
    ],
}


def _build_voorbeelden_block(tag_sleutel):
    examples = FEWSHOT_EXAMPLES.get(tag_sleutel)
    if not examples:
        return ""
    lines = ["\nVoorbeelden (van dit exacte patroon, niet van deze specifieke topic):"]
    for quote, antwoord in examples:
        lines.append(f'- Quote: "{quote}"')
        lines.append(f"  Antwoord: {json.dumps(antwoord, ensure_ascii=False)}")
    return "\n".join(lines) + "\n"


def load_tag(conn, sleutel):
    row = conn.execute(
        """SELECT t.sleutel, t.beschrijving AS tag_beschrijving, l.naam AS labelgroep,
                  l.beschrijving AS labelgroep_beschrijving
           FROM tags t JOIN labelgroepen l ON l.naam = t.labelgroep
           WHERE t.sleutel = ? AND t.active = 1 AND l.active = 1""",
        (sleutel,),
    ).fetchone()
    if row is None:
        raise SystemExit(f"onbekende of inactieve tag: {sleutel!r} (zie config/tags.toml)")
    return row


def compute_prompt_version(tag_row):
    """Hash van alles wat de prompt-inhoud voor déze tag bepaalt: het gedeelde
    template, de tag-specifieke few-shot-voorbeelden (FEWSHOT_EXAMPLES) en de
    taxonomie-tekst zelf (tag_beschrijving/labelgroep_beschrijving) -- een
    latere aanscherping van één van die drie (zie issue #321: de eerste
    Stijl-Godwin-poging kreeg alsnog few-shots na een precisieprobleem) moet
    een nieuwe versie opleveren, anders blokkeert het skip-mechanisme in
    fetch_candidates() een broodnodige herbeoordeling stilzwijgend."""
    payload = json.dumps(
        {
            "template": PROMPT_TEMPLATE,
            "voorbeelden": FEWSHOT_EXAMPLES.get(tag_row["sleutel"], []),
            "tag_beschrijving": tag_row["tag_beschrijving"],
            "labelgroep_beschrijving": tag_row["labelgroep_beschrijving"],
        },
        sort_keys=True, default=str,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:12]


def fetch_candidates(conn, tag_sleutel, prompt_version, topic_ids, ids=None, limit=None):
    """Reeds getagde argumenten (tagged_at IS NOT NULL) die nog niet
    succesvol door déze exacte prompt_version voor déze tag zijn gehaald --
    idempotent, een herrun pakt vanzelf alleen de rest. Bewust gebaseerd op
    llm_calls (elke poging wordt daar gelogd, ook een "nee"-uitkomst),
    NIET op argument_tags: dat laatste krijgt alleen een rij bij "ja", dus
    een "nee"-resultaat zou anders bij elke herrun opnieuw (en op precies
    dezelfde ongewijzigde prompt) aan het LLM gevraagd worden."""
    topic_placeholders = ",".join("?" for _ in topic_ids)
    params = [*topic_ids, prompt_version]
    id_clause = ""
    if ids is not None:
        id_placeholders = ",".join("?" for _ in ids)
        id_clause = f" AND ar.id IN ({id_placeholders})"
        params.extend(ids)
    limit_clause = ""
    if limit is not None:
        limit_clause = " LIMIT ?"
        params.append(limit)
    query = f"""SELECT ar.id, ar.document_id, ar.topic_id, ar.actor_id, ar.stance, ar.typology,
                      ar.quote_text, ar.quote_context,
                      act.name AS actor_name, act.party AS actor_party, tp.name AS topic_name
               FROM arguments ar
               JOIN actors act ON act.id = ar.actor_id
               JOIN topics tp ON tp.id = ar.topic_id
               WHERE ar.tagged_at IS NOT NULL
                 AND ar.topic_id IN ({topic_placeholders})
                 AND NOT EXISTS (
                     SELECT 1 FROM llm_calls lc
                     WHERE lc.argument_id = ar.id AND lc.stage = 'tagging'
                       AND lc.prompt_version = ? AND lc.status = 'ok'
                 ){id_clause}
               ORDER BY ar.id{limit_clause}"""
    return conn.execute(query, params).fetchall()


def _build_prompt(topic_name, actor_name, actor_party, stance, typology, quote_text, quote_context, tag_row):
    actor_party_suffix = f" ({actor_party})" if actor_party else ""
    quote_context_block = f"Context: {quote_context}" if quote_context else ""
    return PROMPT_TEMPLATE.format(
        topic=topic_name,
        actor_name=actor_name,
        actor_party_suffix=actor_party_suffix,
        stance=stance,
        typology=typology,
        quote_text=quote_text,
        quote_context_block=quote_context_block,
        labelgroep=tag_row["labelgroep"],
        labelgroep_beschrijving=tag_row["labelgroep_beschrijving"],
        tag_sleutel=tag_row["sleutel"],
        tag_beschrijving=tag_row["tag_beschrijving"],
        voorbeelden_block=_build_voorbeelden_block(tag_row["sleutel"]),
    )


def _tag_one(arg, tag_row, model, base_url, reasoning_effort, timeout, max_tokens, api_key):
    """Eén argument door de LLM halen, zonder DB-writes -- puur zodat dit
    veilig via dask over meerdere workers/threads kan lopen (--parallel)."""
    prompt = _build_prompt(
        arg["topic_name"], arg["actor_name"], arg["actor_party"], arg["stance"], arg["typology"],
        arg["quote_text"], arg["quote_context"], tag_row,
    )
    start = time.monotonic()
    started_at = datetime.now(timezone.utc).isoformat()
    raw_content = None
    try:
        raw_content, usage, finish_reason = call_llm(
            base_url, model, prompt, reasoning_effort, timeout, max_tokens, api_key=api_key,
        )
        if finish_reason == "length":
            raise ValueError(f"antwoord afgekapt op max_tokens={max_tokens} (verhoog --max-tokens)")
        parsed = _extract_json(raw_content)
        if not isinstance(parsed, dict):
            raise ValueError(f"onverwacht antwoordtype: {type(parsed)}")
        van_toepassing = bool(parsed.get("van_toepassing"))
        reden = parsed.get("reden") if van_toepassing else None
        quote_fragment_raw = parsed.get("quote_fragment") if van_toepassing else None
        if not isinstance(quote_fragment_raw, str):
            quote_fragment_raw = None
        return {
            "arg": arg, "ok": True, "raw_content": raw_content, "usage": usage,
            "van_toepassing": van_toepassing, "reden": reden, "quote_fragment_raw": quote_fragment_raw,
            "elapsed": time.monotonic() - start, "started_at": started_at,
        }
    except Exception as exc:
        return {
            "arg": arg, "ok": False, "raw_content": raw_content, "error": str(exc),
            "elapsed": time.monotonic() - start, "started_at": started_at,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tag", required=True, help="exacte tag_sleutel uit config/tags.toml, bv. Stijl-Godwin")
    topic_group = parser.add_mutually_exclusive_group(required=True)
    topic_group.add_argument("--topic", help="topic-slug, bv. stikstof")
    topic_group.add_argument("--all-topics", action="store_true", help="alle topics in de database")
    parser.add_argument("--limit", type=int, default=None, help="max aantal argumenten deze run (default: alles)")
    parser.add_argument(
        "--ids", default=None,
        help="komma-gescheiden lijst van specifieke argument-id's (bv. regex-kandidaten) i.p.v. alle getagde argumenten",
    )
    parser.add_argument(
        "--ids-file", default=None,
        help="pad naar een bestand met één argument-id per regel (# begint een commentaarregel); combineerbaar met --ids",
    )
    parser.add_argument("--model", default="qwen/qwen3.8-27b")
    parser.add_argument("--base-url", default="http://localhost:1234/v1")
    parser.add_argument("--api-key", default=None, help="Bearer-token voor de --base-url-backend, indien vereist")
    parser.add_argument("--reasoning-effort", default="none")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--max-tokens", type=int, default=500)
    parser.add_argument("--dry-run", action="store_true", help="niets naar de database schrijven, alleen printen")
    parser.add_argument(
        "--parallel", action="store_true",
        help="verdeel LLM-calls over dask i.p.v. sequentieel -- alleen zinvol tegen een remote provider "
             "die concurrency aankan (bv. de HF-router)",
    )
    args = parser.parse_args()

    conn = db.connect()
    tag_row = load_tag(conn, args.tag)

    if args.all_topics:
        topic_ids = [row["id"] for row in conn.execute("SELECT id FROM topics").fetchall()]
    else:
        topic_row = conn.execute("SELECT id FROM topics WHERE slug = ?", (args.topic,)).fetchone()
        if topic_row is None:
            raise SystemExit(f"onbekende topic-slug: {args.topic}")
        topic_ids = [topic_row["id"]]

    ids = None
    if args.ids or args.ids_file:
        ids = []
        if args.ids:
            ids.extend(int(x) for x in args.ids.split(",") if x.strip())
        if args.ids_file:
            for regel in Path(args.ids_file).read_text().splitlines():
                regel = regel.split("#", 1)[0].strip()
                if regel:
                    ids.append(int(regel))
        ids = sorted(set(ids))

    prompt_version = compute_prompt_version(tag_row)
    arguments = fetch_candidates(conn, tag_row["sleutel"], prompt_version, topic_ids, ids=ids, limit=args.limit)
    if not arguments:
        logger.info("Geen kandidaten (allemaal al beoordeeld voor tag %s, of geen getagde argumenten in scope).", tag_row["sleutel"])
        return
    arguments = [dict(arg) for arg in arguments]
    if ids is not None and len(arguments) < len(ids):
        gevonden = {row["id"] for row in arguments}
        gemist = [i for i in ids if i not in gevonden]
        logger.warning(
            "%d van %d opgegeven id's niet meegenomen (verkeerde topic, nog niet getagd, al beoordeeld voor deze tag, of bestaat niet): %s",
            len(gemist), len(ids), gemist,
        )

    logger.info(
        "Tag: %s (%s) | model=%s | prompt_version=%s | %d argumenten",
        tag_row["sleutel"], tag_row["labelgroep"], args.model, prompt_version, len(arguments),
    )

    total_toegekend = total_errors = 0
    latencies = []
    qf_totals = Counter()
    price_baseline = get_baseline_pricing(args.model, args.base_url)
    PRICE_CHECK_INTERVAL = 100

    def process_result(r):
        nonlocal total_toegekend, total_errors
        arg, elapsed, started_at = r["arg"], r["elapsed"], r["started_at"]
        if not r["ok"]:
            logger.error("[arg %5d] %-25s FOUT na %5.1fs: %s", arg["id"], arg["actor_name"], elapsed, r["error"])
            total_errors += 1
            if not args.dry_run:
                record_llm_call(
                    conn, stage="tagging", topic_id=arg["topic_id"], document_id=arg["document_id"], argument_id=arg["id"],
                    model=args.model, prompt_version=prompt_version, started_at=started_at, duration_s=elapsed,
                    response=r["raw_content"], status="error", error_message=r["error"],
                )
            return
        latencies.append(elapsed)
        if not args.dry_run:
            record_llm_call(
                conn, stage="tagging", topic_id=arg["topic_id"], document_id=arg["document_id"], argument_id=arg["id"],
                model=args.model, prompt_version=prompt_version, started_at=started_at, duration_s=elapsed,
                response=r["raw_content"], status="ok", usage=r["usage"],
            )

        if r["van_toepassing"]:
            classification = classify_quote_fragment(r["quote_fragment_raw"], arg["quote_text"])
            qf_totals[classification] += 1
            quote_fragment = r["quote_fragment_raw"] if classification in (QF_GELDIG, QF_GELDIG_MEERDELIG) else None
            tags = [(tag_row["sleutel"], r["reden"], quote_fragment)]
            total_toegekend += 1
        else:
            tags = []

        if not args.dry_run and tags:
            with conn:
                insert_llm_tags(conn, arg["id"], tags)

        logger.info(
            "[arg %5d] %-25s %5.1fs | %s: %s",
            arg["id"], arg["actor_name"], elapsed, tag_row["sleutel"], "ja" if r["van_toepassing"] else "nee",
        )

    if args.parallel:
        client = make_client(dashboard=True)
        logger.info("Parallelle modus: %d LLM-calls verdeeld over dask (dashboard: %s)", len(arguments), client.dashboard_link)
        futures = client.map(
            _tag_one, arguments,
            tag_row=dict(tag_row), model=args.model, base_url=args.base_url, reasoning_effort=args.reasoning_effort,
            timeout=args.timeout, max_tokens=args.max_tokens, api_key=args.api_key,
        )
        for i, future in enumerate(as_completed(futures), 1):
            process_result(future.result())
            if i % PRICE_CHECK_INTERVAL == 0 and not price_still_matches(args.model, args.base_url, price_baseline):
                remaining = [f for f in futures if not f.done()]
                logger.error(
                    "Batch afgebroken na %d/%d argumenten wegens prijsstijging (%d resterende taken geannuleerd).",
                    i, len(arguments), len(remaining),
                )
                client.cancel(remaining)
                break
        client.close()
    else:
        for i, arg in enumerate(arguments, 1):
            process_result(_tag_one(
                arg, dict(tag_row), args.model, args.base_url, args.reasoning_effort, args.timeout, args.max_tokens, args.api_key,
            ))
            if i % PRICE_CHECK_INTERVAL == 0 and not price_still_matches(args.model, args.base_url, price_baseline):
                logger.error("Batch afgebroken na %d/%d argumenten wegens prijsstijging.", i, len(arguments))
                break

    conn.close()

    logger.info("Klaar: %d argumenten verwerkt, %d fout(en).", len(arguments), total_errors)
    logger.info("Toegekend: %s bij %d/%d argumenten.", tag_row["sleutel"], total_toegekend, len(arguments))
    if qf_totals:
        logger.info(
            "quote_fragment-compliance: geldig=%d geldig_meerdelig=%d geen_fragment=%d niet_gevonden=%d ambigu=%d",
            qf_totals[QF_GELDIG], qf_totals[QF_GELDIG_MEERDELIG], qf_totals[QF_GEEN_FRAGMENT],
            qf_totals[QF_NIET_GEVONDEN], qf_totals[QF_AMBIGU],
        )
    if latencies:
        avg = sum(latencies) / len(latencies)
        logger.info("Latency: gem=%.1fs min=%.1fs max=%.1fs", avg, min(latencies), max(latencies))
    if args.dry_run:
        logger.info("Dry-run: niets weggeschreven naar de database.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
