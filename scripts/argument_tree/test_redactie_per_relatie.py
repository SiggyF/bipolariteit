"""
Vervolg op scripts/argument_tree/test_bidirectionele_redactie.py: test of de perfecte
uniformiteit (8 van de 8 conflict-relaties kregen steeds hetzelfde label,
over drie verschillende prompt-versies heen) een batch-effect is -- het
model leest alle relaties in één call en herhaalt zijn eerste
interpretatiekader voor de rest -- of een echte beperking van het model op
deze taak. Roept boomredactie.md nu APART aan per relatie (elke call ziet
maar één relatie + de erbij horende nodes), zodat onderlinge besmetting
tussen relaties binnen één antwoord onmogelijk is.

Gebruik:
    PYTHONPATH=. uv run python scripts/argument_tree/test_redactie_per_relatie.py
"""

import json
import logging
from pathlib import Path

from pipeline.confrontatie_tree import merge_review_neutraal
from scripts.argument_tree.agy_run_confrontatie_tree import DEFAULT_MODEL, REDACTIE_PROMPT_PATH, run_agy_prompt
from pipeline.extract_arguments import _extract_json

logger = logging.getLogger(__name__)

STRUCTURED_PATH = Path(__file__).parent.parent.parent / "data" / "export" / "argument-docs" / "stikstof-structured-only.json"
OUT_PATH = Path(__file__).parent.parent.parent / "data" / "export" / "argument-docs" / "stikstof-per-relatie-test.json"


def _nodes_for(structured, relation):
    ids = set(relation["premise_argument_ids"]) | {relation["target_argument_id"]}
    return [n for n in structured["nodes"] if n["argument_id"] in ids]


def run_one(structured, relation, topic_name, model, timeout):
    mini = {
        "nodes": _nodes_for(structured, relation),
        "relations": [relation],
        "coordinatieve_groepen": [],
        "twijfelachtige_classificaties": [],
    }
    tree_json = json.dumps(mini, ensure_ascii=False, indent=2)
    prompt = REDACTIE_PROMPT_PATH.read_text().format(topic=topic_name, kant="", tree_json=tree_json)
    stdout, stderr, elapsed = run_agy_prompt(prompt, model, timeout, "redactie-los", skip_permissions=True)
    logger.info("call klaar in %.1fs", elapsed)
    if not stdout:
        raise SystemExit(f"leeg antwoord (stderr, eerste 2000 tekens): {stderr[:2000]}")
    review = _extract_json(stdout)
    if "beoordelingen" not in review or not review["beoordelingen"]:
        raise SystemExit(f"redactie-output mist 'beoordelingen'-veld: {stdout[:500]}")
    return review["beoordelingen"][0]


def main():
    structured = json.loads(STRUCTURED_PATH.read_text())
    gist_by_id = {n["argument_id"]: n["gist"] for n in structured["nodes"]}
    conflicts = [r for r in structured["relations"] if r["relation_type"] == "conflict"]
    logger.info("%d conflict-relaties, elk in een aparte call", len(conflicts))

    print(f"\n{len(conflicts)} conflict-relaties, elk apart beoordeeld\n")
    for relation in conflicts:
        b = run_one(structured, relation, "Stikstof", DEFAULT_MODEL, 1800)
        premises = ", ".join(gist_by_id.get(pid, str(pid)) for pid in relation["premise_argument_ids"])
        target = gist_by_id.get(relation["target_argument_id"], relation["target_argument_id"])
        print(f"[{b.get('sterkte')}/{b.get('type')}] {premises} <-> {target}")
        print(f"    reden: {b.get('reden')}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
