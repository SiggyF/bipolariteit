"""
Losse LLM-naamgevingsstap voor een al gedraaide clustering
(pipeline/plenary_map/cluster.py). Werkt uitsluitend op de opgeslagen
clusters-/hierarchy-/cluster-label-input-bestanden in data/plenary-map/ --
geen UMAP-coördinaten of documentcorpus nodig, dus geschikt om los te
draaien (bv. in de devcontainer tegen een gratis remote router, terwijl de
UMAP-fit zelf op de host draaide vanwege geheugengebruik, zie
docs/handoff.md).

Hervatbaar: een cluster met een al gevulde `duiding` wordt overgeslagen, dus
herhaald aanroepen op dezelfde `--label` labelt alleen wat nog ontbreekt.
`--limit` begrenst hoeveel NIEUWE clusters één aanroep labelt, zodat dit in
meerdere losse porties kan (bv. om tussentijds op prijs/rate-limits te
controleren).

Gebruik:
    uv run python -m pipeline.plenary_map.label_export --label full \
        --base-url https://router.huggingface.co/v1 \
        --llm-chat-model Qwen/Qwen3.8-27B:ovhcloud --llm-api-key $HF_TOKEN \
        --export-suffix=-full --export-frontend --limit 100 --parallel
"""
import argparse
import json
import logging

from pipeline.dask_client import make_client
from pipeline.embed.lmstudio import detect_base_url
from pipeline.hf_pricing import get_baseline_pricing, price_still_matches
from pipeline.paths import REPO_ROOT
from pipeline.plenary_map.label import label_clusters_with_llm, label_clusters_with_llm_dask

logger = logging.getLogger(__name__)

OUTPUT_DIR = REPO_ROOT / "data" / "plenary-map"
CLUSTERS_EXPORT_PATH = REPO_ROOT / "data" / "export" / "plenair-map-clusters.json"
HIERARCHY_EXPORT_PATH = REPO_ROOT / "data" / "export" / "plenair-map-hierarchy.json"
WRITE_INTERVAL = 20
PRICE_CHECK_INTERVAL = 100


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
        "--parallel", action="store_true",
        help="verdeel LLM-calls over dask (de devcontainer's persistente scheduler, zie pipeline/dask_client.py) "
             "i.p.v. sequentieel -- alleen zinvol tegen een remote provider die concurrency aankan (bv. de "
             "HF-router); lokale LM Studio verwerkt toch maar één request tegelijk",
    )
    parser.add_argument(
        "--export-frontend", action="store_true",
        help="ook data/export/plenair-map-clusters<suffix>.json en -hierarchy<suffix>.json bijwerken",
    )
    parser.add_argument(
        "--export-suffix", default="", choices=["", "-full"],
        help="zie pipeline/plenary_map/cluster.py's --export-suffix -- zelfde vaste keuze "
        "('' of '-full'), om dezelfde reden (issue #316).",
    )
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

    def _write():
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

    # Elk cluster wegschrijven is op de volle ~3600-cluster-dataset onnodig
    # veel I/O (clusters+hierarchy+suffixed-kopieën, tot ~22 MiB per keer) --
    # elke WRITE_INTERVAL clusters is frequent genoeg om bij een afgebroken
    # run weinig voortgang te verliezen, zonder de disk plat te leggen.
    done_count = 0

    def _persist(level_idx, cluster_id):
        nonlocal done_count
        done_count += 1
        if done_count % WRITE_INTERVAL == 0:
            _write()

    llm_base_url = detect_base_url(args.base_url)
    price_baseline = get_baseline_pricing(args.llm_chat_model, llm_base_url)

    if args.parallel:
        client = make_client(dashboard=True)
        logger.info("Parallelle modus: LLM-naamgeving verdeeld over dask (dashboard: %s)", client.dashboard_link)
        label_clusters_with_llm_dask(
            level_lists, hierarchy, examples_by_level, llm_base_url, args.llm_chat_model,
            args.llm_reasoning_effort, client, api_key=args.llm_api_key,
            limit=args.limit, on_cluster_labeled=_persist,
            price_check=lambda i: i % PRICE_CHECK_INTERVAL != 0 or price_still_matches(
                args.llm_chat_model, llm_base_url, price_baseline,
            ),
        )
        client.close()
    else:
        label_clusters_with_llm(
            level_lists, hierarchy, examples_by_level, llm_base_url, args.llm_chat_model,
            args.llm_reasoning_effort, api_key=args.llm_api_key,
            limit=args.limit, on_cluster_labeled=_persist,
        )

    _write()
    remaining = sum(1 for summaries in level_lists for s in summaries if not s.get("duiding"))
    logger.info("klaar -- %d clusters nog te labelen (roep opnieuw aan om verder te gaan)", remaining)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
