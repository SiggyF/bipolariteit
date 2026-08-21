"""
Sanity-check op het UMAP/bge-m3-onderzoek (issue #156, zie
docs/poc/umap-argumenten/): als embeddings binnen één topic al
inhoudelijke sub-onderwerp-clusters laten zien, herkent hetzelfde model dan
ook de grovere topic-grenzen zelf, puur op basis van quote_text-semantiek,
zonder dat het topic_id ergens in de tekst voorkomt?

Poolt alle argumenten van alle topics, embedt met bge-m3 (via LM Studio),
projecteert naar 2D met UMAP, en kleurt op topic -- ter validatie dat het
model uberhaupt onderwerpsemantiek vastlegt op een schaal waar we het
antwoord al kennen.

Niet geintegreerd in de pipeline. Cache in data/embeddings/ (gitignored).

Gebruik:
    uv run python scripts/experiment_topic_separation.py
"""
import argparse
import time

import matplotlib.pyplot as plt
import numpy as np
import umap

from pipeline.db import db
from pipeline.paths import REPO_ROOT
from scripts.experiment_umap_arguments import detect_base_url, embed_texts, run_umap

CACHE_DIR = REPO_ROOT / "data" / "embeddings"
OUTPUT_DIR = REPO_ROOT / "docs" / "poc" / "umap-argumenten"
MODEL = "text-embedding-bge-m3"


def fetch_all_topics(conn, min_quote_len):
    rows = conn.execute(
        """
        SELECT a.id, a.quote_text, t.slug AS topic_slug
        FROM arguments a
        JOIN topics t ON t.id = a.topic_id
        WHERE length(a.quote_text) >= ?
        ORDER BY t.slug, a.id
        """,
        (min_quote_len,),
    ).fetchall()
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--min-quote-len", type=int, default=30)
    parser.add_argument("--refresh", action="store_true", help="cache negeren en embeddings herberekenen")
    parser.add_argument("--base-url", default=None)
    args = parser.parse_args()

    cache_path = CACHE_DIR / f"{MODEL}_all-topics.npz"

    if not args.refresh and cache_path.exists():
        data = np.load(cache_path, allow_pickle=True)
        ids, vectors, texts, topics = data["ids"], data["vectors"], list(data["texts"]), list(data["topics"])
        print(f"cache geladen: {len(ids)} argumenten uit {cache_path}")
    else:
        conn = db.connect()
        rows = fetch_all_topics(conn, args.min_quote_len)
        conn.close()
        texts = [r["quote_text"] for r in rows]
        topics = [r["topic_slug"] for r in rows]
        ids = np.array([r["id"] for r in rows])
        print(f"{len(texts)} argumenten over {len(set(topics))} topics: {sorted(set(topics))}")

        base_url = detect_base_url(args.base_url)
        t0 = time.monotonic()
        vectors = embed_texts(base_url, texts, MODEL)
        print(f"embeddings opgehaald in {time.monotonic() - t0:.1f}s")

        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        np.savez(
            cache_path,
            ids=ids,
            vectors=vectors,
            texts=np.array(texts, dtype=object),
            topics=np.array(topics, dtype=object),
        )
        print(f"gecached in {cache_path}")

    t0 = time.monotonic()
    coords = run_umap(vectors)
    print(f"UMAP in {time.monotonic() - t0:.1f}s")

    fig, ax = plt.subplots(figsize=(10, 8))
    topic_labels = sorted(set(topics))
    cmap = plt.get_cmap("tab10")
    for i, topic in enumerate(topic_labels):
        mask = [t == topic for t in topics]
        ax.scatter(
            coords[mask, 0], coords[mask, 1], s=10, alpha=0.5,
            color=cmap(i % cmap.N), label=f"{topic} (n={sum(mask)})",
        )
    ax.set_title("UMAP (bge-m3) - alle topics gepoold - kleur=topic")
    ax.legend(markerscale=2, fontsize=9, loc="best")
    fig.tight_layout()
    out_path = OUTPUT_DIR / "bgem3_all-topics_topic.png"
    fig.savefig(out_path, dpi=150)
    print(f"plot opgeslagen: {out_path}")


if __name__ == "__main__":
    main()
