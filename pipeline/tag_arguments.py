"""
Tweede-pass tagging: kent taxonomie-tags (config/tags.toml, geladen via
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
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from dask.distributed import as_completed
from json_repair import repair_json

from pipeline.dask_client import make_client
from pipeline.db import db
from pipeline.hf_pricing import get_baseline_pricing, price_still_matches
from pipeline.llm_client import call_llm
from pipeline.llm_log import record_llm_call
from pipeline.match_argument_spans import normalize_text
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
    herhaling van de generieke tag-beschrijving hierboven -- en een
    `quote_fragment`: het letterlijke stukje van de quote waar de tag op
    slaat, of null voor de hele quote (zie classify_quote_fragment, issue
    #109). Daarom is de skeleton-waarde per tag een object
    {sleutel, reden, quote_fragment} i.p.v. een kale string."""
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
        tag_obj = {
            "sleutel": "<TAG_SLEUTEL>",
            "reden": "<korte argument-specifieke onderbouwing>",
            "quote_fragment": "<letterlijk fragment uit de quote, of null>",
        }
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


# json_repair-logregels die aangeven dat het een ontbrekende sluithaak/quote
# zelf moest verzinnen -- d.w.z. de respons was echt afgekapt (bv. door
# max_tokens), niet alleen een klein syntaxfoutje. Zulke reparaties bevatten
# per definitie gegokte/ontbrekende data (het laatste, afgekapte tag-object
# mist dan bv. quote_fragment of zelfs reden) en worden daarom NIET
# geaccepteerd -- zie _extract_json(). Getest tegen alle 152 historische
# foutieve llm_calls-responses: dit patroon onderscheidt de 15 echte
# afkappingen betrouwbaar van de 137 zuivere syntaxfoutjes (o.a. de dubbele-
# sluithaak-bug), zelfs als de oorspronkelijke json.loads()-foutmelding qua
# tekst niet expliciet "unterminated" zegt.
_TRUNCATION_REPAIR_MARKER = "missed the closing"


def _extract_json(raw_text):
    fence_match = _JSON_FENCE_RE.search(raw_text)
    candidate = fence_match.group(1) if fence_match else raw_text.strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        # json_repair (https://github.com/mangiucugna/json_repair) i.p.v.
        # zelf regexes te onderhouden per waargenomen generatiefout (dubbele
        # sluithaak, verkeerd haaktype, ...). Alleen zuivere syntaxfouten
        # worden geaccepteerd: geen (niet-leeg) object terug, of een teken dat
        # de respons was afgekapt (_TRUNCATION_REPAIR_MARKER) -- dan bubbelt
        # de oorspronkelijke JSONDecodeError door, zodat zo'n argument als
        # mislukt geldt (en dus opnieuw geprobeerd kan worden) i.p.v. stil een
        # onvolledig resultaat te accepteren.
        repaired, log = repair_json(candidate, return_objects=True, logging=True)
        if not isinstance(repaired, dict) or not repaired:
            raise exc
        if any(_TRUNCATION_REPAIR_MARKER in entry["text"] for entry in log):
            raise exc
        logger.warning("JSON gerepareerd met json_repair vóór het parsen")
        return repaired


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
    """Accepteert zowel het nieuwe {sleutel, reden, quote_fragment}-object als
    (voor achterwaartse compatibiliteit met oudere geplakte Gemini-antwoorden)
    een kale sleutel-string zonder reden/fragment. Retourneert
    (sleutel, reden, quote_fragment), _GEEN_TAG als het model expliciet "geen
    tag" bedoelde, of None bij een echt onherkenbare vorm."""
    if isinstance(entry, str):
        return _normalize_sleutel(entry), None, None
    if isinstance(entry, dict) and "sleutel" in entry:
        sleutel = entry["sleutel"]
        if sleutel in _GEEN_TAG_WAARDEN:
            return _GEEN_TAG
        if isinstance(sleutel, str):
            quote_fragment = entry.get("quote_fragment")
            if not isinstance(quote_fragment, str):
                quote_fragment = None
            return _normalize_sleutel(sleutel), entry.get("reden"), quote_fragment
    return None


# Classificatie van een quote_fragment tegen de bijbehorende quote_text (issue
# #109) -- alleen "geldig"/"geldig_meerdelig" worden daadwerkelijk opgeslagen;
# de rest wordt tot None herleid (nooit gokken, zelfde principe als
# match_argument_spans.py).
QF_GEEN_FRAGMENT = "geen_fragment"  # model gaf null: tag slaat op hele quote
QF_GELDIG = "geldig"  # unieke, letterlijke substring van quote_text
QF_GELDIG_MEERDELIG = "geldig_meerdelig"  # unieke match via ...-gat (zie hieronder), meerdere zinsdelen samen
QF_NIET_GEVONDEN = "niet_gevonden"  # geen substring: geparafraseerd of verzonnen
QF_AMBIGU = "ambigu"  # meer dan één voorkomen in quote_text -- welke bedoeld is, is niet af te leiden

# Het model plakt bij tags die per definitie over meerdere plekken in de quote
# gaan (vooral Stijl-Herhaling) regelmatig twee losse zinsdelen aan elkaar met
# "..." i.p.v. één letterlijk aaneengesloten fragment te geven (bv. "Mensen
# zijn gebaat... waar de mensen bij gebaat zijn"). Dat is geen parafrase/
# verzinsel -- beide zinsdelen staan wél letterlijk in de quote, alleen niet
# aaneengesloten. In plaats van dat af te keuren als "niet_gevonden", elk los
# zinsdeel apart valideren en "..." als jokerteken behandelen (regex .*?)
# tussen de delen: precies bruikbaar als latere video-spanne (begin van het
# eerste deel tot eind van het laatste, zie pipeline/match_tag_spans.py).
_ELLIPSIS_RE = re.compile(r"\.\.\.|…")


def classify_quote_fragment(quote_fragment, quote_text):
    """Zelfde "nooit gokken"-principe als match_argument_spans.py: een
    fragment dat niet uniek in quote_text voorkomt (bv. bij een
    Stijl-Herhaling-tag, waar het gemarkeerde zinsdeel per definitie kan
    herhalen) wordt niet gedisambigueerd, maar afgekeurd."""
    if not quote_fragment or not quote_fragment.strip():
        return QF_GEEN_FRAGMENT
    haystack = normalize_text(quote_text)

    delen = [normalize_text(deel) for deel in _ELLIPSIS_RE.split(quote_fragment)]
    delen = [deel for deel in delen if deel]
    if not delen:
        return QF_GEEN_FRAGMENT

    if len(delen) == 1:
        needle = delen[0]
        count = haystack.count(needle)
        if count == 0:
            return QF_NIET_GEVONDEN
        if count > 1:
            return QF_AMBIGU
        return QF_GELDIG

    pattern = ".*?".join(re.escape(deel) for deel in delen)
    matches = list(re.finditer(pattern, haystack))
    if not matches:
        return QF_NIET_GEVONDEN
    if len(matches) > 1:
        return QF_AMBIGU
    return QF_GELDIG_MEERDELIG


def _validate_tags(parsed, valid_tags, quote_text, qf_stats=None):
    """Retourneert lijst van (sleutel, reden, quote_fragment) die
    geaccepteerd worden; logt en slaat ongeldige velden/sleutels over i.p.v.
    de hele batch te laten falen. quote_fragment is alleen gezet als
    classify_quote_fragment() 'geldig'/'geldig_meerdelig' oordeelt, anders
    None. qf_stats (als meegegeven) telt de classificatie van elke
    toegekende tag, voor de compliance-samenvatting in main()."""
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
        for sleutel, reden, quote_fragment_raw in coerced:
            if sleutel not in allowed:
                logger.warning("    overgeslagen onbekende sleutel in %r: %r", field, sleutel)
                continue
            classification = classify_quote_fragment(quote_fragment_raw, quote_text)
            if qf_stats is not None:
                qf_stats[classification] += 1
            quote_fragment = quote_fragment_raw if classification in (QF_GELDIG, QF_GELDIG_MEERDELIG) else None
            accepted.append((sleutel, reden, quote_fragment))
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


def insert_llm_tags(conn, argument_id, tags):
    """Nieuwe (argument_id, tag_sleutel)-combinaties worden toegevoegd. Bestaat
    de combinatie al (bv. een --backfill-quote-fragment-herrun van een argument
    dat al getagd was), dan wordt uitsluitend een leeg quote_fragment(_status)
    gevuld -- reden/created_by/assigned_at van de bestaande rij blijven
    ongemoeid, en een al opgeloste quote_fragment_status wordt nooit
    overschreven. Zie issue #109-vervolg: additief aanvullen, nooit
    stilzwijgend verwijderen of overschrijven.

    quote_fragment_status maakt hier expliciet of quote_fragment=NULL "hele
    quote" betekent (dit antwoord beoordeelde de tag en er is geen fragment
    van toepassing) of gewoon nog nooit beoordeeld is (quote_fragment_status
    blijft dan NULL, zie fetch_quote_fragment_backfill_arguments())."""
    now = datetime.now(timezone.utc).isoformat()
    for sleutel, reden, quote_fragment in tags:
        status = "fragment" if quote_fragment is not None else "hele_quote"
        conn.execute(
            """INSERT INTO argument_tags
                   (argument_id, tag_sleutel, created_by, confidence, reden, quote_fragment, quote_fragment_status, assigned_at)
               VALUES (?, ?, 'llm', NULL, ?, ?, ?, ?)
               ON CONFLICT(argument_id, tag_sleutel) DO UPDATE SET
                   quote_fragment = excluded.quote_fragment,
                   quote_fragment_status = excluded.quote_fragment_status
               WHERE argument_tags.quote_fragment_status IS NULL
                 AND argument_tags.created_by = 'llm'""",
            (argument_id, sleutel, reden, quote_fragment, status, now),
        )


def fetch_untagged_arguments(conn, topic_id, limit, min_id=0, vanaf=None, ids=None, recent_first=False):
    """`vanaf` is een ISO-datum op de publicatiedatum van het brondocument;
    zelfde drempel als bij de extractie ([verwerking].vanaf), zodat we
    geen argumenten taggen uit een periode die we verder buiten beschouwing
    laten. De data blijft staan, alleen deze query ziet 'm niet.

    `ids`, indien gegeven, beperkt de selectie tot precies die argument-id's
    (bv. een gerichte hertag-batch na een gefaalde eerdere poging) -- min_id/
    vanaf worden dan genegeerd, `tagged_at IS NULL` blijft wel gelden zodat
    dit nooit per ongeluk een al goed getagd argument overschrijft.

    `recent_first`: sorteer op documentdatum aflopend i.p.v. op argument-id
    oplopend, om bij een beperkte `limit` het meest recente parlementaire
    jaar voorrang te geven boven oudere achterstand."""
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
    order_by = "d.published_at DESC, ar.id" if recent_first else "ar.id"
    return conn.execute(
        f"""SELECT ar.id, ar.document_id, ar.actor_id, ar.stance, ar.typology,
                  ar.quote_text, ar.quote_context,
                  act.name AS actor_name, act.party AS actor_party
           FROM arguments ar
           JOIN actors act ON act.id = ar.actor_id
           JOIN documents d ON d.id = ar.document_id
           WHERE ar.topic_id = ?
             AND ar.id >= ?
             AND d.published_at >= ?
             AND ar.tagged_at IS NULL
           ORDER BY {order_by}
           LIMIT ?""",
        (topic_id, min_id, vanaf, limit),
    ).fetchall()


def fetch_quote_fragment_backfill_arguments(conn, topic_id, limit, min_id=0, ids=None, recent_first=False):
    """Selecteert argumenten die al getagd zijn (`tagged_at` gezet) maar nog
    een `llm`-tag hebben met `quote_fragment_status IS NULL` -- d.w.z. nooit
    beoordeeld op quote_fragment, meestal getagd vóór issue #109. In
    tegenstelling tot fetch_untagged_arguments() is `tagged_at IS NOT NULL`
    hier juist de voorwaarde, niet het filter dat uitsluit. De herrun voegt
    alleen ontbrekend quote_fragment(_status) toe (zie insert_llm_tags()),
    verwijdert of overschrijft nooit bestaande argument_tags-rijen.

    `quote_fragment_status` (i.p.v. simpelweg `quote_fragment IS NULL`)
    maakt het verschil expliciet tussen "hele_quote" (dit antwoord IS al
    beoordeeld, en er is legitiem geen fragment van toepassing -- zie
    schema.sql) en "nooit beoordeeld" (blijft NULL): zonder die scheiding
    zou een argument met een legitieme hele_quote-tag voor altijd
    "kandidaat" blijven, ook na een geslaagde herrun."""
    exists_clause = """EXISTS (
        SELECT 1 FROM argument_tags at
        WHERE at.argument_id = ar.id AND at.created_by = 'llm' AND at.quote_fragment_status IS NULL
    )"""
    if ids is not None:
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        query = f"""SELECT ar.id, ar.document_id, ar.actor_id, ar.stance, ar.typology,
                      ar.quote_text, ar.quote_context,
                      act.name AS actor_name, act.party AS actor_party
               FROM arguments ar
               JOIN actors act ON act.id = ar.actor_id
               WHERE ar.topic_id = ?
                 AND ar.id IN ({placeholders})
                 AND ar.tagged_at IS NOT NULL
                 AND {exists_clause}
               ORDER BY ar.id"""
        rows = conn.execute(query, (topic_id, *ids)).fetchall()
        return rows

    order_by = "d.published_at DESC, ar.id" if recent_first else "ar.id"
    query = f"""SELECT ar.id, ar.document_id, ar.actor_id, ar.stance, ar.typology,
                  ar.quote_text, ar.quote_context,
                  act.name AS actor_name, act.party AS actor_party
           FROM arguments ar
           JOIN actors act ON act.id = ar.actor_id
           JOIN documents d ON d.id = ar.document_id
           WHERE ar.topic_id = ?
             AND ar.id >= ?
             AND ar.tagged_at IS NOT NULL
             AND {exists_clause}
           ORDER BY {order_by}
           LIMIT ?"""
    rows = conn.execute(query, (topic_id, min_id, limit)).fetchall()
    return rows


def _tag_one(arg, topic_name, tag_catalogue, tag_json_skeleton, valid_tags, model, base_url, reasoning_effort, timeout, max_tokens, api_key):
    """Eén argument door de LLM halen, zonder DB-writes -- puur zodat dit
    veilig via dask over meerdere workers/threads kan lopen (--parallel).
    sqlite3-writes (incl. assign_derived_tags) blijven altijd in het
    hoofdproces, in `main()`."""
    prompt = _build_prompt(
        topic_name, arg["actor_name"], arg["actor_party"], arg["stance"], arg["typology"],
        arg["quote_text"], arg["quote_context"], tag_catalogue, tag_json_skeleton,
    )
    start = time.monotonic()
    started_at = datetime.now(timezone.utc).isoformat()
    raw_content = None  # blijft None als call_llm() zelf al faalt (bv. timeout); anders
    # overschreven zodra we een antwoord terug hebben, óók als de JSON-parse daarna
    # alsnog faalt -- zonder dit ging elke parse-fout de ruwe respons kwijt (nergens
    # meer te zien wat er precies mis was: afgekapt, extra tekst na de JSON, etc.)
    try:
        raw_content, usage, finish_reason = call_llm(
            base_url, model, prompt, reasoning_effort, timeout, max_tokens, api_key=api_key,
        )
        if finish_reason == "length":
            raise ValueError(f"antwoord afgekapt op max_tokens={max_tokens} (verhoog --max-tokens)")
        qf_stats = Counter()
        llm_tags = _validate_tags(_extract_json(raw_content), valid_tags, arg["quote_text"], qf_stats=qf_stats)
        return {
            "arg": arg, "ok": True, "raw_content": raw_content, "usage": usage, "llm_tags": llm_tags,
            "qf_stats": qf_stats, "elapsed": time.monotonic() - start, "started_at": started_at,
        }
    except Exception as exc:
        return {
            "arg": arg, "ok": False, "raw_content": raw_content, "error": str(exc),
            "elapsed": time.monotonic() - start, "started_at": started_at,
        }


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
    parser.add_argument(
        "--api-key", default=None,
        help="Bearer-token voor de --base-url-backend, indien vereist (bv. een HF-router-token; "
             "lokale LM Studio/agy hebben dit niet nodig, dan gewoon weglaten)",
    )
    parser.add_argument("--reasoning-effort", default="none")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument(
        "--max-tokens", type=int, default=2000,
        help="max_tokens per argument (default 2000; 1000 kapte volle taglijsten af)",
    )
    parser.add_argument(
        "--vanaf",
        default=None,
        help="ISO-datum; overschrijft [verwerking].vanaf uit config/politieke-periodes.toml "
             "(voor een bewuste backfill van een oudere periode)",
    )
    parser.add_argument(
        "--recent-first", action="store_true",
        help="prioriteer argumenten met de meest recente documentdatum (i.p.v. de default, oplopend op id)",
    )
    parser.add_argument("--dry-run", action="store_true", help="niets naar de database schrijven, alleen printen")
    parser.add_argument(
        "--backfill-quote-fragment", action="store_true",
        help="i.p.v. ongetagde argumenten: al getagde argumenten met een llm-tag zonder quote_fragment "
             "opnieuw taggen en additief aanvullen (nooit bestaande argument_tags verwijderen/overschrijven "
             "buiten het lege quote_fragment-veld) -- combineerbaar met --ids/--ids-file/--min-id/--limit/--recent-first",
    )
    parser.add_argument(
        "--parallel", action="store_true",
        help="verdeel LLM-calls over dask (de devcontainer's persistente scheduler, zie pipeline/dask_client.py) "
             "i.p.v. sequentieel -- alleen zinvol tegen een remote provider die concurrency aankan (bv. de "
             "HF-router); lokale LM Studio verwerkt toch maar één request tegelijk",
    )
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

    if args.backfill_quote_fragment:
        arguments = fetch_quote_fragment_backfill_arguments(
            conn, topic_id, args.limit, args.min_id, ids=ids, recent_first=args.recent_first
        )
        if not arguments:
            logger.info("Geen argumenten met ontbrekend quote_fragment (al aangevuld, of geen achterstand).")
            return
    else:
        arguments = fetch_untagged_arguments(
            conn, topic_id, args.limit, args.min_id, args.vanaf, ids=ids, recent_first=args.recent_first
        )
        if not arguments:
            logger.info("Geen ongetagde argumenten (al verwerkt, of geen argumenten voor deze topic).")
            return
    # dask kan sqlite3.Row niet deterministisch tokenizen/serialiseren (nodig
    # voor --parallel); gewone dicts werken overal waar Row ook werkte.
    arguments = [dict(arg) for arg in arguments]
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
    qf_totals = Counter()

    # Prijs vooraf vastleggen (alleen zinvol tegen de HF-router, zie
    # pipeline/hf_pricing.py) en tijdens de run periodiek herchecken -- zie
    # dezelfde aanpak in extract_arguments.py. Een prijsdáling is geen reden
    # om te stoppen.
    price_baseline = get_baseline_pricing(args.model, args.base_url)
    PRICE_CHECK_INTERVAL = 100

    def process_result(r):
        """Schrijft één resultaat direct weg zodra het binnenkomt -- zie
        dezelfde toelichting in extract_arguments.py's process_result()."""
        nonlocal total_derived, total_llm, total_errors
        arg, elapsed, started_at = r["arg"], r["elapsed"], r["started_at"]
        qf_totals.update(r.get("qf_stats") or {})
        derived = assign_derived_tags(conn, arg["id"], arg["document_id"], arg["actor_id"], dry_run=True)
        total_derived += len(derived)

        if not r["ok"]:
            logger.error("[arg %5d] %-25s FOUT na %5.1fs: %s", arg["id"], arg["actor_name"], elapsed, r["error"])
            total_errors += 1
            if not args.dry_run:
                record_llm_call(
                    conn, stage="tagging", topic_id=topic_id, document_id=arg["document_id"], argument_id=arg["id"],
                    model=args.model, prompt_version=PROMPT_VERSION, started_at=started_at, duration_s=elapsed,
                    response=r["raw_content"], status="error", error_message=r["error"],
                )
            return
        latencies.append(elapsed)
        raw_content, usage, llm_tags = r["raw_content"], r["usage"], r["llm_tags"]
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

        llm_sleutels = [sleutel for sleutel, _reden, _quote_fragment in llm_tags]
        total_llm += len(llm_tags)
        logger.info(
            "[arg %5d] %-25s %5.1fs | derived: %s | llm: %s",
            arg["id"], arg["actor_name"], elapsed, derived, llm_sleutels,
        )

    if args.parallel:
        client = make_client(dashboard=True)
        logger.info("Parallelle modus: %d LLM-calls verdeeld over dask (dashboard: %s)", len(arguments), client.dashboard_link)
        futures = client.map(
            _tag_one, arguments,
            topic_name=topic_name, tag_catalogue=tag_catalogue, tag_json_skeleton=tag_json_skeleton,
            valid_tags=valid_tags, model=args.model, base_url=args.base_url, reasoning_effort=args.reasoning_effort,
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
                arg, topic_name, tag_catalogue, tag_json_skeleton, valid_tags, args.model, args.base_url,
                args.reasoning_effort, args.timeout, args.max_tokens, args.api_key,
            ))
            if i % PRICE_CHECK_INTERVAL == 0 and not price_still_matches(args.model, args.base_url, price_baseline):
                logger.error("Batch afgebroken na %d/%d argumenten wegens prijsstijging.", i, len(arguments))
                break

    conn.close()

    logger.info("Klaar: %d argumenten verwerkt, %d fout(en).", len(arguments), total_errors)
    logger.info("Totaal: %d afgeleide tags, %d LLM-tags.", total_derived, total_llm)
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
        logger.info("(--dry-run: niets weggeschreven naar de database)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
