"""
Draait de argumentenboom-structurering (pipeline/prompts/argument_tree_gemini.md)
niet-interactief via `agy` in Docker (docker/agy/Dockerfile), i.p.v. het
argumentdocument + de prompt handmatig in een Gemini-chat te plakken.
Bouwt het argumentdocument zelf op (dezelfde functies als
pipeline/export_argument_doc.py -- geen tussenbestand nodig) en schrijft
Gemini's ruwe structurering direct naar
data/export/argument-docs/<topic>-gemini-tree.json, zodat
`make confrontatie-export TOPIC=<topic>` daarna zonder handmatige tussenstap
kan draaien.

In tegenstelling tot de extractie-/tagging-agy-scripts (honderden calls,
dus een goedkoop `flash-low`-model) is dit één call per topic -- de default
is daarom een zwaarder model. Zie
docs/design/argumentenboom/thema-en-samenvatting-workflow.md voor de volledige
workflow en hoe je itereert als de output niet scherp/leesbaar genoeg is.

Vereist: `docker build -t bipolariteit-agy docker/agy` en een eenmalige
interactieve login (zie docs/handoff.md, sectie "Antigravity CLI (agy) in
Docker") -- dezelfde `~/.bipolariteit/agy_gemini_config`-sessie als de
extractie-/tagging-agy-scripts.

Gebruik:
    PYTHONPATH=. uv run python scripts/agy_run_confrontatie_tree.py --topic stikstof
    PYTHONPATH=. uv run python scripts/agy_run_confrontatie_tree.py --topic stikstof --model gemini-3.6-flash-medium
"""

import argparse
import json
import logging
import subprocess
import time
from pathlib import Path

from pipeline.db import db
from pipeline.export_argument_doc import build_document, fetch_stance_arguments
from pipeline.extract_arguments import _extract_json
from pipeline.periodes import PeriodeIndex

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "pipeline" / "prompts" / "argument_tree_gemini.md"
GEMINI_TREE_DIR = Path(__file__).parent.parent / "data" / "export" / "argument-docs"

# Buiten de repo (bevat een live OAuth-token, nooit in een git-repo laten
# staan) -- zelfde sessie als scripts/agy_run_extraction_batch.py.
AGY_GEMINI_CONFIG_DIR = str(Path.home() / ".bipolariteit" / "agy_gemini_config")

# Eén call per topic i.p.v. honderden zoals bij extractie/tagging -- de
# extra kosten/tijd van een zwaarder model wegen hier niet zwaar, en dit is
# inhoudelijk lastiger werk (structureren + scherpe thema's + samenvatten)
# dan de per-document-extractie waar `flash-low` voor gekozen is.
DEFAULT_MODEL = "gemini-3.6-flash-high"


def run_agy(prompt, model, timeout):
    result = subprocess.run(
        [
            "docker", "run", "--rm",
            "-v", f"{AGY_GEMINI_CONFIG_DIR}:/home/agy/.gemini",
            "bipolariteit-agy",
            "agy", "--print", prompt,
            "--model", model,
            "--sandbox",
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.stdout.strip(), result.stderr.strip()


def build_prompt(conn, topic_row, stances, vanaf):
    stances_by_name = {
        stance: fetch_stance_arguments(conn, topic_row["id"], stance, vanaf, limit=None) for stance in stances
    }
    document = build_document(topic_row, stances_by_name)
    prompt_template = PROMPT_PATH.read_text()
    total = sum(len(v) for v in stances_by_name.values())
    return f"{document}\n\n{prompt_template.format(topic=topic_row['name'])}", total


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", required=True, help="topic-slug, bv. stikstof")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"agy-model (default {DEFAULT_MODEL})")
    parser.add_argument("--stances", default="pro,contra", help="kommagescheiden lijst, default pro,contra")
    parser.add_argument("--vanaf", default=None, help="ISO-datum; overschrijft [verwerking].vanaf")
    parser.add_argument(
        "--out", default=None, help="uitvoerpad (default: data/export/argument-docs/<topic>-gemini-tree.json)"
    )
    parser.add_argument("--timeout", type=int, default=1800, help="timeout in seconden voor de agy-call (default 1800)")
    parser.add_argument("--dry-run", action="store_true", help="alleen de opgebouwde prompt printen, geen agy-call")
    args = parser.parse_args()

    stances = [s.strip() for s in args.stances.split(",") if s.strip()]

    conn = db.connect()
    topic_row = conn.execute("SELECT id, slug, name, description FROM topics WHERE slug = ?", (args.topic,)).fetchone()
    if topic_row is None:
        raise SystemExit(f"onbekende topic-slug: {args.topic}")

    vanaf = args.vanaf if args.vanaf is not None else PeriodeIndex().drempel
    prompt, total_args = build_prompt(conn, topic_row, stances, vanaf)
    conn.close()

    logger.info(
        "topic=%s model=%s %d argumenten, promptlengte %d tekens", topic_row["slug"], args.model, total_args, len(prompt)
    )

    if args.dry_run:
        print(prompt)
        logger.info("(--dry-run: geen agy-call)")
        return

    start = time.monotonic()
    stdout, stderr = run_agy(prompt, args.model, args.timeout)
    elapsed = time.monotonic() - start
    logger.info("agy-call klaar in %.1fs", elapsed)

    if not stdout:
        raise SystemExit(f"leeg antwoord van agy (stderr: {stderr[:2000]})")

    try:
        parsed = _extract_json(stdout)
    except Exception as exc:
        raise SystemExit(
            f"agy-output is geen geldige JSON ({exc}); niet weggeschreven.\n--- ruwe output ---\n{stdout}"
        )

    out_path = Path(args.out) if args.out else GEMINI_TREE_DIR / f"{args.topic}-gemini-tree.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2))
    logger.info("Gemini-tree -> %s", out_path)
    if "toelichting" in parsed:
        logger.info("Toelichting van Gemini: %s", parsed["toelichting"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
