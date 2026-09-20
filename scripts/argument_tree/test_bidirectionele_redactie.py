"""
Eenmalig test-script (branch experiment/252-bidirectionele-weerlegging):
hergebruikt de al gestructureerde stikstof-boom (opgeslagen door een vorige
run, data/export/argument-docs/stikstof-structured-only.json -- geen nieuwe
structureer-call nodig) en draait de redactiestap opnieuw met de nieuwe,
neutrale boomredactie.md (één beoordelaar zonder pro/contra-rol, feitelijke
vraag: expliciete verwijzing of logische samenhang, i.p.v. een eerdere
pro/contra-rolversie die label-gedreven bleek te oordelen -- zie
sessie-overleg).

Gebruik:
    PYTHONPATH=. uv run python scripts/argument_tree/test_bidirectionele_redactie.py
"""

import json
import logging
from pathlib import Path

from pipeline.confrontatie_tree import merge_review_neutraal
from scripts.argument_tree.agy_run_confrontatie_tree import DEFAULT_MODEL, REDACTIE_PROMPT_PATH, run_agy_prompt
from pipeline.extract_arguments import _extract_json

logger = logging.getLogger(__name__)

STRUCTURED_PATH = Path(__file__).parent.parent.parent / "data" / "export" / "argument-docs" / "stikstof-structured-only.json"
OUT_PATH = Path(__file__).parent.parent.parent / "data" / "export" / "argument-docs" / "stikstof-neutraal-test.json"


def run_neutrale_redactie(structured, topic_name, model, timeout):
    tree_json = json.dumps(structured, ensure_ascii=False, indent=2)
    prompt = REDACTIE_PROMPT_PATH.read_text().format(topic=topic_name, kant="", tree_json=tree_json)
    stdout, stderr, elapsed = run_agy_prompt(prompt, model, timeout, "redactie-neutraal", skip_permissions=True)
    logger.info("redactie-neutraal-call klaar in %.1fs", elapsed)
    if not stdout:
        raise SystemExit(f"leeg antwoord (stderr, eerste 2000 tekens): {stderr[:2000]}")
    review = _extract_json(stdout)
    if "beoordelingen" not in review:
        raise SystemExit(f"redactie-output mist 'beoordelingen'-veld: {stdout[:500]}")
    return review


def main():
    structured = json.loads(STRUCTURED_PATH.read_text())
    logger.info("structured geladen: %d nodes, %d relations", len(structured["nodes"]), len(structured["relations"]))

    review = run_neutrale_redactie(structured, "Stikstof", DEFAULT_MODEL, 1800)

    result = merge_review_neutraal(structured, review)
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    logger.info("-> %s", OUT_PATH)

    gist_by_id = {n["argument_id"]: n["gist"] for n in structured["nodes"]}
    print(f"\n{len(result['relations'])} relaties over van de {len(structured['relations'])} voorgestelde\n")
    for r in result["relations"]:
        if r["relation_type"] != "conflict":
            continue
        premises = ", ".join(gist_by_id.get(pid, str(pid)) for pid in r["premise_argument_ids"])
        target = gist_by_id.get(r["target_argument_id"], r["target_argument_id"])
        print(f"[{r['sterkte']}/{r['type']}] {premises} <-> {target}")
        print(f"    reden: {r['reden']}")
        if r.get("thema"):
            print(f"    thema: {r['thema']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
