"""
Onderzoekje voor issue #156: levert een UMAP-visualisatie van argument-quotes
iets interpreteerbaars op, voordat dit een vaste export/UI-onderdeel wordt?

Drie varianten naast elkaar op dezelfde steekproef (één topic, standaard
"asiel"):
- token-based: TF-IDF over quote_text, direct de UMAP in (goedkoop, geen
  model-forward-pass).
- embedding-based (nomic): LM Studio's text-embedding-nomic-embed-text-v1.5
  (moet al geladen zijn, zie scripts/detect_llm_base_url.sh) -- overwegend
  Engels getraind.
- embedding-based (bge-m3): BAAI/bge-m3, ook via LM Studio (host-GPU i.p.v.
  lokaal in de container draaien -- CPU-only in de devcontainer bleek voor
  dit 568M-parameter model te traag, ~27min voor 3555 quotes; laad het model
  eerst in LM Studio zelf, dit script downloadt niets). Expliciet
  multilingual, dus eerlijkere test voor dit Nederlandstalige corpus dan het
  overwegend Engelse nomic-model.

Puur leesactie op de database, schrijft niets terug. Output: twee PNG's per
variant (gekleurd op stance en op partij) plus een timing-samenvatting, in
docs/poc/umap-argumenten/.

Gebruik:
    uv run python scripts/experiment_umap_arguments.py
    uv run python scripts/experiment_umap_arguments.py --topic-slug stikstof --min-quote-len 40
"""
import argparse
import time

import matplotlib.pyplot as plt
import nltk
import numpy as np
import requests
import umap
from sklearn.feature_extraction.text import TfidfVectorizer
from tqdm import tqdm

from pipeline.db import db
from pipeline.paths import REPO_ROOT

OUTPUT_DIR = REPO_ROOT / "docs" / "poc" / "umap-argumenten"
EMBED_MODEL = "text-embedding-nomic-embed-text-v1.5"
MULTILINGUAL_MODEL = "text-embedding-bge-m3"


def _dutch_stopwords():
    try:
        return nltk.corpus.stopwords.words("dutch")
    except LookupError:
        nltk.download("stopwords", quiet=True)
        return nltk.corpus.stopwords.words("dutch")


DUTCH_STOPWORDS = _dutch_stopwords()


def fetch_arguments(conn, topic_slug, min_quote_len):
    rows = conn.execute(
        """
        SELECT a.id, a.quote_text, a.stance, a.typology, ac.name AS actor_name, ac.party,
            (SELECT at.tag_sleutel FROM argument_tags at JOIN tags t ON t.sleutel = at.tag_sleutel
             WHERE at.argument_id = a.id AND t.labelgroep = 'Stijlmiddelen'
             ORDER BY at.tag_sleutel LIMIT 1) AS stijl_tag,
            (SELECT at.tag_sleutel FROM argument_tags at JOIN tags t ON t.sleutel = at.tag_sleutel
             WHERE at.argument_id = a.id AND t.labelgroep = 'Debatzetten'
             ORDER BY at.tag_sleutel LIMIT 1) AS debatzet_tag
        FROM arguments a
        JOIN topics t ON t.id = a.topic_id
        JOIN actors ac ON ac.id = a.actor_id
        WHERE t.slug = ? AND length(a.quote_text) >= ?
        ORDER BY a.id
        """,
        (topic_slug, min_quote_len),
    ).fetchall()
    return rows


def detect_base_url(explicit_base_url):
    if explicit_base_url:
        return explicit_base_url
    for candidate in ("http://localhost:1234/v1", "http://host.docker.internal:1234/v1"):
        try:
            requests.get(f"{candidate}/models", timeout=2).raise_for_status()
            return candidate
        except requests.RequestException:
            continue
    raise SystemExit("geen LM Studio-backend bereikbaar op localhost of host.docker.internal:1234")


def embed_texts(base_url, texts, model, batch_size=32):
    vectors = []
    batches = range(0, len(texts), batch_size)
    for i in tqdm(batches, desc=f"{model}-embeddings ophalen", unit="batch"):
        batch = texts[i : i + batch_size]
        resp = requests.post(
            f"{base_url}/embeddings",
            json={"model": model, "input": batch},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        vectors.extend(item["embedding"] for item in data)
    return np.array(vectors)


def run_umap(vectors, seed=42):
    reducer = umap.UMAP(n_neighbors=15, min_dist=0.1, metric="cosine", random_state=seed, verbose=True)
    return reducer.fit_transform(vectors)


def plot_all_dims(coords, label_dims, variant_label, prefix, topic_slug):
    for dim_name, labels in label_dims.items():
        title = f"UMAP ({variant_label}) - {topic_slug} - kleur={dim_name}"
        out_path = OUTPUT_DIR / f"{prefix}_{topic_slug}_{dim_name}.png"
        plot_coords(coords, labels, title, out_path)


def plot_coords(coords, labels, title, out_path):
    fig, ax = plt.subplots(figsize=(9, 7))
    categories = sorted(set(labels))
    cmap = plt.get_cmap("tab10" if len(categories) <= 10 else "tab20")
    for i, cat in enumerate(categories):
        mask = [label == cat for label in labels]
        ax.scatter(coords[mask, 0], coords[mask, 1], s=8, alpha=0.6, label=cat, color=cmap(i % cmap.N))
    ax.set_title(title)
    ax.legend(markerscale=2, fontsize=8, loc="best")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic-slug", default="asiel")
    parser.add_argument("--min-quote-len", type=int, default=30, help="filtert te schrale quotes eruit")
    parser.add_argument("--base-url", default=None, help="LM Studio base URL; standaard auto-detect")
    parser.add_argument("--skip-embedding", action="store_true", help="nomic-variant overslaan")
    parser.add_argument("--skip-multilingual", action="store_true", help="bge-m3-variant overslaan")
    parser.add_argument(
        "--multilingual-model", default=MULTILINGUAL_MODEL, help="model-id zoals LM Studio 'm rapporteert onder /v1/models"
    )
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    conn = db.connect()
    rows = fetch_arguments(conn, args.topic_slug, args.min_quote_len)
    conn.close()
    if not rows:
        raise SystemExit(f"geen argumenten gevonden voor topic-slug '{args.topic_slug}'")

    texts = [r["quote_text"] for r in rows]
    label_dims = {
        "stance": [r["stance"] for r in rows],
        "partij": [r["party"] or "onbekend" for r in rows],
        # bij meerdere Stijl-/Debatzet-tags op één argument (selectie='meervoud')
        # toont dit alleen de alfabetisch eerste -- grove aanname, prima voor een
        # eerste blik, niet geschikt om conclusies op te baseren.
        "stijl": [r["stijl_tag"] or "geen" for r in rows],
        "debatzet": [r["debatzet_tag"] or "geen" for r in rows],
    }
    print(f"{len(texts)} argument-quotes voor topic '{args.topic_slug}' (min_quote_len={args.min_quote_len})")

    # --- token-based (TF-IDF) ---
    t0 = time.monotonic()
    tfidf = TfidfVectorizer(stop_words=DUTCH_STOPWORDS, lowercase=True, ngram_range=(1, 2), min_df=2)
    token_vectors = tfidf.fit_transform(texts).toarray()
    token_coords = run_umap(token_vectors)
    token_elapsed = time.monotonic() - t0
    print(f"token-based: vectorized+UMAP in {token_elapsed:.1f}s, vocab={len(tfidf.vocabulary_)}")

    plot_all_dims(token_coords, label_dims, "token-based, TF-IDF", "token", args.topic_slug)

    # --- embedding-based (LM Studio, nomic) ---
    if not args.skip_embedding:
        base_url = detect_base_url(args.base_url)

        t0 = time.monotonic()
        embed_vectors = embed_texts(base_url, texts, EMBED_MODEL)
        embed_coords = run_umap(embed_vectors)
        embed_elapsed = time.monotonic() - t0
        print(f"embedding-based (nomic): embeddings+UMAP in {embed_elapsed:.1f}s ({base_url}, model={EMBED_MODEL})")

        plot_all_dims(embed_coords, label_dims, "nomic", "embed", args.topic_slug)

    # --- embedding-based (bge-m3, ook via LM Studio -- host-GPU i.p.v. CPU-only container) ---
    if not args.skip_multilingual:
        base_url = detect_base_url(args.base_url)

        t0 = time.monotonic()
        ml_vectors = embed_texts(base_url, texts, args.multilingual_model)
        ml_coords = run_umap(ml_vectors)
        ml_elapsed = time.monotonic() - t0
        print(f"embedding-based (bge-m3): embeddings+UMAP in {ml_elapsed:.1f}s ({base_url}, model={args.multilingual_model})")

        plot_all_dims(ml_coords, label_dims, "bge-m3", "bgem3", args.topic_slug)

    print(f"\nplots geschreven naar {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
