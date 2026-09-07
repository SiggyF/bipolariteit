"""
Vervolgtest op scripts/test_rebuttal_detection.py: dezelfde functionele
"reageert B op de kern van A?"-vraag, maar nu alle conflict-relaties van een
topic in EEN call (batch) i.p.v. elk apart. Doel: nagaan of het eerdere
uniformiteitsprobleem specifiek aan de interpretatieve vragen lag (zoals we
concludeerden) of aan het batchen zelf -- als deze batch-versie ook
discrimineert, kan de productiepijplijn veel goedkoper met 1 call per topic
i.p.v. 1 call per relatie.

Vergelijk de uitkomst met data/export/argument-docs/<topic>-rebuttal-test.json
(de al bestaande, losse-call resultaten) voor dezelfde relaties.

Gebruik:
    PYTHONPATH=. uv run python scripts/test_rebuttal_detection_batch.py --topic stikstof
"""

import argparse
import json
import logging
from pathlib import Path

from scripts.agy_run_confrontatie_tree import DEFAULT_MODEL, run_agy_prompt
from pipeline.extract_arguments import _extract_json

logger = logging.getLogger(__name__)

DOCS_DIR = Path(__file__).parent.parent / "data" / "export" / "argument-docs"
PROMPT_PATH = Path(__file__).parent.parent / "pipeline" / "prompts" / "boomredactie_rebuttal_detection_batch.md"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", default="stikstof")
    args = parser.parse_args()

    structured = json.loads((DOCS_DIR / f"{args.topic}-structured-only.json").read_text())
    gist_by_id = {n["argument_id"]: n["gist"] for n in structured["nodes"]}
    conflicts = [r for r in structured["relations"] if r["relation_type"] == "conflict"]
    logger.info("topic=%s: %d conflict-relaties in 1 batch-call", args.topic, len(conflicts))

    mini = {"nodes": structured["nodes"], "relations": conflicts}
    tree_json = json.dumps(mini, ensure_ascii=False, indent=2)
    prompt = PROMPT_PATH.read_text().format(topic=args.topic.capitalize(), tree_json=tree_json)
    stdout, stderr, elapsed = run_agy_prompt(prompt, DEFAULT_MODEL, 1800, "rebuttal-detection-batch", skip_permissions=True)
    logger.info("batch-call klaar in %.1fs", elapsed)
    if not stdout:
        raise SystemExit(f"leeg antwoord (stderr, eerste 2000 tekens): {stderr[:2000]}")
    review = _extract_json(stdout)

    out_path = DOCS_DIR / f"{args.topic}-rebuttal-batch-test.json"
    uitkomsten = []
    print(f"\n{len(conflicts)} conflict-relaties (1 batch-call)\n")
    for i, relation in enumerate(conflicts):
        b = next((x for x in review["beoordelingen"] if x["relation_index"] == i), {})
        premises = ", ".join(gist_by_id.get(pid, str(pid)) for pid in relation["premise_argument_ids"])
        target = gist_by_id.get(relation["target_argument_id"], relation["target_argument_id"])
        print(f"[{b.get('reageert_op_kern')}] {premises} <-> {target}")
        print(f"    reden: {b.get('reden')}")
        uitkomsten.append({
            "premise_gist": premises, "target_gist": target,
            "reageert_op_kern": b.get("reageert_op_kern"), "reden": b.get("reden"),
        })
    out_path.write_text(json.dumps(uitkomsten, ensure_ascii=False, indent=2))
    logger.info("-> %s", out_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
