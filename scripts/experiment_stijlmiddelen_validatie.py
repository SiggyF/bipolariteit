"""
Validatie-experiment voor issue #67: kan het taggingmodel de 5 kandidaat-
stijlmiddelen (Slogan, Herhaling, Drieledige Opsomming, Antithese, Retorische
Vraag) herkennen, vóórdat we ze daadwerkelijk in data/tags.toml opnemen?

Puur leesactie: schrijft niets naar de database, wijzigt geen
tags.toml/schema/prompts. Draait tegen het lokale eval-model (LM Studio),
naar het patroon van scripts/experiment_two_turn_tagging.py (issue #50) --
dus geen productiequotum.

Werkwijze:
1. Extraheert argumenten uit de fictieve testtoespraak in stijlvalidatie.json
   met de bestaande, ongewijzigde extract_argument.md-prompt.
2. Tagt elk geëxtraheerd argument met de bestaande tag_argument.md-prompt,
   waarvan de taxonomie-catalogus hier tijdelijk (alleen in het geheugen)
   wordt aangevuld met de 5 kandidaat-stijlmiddelen.
3. Matcht elk geëxtraheerd argument aan het dichtstbijzijnde item uit
   stijlvalidatie.json (op tekstoverlap) en rapporteert verwacht vs. herkend.

Gebruik:
    uv run python scripts/experiment_stijlmiddelen_validatie.py
    uv run python scripts/experiment_stijlmiddelen_validatie.py --model qwen/qwen3.6-27b
"""
import argparse
import difflib
import json
from pathlib import Path

from pipeline.db import db
from pipeline.extract_arguments import (
    _build_prompt as build_extract_prompt,
    _extract_json,
    _validate_argument,
    call_llm as call_llm_extract,
)
from pipeline.tag_arguments import (
    _build_prompt as build_tag_prompt,
    _extract_json as extract_tag_json,
    build_tag_catalogue,
    call_llm as call_llm_tag,
)

DATA_PATH = Path(__file__).parent / "stijlvalidatie.json"

TOPIC_NAME = "Diverse onderwerpen (validatie-experiment)"
TOPIC_DESCRIPTION = (
    "Fictieve testtoespraak, samengesteld om stijlmiddelen-herkenning te valideren; "
    "niet gebonden aan één specifieke pro/contra-as."
)
ACTOR_NAME = "Spreker A"

# Kandidaat-stijlmiddelen (definities uit docs/Taxonomie Stijlmiddelen Politieke
# Debatten.md), hier hardcoded voor het experiment -- NIET in data/tags.toml,
# dus geen DB/schema-wijziging nodig om dit te testen.
STIJLMIDDEL_DEFINITIES = [
    ("stijlmiddel-slogan", "Beknopte, pakkende frase."),
    ("stijlmiddel-herhaling", "Herhaling van hetzelfde woord of dezelfde woordgroep binnen het fragment, ter nadruk."),
    (
        "stijlmiddel-aangekondigde-opsomming",
        "Vooraf het aantal elementen aankondigen (twee, drie, vijf, ...), gevolgd door een opsomming van "
        "precies dat aantal (bv. 'ik noem twee dingen: A en B') -- niet zomaar elke opsomming van meerdere dingen.",
    ),
    ("stijlmiddel-antithese", "Het naast elkaar plaatsen van twee tegengestelde begrippen of ideeën."),
    ("stijlmiddel-retorische-vraag", "Een vraag waarvan het antwoord al besloten ligt in de formulering zelf."),
]


def extended_tag_catalogue(conn):
    base_catalogue, base_skeleton_json = build_tag_catalogue(conn)
    lines = [base_catalogue, "", "### Stijlmiddelen (vormelijke/retorische middelen, geen redeneerfout of framing) -- kies nul of meer"]
    for sleutel, beschrijving in STIJLMIDDEL_DEFINITIES:
        lines.append(f"- {sleutel}: {beschrijving}")
    skeleton = json.loads(base_skeleton_json)
    skeleton["stijlmiddelen"] = [{"sleutel": "<TAG_SLEUTEL>", "reden": "<korte argument-specifieke onderbouwing>"}]
    return "\n".join(lines).strip(), json.dumps(skeleton, ensure_ascii=False, indent=2)


def best_match(quote_text, items):
    """Matcht een geëxtraheerd citaat aan het dichtstbijzijnde stijlvalidatie-item
    op tekstoverlap. Retourneert (item, ratio) of (None, 0.0)."""
    best_item, best_ratio = None, 0.0
    quote_norm = quote_text.strip().lower()
    for item in items:
        item_norm = item["tekst"].strip().lower()
        if item_norm in quote_norm or quote_norm in item_norm:
            ratio = 1.0
        else:
            ratio = difflib.SequenceMatcher(None, quote_norm, item_norm).ratio()
        if ratio > best_ratio:
            best_item, best_ratio = item, ratio
    return best_item, best_ratio


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default="qwen/qwen3.6-27b")
    parser.add_argument("--base-url", default="http://localhost:1234/v1")
    parser.add_argument("--reasoning-effort", default="none")
    parser.add_argument("--timeout", type=float, default=400.0)
    args = parser.parse_args()

    data = json.loads(DATA_PATH.read_text())
    documenttekst = data["documenttekst"]
    items = data["items"]

    print(f"Model: {args.model} | {len(items)} verwachte items\n")

    extract_prompt = build_extract_prompt(TOPIC_NAME, TOPIC_DESCRIPTION, ACTOR_NAME, None, documenttekst)
    raw, _usage, finish_reason = call_llm_extract(args.base_url, args.model, extract_prompt, args.reasoning_effort, args.timeout, 4000)
    if finish_reason == "length":
        raise SystemExit("extractie-antwoord afgekapt op max_tokens -- verhoog dit in het script")
    parsed = _extract_json(raw)
    arguments = parsed.get("arguments", []) if isinstance(parsed, dict) else parsed

    valid_arguments = []
    for arg in arguments:
        try:
            _validate_argument(arg)
            valid_arguments.append(arg)
        except ValueError as exc:
            print(f"  overgeslagen argument bij extractie: {exc}")
    print(f"Extractie: {len(valid_arguments)} argumenten herkend (van {len(items)} verwacht)\n")

    conn = db.connect()
    tag_catalogue, tag_json_skeleton = extended_tag_catalogue(conn)
    conn.close()

    matched_item_ids = set()
    results = []  # (item, herkende_sleutels)

    for arg in valid_arguments:
        item, ratio = best_match(arg["quote_text"], items)
        tag_prompt = build_tag_prompt(
            TOPIC_NAME, ACTOR_NAME, None, arg["stance"], arg["typology"],
            arg["quote_text"], arg.get("quote_context"), tag_catalogue, tag_json_skeleton,
        )
        raw_tag, _usage = call_llm_tag(args.base_url, args.model, tag_prompt, args.reasoning_effort, args.timeout)
        try:
            tag_parsed = extract_tag_json(raw_tag)
        except json.JSONDecodeError as exc:
            print(f"  tag-parsefout voor {arg['quote_text']!r}: {exc}")
            tag_parsed = {}
        stijlmiddel_entries = tag_parsed.get("stijlmiddelen") or []
        herkend = sorted({
            entry.get("sleutel") if isinstance(entry, dict) else entry
            for entry in stijlmiddel_entries
            if entry not in (None, "null")
        })

        if item is not None and ratio >= 0.5:
            matched_item_ids.add(item["id"])
        results.append((item, ratio, arg["quote_text"], herkend))

    print(f"{'verwacht':<32} {'herkend':<60} {'match':<6} citaat")
    print("-" * 130)
    hits, misses = 0, 0
    for item, ratio, quote_text, herkend in results:
        verwacht = item["verwacht_stijlmiddel"] if item else "(geen match)"
        ok = item is not None and ratio >= 0.5 and verwacht in herkend
        hits += ok
        misses += not ok
        print(f"{verwacht:<32} {','.join(herkend) or '-':<60} {'OK' if ok else 'MIS':<6} {quote_text[:60]!r}")

    unmatched = [item for item in items if item["id"] not in matched_item_ids]
    if unmatched:
        print(f"\n{len(unmatched)} item(s) niet teruggevonden in de extractie (mogelijk samengevoegd of gemist):")
        for item in unmatched:
            print(f"  [{item['verwacht_stijlmiddel']}] {item['tekst']!r}")

    print(f"\nTotaal: {hits} hit(s), {misses} mis(sen) op {len(results)} geëxtraheerde argumenten "
          f"({len(items)} verwacht).")

    per_stijlmiddel = {}
    for item, ratio, _quote, herkend in results:
        if item is None:
            continue
        verwacht = item["verwacht_stijlmiddel"]
        ok = ratio >= 0.5 and verwacht in herkend
        stats = per_stijlmiddel.setdefault(verwacht, [0, 0])
        stats[0] += ok
        stats[1] += 1
    print("\nPer stijlmiddel:")
    for sleutel, (ok_count, total) in sorted(per_stijlmiddel.items()):
        print(f"  {sleutel:<32} {ok_count}/{total}")


if __name__ == "__main__":
    main()
