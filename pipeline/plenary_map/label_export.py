"""
Losse LLM-naamgevingsstap voor een al gedraaide UMAP/HDBSCAN-clustering
(pipeline/plenary_map/cluster.py --skip-clustering=False --skip-llm-naming).
Werkt uitsluitend op de opgeslagen clusters-/hierarchy-/cluster-label-input-
bestanden in docs/poc/umap-documenten/ -- geen UMAP-coördinaten of
documentcorpus nodig, dus geschikt om los te draaien (bv. in de
devcontainer tegen een gratis remote router, terwijl de UMAP-fit zelf op de
host draaide vanwege geheugengebruik, zie docs/handoff.md).

Hervatbaar: een cluster met een al gevulde `duiding` wordt overgeslagen, dus
herhaald aanroepen op dezelfde `--label` labelt alleen wat nog ontbreekt.
`--limit` begrenst hoeveel NIEUWE clusters één aanroep labelt, zodat dit in
meerdere losse porties kan (bv. om tussentijds op prijs/rate-limits te
controleren).

Gebruik:
    uv run python -m pipeline.plenary_map.label_export --label full \
        --base-url https://router.huggingface.co/v1 \
        --llm-chat-model Qwen/Qwen3.8-27B:ovhcloud --llm-api-key $HF_TOKEN \
        --export-suffix=-full-v2 --export-frontend --limit 100
"""
import argparse
import json
import logging

from pipeline.embed.lmstudio import detect_base_url
from pipeline.paths import REPO_ROOT
from pipeline.plenary_map.label import label_clusters_with_llm

logger = logging.getLogger(__name__)

OUTPUT_DIR = REPO_ROOT / "docs" / "poc" / "umap-documenten"
CLUSTERS_EXPORT_PATH = REPO_ROOT / "data" / "export" / "plenair-map-clusters.json"
HIERARCHY_EXPORT_PATH = REPO_ROOT / "data" / "export" / "plenair-map-hierarchy.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--label", required=True, help="zelfde --label als de cluster.py-run die dit produceerde")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--llm-chat-model", default="qwen/qwen3.6-27b")
    parser.add_argument("--llm-api-key", default=None)
    parser.add_argument("--llm-reasoning-effort", default="none")
    parser.add_argument(
        "--limit", type=int, default=None,
        help="max aantal NOG NIET gelabelde clusters deze aanroep (default: alles in één keer)",
    )
    parser.add_argument(
        "--export-frontend", action="store_true",
        help="ook data/export/plenair-map-clusters<suffix>.json en -hierarchy<suffix>.json bijwerken",
    )
    parser.add_argument("--export-suffix", default="")
    args = parser.parse_args()

    clusters_path = OUTPUT_DIR / f"clusters-{args.label}.json"
    hierarchy_path = OUTPUT_DIR / f"hierarchy-{args.label}.json"
    examples_path = OUTPUT_DIR / f"cluster-label-input-{args.label}.json"
    cluster_summaries = json.loads(clusters_path.read_text(encoding="utf-8"))
    hierarchy = json.loads(hierarchy_path.read_text(encoding="utf-8"))
    examples_by_level = json.loads(examples_path.read_text(encoding="utf-8"))
    level_lists = cluster_summaries["levels"]

    total = sum(len(summaries) for summaries in level_lists)
    todo = sum(1 for summaries in level_lists for s in summaries if not s.get("duiding"))
    logger.info("%d/%d clusters nog te labelen (label=%s)", todo, total, args.label)

    def _suffixed(path):
        return path.with_name(f"{path.stem}{args.export_suffix}{path.suffix}") if args.export_suffix else path

    def _persist(level_idx, cluster_id):
        # coarse/fine zijn losse top-level sleutels (backward compat,
        # PlenairMap.vue) die na json.load() NIET meer hetzelfde list-object
        # zijn als levels[0]/levels[-1] -- expliciet opnieuw gelijk zetten
        # vóór het wegschrijven, anders blijven ze de oude namen tonen.
        cluster_summaries["coarse"] = level_lists[0]
        cluster_summaries["fine"] = level_lists[-1]
        clusters_path.write_text(json.dumps(cluster_summaries, ensure_ascii=False, indent=2), encoding="utf-8")
        hierarchy_path.write_text(json.dumps(hierarchy, ensure_ascii=False, indent=2), encoding="utf-8")
        if args.export_frontend:
            _suffixed(CLUSTERS_EXPORT_PATH).write_text(
                json.dumps(cluster_summaries, ensure_ascii=False), encoding="utf-8",
            )
            _suffixed(HIERARCHY_EXPORT_PATH).write_text(
                json.dumps(hierarchy, ensure_ascii=False), encoding="utf-8",
            )

    llm_base_url = detect_base_url(args.base_url)
    label_clusters_with_llm(
        level_lists, hierarchy, examples_by_level, llm_base_url, args.llm_chat_model,
        args.llm_reasoning_effort, api_key=args.llm_api_key,
        limit=args.limit, on_cluster_labeled=_persist,
    )

    remaining = sum(1 for summaries in level_lists for s in summaries if not s.get("duiding"))
    logger.info("klaar -- %d clusters nog te labelen (roep opnieuw aan om verder te gaan)", remaining)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
