"""
Onderzoek voor issue #253: is spreekbeurt-niveau clustering (de topic-map,
op de hele spreekbeurttekst) precies genoeg om individuele argumenten aan
een topic-cluster te koppelen, of moet dat per individueel argument
(op quote_text)? Dit antwoord bepaalt het ontwerp van #254 (canonieke
KPA-achtige clustering, RFC-fase 1, #175), die op #253's subtopic-
granulariteit bouwt.

Methode: voor een topic worden argumenten opgehaald met hun brondocument-id.
Het documentcluster (fine-level, uit de al gegenereerde plenaire-kaart-export)
wordt per argument gepropageerd. Los daarvan worden de argumenten zelf
(quote_text) embed en onafhankelijk geclusterd, met dezelfde UMAP+HDBSCAN-
methode als de topic-map, voor een eerlijke vergelijking. De overeenstemming
tussen beide clusterindelingen (ARI/NMI) plus een paar concrete voorbeelden
van spreekbeurten die uiteenvallen in verschillende argument-clusters geven
een eerste antwoord op de vraag.

Niet geïntegreerd in de pipeline. Embeddings worden lokaal gecached in
data/embeddings/ (gitignored, regenereerbaar), net als
scripts/experiment_find_similar_arguments.py.

Gebruik:
    uv run python scripts/experiment_argument_vs_document_clustering.py --topic-slug abortus
"""
import argparse
import json
import logging

import numpy as np
from sklearn.cluster import HDBSCAN
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

from pipeline.db import db
from pipeline.embed.lmstudio import detect_base_url, embed_texts
from pipeline.paths import REPO_ROOT
from scripts.experiment_umap_arguments import plot_coords, run_umap

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

MODEL = "text-embedding-bge-m3"
CACHE_DIR = REPO_ROOT / "data" / "embeddings"
PLENAIR_MAP_EXPORT = REPO_ROOT / "data" / "export" / "plenair-map" / "plenair-map.json"
REPORT_PATH = REPO_ROOT / "docs" / "research" / "onderzoeksvraag-argument-clustering-granulariteit.md"

NOISE_LABEL = -1


def cache_path(topic_slug):
    return CACHE_DIR / f"{MODEL}_{topic_slug}_argvsdoc.npz"


def fetch_arguments_with_document(conn, topic_slug, min_quote_len):
    return conn.execute(
        """
        SELECT a.id, a.document_id, a.quote_text, a.stance, ac.party
        FROM arguments a
        JOIN topics t ON t.id = a.topic_id
        JOIN actors ac ON ac.id = a.actor_id
        WHERE t.slug = ? AND length(a.quote_text) >= ?
        ORDER BY a.document_id, a.id
        """,
        (topic_slug, min_quote_len),
    ).fetchall()


def build_or_load_cache(topic_slug, min_quote_len, base_url, refresh):
    path = cache_path(topic_slug)
    if not refresh and path.exists():
        data = np.load(path, allow_pickle=True)
        logger.info("cache geladen: %d argumenten uit %s", len(data["ids"]), path)
        return data["ids"], data["document_ids"], data["vectors"], list(data["texts"]), list(data["meta"])

    conn = db.connect()
    rows = fetch_arguments_with_document(conn, topic_slug, min_quote_len)
    conn.close()
    if not rows:
        raise SystemExit(f"geen argumenten gevonden voor topic-slug '{topic_slug}'")

    texts = [r["quote_text"] for r in rows]
    meta = [f"{r['stance']}, {r['party'] or 'onbekend'}" for r in rows]
    ids = np.array([r["id"] for r in rows])
    document_ids = np.array([r["document_id"] for r in rows])
    vectors = embed_texts(base_url, texts, MODEL)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    np.savez(
        path,
        ids=ids,
        document_ids=document_ids,
        vectors=vectors,
        texts=np.array(texts, dtype=object),
        meta=np.array(meta, dtype=object),
    )
    logger.info("%d argumenten gecached in %s", len(ids), path)
    return ids, document_ids, vectors, texts, meta


def load_document_clusters(topic_slug, export_path):
    with open(export_path) as f:
        export = json.load(f)
    if topic_slug not in export["topics"]:
        raise SystemExit(f"topic-slug '{topic_slug}' niet aanwezig in {export_path} (topics: {export['topics']})")
    topic_idx = export["topics"].index(topic_slug)
    return {
        point[0]: point[10]
        for point in export["points"]
        if point[3] == topic_idx
    }


def cluster_arguments(vectors, min_cluster_size, seed):
    coords = run_umap(vectors, seed=seed)
    labels = HDBSCAN(min_cluster_size=min_cluster_size).fit(coords).labels_
    return coords, labels


def propagate_document_labels(document_ids, document_clusters):
    matched = np.array([doc_id in document_clusters for doc_id in document_ids])
    doc_labels = np.array([document_clusters.get(doc_id, NOISE_LABEL) for doc_id in document_ids])
    return doc_labels, matched


def compute_agreement(doc_labels, arg_labels):
    return {
        "n": len(doc_labels),
        "ari": adjusted_rand_score(doc_labels, arg_labels),
        "nmi": normalized_mutual_info_score(doc_labels, arg_labels),
        "noise_rate_doc": float(np.mean(doc_labels == NOISE_LABEL)),
        "noise_rate_arg": float(np.mean(arg_labels == NOISE_LABEL)),
    }


def select_qualitative_examples(ids, document_ids, arg_labels, doc_labels, texts, meta, top_n):
    by_document = {}
    for i, doc_id in enumerate(document_ids):
        by_document.setdefault(doc_id, []).append(i)

    candidates = []
    for doc_id, indices in by_document.items():
        if len(indices) < 2:
            continue
        distinct_clusters = {arg_labels[i] for i in indices}
        candidates.append((doc_id, distinct_clusters, indices))

    candidates.sort(key=lambda c: (len(c[1]), len(c[2])), reverse=True)

    examples = []
    for doc_id, distinct_clusters, indices in candidates[:top_n]:
        examples.append(
            {
                "document_id": int(doc_id),
                "document_cluster": int(doc_labels[indices[0]]),
                "n_distinct_argument_clusters": len(distinct_clusters),
                "arguments": [
                    {
                        "argument_id": int(ids[i]),
                        "argument_cluster": int(arg_labels[i]),
                        "meta": meta[i],
                        "quote_snippet": texts[i][:180],
                    }
                    for i in indices
                ],
            }
        )
    return examples


def write_geojson(ids, document_ids, coords, arg_labels, doc_labels, texts, meta, out_path):
    # UMAP-coordinaten zijn een arbitraire 2D-inbedding, geen aardse projectie
    # -- geen "crs"-veld, QGIS laadt dit dan als generieke (niet-geografische)
    # laag, wat hier klopt.
    features = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(x), float(y)]},
            "properties": {
                "argument_id": int(arg_id),
                "document_id": int(doc_id),
                "argument_cluster": int(arg_label),
                "document_cluster": int(doc_label),
                "meta": meta_str,
                "quote_snippet": text[:200],
            },
        }
        for arg_id, doc_id, (x, y), arg_label, doc_label, text, meta_str in zip(
            ids, document_ids, coords, arg_labels, doc_labels, texts, meta
        )
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f)
    logger.info("geojson geschreven naar %s", out_path)


def write_report(topic_slug, stats, matched_fraction, examples, out_path):
    duiding = (
        "ARI < 0.3 duidt op flink signaalverlies bij propageren op spreekbeurt-niveau "
        "-- clusteren per individueel argument is dan waarschijnlijk nodig voor #254."
        if stats["ari"] < 0.3
        else "ARI >= 0.3 duidt erop dat propageren op spreekbeurt-niveau een redelijk deel "
        "van het signaal behoudt -- mogelijk voldoende als eerste opzet voor #254."
    )

    lines = [
        f"# Onderzoeksvraag: spreekbeurt- of argument-niveau clustering? ({topic_slug})",
        "",
        "## Vraag en context",
        "",
        "Issue #253 (topic-map-koppeling aan de argumentenboom) stelt de vraag niet vooraf "
        "aan te nemen of spreekbeurt-niveau clustering (de bestaande topic-map) precies genoeg "
        "is om individuele argumenten aan een topic-cluster te koppelen, of dat clusteren per "
        "individueel argument nodig is. Dit antwoord bepaalt het ontwerp van #254 "
        "(canonieke KPA-achtige clustering, RFC-fase 1, #175).",
        "",
        "## Methode",
        "",
        f"- Topic: `{topic_slug}`",
        f"- Embeddingmodel: `{MODEL}` (LM Studio)",
        "- Documentcluster (fine-level) per argument gepropageerd vanuit de bestaande "
        "plenaire-kaart-export (`data/export/plenair-map/plenair-map.json`), geen her-run.",
        "- Argumenten (`quote_text`) onafhankelijk embed en geclusterd met dezelfde methode "
        "als de topic-map: UMAP (`n_neighbors=15, min_dist=0.1, metric=cosine`) gevolgd door "
        "HDBSCAN, voor een eerlijke vergelijking.",
        "- Overeenstemming gemeten met Adjusted Rand Index (chance-corrected, ongevoelig voor "
        "verschillende cluster-nummering) en Normalized Mutual Information (ongevoelig voor "
        "verschillend aantal clusters). HDBSCAN-noise (`-1`) telt mee als eigen label -- "
        "weglaten zou net de gevallen verdoezelen die de vraag beantwoorden.",
        f"- {matched_fraction:.1%} van de argumenten had een brondocument met een "
        "clustertoewijzing en is meegenomen; de rest is uitgesloten (zegt iets over de "
        "dekking van de bestaande export, niet over de onderzoeksvraag zelf).",
        "",
        "## Resultaten",
        "",
        f"- n (meegenomen argumenten): {stats['n']}",
        f"- Adjusted Rand Index: {stats['ari']:.3f}",
        f"- Normalized Mutual Information: {stats['nmi']:.3f}",
        f"- Noise-rate documentcluster-niveau: {stats['noise_rate_doc']:.1%}",
        f"- Noise-rate argumentcluster-niveau: {stats['noise_rate_arg']:.1%}",
        "",
        f"**Voorlopige duiding (drempelwaarde, geen definitieve conclusie):** {duiding}",
        "",
        "## Voorbeelden: spreekbeurten die uiteenvallen in argument-clusters",
        "",
    ]

    for ex in examples:
        lines.append(
            f"### Document {ex['document_id']} (documentcluster {ex['document_cluster']}, "
            f"{ex['n_distinct_argument_clusters']} verschillende argument-clusters)"
        )
        lines.append("")
        for arg in ex["arguments"]:
            lines.append(
                f"- argument {arg['argument_id']} (cluster {arg['argument_cluster']}, "
                f"{arg['meta']}): {arg['quote_snippet']!r}"
            )
        lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines))
    logger.info("verslag geschreven naar %s", out_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic-slug", default="abortus")
    parser.add_argument("--min-quote-len", type=int, default=30)
    parser.add_argument("--min-cluster-size", type=int, default=5)
    parser.add_argument("--refresh", action="store_true", help="embedding-cache negeren en opnieuw berekenen")
    parser.add_argument("--base-url", default=None, help="LM Studio base URL; standaard auto-detect")
    parser.add_argument("--plenair-map-export", default=PLENAIR_MAP_EXPORT, type=type(PLENAIR_MAP_EXPORT))
    parser.add_argument("--top-n-examples", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--report-path", default=REPORT_PATH, type=type(REPORT_PATH))
    args = parser.parse_args()

    base_url = detect_base_url(args.base_url)
    ids, document_ids, vectors, texts, meta = build_or_load_cache(
        args.topic_slug, args.min_quote_len, base_url, args.refresh
    )
    logger.info("%d argumenten voor topic '%s'", len(ids), args.topic_slug)

    document_clusters = load_document_clusters(args.topic_slug, args.plenair_map_export)
    doc_labels, matched = propagate_document_labels(document_ids, document_clusters)
    matched_fraction = float(np.mean(matched))
    logger.info("%.1f%% van de argumenten heeft een documentcluster-toewijzing", matched_fraction * 100)

    coords, arg_labels = cluster_arguments(vectors, args.min_cluster_size, args.seed)
    n_arg_clusters = len(set(arg_labels) - {NOISE_LABEL})
    logger.info("%d argument-clusters gevonden (excl. noise)", n_arg_clusters)

    ids_m, document_ids_m, arg_labels_m, doc_labels_m, texts_m, meta_m = (
        ids[matched], document_ids[matched], arg_labels[matched], doc_labels[matched],
        [t for t, m in zip(texts, matched) if m], [m_ for m_, m in zip(meta, matched) if m],
    )

    stats = compute_agreement(doc_labels_m, arg_labels_m)
    logger.info("ARI=%.3f NMI=%.3f", stats["ari"], stats["nmi"])

    examples = select_qualitative_examples(
        ids_m, document_ids_m, arg_labels_m, doc_labels_m, texts_m, meta_m, args.top_n_examples
    )

    write_report(args.topic_slug, stats, matched_fraction, examples, args.report_path)

    plot_dir = args.report_path.parent
    plot_coords(
        coords, [str(label) for label in arg_labels],
        f"Argument-niveau UMAP+HDBSCAN - {args.topic_slug} - kleur=argumentcluster",
        plot_dir / f"argument-clusters-{args.topic_slug}.png",
    )
    plot_coords(
        coords, [str(label) for label in doc_labels],
        f"Argument-niveau UMAP - {args.topic_slug} - kleur=gepropageerd spreekbeurtcluster",
        plot_dir / f"document-clusters-propagated-{args.topic_slug}.png",
    )
    logger.info("plots geschreven naar %s", plot_dir)

    write_geojson(
        ids, document_ids, coords, arg_labels, doc_labels, texts, meta,
        plot_dir / f"argument-clusters-{args.topic_slug}.geojson",
    )


if __name__ == "__main__":
    main()
