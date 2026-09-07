"""
Test van aanbeveling 4 uit het onderzoeksrapport (docs/research/
Betrouwbaarheid LLM Argumentrelaties.md): i.p.v. een geldigheidsoordeel
("houdt deze relatie logisch stand") een zuiver functionele, feitelijke
vraag stellen -- vergelijkbaar met IBM Project Debater se "rebuttal
detection": reageert argument B aantoonbaar op de kern van argument A, ja
of nee? Geen categorieen, geen interpretatie, geen rol.

Elke relatie in een eigen, geisoleerde call (zoals scripts/
test_redactie_per_relatie.py) op dezelfde 8 conflict-relaties van stikstof,
om te zien of dit wel discrimineert waar de eerdere vier ontwerpen dat niet
deden.

Gebruik:
    PYTHONPATH=. uv run python scripts/test_rebuttal_detection.py --topic stikstof
    PYTHONPATH=. uv run python scripts/test_rebuttal_detection.py --topic abortus
"""

import argparse
import json
import logging
from pathlib import Path

from scripts.agy_run_confrontatie_tree import DEFAULT_MODEL, run_agy_prompt
from pipeline.extract_arguments import _extract_json

logger = logging.getLogger(__name__)

DOCS_DIR = Path(__file__).parent.parent / "data" / "export" / "argument-docs"
PROMPT_PATH = Path(__file__).parent.parent / "pipeline" / "prompts" / "boomredactie_rebuttal_detection.md"


def _nodes_for(structured, relation):
    ids = set(relation["premise_argument_ids"]) | {relation["target_argument_id"]}
    return [n for n in structured["nodes"] if n["argument_id"] in ids]


def run_one(structured, relation, topic_name, model, timeout):
    mini = {"nodes": _nodes_for(structured, relation), "relations": [relation]}
    tree_json = json.dumps(mini, ensure_ascii=False, indent=2)
    prompt = PROMPT_PATH.read_text().format(topic=topic_name, tree_json=tree_json)
    stdout, stderr, elapsed = run_agy_prompt(prompt, model, timeout, "rebuttal-detection", skip_permissions=True)
    logger.info("call klaar in %.1fs", elapsed)
    if not stdout:
        raise SystemExit(f"leeg antwoord (stderr, eerste 2000 tekens): {stderr[:2000]}")
    return _extract_json(stdout)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", default="stikstof")
    args = parser.parse_args()

    structured_path = DOCS_DIR / f"{args.topic}-structured-only.json"
    out_path = DOCS_DIR / f"{args.topic}-rebuttal-test.json"
    structured = json.loads(structured_path.read_text())
    gist_by_id = {n["argument_id"]: n["gist"] for n in structured["nodes"]}
    conflicts = [r for r in structured["relations"] if r["relation_type"] == "conflict"]
    logger.info("topic=%s: %d conflict-relaties, elk apart, functionele ja/nee-vraag", args.topic, len(conflicts))

    print(f"\n{len(conflicts)} conflict-relaties\n")
    uitkomsten = []
    for relation in conflicts:
        result = run_one(structured, relation, args.topic.capitalize(), DEFAULT_MODEL, 1800)
        premises = ", ".join(gist_by_id.get(pid, str(pid)) for pid in relation["premise_argument_ids"])
        target = gist_by_id.get(relation["target_argument_id"], relation["target_argument_id"])
        print(f"[{result.get('reageert_op_kern')}] {premises} <-> {target}")
        print(f"    reden: {result.get('reden')}")
        uitkomsten.append({
            "premise_gist": premises,
            "target_gist": target,
            "premise_argument_ids": relation["premise_argument_ids"],
            "target_argument_id": relation["target_argument_id"],
            "reageert_op_kern": result.get("reageert_op_kern"),
            "reden": result.get("reden"),
        })
        # Na elke call wegschrijven, niet pas aan het eind -- zo staat er ook
        # iets bruikbaars klaar als een latere call in de reeks vastloopt.
        out_path.write_text(json.dumps(uitkomsten, ensure_ascii=False, indent=2))

    logger.info("-> %s", out_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
