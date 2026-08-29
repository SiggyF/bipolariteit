"""
Tweede-pass tagging: kent taxonomie-tags (data/tags.toml, geladen via
pipeline/db/seed_tags.py) toe aan reeds geëxtraheerde `arguments`-rijen.

Draait NA extract_arguments.py en NA seed_tags.py, en laat extract_arguments.py
zelf ongewijzigd -- twee losse passes zodat de al-werkende stance/typology/
claims-extractie niet meeloopt met het risico van een grotere, complexere
LLM-call (kost wel ~2x de totale LLM-tijd per argument).

Drie labelgroepen (Issue Arena, Actor Type, Parlementaire Context) worden
deterministisch afgeleid uit al bekende DB-data (created_by='derived'),
zonder LLM. De overige labelgroepen gaan naar het lokale LLM (created_by='llm').

Gebruik:
    uv run python -m pipeline.tag_arguments --topic stikstof --limit 15
    uv run python -m pipeline.tag_arguments --topic stikstof --limit 15 --dry-run
    uv run python -m pipeline.tag_arguments --topic stikstof --ids 101,204,309
    uv run python -m pipeline.tag_arguments --topic stikstof --ids-file gefaald.txt
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
from pipeline.taxonomy import DERIVED_LABELGROEPEN, field_name_for

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = (Path(__file__).parent / "prompts" / "tag_argument.md").read_text()
PROMPT_VERSION = hashlib.sha256(PROMPT_TEMPLATE.encode()).hexdigest()[:12]

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)

# Mapping van VLOS <activiteit soort="..."> naar Parlementaire-Context-tag.
# Alleen "Plenair debat" is geverifieerd tegen echte data (5 lokale
# stikstof-verslagen); de overige drie zijn een aanname op basis van de
# terminologie in docs/plan.md en moeten nog bevestigd worden zodra een
# verslag van dat type wordt geïngest. Onbekende/niet-gemapte waarden
# blijven bewust ongetagd (nooit gokken).
ACTIVITEIT_SOORT_TO_CONTEXT = {
    "Plenair debat": "Context-Plenair",  # geverifieerd
    "Vragenuur": "Context-Vragenuur",  # aanname, nog te verifiëren
    "Commissiedebat": "Context-Commissie",  # aanname, nog te verifiëren
    "Wetgevingsoverleg": "Context-Commissie",  # aanname, nog te verifiëren
    "Tweeminutendebat": "Context-Tweeminutendebat",  # aanname, nog te verifiëren
}


def load_valid_tags(conn):
    """{field_name: (selectie, labelgroep_naam, {geldige sleutels})} voor
    actieve, niet-afgeleide labelgroepen (de labelgroepen die naar het LLM gaan)."""
    rows = conn.execute(
        """SELECT l.naam AS labelgroep, l.selectie, t.sleutel
           FROM labelgroepen l JOIN tags t ON t.labelgroep = l.naam
           WHERE l.active = 1 AND t.active = 1"""
    ).fetchall()
    result = {}
    for row in rows:
        if row["labelgroep"] in DERIVED_LABELGROEPEN:
            continue
        field = field_name_for(row["labelgroep"])
        entry = result.setdefault(field, (row["selectie"], row["labelgroep"], set()))
        entry[2].add(row["sleutel"])
    return result


def load_all_active_tags_by_labelgroep(conn):
    """{labelgroep_naam: [(sleutel, beschrijving), ...]} voor alle actieve labelgroepen/tags."""
    rows = conn.execute(
        """SELECT l.naam AS labelgroep, l.beschrijving AS labelgroep_beschrijving, l.selectie,
                  t.sleutel, t.beschrijving AS tag_beschrijving
           FROM labelgroepen l JOIN tags t ON t.labelgroep = l.naam
           WHERE l.active = 1 AND t.active = 1
           ORDER BY l.naam, t.sleutel"""
    ).fetchall()
    grouped = {}
    for row in rows:
        grouped.setdefault(row["labelgroep"], {"beschrijving": row["labelgroep_beschrijving"], "selectie": row["selectie"], "tags": []})
        grouped[row["labelgroep"]]["tags"].append((row["sleutel"], row["tag_beschrijving"]))
    return grouped


def build_tag_catalogue(conn):
    """Genereert de taxonomie-tekst + JSON-skeleton voor de prompt, puur
    afgeleid van de huidige DB-inhoud (nooit hardcoded tagnamen) zodat een
    tags.toml-update (na een nieuwe seed_tags.py-run) automatisch meekomt in
    de allereerstvolgende tag_arguments.py-aanroep.

    Elke toegekende tag moet vergezeld gaan van een `reden` -- een korte,
    argument-specifieke onderbouwing (waarom past dit label HIER), niet een
    herhaling van de generieke tag-beschrijving hierboven. Daarom is de
    skeleton-waarde per tag een object {sleutel, reden} i.p.v. een kale string."""
    grouped = load_all_active_tags_by_labelgroep(conn)
    catalogue_lines = []
    skeleton = {}
    for labelgroep, info in grouped.items():
        if labelgroep in DERIVED_LABELGROEPEN:
            continue
        field = field_name_for(labelgroep)
        keuze = "kies precies één (of null)" if info["selectie"] == "enkel" else "kies nul of meer"
        catalogue_lines.append(f"### {labelgroep} ({info['beschrijving']}) -- {keuze}")
        for sleutel, beschrijving in info["tags"]:
            catalogue_lines.append(f"- {sleutel}: {beschrijving}")
        catalogue_lines.append("")
        tag_obj = {"sleutel": "<TAG_SLEUTEL>", "reden": "<korte argument-specifieke onderbouwing>"}
        skeleton[field] = tag_obj if info["selectie"] == "enkel" else [tag_obj]
    return "\n".join(catalogue_lines).strip(), json.dumps(skeleton, ensure_ascii=False, indent=2)


def _build_prompt(topic_name, actor_name, actor_party, stance, typology, quote_text, quote_context, tag_catalogue, tag_json_skeleton):
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
        tag_catalogue=tag_catalogue,
        tag_json_skeleton=tag_json_skeleton,
    )


def _extract_json(raw_text):
    fence_match = _JSON_FENCE_RE.search(raw_text)
    candidate = fence_match.group(1) if fence_match else raw_text.strip()
    return json.loads(candidate)


class LLMResponse(NamedTuple):
    content: str
    usage: dict
    finish_reason: str | None


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


# Sentinel voor "het model bedoelde hier expliciet geen tag" -- onderscheiden
# van een echt onherkenbare vorm, want dat eerste is geen fout en verdient
# geen waarschuwing (zie _coerce_tag_entry).
_GEEN_TAG = object()

# Vormen waarin het model "geen tag van toepassing" verpakt in plaats van het
# skeleton-veld gewoon leeg te laten: een lege lijst, JSON null, of (geplakt)
# de string "null". Alle drie gezien in de praktijk voor dezelfde intentie.
_GEEN_TAG_WAARDEN = (None, [], "null")


def _normalize_sleutel(sleutel):
    """Modellen plakken soms een spatie rond het streepje in een sleutel (bv.
    'Stijl- Herhaling' i.p.v. 'Stijl-Herhaling') -- vormfoutje, geen andere
    sleutel bedoeld. Normaliseren vóór de allowed-check, anders wordt een
    correcte herkenning stilzwijgend als 'onbekende sleutel' weggegooid."""
    return re.sub(r"\s*-\s*", "-", sleutel.strip())


def _coerce_tag_entry(entry):
    """Accepteert zowel het nieuwe {sleutel, reden}-object als (voor
    achterwaartse compatibiliteit met oudere geplakte Gemini-antwoorden) een
    kale sleutel-string zonder reden. Retourneert (sleutel, reden), _GEEN_TAG
    als het model expliciet "geen tag" bedoelde, of None bij een echt
    onherkenbare vorm."""
    if isinstance(entry, str):
        return _normalize_sleutel(entry), None
    if isinstance(entry, dict) and "sleutel" in entry:
        sleutel = entry["sleutel"]
        if sleutel in _GEEN_TAG_WAARDEN:
            return _GEEN_TAG
        if isinstance(sleutel, str):
            return _normalize_sleutel(sleutel), entry.get("reden")
    return None


def _validate_tags(parsed, valid_tags):
    """Retourneert lijst van (sleutel, reden) die geaccepteerd worden;
    logt en slaat ongeldige velden/sleutels over i.p.v. de hele batch te laten falen."""
    accepted = []
    for field, (selectie, _labelgroep, allowed) in valid_tags.items():
        value = parsed.get(field)
        if value is None:
            continue
        entries = [value] if isinstance(value, (str, dict)) else value
        if not isinstance(entries, list):
            logger.warning("    overgeslagen veld %r: onverwacht type %s", field, type(value))
            continue
        coerced = []
        for entry in entries:
            result = _coerce_tag_entry(entry)
            if result is _GEEN_TAG:
                continue
            if result is None:
                logger.warning("    overgeslagen onherkenbaar tag-item in %r: %r", field, entry)
                continue
            coerced.append(result)
        if selectie == "enkel" and len(coerced) > 1:
            logger.warning("    overgeslagen veld %r: enkelvoudige labelgroep kreeg meerdere tags: %s", field, coerced)
            continue
        for sleutel, reden in coerced:
            if sleutel in allowed:
                accepted.append((sleutel, reden))
            else:
                logger.warning("    overgeslagen onbekende sleutel in %r: %r", field, sleutel)
    return accepted


def assign_derived_tags(conn, argument_id, document_id, actor_id, dry_run=False):
    """Bepaalt Arena-Parlement / Actor-Type / Parlementaire-Context zonder
    LLM, puur uit al bekende DB-data. Kost niets, dus altijd berekend --
    maar respecteert --dry-run net als de LLM-tags: bij dry_run wordt niets
    weggeschreven, alleen het resultaat geretourneerd voor de preview-print."""
    assigned = []
    row = conn.execute(
        """SELECT s.type AS source_type, d.activiteit_soort, a.party AS actor_party
           FROM documents d
           JOIN sources s ON s.id = d.source_id
           JOIN actors a ON a.id = ?
           WHERE d.id = ?""",
        (actor_id, document_id),
    ).fetchone()
    if row is None:
        return assigned

    if row["source_type"] == "tweede_kamer":
        assigned.append(("Arena-Parlement", "Bron is een Tweede Kamer-debat (documents.source.type = 'tweede_kamer')."))

    if row["actor_party"]:
        assigned.append(("Actor-Politicus", f"Spreker heeft een geregistreerde partij ({row['actor_party']})."))

    context_tag = ACTIVITEIT_SOORT_TO_CONTEXT.get(row["activiteit_soort"])
    if context_tag:
        assigned.append((context_tag, f"Afgeleid van VLOS-activiteitsoort '{row['activiteit_soort']}'."))

    if not dry_run:
        for sleutel, reden in assigned:
            conn.execute(
                """INSERT OR IGNORE INTO argument_tags (argument_id, tag_sleutel, created_by, confidence, reden, assigned_at)
                   VALUES (?, ?, 'derived', NULL, ?, ?)""",
                (argument_id, sleutel, reden, datetime.now(timezone.utc).isoformat()),
            )
    return [sleutel for sleutel, _reden in assigned]


def insert_llm_tags(conn, argument_id, tag_reden_pairs):
    now = datetime.now(timezone.utc).isoformat()
    for sleutel, reden in tag_reden_pairs:
        conn.execute(
            """INSERT OR IGNORE INTO argument_tags (argument_id, tag_sleutel, created_by, confidence, reden, assigned_at)
               VALUES (?, ?, 'llm', NULL, ?, ?)""",
            (argument_id, sleutel, reden, now),
        )


def fetch_untagged_arguments(conn, topic_id, limit, min_id=0, vanaf=None, ids=None):
    """`vanaf` is een ISO-datum op de publicatiedatum van het brondocument;
    zelfde drempel als bij de extractie ([verwerking].vanaf), zodat we
    geen argumenten taggen uit een periode die we verder buiten beschouwing
    laten. De data blijft staan, alleen deze query ziet 'm niet.

    `ids`, indien gegeven, beperkt de selectie tot precies die argument-id's
    (bv. een gerichte hertag-batch na een gefaalde eerdere poging) -- min_id/
    vanaf worden dan genegeerd, `tagged_at IS NULL` blijft wel gelden zodat
    dit nooit per ongeluk een al goed getagd argument overschrijft."""
    if ids is not None:
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        return conn.execute(
            f"""SELECT ar.id, ar.document_id, ar.actor_id, ar.stance, ar.typology,
                      ar.quote_text, ar.quote_context,
                      act.name AS actor_name, act.party AS actor_party
               FROM arguments ar
               JOIN actors act ON act.id = ar.actor_id
               WHERE ar.topic_id = ?
                 AND ar.id IN ({placeholders})
                 AND ar.tagged_at IS NULL
               ORDER BY ar.id""",
            (topic_id, *ids),
        ).fetchall()

    if vanaf is None:
        vanaf = PeriodeIndex().drempel
    return conn.execute(
        """SELECT ar.id, ar.document_id, ar.actor_id, ar.stance, ar.typology,
                  ar.quote_text, ar.quote_context,
                  act.name AS actor_name, act.party AS actor_party
           FROM arguments ar
           JOIN actors act ON act.id = ar.actor_id
           JOIN documents d ON d.id = ar.document_id
           WHERE ar.topic_id = ?
             AND ar.id >= ?
             AND d.published_at >= ?
             AND ar.tagged_at IS NULL
           ORDER BY ar.id
           LIMIT ?""",
        (topic_id, min_id, vanaf, limit),
    ).fetchall()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", required=True, help="topic-slug, bv. stikstof")
    parser.add_argument("--limit", type=int, default=15, help="max aantal arguments deze run (default 15)")
    parser.add_argument("--min-id", type=int, default=0, help="alleen arguments met id >= deze waarde")
    parser.add_argument(
        "--ids", default=None,
        help="komma-gescheiden lijst van specifieke argument-id's (bv. na een gefaalde run) -- "
             "i.p.v. de gebruikelijke min-id/limit-scan; negeert --min-id/--limit/--vanaf",
    )
    parser.add_argument(
        "--ids-file", default=None,
        help="pad naar een bestand met één argument-id per regel (# begint een commentaarregel); "
             "combineerbaar met --ids",
    )
    parser.add_argument("--model", default="qwen/qwen3.6-27b")
    parser.add_argument("--base-url", default="http://localhost:1234/v1")
    parser.add_argument("--reasoning-effort", default="none")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument(
        "--max-tokens", type=int, default=2000,
        help="max_tokens per argument (default 2000; 1000 kapte volle taglijsten af)",
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
    topic_row = conn.execute("SELECT id, name FROM topics WHERE slug = ?", (args.topic,)).fetchone()
    if topic_row is None:
        raise SystemExit(f"onbekende topic-slug: {args.topic}")
    topic_id, topic_name = topic_row["id"], topic_row["name"]

    valid_tags = load_valid_tags(conn)
    tag_catalogue, tag_json_skeleton = build_tag_catalogue(conn)

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

    arguments = fetch_untagged_arguments(conn, topic_id, args.limit, args.min_id, args.vanaf, ids=ids)
    if not arguments:
        logger.info("Geen ongetagde argumenten (al verwerkt, of geen argumenten voor deze topic).")
        return
    if ids is not None and len(arguments) < len(ids):
        gevonden = {row["id"] for row in arguments}
        gemist = [i for i in ids if i not in gevonden]
        logger.warning(
            "%d van %d opgegeven id's niet meegenomen (verkeerde topic, al getagd, of bestaat niet): %s",
            len(gemist), len(ids), gemist,
        )

    logger.info(
        "Model: %s | reasoning_effort=%r | prompt_version=%s | %d argumenten",
        args.model, args.reasoning_effort, PROMPT_VERSION, len(arguments),
    )

    total_derived = 0
    total_llm = 0
    total_errors = 0
    latencies = []

    for arg in arguments:
        derived = assign_derived_tags(conn, arg["id"], arg["document_id"], arg["actor_id"], dry_run=True)
        total_derived += len(derived)

        prompt = _build_prompt(
            topic_name, arg["actor_name"], arg["actor_party"], arg["stance"], arg["typology"],
            arg["quote_text"], arg["quote_context"], tag_catalogue, tag_json_skeleton,
        )
        start = time.monotonic()
        started_at = datetime.now(timezone.utc).isoformat()
        llm_tags = []
        raw_content = None
        try:
            raw_content, usage, finish_reason = call_llm(
                args.base_url, args.model, prompt, args.reasoning_effort, args.timeout, args.max_tokens
            )
            if finish_reason == "length":
                raise ValueError(f"antwoord afgekapt op max_tokens={args.max_tokens} (verhoog --max-tokens)")
            parsed = _extract_json(raw_content)
            llm_tags = _validate_tags(parsed, valid_tags)
        except Exception as exc:
            elapsed = time.monotonic() - start
            logger.error("[arg %5d] %-25s FOUT na %5.1fs: %s", arg["id"], arg["actor_name"], elapsed, exc)
            total_errors += 1
            if not args.dry_run:
                record_llm_call(
                    conn, stage="tagging", topic_id=topic_id, document_id=arg["document_id"], argument_id=arg["id"],
                    model=args.model, prompt_version=PROMPT_VERSION, started_at=started_at, duration_s=elapsed,
                    response=raw_content, status="error", error_message=str(exc),
                )
            continue
        elapsed = time.monotonic() - start
        latencies.append(elapsed)
        if not args.dry_run:
            record_llm_call(
                conn, stage="tagging", topic_id=topic_id, document_id=arg["document_id"], argument_id=arg["id"],
                model=args.model, prompt_version=PROMPT_VERSION, started_at=started_at, duration_s=elapsed,
                response=raw_content, status="ok", usage=usage,
            )

        if not args.dry_run:
            with conn:
                assign_derived_tags(conn, arg["id"], arg["document_id"], arg["actor_id"], dry_run=False)
                insert_llm_tags(conn, arg["id"], llm_tags)
                conn.execute(
                    "UPDATE arguments SET tagged_at = ?, tag_prompt_version = ?, tag_model = ? WHERE id = ?",
                    (datetime.now(timezone.utc).isoformat(), PROMPT_VERSION, args.model, arg["id"]),
                )

        llm_sleutels = [sleutel for sleutel, _reden in llm_tags]
        total_llm += len(llm_tags)
        logger.info(
            "[arg %5d] %-25s %5.1fs | derived: %s | llm: %s",
            arg["id"], arg["actor_name"], elapsed, derived, llm_sleutels,
        )

    conn.close()

    logger.info("Klaar: %d argumenten verwerkt, %d fout(en).", len(arguments), total_errors)
    logger.info("Totaal: %d afgeleide tags, %d LLM-tags.", total_derived, total_llm)
    if latencies:
        avg = sum(latencies) / len(latencies)
        logger.info("Latency: gem=%.1fs min=%.1fs max=%.1fs", avg, min(latencies), max(latencies))
    if args.dry_run:
        logger.info("(--dry-run: niets weggeschreven naar de database)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
