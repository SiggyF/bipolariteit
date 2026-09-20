"""
Stap 3 voor issue #254 (canonieke KPA-clustering, RFC-fase 1, #175): bouwt
het argumentexport-document (pipeline/export_argument_doc.py, de invoer voor
de structureringsstap pipeline/prompts/argument_tree_gemini.md) opnieuw op,
maar met bijna-identieke citaten binnen dezelfde stance samengevoegd tot één
canonieke stelling (instances + weight_by_party) i.p.v. losse, herhalende
entries.

Aanleiding: verificatie tegen de al-gebouwde argumentenbomen
(data/export/argument-trees/*.json) laat zien dat de bestaande structurerings-
stap al zo agressief subsampelt (15-30 van de honderden/duizenden argumenten
per kant) dat bijna-duplicaten zelden allebei de uiteindelijke boom halen --
samenvoegen ná de structureringsstap (in build_confrontatie_export.py) heeft
dus vrijwel niets om samen te voegen. Dit script voegt daarom samen VÓÓR
Gemini het document ziet, zodat Gemini kiest tussen canonieke stellingen
(met zichtbaar partijgewicht) i.p.v. tussen losse, deels overlappende quotes.

NOG NIET gewired in scripts/argument_tree/agy_run_confrontatie_tree.py of
pipeline/prompts/argument_tree_gemini.md -- dit is de losse, verifieerbare
bouwsteen; wiring is een aparte, kleinere stap zodra dit document zelf
gecontroleerd is.

Verificatie (zie --report, staat aan by default):
- documentgrootte vóór/na (aantal entries dat Gemini zou moeten doorlezen)
- afgedrukte canonieke entries (claim + instances + weight_by_party) voor
  handmatige steekproef, zodat je kunt zien of samenvoeging klopt vóórdat
  dit ooit een Gemini-call kost

Gebruik:
    uv run python scripts/argument_tree/experiment_canonical_claim_document.py --topic stikstof
    uv run python scripts/argument_tree/experiment_canonical_claim_document.py --topic stikstof \
        --model qwen/qwen3.8-27b --out /tmp/stikstof-canoniek.md
"""
import argparse
from pathlib import Path

from pipeline.db import db
from pipeline.embed.lmstudio import detect_base_url, embed_texts
from pipeline.export_argument_doc import STANCE_LABELS, VALID_STANCES, _format_argument, fetch_stance_arguments
from pipeline.periodes import PeriodeIndex
from scripts.argument_tree.experiment_canonical_claim_clustering import DEFAULT_DISTANCE_THRESHOLD, build_canonical_clusters
from scripts.argument_tree.experiment_canonical_claim_naming import name_cluster
from scripts.argument_tree.experiment_find_similar_arguments import MODEL as EMBED_MODEL

DOC_EXPORT_DIR = Path(__file__).parent.parent.parent / "data" / "export" / "argument-docs"


def cluster_by_stance(arguments, stance, base_url, distance_threshold):
    """`arguments` komt uit fetch_stance_arguments -- allemaal dezelfde
    stance, dus hier geen stance-splitsing meer nodig (in tegenstelling tot
    build_canonical_clusters, dat over meerdere stances tegelijk werkt)."""
    texts = [a["quote_text"] for a in arguments]
    ids = [a["id"] for a in arguments]
    parties = [a["actor_party"] or "onbekend" for a in arguments]
    vectors = embed_texts(base_url, texts, EMBED_MODEL)
    stances = [stance] * len(arguments)
    return build_canonical_clusters(ids, vectors, texts, stances, parties, distance_threshold), vectors


def format_canonical_entry(cluster, by_id, canonical_claim):
    """Analoog aan _format_argument, maar voor een samengevoegd cluster:
    de canonieke stelling voorop, dan elk brondquote met spreker/partij
    eronder -- zodat de redactiestap (en een mens die dit document leest)
    nog steeds bij elk lid het letterlijke citaat en de link terugvindt."""
    ids_str = ",".join(str(i) for i in cluster["instances"])
    weight_str = ", ".join(f"{party}: {n}" for party, n in sorted(cluster["weight_by_party"].items(), key=lambda kv: -kv[1]))
    lines = [
        f'### canonieke stelling (instances: {ids_str}): {weight_str}',
        f"> {canonical_claim}",
        "Brondquotes:",
    ]
    for instance_id in cluster["instances"]:
        arg = by_id[instance_id]
        lines.append(f'- id {arg["id"]}, {arg["actor_name"]} ({arg["actor_party"]}): "{arg["quote_text"][:200]}"')
    return "\n".join(lines)


def build_canonical_document(topic_row, stances_by_name, base_url, model, distance_threshold, reasoning_effort, timeout, max_tokens):
    entries_by_stance = {}
    stats = {}
    for stance, arguments in stances_by_name.items():
        if not arguments:
            entries_by_stance[stance] = []
            stats[stance] = (0, 0)
            continue
        clusters, _ = cluster_by_stance(arguments, stance, base_url, distance_threshold)
        by_id = {a["id"]: a for a in arguments}

        multi_count = sum(1 for c in clusters if len(c["instances"]) > 1)
        named = 0
        entries = []
        for cluster in clusters:
            if len(cluster["instances"]) == 1:
                entries.append(_format_argument(by_id[cluster["instances"][0]]))
            else:
                named += 1
                print(f"  [{stance}] cluster {named}/{multi_count} benoemen (n={len(cluster['instances'])})...")
                claim = name_cluster(cluster, topic_row["slug"], base_url, model, reasoning_effort, timeout, max_tokens)
                entries.append(format_canonical_entry(cluster, by_id, claim))
        entries_by_stance[stance] = entries
        stats[stance] = (len(arguments), len(entries))

    return entries_by_stance, stats


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--stances", default="pro,contra")
    parser.add_argument("--vanaf", default=None)
    parser.add_argument("--threshold", type=float, default=DEFAULT_DISTANCE_THRESHOLD)
    parser.add_argument("--model", default="qwen/qwen3.8-27b", help="chat-model voor het benoemen van clusters")
    parser.add_argument("--reasoning-effort", default="none")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--max-tokens", type=int, default=500)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--out", default=None, help="uitvoerpad (default: geen, alleen --report)")
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
    stances_by_name = {stance: fetch_stance_arguments(conn, topic_row["id"], stance, vanaf, limit=None) for stance in stances}
    conn.close()

    base_url = detect_base_url(args.base_url)
    entries_by_stance, stats = build_canonical_document(
        topic_row, stances_by_name, base_url, args.model, args.threshold, args.reasoning_effort, args.timeout, args.max_tokens,
    )

    print(f"\ntopic={topic_row['slug']}")
    for stance in stances:
        before, after = stats[stance]
        print(f"  {STANCE_LABELS[stance]}: {before} argumenten -> {after} entries voor Gemini "
              f"({before - after} samengevoegd, {100 * (before - after) / before:.1f}% reductie)" if before else
              f"  {STANCE_LABELS[stance]}: geen argumenten")

    print("\n--- voorbeeld canonieke entries (eerste 5 met >1 instance per stance) ---")
    for stance in stances:
        shown = 0
        for entry in entries_by_stance[stance]:
            if "canonieke stelling" in entry and shown < 5:
                print(f"\n[{stance}]\n{entry}")
                shown += 1

    if args.out:
        lines = [f"# Canoniek argumentexport: {topic_row['name']} ({topic_row['slug']})", ""]
        for stance in stances:
            lines.append(f"## {STANCE_LABELS[stance]} ({len(entries_by_stance[stance])} entries)")
            lines.append("")
            lines.extend(entries_by_stance[stance])
            lines.append("")
        Path(args.out).write_text("\n".join(lines))
        print(f"\nweggeschreven naar {args.out}")


if __name__ == "__main__":
    main()
