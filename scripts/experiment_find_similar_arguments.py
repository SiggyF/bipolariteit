"""
Vervolg op het UMAP-onderzoekje (issue #156, zie docs/poc/umap-argumenten/):
i.p.v. een 2D-visualisatie, direct cosine-similarity search op de bge-m3-
embeddings om "gerelateerde argumenten" te vinden -- de sub-topic-clusters
die daar naar boven kwamen (bv. Syrië-veiligheid, dwangsommen, kinderen in
de opvang) suggereren dat dit een sterker signaal geeft dan de oorspronkelijke
pro/contra-clustering.

Niet geïntegreerd in de pipeline. Embeddings worden lokaal gecached in
data/embeddings/ (gitignored, regenereerbaar) zodat een her-query niet
opnieuw naar LM Studio hoeft.

Gebruik:
    # embeddings (her)berekenen en cachen voor een topic
    uv run python scripts/experiment_find_similar_arguments.py --topic-slug abortus --refresh

    # dichtstbijzijnde argumenten opzoeken bij een bestaand argument-id
    uv run python scripts/experiment_find_similar_arguments.py --topic-slug abortus --argument-id 1707

    # of bij losse tekst (bv. een nieuw citaat, nog niet in de database)
    uv run python scripts/experiment_find_similar_arguments.py --topic-slug abortus --text "..."
"""
import argparse

import numpy as np

from pipeline.db import db
from pipeline.paths import REPO_ROOT
from scripts.experiment_umap_arguments import detect_base_url, embed_texts, fetch_arguments

CACHE_DIR = REPO_ROOT / "data" / "embeddings"
MODEL = "text-embedding-bge-m3"


def cache_path(topic_slug):
    return CACHE_DIR / f"{MODEL}_{topic_slug}.npz"


def build_cache(topic_slug, min_quote_len, base_url):
    conn = db.connect()
    rows = fetch_arguments(conn, topic_slug, min_quote_len)
    conn.close()
    if not rows:
        raise SystemExit(f"geen argumenten gevonden voor topic-slug '{topic_slug}'")

    texts = [r["quote_text"] for r in rows]
    meta = [f"{r['stance']}, {r['party'] or 'onbekend'}" for r in rows]
    ids = np.array([r["id"] for r in rows])
    vectors = embed_texts(base_url, texts, MODEL)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    np.savez(
        cache_path(topic_slug),
        ids=ids,
        vectors=vectors,
        texts=np.array(texts, dtype=object),
        meta=np.array(meta, dtype=object),
    )
    print(f"{len(ids)} argumenten gecached in {cache_path(topic_slug)}")
    return ids, vectors, texts, meta


def load_cache(topic_slug):
    path = cache_path(topic_slug)
    if not path.exists():
        return None
    data = np.load(path, allow_pickle=True)
    return data["ids"], data["vectors"], list(data["texts"]), list(data["meta"])


def nearest(vectors, query_vector, top_k, exclude_idx=None):
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    unit = vectors / norms
    query_unit = query_vector / np.linalg.norm(query_vector)
    sims = unit @ query_unit
    order = np.argsort(-sims)
    results = []
    for i in order:
        if exclude_idx is not None and i == exclude_idx:
            continue
        results.append((i, sims[i]))
        if len(results) >= top_k:
            break
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic-slug", required=True)
    parser.add_argument("--min-quote-len", type=int, default=30)
    parser.add_argument("--refresh", action="store_true", help="cache negeren en embeddings herberekenen")
    parser.add_argument("--argument-id", type=int, help="zoek gerelateerde argumenten voor dit bestaande id")
    parser.add_argument("--text", help="zoek gerelateerde argumenten voor losse tekst i.p.v. een bestaand id")
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--base-url", default=None)
    args = parser.parse_args()

    if args.argument_id and args.text:
        raise SystemExit("gebruik --argument-id óf --text, niet beide")

    cached = None if args.refresh else load_cache(args.topic_slug)
    if cached is None:
        base_url = detect_base_url(args.base_url)
        ids, vectors, texts, meta = build_cache(args.topic_slug, args.min_quote_len, base_url)
    else:
        ids, vectors, texts, meta = cached
        print(f"cache geladen: {len(ids)} argumenten uit {cache_path(args.topic_slug)}")

    if not args.argument_id and not args.text:
        return

    if args.argument_id:
        matches = np.where(ids == args.argument_id)[0]
        if len(matches) == 0:
            raise SystemExit(f"argument-id {args.argument_id} niet gevonden in topic '{args.topic_slug}'")
        idx = matches[0]
        query_vector = vectors[idx]
        print(f"\ntarget [{args.argument_id}]: {texts[idx][:200]!r}\n")
        results = nearest(vectors, query_vector, args.top_k, exclude_idx=idx)
    else:
        base_url = detect_base_url(args.base_url)
        query_vector = embed_texts(base_url, [args.text], MODEL)[0]
        print(f"\ntarget (losse tekst): {args.text[:200]!r}\n")
        results = nearest(vectors, query_vector, args.top_k)

    for i, sim in results:
        print(f"sim={sim:.3f} [{ids[i]}] ({meta[i]}): {texts[i][:200]!r}\n")


if __name__ == "__main__":
    main()
