"""
Sanity-check op clusterlabel-kwaliteit na een labeling-run (`make label-clusters`).

Aanleiding: de ~90 voor/na-casussen in docs/cluster-labeling-werkwijze.md laten
een aantal terugkerende faalpatronen zien in TF-IDF/LLM-gegenereerde
clusterlabels (zie het #356-plan-comment op issue #356):
- A. Terugkerend generiek label (dezelfde naam op veel clusters)
- B. Ouder-kind-tautologie (kind herhaalt (een variant van) de oudernaam)
- D. Persoons-/partijnamen i.p.v. een inhoudelijk onderwerp
- H. Te lang/samengesteld label i.p.v. één krachtig woord

Dit script rapporteert alleen -- het past niets automatisch toe (conform
docs/cluster-labeling-werkwijze.md: "wijzigingen worden nooit en bloc
geautomatiseerd doorgevoerd"). De output is input voor een handmatige
correctieronde via config/<label>/cluster_label_overrides.toml.

Gebruik:
    uv run python scripts/check_cluster_label_quality.py \\
        --clusters-json data/export/plenair-map/plenair-map-clusters-full.json
"""
import json
import re
from collections import defaultdict
from pathlib import Path

import click

from pipeline.db import db
from pipeline.paths import REPO_ROOT

CLUSTERS_FULL_PATH = REPO_ROOT / "data" / "export" / "plenair-map" / "plenair-map-clusters-full.json"
MAX_LABEL_WORDS = 2


def _iter_summaries(level_lists):
    for level_idx, summaries in enumerate(level_lists):
        for summary in summaries:
            yield level_idx, summary


def _fetch_person_and_party_tokens(conn):
    """Zelfde brontabel als cluster.py's fetch_actor_and_party_stopwords() --
    hergebruikt i.p.v. een los onderhouden naamlijst, zodat deze check
    automatisch meegroeit met de acteurstabel."""
    actor_names = [r[0] for r in conn.execute("SELECT name FROM actors WHERE name IS NOT NULL").fetchall()]
    party_names = [r[0] for r in conn.execute("SELECT party FROM actors WHERE party IS NOT NULL").fetchall()]
    tokens = set()
    for name in actor_names + party_names:
        tokens.update(t.lower() for t in re.findall(r"\b\w+\b", name) if len(t) >= 3)
    return tokens


def find_duplicate_labels(level_lists):
    """Patroon A: dezelfde labeltekst (case-insensitief) op meer dan één
    cluster, over de hele kaart heen."""
    by_name = defaultdict(list)
    for level_idx, summary in _iter_summaries(level_lists):
        by_name[summary["name"].strip().lower()].append((level_idx, summary["cluster_id"]))
    return {name: locs for name, locs in by_name.items() if len(locs) > 1}


def find_parent_child_tautologies(level_lists):
    """Patroon B: kind-label dat (een variant van) de oudernaam herhaalt --
    gedetecteerd als substring-overlap in beide richtingen, case-insensitief."""
    findings = []
    for level_idx, summary in _iter_summaries(level_lists):
        parent_name = summary.get("parent_name")
        if not parent_name:
            continue
        name, parent = summary["name"].strip().lower(), parent_name.strip().lower()
        if name and parent and (name in parent or parent in name):
            findings.append((level_idx, summary["cluster_id"], summary["name"], parent_name))
    return findings


def find_person_or_party_labels(level_lists, person_party_tokens):
    """Patroon D: label bevat een acteur- of partijnaam i.p.v. een
    inhoudelijk onderwerp."""
    findings = []
    for level_idx, summary in _iter_summaries(level_lists):
        name_tokens = {t.lower() for t in re.findall(r"\b\w+\b", summary["name"])}
        hit = name_tokens & person_party_tokens
        if hit:
            findings.append((level_idx, summary["cluster_id"], summary["name"], sorted(hit)))
    return findings


def find_overlong_labels(level_lists, max_words=MAX_LABEL_WORDS):
    """Patroon H: label van meer dan `max_words` woorden."""
    findings = []
    for level_idx, summary in _iter_summaries(level_lists):
        words = summary["name"].strip().split()
        if len(words) > max_words:
            findings.append((level_idx, summary["cluster_id"], summary["name"]))
    return findings


def build_report(level_lists, person_party_tokens, max_words=MAX_LABEL_WORDS):
    return {
        "duplicate_labels": find_duplicate_labels(level_lists),
        "parent_child_tautologies": find_parent_child_tautologies(level_lists),
        "person_or_party_labels": find_person_or_party_labels(level_lists, person_party_tokens),
        "overlong_labels": find_overlong_labels(level_lists, max_words=max_words),
    }


def format_report(report):
    lines = []
    dup = report["duplicate_labels"]
    lines.append(f"## Patroon A: terugkerende labels ({len(dup)} unieke labels, meerdere clusters)")
    for name, locs in sorted(dup.items(), key=lambda kv: -len(kv[1])):
        loc_str = ", ".join(f"L{li}-{cid}" for li, cid in locs)
        lines.append(f"- \"{name}\" x{len(locs)}: {loc_str}")

    taut = report["parent_child_tautologies"]
    lines.append(f"\n## Patroon B: ouder-kind-tautologie ({len(taut)})")
    for level_idx, cluster_id, name, parent_name in taut:
        lines.append(f"- L{level_idx}-{cluster_id} \"{name}\" onder ouder \"{parent_name}\"")

    pp = report["person_or_party_labels"]
    lines.append(f"\n## Patroon D: persoons-/partijnamen in label ({len(pp)})")
    for level_idx, cluster_id, name, hit in pp:
        lines.append(f"- L{level_idx}-{cluster_id} \"{name}\" (treft: {', '.join(hit)})")

    overlong = report["overlong_labels"]
    lines.append(f"\n## Patroon H: te lang label (> {MAX_LABEL_WORDS} woorden) ({len(overlong)})")
    for level_idx, cluster_id, name in overlong:
        lines.append(f"- L{level_idx}-{cluster_id} \"{name}\"")

    return "\n".join(lines)


@click.command()
@click.option("--clusters-json", type=click.Path(exists=True, path_type=Path), default=CLUSTERS_FULL_PATH)
@click.option("--max-label-words", type=int, default=MAX_LABEL_WORDS)
@click.option("--output", type=click.Path(path_type=Path), default=None, help="rapport ook naar bestand schrijven")
def main(clusters_json: Path, max_label_words: int, output: Path):
    cluster_summaries = json.loads(clusters_json.read_text(encoding="utf-8"))
    level_lists = cluster_summaries["levels"]

    conn = db.connect()
    person_party_tokens = _fetch_person_and_party_tokens(conn)
    conn.close()

    report = build_report(level_lists, person_party_tokens, max_words=max_label_words)
    text = format_report(report)
    print(text)
    if output is not None:
        output.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
