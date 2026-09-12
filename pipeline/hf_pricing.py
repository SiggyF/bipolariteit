"""
Prijscontrole tegen de Hugging Face-router's eigen `/v1/models`-API
(https://router.huggingface.co/v1/models). Gebruikt om vóór en tijdens een
lange LLM-batch te verifiëren dat de opgegeven `<model>:<provider>`-combinatie
nog tegen dezelfde prijs draait als bij de start -- een provider kan
halverwege een run stilletjes gaan rekenen (zie de OVHcloud/Qwen-observatie
in docs/handoff.md), en dat mag onopgemerkt geen kosten opleveren.

Alleen relevant voor `--base-url https://router.huggingface.co/v1`; voor een
lokale backend (LM Studio, geen `<model>:<provider>`-notatie) zijn deze
functies no-ops.
"""

import logging

import requests

logger = logging.getLogger(__name__)

ROUTER_MODELS_URL = "https://router.huggingface.co/v1/models"


def split_router_model(model: str) -> tuple[str, str] | tuple[None, None]:
    """"<org>/<model>:<provider>" -> (model_id, provider); anders (None, None)
    (bv. een lokaal LM Studio-modelnaam zonder provider-suffix)."""
    if ":" not in model:
        return None, None
    model_id, provider = model.rsplit(":", 1)
    return model_id, provider


def fetch_provider_pricing(model_id: str, provider: str) -> dict | None:
    """{"input": ..., "output": ...} in USD per miljoen tokens, of None als
    het model/de provider niet (meer) gevonden wordt."""
    resp = requests.get(ROUTER_MODELS_URL, timeout=10)
    resp.raise_for_status()
    for m in resp.json().get("data", []):
        if m.get("id") == model_id:
            for p in m.get("providers", []):
                if p.get("provider") == provider:
                    return p.get("pricing")
    return None


def get_baseline_pricing(model: str, base_url: str) -> dict | None:
    """Haalt de prijs op vóór een batch start, als referentiepunt voor latere
    `price_still_matches()`-aanroepen. Geeft None terug (= geen controle
    nodig/mogelijk) voor lokale backends of als de check zelf mislukt --
    fail-open, dit is een extra vangnet, geen harde afhankelijkheid."""
    if "router.huggingface.co" not in base_url:
        return None
    model_id, provider = split_router_model(model)
    if not model_id:
        return None
    try:
        pricing = fetch_provider_pricing(model_id, provider)
    except requests.RequestException as exc:
        logger.warning("Kon prijs niet vooraf verifiëren (%s) -- doorgaan zonder garantie.", exc)
        return None
    if pricing is None:
        logger.warning("Provider %s niet gevonden voor %s -- doorgaan zonder prijsgarantie.", provider, model_id)
    else:
        logger.info("Prijs vooraf geverifieerd: %s @ %s = %s USD/M tokens", model_id, provider, pricing)
    return pricing


def price_still_matches(model: str, base_url: str, baseline: dict) -> bool:
    """True zolang de prijs niet hóger is dan `baseline` -- een prijsdaling
    is geen reden om te stoppen, alleen een stijging. Fail-open bij een
    netwerkfout of ontbrekende baseline (dan is er niets om tegen te
    vergelijken) zodat een tijdelijke hik de hele batch niet onnodig stopt."""
    if baseline is None:
        return True
    model_id, provider = split_router_model(model)
    if not model_id:
        return True
    try:
        current = fetch_provider_pricing(model_id, provider)
    except requests.RequestException as exc:
        logger.warning("Prijscontrole tijdens run mislukt (%s) -- doorgaan.", exc)
        return True
    if current is None:
        return True
    if current.get("input", 0) > baseline.get("input", 0) or current.get("output", 0) > baseline.get("output", 0):
        logger.error(
            "PRIJSSTIJGING gedetecteerd tijdens run: was %s, is nu %s (%s @ %s) -- resterende taken annuleren.",
            baseline, current, model_id, provider,
        )
        return False
    return True
