"""
Stap 1 voor issue #254 (canonieke KPA-achtige clustering, RFC-fase 1, #175):
groepeer quotes binnen één topic en dezelfde stance tot canonieke stellingen,
op basis van cosine-afstand tussen bge-m3-embeddings (zelfde route als
scripts/experiment_find_similar_arguments.py, hergebruikt hier -- cache in
data/embeddings/ wordt gedeeld).

Puur embedding-clustering, GEEN LLM-call: het #253-onderzoek
(docs/research/onderzoeksvraag-argument-clustering-granulariteit.md) en het
#252-onderzoek (LLM-as-judge onbetrouwbaar bij interpretatieve vragen) wijzen
allebei naar een feitelijk/geometrisch signaal i.p.v. een modeloordeel voor
dit soort samenvoegbeslissingen. Het LLM-naamgeven van de canonieke stelling
per cluster (fase 2 van #254) komt in een los script, ná verificatie van deze
clustering zelf.

Clustert per stance apart (pro/contra/unclear nooit samengevoegd -- dat zou
een canonieke stelling met tegenstrijdige instances opleveren) met
sklearn's AgglomerativeClustering (average linkage, precomputed cosine-
afstand, distance_threshold). Geen HDBSCAN: bij deze kleine, per-topic-per-
stance steekproeven (tientallen tot een paar honderd quotes) is een simpele,
uitlegbare afstandsdrempel makkelijker te verifiëren dan HDBSCAN's
dichtheidsparameters.

Verificatie (zie --report, staat aan by default):
- clustergrootteverdeling (hoeveel singletons vs. samengevoegde clusters)
- gemiddelde intra-clustersimilariteit vs. een willekeurige-paar-baseline
  (het cluster moet aantoonbaar hechter zijn dan toeval, geen ruis)
- voorbeeldclusters afgedrukt voor handmatige steekproef, zelfde aanpak als
  het #253-onderzoek

Gebruik:
    uv run python scripts/experiment_canonical_claim_clustering.py --topic-slug abortus
    uv run python scripts/experiment_canonical_claim_clustering.py --topic-slug abortus --threshold 0.2 --examples 5
"""
import argparse

import numpy as np
from sklearn.cluster import AgglomerativeClustering

from pipeline.embed.lmstudio import detect_base_url
from scripts.experiment_find_similar_arguments import build_cache, cache_path, load_cache

DEFAULT_DISTANCE_THRESHOLD = 0.2  # cosine-afstand (1 - sim); sim >= 0.8 om samen te voegen


def cosine_distance_matrix(vectors):
    unit = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    sims = unit @ unit.T
    return 1.0 - np.clip(sims, -1.0, 1.0)


def cluster_stance_group(vectors, distance_threshold):
    """Retourneert een label per rij in `vectors` (allemaal dezelfde stance).
    Eén quote (n=1) is triviaal zijn eigen cluster -- AgglomerativeClustering
    heeft minstens 2 samples nodig."""
    if len(vectors) == 1:
        return np.array([0])
    distances = cosine_distance_matrix(vectors)
    clustering = AgglomerativeClustering(
        metric="precomputed", linkage="average", distance_threshold=distance_threshold, n_clusters=None,
    )
    return clustering.fit_predict(distances)


def build_canonical_clusters(ids, vectors, texts, stances, parties, distance_threshold):
    """Clustert per stance apart en retourneert een platte lijst clusters:
    {"stance", "instances": [argument_id,...], "weight_by_party": {...},
    "member_texts": [...], "intra_cluster_sim": float|None}."""
    clusters = []
    for stance in sorted(set(stances)):
        idx = [i for i, s in enumerate(stances) if s == stance]
        group_vectors = vectors[idx]
        labels = cluster_stance_group(group_vectors, distance_threshold)

        by_label = {}
        for local_i, label in enumerate(labels):
            by_label.setdefault(label, []).append(idx[local_i])

        for member_idx in by_label.values():
            weight_by_party = {}
            for i in member_idx:
                party = parties[i] or "onbekend"
                weight_by_party[party] = weight_by_party.get(party, 0) + 1
            clusters.append({
                "stance": stance,
                "instances": [int(ids[i]) for i in member_idx],
                "weight_by_party": weight_by_party,
                "member_texts": [texts[i] for i in member_idx],
                "intra_cluster_sim": mean_pairwise_sim(vectors[member_idx]) if len(member_idx) > 1 else None,
            })
    return clusters


def mean_pairwise_sim(vectors):
    unit = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    sims = unit @ unit.T
    n = len(vectors)
    upper = sims[np.triu_indices(n, k=1)]
    return float(upper.mean())


def random_pair_baseline(vectors, n_samples=2000, seed=42):
    """Gemiddelde cosine-sim tussen willekeurige paren uit de hele topic-
    steekproef (niet per stance) -- de vergelijkingsmaat om te laten zien dat
    een cluster aantoonbaar hechter is dan toeval, zelfde soort redenering
    als de ARI/NMI-vergelijking in het #253-onderzoek."""
    rng = np.random.default_rng(seed)
    n = len(vectors)
    unit = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    a = rng.integers(0, n, n_samples)
    b = rng.integers(0, n, n_samples)
    mask = a != b
    sims = (unit[a[mask]] * unit[b[mask]]).sum(axis=1)
    return float(sims.mean())


def print_report(clusters, vectors, examples):
    sizes = [len(c["instances"]) for c in clusters]
    multi = [c for c in clusters if len(c["instances"]) > 1]
    singleton_count = len(sizes) - len(multi)

    print(f"\n{len(clusters)} clusters totaal ({singleton_count} singleton, {len(multi)} samengevoegd)")
    print(f"clustergroottes: min={min(sizes)}, max={max(sizes)}, mediaan={int(np.median(sizes))}")

    baseline = random_pair_baseline(vectors)
    print(f"\nwillekeurige-paar-baseline cosine-sim (hele topic): {baseline:.3f}")
    if multi:
        avg_intra = float(np.mean([c["intra_cluster_sim"] for c in multi]))
        print(f"gemiddelde intra-clustersimilariteit (samengevoegde clusters): {avg_intra:.3f}")
        if avg_intra <= baseline:
            print("WAARSCHUWING: intra-clustersimilariteit ligt niet boven de willekeurige-paar-baseline -- "
                  "drempel waarschijnlijk te los, clusters zijn niet aantoonbaar hechter dan toeval.")
    else:
        print("geen enkel cluster met >1 lid -- drempel waarschijnlijk te streng.")

    if examples and multi:
        print(f"\n--- {min(examples, len(multi))} voorbeeldclusters (grootste eerst, voor handmatige steekproef) ---")
        for c in sorted(multi, key=lambda c: -len(c["instances"]))[:examples]:
            print(f"\n[{c['stance']}] n={len(c['instances'])} sim={c['intra_cluster_sim']:.3f} "
                  f"weight_by_party={c['weight_by_party']}")
            for text in c["member_texts"]:
                print(f"  - {text[:160]!r}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic-slug", required=True)
    parser.add_argument("--min-quote-len", type=int, default=30)
    parser.add_argument("--refresh", action="store_true", help="embeddingcache negeren en herberekenen")
    parser.add_argument("--threshold", type=float, default=DEFAULT_DISTANCE_THRESHOLD,
                         help="cosine-afstandsdrempel voor samenvoegen (lager = strenger)")
    parser.add_argument("--examples", type=int, default=8, help="aantal voorbeeldclusters om af te drukken (0 = geen)")
    parser.add_argument("--base-url", default=None)
    args = parser.parse_args()

    cached = None if args.refresh else load_cache(args.topic_slug)
    if cached is None:
        base_url = detect_base_url(args.base_url)
        ids, vectors, texts, meta = build_cache(args.topic_slug, args.min_quote_len, base_url)
    else:
        ids, vectors, texts, meta = cached
        print(f"cache geladen: {len(ids)} argumenten uit {cache_path(args.topic_slug)}")

    # meta is "stance, partij" (zie experiment_find_similar_arguments.build_cache)
    stances = [m.split(", ", 1)[0] for m in meta]
    parties = [m.split(", ", 1)[1] for m in meta]

    clusters = build_canonical_clusters(ids, vectors, texts, stances, parties, args.threshold)
    print_report(clusters, vectors, args.examples)


if __name__ == "__main__":
    main()
