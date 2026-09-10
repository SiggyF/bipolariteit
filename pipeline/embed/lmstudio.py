"""
LM Studio-cliënt voor het embedden van tekst (OpenAI-compatibele
`/embeddings`-endpoint). Gebruikt door pipeline/embed/documents.py (de
plenaire-kaart-embedstap) en door losse scripts/notebooks die zelf ook
tegen LM Studio embedden (zie de importeurs van dit bestand).
"""

import numpy as np
import requests
from tqdm import tqdm


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


def embed_texts(base_url, texts, model, batch_size=32, on_batch=None):
    """on_batch(start_index, batch_vectors), indien gegeven, wordt na elke
    losse HTTP-batch aangeroepen -- zo kan de aanroeper elke batch meteen
    persisteren i.p.v. pas na het volledige (mogelijk urenlange) verzoek,
    zodat een tussentijdse onderbreking niet alle al opgehaalde batches
    verliest."""
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
        batch_vectors = np.array([item["embedding"] for item in data])
        vectors.append(batch_vectors)
        if on_batch is not None:
            on_batch(i, batch_vectors)
    return np.concatenate(vectors) if vectors else np.array([])
