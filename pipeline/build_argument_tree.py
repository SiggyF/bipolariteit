"""
Argumentenboom: groepeert de reeds geëxtraheerde argumenten van één topic per
standpunt (pro/contra/unclear) in een klein aantal inhoudelijke clusters,
als voorbereiding op een d2-diagram (zie render_argument_tree.py).

De boom-top (topic -> standpunt) staat al vast uit het bestaande datamodel
(`arguments.stance`) en wordt hier NIET door een LLM bedacht -- alleen de
laag daaronder (welke argumenten dezelfde onderliggende reden delen -- of
juist een reden voor elkaar zijn -- en hoe een coördinatieve groep heet)
komt van het model. Zie pipeline/prompts/argument_tree.md voor de precieze
instructie. `_validate_tree()` garandeert dat elk argument in de output een
bestaand, letterlijk argument-id is: de LLM kan nooit een argument
verzinnen of laten verdwijnen, hooguit fout structureren.

De groeperingsaanpak is nog experimenteel (zie pipeline/prompts/argument_tree.md).
Daarom schrijft dit script naar een losse JSON-export
(data/export/argument-trees/<slug>.json, bewust NIET in data/export/topics/
zelf -- zie TREE_EXPORT_DIR) in plaats van naar SQLite -- geen schema-migratie
nodig zolang de vorm van de boom nog verandert.

Gebruik:
    uv run python -m pipeline.build_argument_tree --topic stikstof
    uv run python -m pipeline.build_argument_tree --topic stikstof --dry-run
"""

import argparse
import hashlib
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from pipeline.db import db
from pipeline.periodes import PeriodeIndex

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = (Path(__file__).parent / "prompts" / "argument_tree.md").read_text()
PROMPT_VERSION = hashlib.sha256(PROMPT_TEMPLATE.encode()).hexdigest()[:12]

# Losse map i.p.v. data/export/topics/ zelf: alle frontend-pagina's globben
# "data/export/topics/*.json" en verwachten daar een volledige topic-export
# (.slug/.name/.arguments) -- een <slug>-tree.json ertussen zou die glob op
# meerdere plekken breken (dubbele getStaticPaths-entries, mod.default.arguments
# is undefined). Zie frontend/src/pages/topics/[slug].astro.
TREE_EXPORT_DIR = Path(__file__).parent.parent / "data" / "export" / "argument-trees"

VALID_STANCES = ("pro", "contra", "unclear")
QUOTE_PREVIEW_LEN = 220

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _extract_json(raw_text):
    fence_match = _JSON_FENCE_RE.search(raw_text)
    candidate = fence_match.group(1) if fence_match else raw_text.strip()
    return json.loads(candidate)


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
    return content, usage, finish_reason


def fetch_stance_arguments(conn, topic_id, stance, vanaf):
    """Argumenten van dit topic+standpunt, met alles wat de d2-render nodig
    heeft (quote_text, actor) zodat build_argument_tree.py en
    render_argument_tree.py niet allebei los de database hoeven te lezen --
    de boom-JSON is zelf de volledige input voor de render-stap."""
    rows = conn.execute(
        """SELECT ar.id, ar.quote_text, ar.typology, ac.name AS actor_name, ac.party AS actor_party
           FROM arguments ar
           JOIN actors ac ON ac.id = ar.actor_id
           JOIN documents d ON d.id = ar.document_id
           WHERE ar.topic_id = ? AND ar.stance = ? AND d.published_at >= ?
           ORDER BY ar.id""",
        (topic_id, stance, vanaf),
    ).fetchall()

    tags_by_argument = {}
    for tag in conn.execute(
        """SELECT at.argument_id, t.sleutel
           FROM argument_tags at
           JOIN tags t ON t.sleutel = at.tag_sleutel
           JOIN arguments ar ON ar.id = at.argument_id
           WHERE ar.topic_id = ? AND ar.stance = ? AND t.active = 1""",
        (topic_id, stance),
    ).fetchall():
        tags_by_argument.setdefault(tag["argument_id"], []).append(tag["sleutel"])

    arguments = []
    for row in rows:
        arguments.append(
            {
                "id": row["id"],
                "quote_text": row["quote_text"],
                "typology": row["typology"],
                "actor_name": row["actor_name"],
                "actor_party": row["actor_party"],
                "tags": tags_by_argument.get(row["id"], []),
            }
        )
    return arguments


def _format_arguments_block(arguments):
    lines = []
    for arg in arguments:
        quote = arg["quote_text"]
        preview = quote if len(quote) <= QUOTE_PREVIEW_LEN else quote[:QUOTE_PREVIEW_LEN].rstrip() + "…"
        tags_suffix = f" [tags: {', '.join(arg['tags'])}]" if arg["tags"] else ""
        lines.append(f'- id {arg["id"]} ({arg["typology"]}): "{preview}"{tags_suffix}')
    return "\n".join(lines) if lines else "(geen)"


def _validate_node(node, valid_ids, seen_ids):
    """Eén knoop is óf een los argument (`argument_id`) óf een coördinatieve
    groep (`label` + >=2 `argument_ids`); beide mogen `children` hebben
    (subordinatieve argumenten die dít specifieke argument/deze groep
    verdedigen). `seen_ids` wordt gedeeld over de hele boom zodat een
    argument-id nooit op twee plekken tegelijk kan opduiken (bv. als
    top-level argument én als subordinatief kind elders)."""
    if not isinstance(node, dict):
        raise ValueError(f"knoop is geen object maar {type(node).__name__}")

    has_argument_id = "argument_id" in node
    has_label = "label" in node
    if has_argument_id == has_label:
        raise ValueError(f"knoop moet óf 'argument_id' óf 'label'+'argument_ids' hebben, niet beide/geen: {node!r}")

    if has_argument_id:
        ids = [node["argument_id"]]
    else:
        ids = node.get("argument_ids")
        if not isinstance(ids, list) or len(ids) < 2:
            raise ValueError(f"coördinatieve groep '{node.get('label')}' heeft geen >=2 argument_ids: {node!r}")

    for argument_id in ids:
        if argument_id not in valid_ids:
            raise ValueError(f"onbekend argument_id {argument_id!r} in knoop {node!r}")
        if argument_id in seen_ids:
            raise ValueError(f"argument_id {argument_id} komt meer dan één keer voor in de boom")
        seen_ids.add(argument_id)

    children = node.get("children") or []
    if not isinstance(children, list):
        raise ValueError(f"'children' moet een lijst zijn: {node!r}")
    validated_children = [_validate_node(child, valid_ids, seen_ids) for child in children]

    result = {"argument_id": node["argument_id"]} if has_argument_id else {
        "label": node["label"],
        "argument_ids": list(ids),
    }
    result["children"] = validated_children
    return result


def _validate_tree(parsed, valid_ids):
    """Faalt hard (geen silent-drop) als de LLM een argument verzint,
    weglaat, of dubbel indeelt -- precies wat de "elk argument moet concreet
    genoemd zijn"-eis van de boom afdwingt."""
    if not isinstance(parsed, dict) or not isinstance(parsed.get("nodes"), list) or not parsed["nodes"]:
        raise ValueError(f"onverwachte JSON-vorm: verwacht {{'nodes': [...]}}, kreeg {type(parsed).__name__}")

    seen_ids = set()
    nodes = [_validate_node(node, valid_ids, seen_ids) for node in parsed["nodes"]]

    missing = valid_ids - seen_ids
    if missing:
        raise ValueError(f"argument_id(s) {sorted(missing)} ontbreken in de boom")

    return nodes


def build_stance_nodes(base_url, model, reasoning_effort, timeout, max_tokens, topic_name, stance, arguments):
    if not arguments:
        return []

    prompt = PROMPT_TEMPLATE.format(
        topic=topic_name,
        stance=stance,
        arguments_block=_format_arguments_block(arguments),
    )
    raw_content, usage, finish_reason = call_llm(base_url, model, prompt, reasoning_effort, timeout, max_tokens)
    if finish_reason == "length":
        raise ValueError(f"antwoord afgekapt op max_tokens={max_tokens} (verhoog --max-tokens)")
    parsed = _extract_json(raw_content)
    valid_ids = {arg["id"] for arg in arguments}
    return _validate_tree(parsed, valid_ids)


def fetch_oppositions(conn, argument_ids):
    """Weerleg-links tussen argumenten die allebei in déze boom zitten --
    beide kanten moeten aanwezig zijn, anders wijst een weerleg-pijl in het
    diagram naar een argument dat niet getekend wordt. Alleen `direct_rebuttal`:
    dat is de relatie die visueel als "onderuithalen" gelezen mag worden;
    `thematic` is een losser verband en zou de stut-metafoor te makkelijk
    ondermijnen zonder dat er echt weerlegd wordt (zie argument_oppositions
    in pipeline/db/schema.sql)."""
    if not argument_ids:
        return []
    placeholders = ",".join("?" * len(argument_ids))
    rows = conn.execute(
        f"""SELECT argument_a_id, argument_b_id, confidence
            FROM argument_oppositions
            WHERE relation_type = 'direct_rebuttal'
              AND argument_a_id IN ({placeholders})
              AND argument_b_id IN ({placeholders})""",
        (*argument_ids, *argument_ids),
    ).fetchall()
    return [
        {"argument_a_id": row["argument_a_id"], "argument_b_id": row["argument_b_id"], "confidence": row["confidence"]}
        for row in rows
    ]


def build_topic_tree(base_url, model, reasoning_effort, timeout, max_tokens, conn, topic_row, vanaf, stances):
    topic_id, topic_name = topic_row["id"], topic_row["name"]
    arguments_by_id = {}
    stance_results = []

    for stance in stances:
        arguments = fetch_stance_arguments(conn, topic_id, stance, vanaf)
        for arg in arguments:
            arguments_by_id[arg["id"]] = arg

        nodes = build_stance_nodes(
            base_url, model, reasoning_effort, timeout, max_tokens, topic_name, stance, arguments
        )
        stance_results.append({"stance": stance, "argument_count": len(arguments), "nodes": nodes})
        logger.info(
            "topic=%s stance=%-8s %d argument(en) -> %d top-level knoop/knopen",
            topic_row["slug"], stance, len(arguments), len(nodes),
        )

    oppositions = fetch_oppositions(conn, list(arguments_by_id.keys()))
    logger.info("topic=%s %d weerleg-link(s) tussen getekende argumenten", topic_row["slug"], len(oppositions))

    return {
        "slug": topic_row["slug"],
        "name": topic_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "prompt_version": PROMPT_VERSION,
        "model": model,
        "stances": stance_results,
        "arguments": arguments_by_id,
        "oppositions": oppositions,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", required=True, help="topic-slug, bv. stikstof")
    parser.add_argument(
        "--stances", default="pro,contra", help="kommagescheiden lijst uit pro,contra,unclear (default pro,contra)"
    )
    parser.add_argument("--model", default="qwen/qwen3.6-27b")
    parser.add_argument("--base-url", default="http://localhost:1234/v1")
    parser.add_argument("--reasoning-effort", default="none")
    parser.add_argument("--max-tokens", type=int, default=4000)
    parser.add_argument("--timeout", type=float, default=400.0)
    parser.add_argument(
        "--vanaf", default=None, help="ISO-datum; overschrijft [verwerking].vanaf uit data/politieke-periodes.toml"
    )
    parser.add_argument("--dry-run", action="store_true", help="niets wegschrijven, alleen printen")
    args = parser.parse_args()

    stances = [s.strip() for s in args.stances.split(",") if s.strip()]
    for stance in stances:
        if stance not in VALID_STANCES:
            raise SystemExit(f"ongeldig standpunt in --stances: {stance!r} (kies uit {VALID_STANCES})")

    conn = db.connect()
    topic_row = conn.execute("SELECT id, slug, name FROM topics WHERE slug = ?", (args.topic,)).fetchone()
    if topic_row is None:
        raise SystemExit(f"onbekende topic-slug: {args.topic}")

    vanaf = args.vanaf if args.vanaf is not None else PeriodeIndex().drempel

    start = time.monotonic()
    tree = build_topic_tree(
        args.base_url, args.model, args.reasoning_effort, args.timeout, args.max_tokens,
        conn, topic_row, vanaf, stances,
    )
    conn.close()
    elapsed = time.monotonic() - start

    total_nodes = sum(len(s["nodes"]) for s in tree["stances"])
    total_arguments = len(tree["arguments"])
    logger.info(
        "Klaar in %.1fs: %d argumenten in %d top-level knopen (prompt_version=%s, model=%s)",
        elapsed, total_arguments, total_nodes, PROMPT_VERSION, args.model,
    )

    if args.dry_run:
        print(json.dumps(tree, ensure_ascii=False, indent=2))
        logger.info("(--dry-run: niets weggeschreven)")
        return

    TREE_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = TREE_EXPORT_DIR / f"{args.topic}.json"
    out_path.write_text(json.dumps(tree, ensure_ascii=False, indent=2))
    logger.info("Boom-JSON -> %s", out_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
