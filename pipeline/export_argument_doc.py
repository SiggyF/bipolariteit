"""
Argumentexport voor de structureringsstap (pipeline/prompts/argument_tree_gemini.md,
zie scripts/argument_tree/agy_run_confrontatie_tree.py): dumpt alle pro/contra-argumenten
van één topic (met typologie, tags, onderbouwende claims) als leesbaar
markdown-document.

GEEN LLM-call -- puur een export, net als build_static_data.py. Bedoeld om
in een Gemini-chat te plakken/uploaden, samen met het bijbehorende
prompt-sjabloon (pipeline/prompts/argument_tree_gemini.md), omdat een lokaal
model de volle argumentenset niet in één context-venster kwijt kan (stikstof
heeft ~1500 pro+contra-argumenten -- zie de LIMIT=60-noodgreep in
build_argument_tree.py::fetch_stance_arguments). Gemini's veel grotere
contextvenster maakt het mogelijk om zelf, over de hele set, een subset van
elkaar weersprekende argumenten te kiezen en de onderbouwing (subordinatieve
steun) daaronder te leggen -- precies het handwerk dat we hier NIET
automatiseren.

Gebruik:
    uv run python -m pipeline.export_argument_doc --topic stikstof
    uv run python -m pipeline.export_argument_doc --topic stikstof --stances contra --limit 200
"""

import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path

from pipeline.build_static_data import _speaker_event_url
from pipeline.db import db
from pipeline.periodes import PeriodeIndex

logger = logging.getLogger(__name__)

# Losse map i.p.v. data/export/topics/ of data/export/argument-trees/: dit is
# geen frontend-input en geen boom-resultaat, maar een tussendocument voor
# een mens (of Gemini) om te lezen. Zie build_argument_tree.py voor dezelfde
# afweging bij TREE_EXPORT_DIR.
DOC_EXPORT_DIR = Path(__file__).parent.parent / "data" / "export" / "argument-docs"

VALID_STANCES = ("pro", "contra", "unclear")
STANCE_LABELS = {"pro": "Pro-argumenten", "contra": "Contra-argumenten", "unclear": "Onduidelijke argumenten"}


def fetch_stance_arguments(conn, topic_id, stance, vanaf, limit):
    """Alle argumenten van dit topic+standpunt, inclusief tags, claims
    (onderbouwing) en links naar het debat -- zonder de kunstmatige LIMIT=60
    van build_argument_tree.py::fetch_stance_arguments (deze export is niet
    bedoeld voor een lokaal model met een klein contextvenster)."""
    query = """SELECT ar.id, ar.quote_text, ar.typology, ac.name AS actor_name, ac.party AS actor_party,
                      d.tweedekamer_activiteit_url, d.video_url, d.published_at, d.speaker_event_anchor_at,
                      d.turn_type, d.is_voorzitter_turn
               FROM arguments ar
               JOIN actors ac ON ac.id = ar.actor_id
               JOIN documents d ON d.id = ar.document_id
               WHERE ar.topic_id = ? AND ar.stance = ? AND d.published_at >= ?
               ORDER BY ar.id"""
    params = [topic_id, stance, vanaf]
    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)
    rows = conn.execute(query, params).fetchall()

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

    claims_by_argument = {}
    for claim in conn.execute(
        """SELECT c.argument_id, c.claim_text, c.attributed_source_text
           FROM claims c
           JOIN arguments ar ON ar.id = c.argument_id
           WHERE ar.topic_id = ? AND ar.stance = ?""",
        (topic_id, stance),
    ).fetchall():
        claims_by_argument.setdefault(claim["argument_id"], []).append(
            {"claim_text": claim["claim_text"], "attributed_source_text": claim["attributed_source_text"]}
        )

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
                "claims": claims_by_argument.get(row["id"], []),
                "tweedekamer_activiteit_url": row["tweedekamer_activiteit_url"],
                "speaker_video_url": _speaker_event_url(
                    row["video_url"],
                    row["published_at"],
                    row["speaker_event_anchor_at"],
                    row["turn_type"],
                    row["is_voorzitter_turn"],
                ),
            }
        )
    return arguments


def _format_argument(arg):
    lines = [f'### id {arg["id"]}: {arg["typology"]}, {arg["actor_name"]} ({arg["actor_party"]})']
    lines.append(f'> {arg["quote_text"]}')
    if arg["tags"]:
        lines.append(f'Tags: {", ".join(arg["tags"])}')
    if arg["claims"]:
        lines.append("Onderbouwing (genoemde claims):")
        for claim in arg["claims"]:
            bron = f' (bron: {claim["attributed_source_text"]})' if claim["attributed_source_text"] else ""
            lines.append(f'- {claim["claim_text"]}{bron}')
    links = [url for url in (arg["tweedekamer_activiteit_url"], arg["speaker_video_url"]) if url]
    if links:
        lines.append(f'Link: {" · ".join(links)}')
    return "\n".join(lines)


def build_document(topic_row, stances_by_name):
    slug, name = topic_row["slug"], topic_row["name"]
    total = sum(len(args) for args in stances_by_name.values())
    lines = [
        f"# Argumentexport: {name} ({slug})",
        "",
        f"Gegenereerd: {datetime.now(timezone.utc).isoformat()}",
        f"Totaal aantal argumenten: {total}",
        "",
        "## Pro/contra-dimensie van dit onderwerp",
        "",
        # Zelfde definitie als bij de extractie (topics.description, zie
        # pipeline/prompts/extract_argument.md) -- zonder deze context is
        # "pro" en "contra" niet interpreteerbaar (het is geen intrinsieke
        # eigenschap van het argument, maar een classificatie t.o.v. déze
        # dimensie).
        topic_row["description"] or "(geen description ingesteld voor dit topic)",
        "",
        "**Voorbehoud:** de stance (pro/contra) hieronder komt uit een eerdere, "
        "niet-foutloze automatische classificatie -- vertrouw er niet blind op, "
        "het citaat zelf is leidend.",
        "",
    ]
    for stance, arguments in stances_by_name.items():
        lines.append(f"## {STANCE_LABELS[stance]} ({len(arguments)})")
        lines.append("")
        for arg in arguments:
            lines.append(_format_argument(arg))
            lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", required=True, help="topic-slug, bv. stikstof")
    parser.add_argument(
        "--stances", default="pro,contra", help="kommagescheiden lijst uit pro,contra,unclear (default pro,contra)"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="max aantal argumenten per standpunt (default: geen limiet -- dit document is voor Gemini's "
             "grote contextvenster, niet voor een lokaal model)",
    )
    parser.add_argument(
        "--vanaf", default=None, help="ISO-datum; overschrijft [verwerking].vanaf uit config/politieke-periodes.toml"
    )
    parser.add_argument("--out", default=None, help="uitvoerpad (default: data/export/argument-docs/<topic>.md)")
    parser.add_argument("--dry-run", action="store_true", help="niets wegschrijven, alleen printen")
    args = parser.parse_args()

    stances = [s.strip() for s in args.stances.split(",") if s.strip()]
    for stance in stances:
        if stance not in VALID_STANCES:
            raise SystemExit(f"ongeldig standpunt in --stances: {stance!r} (kies uit {VALID_STANCES})")

    conn = db.connect()
    topic_row = conn.execute("SELECT id, slug, name, description FROM topics WHERE slug = ?", (args.topic,)).fetchone()
    if topic_row is None:
        raise SystemExit(f"onbekende topic-slug: {args.topic}")

    vanaf = args.vanaf if args.vanaf is not None else PeriodeIndex().drempel

    stances_by_name = {}
    for stance in stances:
        arguments = fetch_stance_arguments(conn, topic_row["id"], stance, vanaf, args.limit)
        stances_by_name[stance] = arguments
        logger.info("topic=%s stance=%-8s %d argument(en)", topic_row["slug"], stance, len(arguments))

    conn.close()

    document = build_document(topic_row, stances_by_name)

    if args.dry_run:
        print(document)
        logger.info("(--dry-run: niets weggeschreven)")
        return

    out_path = Path(args.out) if args.out else DOC_EXPORT_DIR / f"{args.topic}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(document)
    logger.info("Argumentdocument -> %s", out_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
