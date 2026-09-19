"""
Stap 2 voor issue #254 (canonieke KPA-achtige clustering, RFC-fase 1, #175):
geef elk samengevoegd cluster uit scripts/experiment_canonical_claim_clustering.py
een canonieke stelling, via één geïsoleerde LLM-call per cluster (niet
gebatcht -- minder onderlinge leakage, zelfde aanpak als de #252-redactiestap,
zie pipeline/confrontatie_tree.py). Puur samenvattend ("wat is de gedeelde
stelling van deze quotes"), geen interpretatie-/geldigheidsoordeel -- exact
het soort feitelijke/functionele vraag dat het #252-onderzoek als betrouwbaar
voor een LLM aanmerkt (i.t.t. een normatief oordeel).

Verificatie (zie --report, staat aan by default):
- fidelity check: de canonical_claim wordt zelf ge-embed en vergeleken met de
  gemiddelde afstand tot de brondquotes -- moet duidelijk dichterbij liggen
  dan de willekeurige-paar-baseline, anders is de samenvatting waarschijnlijk
  afgedwaald van de brontekst.
- voorbeelden afgedrukt: canonical_claim naast de brondquotes, voor
  handmatige steekproef.

Gebruik:
    uv run python scripts/experiment_canonical_claim_naming.py --topic-slug abortus
"""
import argparse
import json
import re
import time
from pathlib import Path

import numpy as np
import requests

from pipeline.embed.lmstudio import detect_base_url, embed_texts
from pipeline.llm_client import call_llm
from scripts.experiment_canonical_claim_clustering import (
    DEFAULT_DISTANCE_THRESHOLD,
    build_canonical_clusters,
    random_pair_baseline,
)
from scripts.experiment_find_similar_arguments import MODEL, build_cache, cache_path, load_cache

PROMPT_TEMPLATE = (Path(__file__).parent.parent / "pipeline" / "prompts" / "canonical_claim.md").read_text()
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _extract_json(raw_text):
    fence_match = _JSON_FENCE_RE.search(raw_text)
    candidate = fence_match.group(1) if fence_match else raw_text.strip()
    return json.loads(candidate)


def name_cluster(cluster, topic_slug, base_url, model, reasoning_effort, timeout, max_tokens):
    prompt = PROMPT_TEMPLATE.format(
        n=len(cluster["member_texts"]),
        topic=topic_slug,
        stance=cluster["stance"],
        quotes_json=json.dumps(cluster["member_texts"], ensure_ascii=False, indent=2),
    )
    # LM Studio's lokale engine loopt af en toe intern vast (bv. engine-
    # protocol-timeout bij het wisselen tussen embed- en chatmodel op één
    # host-GPU) -- geen data-/promptprobleem, dus een enkele retry volstaat.
    last_exc = None
    for attempt in range(3):
        try:
            response = call_llm(base_url, model, prompt, reasoning_effort, timeout, max_tokens)
            return _extract_json(response.content)["canonical_claim"]
        except requests.exceptions.HTTPError as exc:
            last_exc = exc
            time.sleep(2 * (attempt + 1))
        except (json.JSONDecodeError, KeyError) as exc:
            raise ValueError(f"kon geen canonical_claim parsen uit LLM-respons (finish_reason={response.finish_reason!r}): {response.content!r}") from exc
    raise last_exc


def fidelity_check(claim_vector, member_vectors, baseline):
    """Cosine-sim tussen de canonical_claim-embedding en elk brondquote --
    gemiddelde moet boven de willekeurige-paar-baseline liggen, anders is de
    samenvatting waarschijnlijk afgedwaald van de citaten die 'm voedden."""
    unit_claim = claim_vector / np.linalg.norm(claim_vector)
    unit_members = member_vectors / np.linalg.norm(member_vectors, axis=1, keepdims=True)
    sims = unit_members @ unit_claim
    return float(sims.mean())


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--topic-slug", required=True)
    parser.add_argument("--min-quote-len", type=int, default=30)
    parser.add_argument("--threshold", type=float, default=DEFAULT_DISTANCE_THRESHOLD)
    parser.add_argument("--min-cluster-size", type=int, default=2, help="alleen clusters met >= dit aantal leden benoemen")
    parser.add_argument("--limit", type=int, default=None, help="alleen de N grootste clusters benoemen (kosten beperken)")
    parser.add_argument("--base-url", default=None, help="LLM chat-completion base URL; standaard auto-detect")
    parser.add_argument("--model", required=True, help="chat-model voor het benoemen, bv. via LM Studio geladen")
    parser.add_argument("--reasoning-effort", default="none",
                         help="LM Studio reasoning_effort ('none' default -- anders gaat het max_tokens-budget op aan denkstappen)")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--max-tokens", type=int, default=500)
    args = parser.parse_args()

    cached = load_cache(args.topic_slug)
    if cached is None:
        base_url = detect_base_url(args.base_url)
        ids, vectors, texts, meta = build_cache(args.topic_slug, args.min_quote_len, base_url)
    else:
        ids, vectors, texts, meta = cached
        print(f"cache geladen: {len(ids)} argumenten uit {cache_path(args.topic_slug)}")

    stances = [m.split(", ", 1)[0] for m in meta]
    parties = [m.split(", ", 1)[1] for m in meta]

    clusters = build_canonical_clusters(ids, vectors, texts, stances, parties, args.threshold)
    multi = [c for c in clusters if len(c["instances"]) >= args.min_cluster_size]
    multi.sort(key=lambda c: -len(c["instances"]))
    if args.limit:
        multi = multi[: args.limit]
    print(f"{len(multi)} clusters om te benoemen (min_cluster_size={args.min_cluster_size})")

    llm_base_url = detect_base_url(args.base_url)
    baseline = random_pair_baseline(vectors)

    id_to_idx = {int(aid): i for i, aid in enumerate(ids)}
    fidelities = []
    for cluster in multi:
        claim = name_cluster(cluster, args.topic_slug, llm_base_url, args.model, args.reasoning_effort, args.timeout, args.max_tokens)
        member_vectors = vectors[[id_to_idx[i] for i in cluster["instances"]]]
        claim_vector = embed_texts(llm_base_url, [claim], MODEL)[0]
        fidelity = fidelity_check(claim_vector, member_vectors, baseline)
        fidelities.append(fidelity)

        flag = "" if fidelity > baseline else "  <-- LET OP: onder baseline, mogelijk afgedwaald"
        print(f"\n[{cluster['stance']}] n={len(cluster['instances'])} weight_by_party={cluster['weight_by_party']} "
              f"fidelity={fidelity:.3f} (baseline={baseline:.3f}){flag}")
        print(f"  canonical_claim: {claim!r}")
        for text in cluster["member_texts"]:
            print(f"    - {text[:160]!r}")

    if fidelities:
        print(f"\ngemiddelde fidelity over {len(fidelities)} clusters: {np.mean(fidelities):.3f} (baseline={baseline:.3f})")
        below = sum(1 for f in fidelities if f <= baseline)
        if below:
            print(f"WAARSCHUWING: {below}/{len(fidelities)} canonical_claims liggen op of onder de baseline-similariteit.")


if __name__ == "__main__":
    main()
