"""
Gedeelde OpenAI-compatibele chat-completion-client voor de LLM-pipeline-stages
(`extract_arguments.py`, `tag_arguments.py`). Werkt met elke backend die deze
API spreekt: lokale LM Studio (geen auth), of een remote provider die een
Bearer-token verwacht (bv. Hugging Face's router, `https://router.huggingface.co/v1`,
model als `"<model-id>:<provider>"`) -- pluggable via alleen `--base-url` (+
`--api-key` als de backend auth vereist), geen aparte backend per provider.
"""

from typing import NamedTuple

import requests


class LLMResponse(NamedTuple):
    content: str
    usage: dict
    finish_reason: str | None


def call_llm(base_url, model, prompt, reasoning_effort, timeout, max_tokens, api_key=None):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }
    if reasoning_effort:
        payload["reasoning_effort"] = reasoning_effort

    headers = {"Authorization": f"Bearer {api_key}"} if api_key else None

    resp = requests.post(f"{base_url}/chat/completions", json=payload, headers=headers, timeout=timeout)
    if not resp.ok:
        raise requests.exceptions.HTTPError(f"{resp.status_code} {resp.reason} voor {base_url}/chat/completions: {resp.text[:2000]}", response=resp)
    data = resp.json()
    choice = data["choices"][0]
    content = choice["message"].get("content", "")
    usage = data.get("usage", {})
    finish_reason = choice.get("finish_reason")
    return LLMResponse(content, usage, finish_reason)
