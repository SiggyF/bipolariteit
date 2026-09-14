"""
Zeer ruwe CO2-schatting over alle `llm_calls` (extractie + tagging), voor de
/over-pagina. Twee bewuste beperkingen, allebei zichtbaar in de output zodat
de pagina ze kan vermelden i.p.v. verbergen:

1. De redactie-stap (confrontatie-boom, via Docker agy/Gemini) logt geen
   tokens/duur in `llm_calls` (record_llm_call() wordt daar nergens
   aangeroepen) en telt dus niet mee -- in verhouding tot het totaal aantal
   extractie-/tag-calls is dit een klein deel van het werk.
2. Energie-per-token is een vuistregel, geen meting: gebaseerd op Luccioni,
   Jernite & Strubell, "Power Hungry Processing: Watts Driving the Cost of
   AI Deployment?" (FAccT 2024) en de per-query-cijfers voor een 70B-model
   (batch size 8, cloud-infrastructuur incl. PUE/WUE) uit "How Hungry is
   AI? Benchmarking Energy, Water, and Carbon Footprint of LLM Inference"
   (arXiv:2505.09598, 2025): ~0,3-0,35 Wh per 1000 gegenereerde tokens.
   Onze modellen zijn kleiner (~27-30B i.p.v. 70B) en dit cijfer dekt geen
   losse input/output-verhouding -- we gebruiken het ongewijzigd op de som
   van prompt- + completion-tokens, wat eerder een over- dan een
   onderschatting is.

Stroom-CO2-intensiteit is bewust per bron gesplitst, niet één landelijk
gemiddelde:
- lokaal (LM Studio, `qwen/qwen3.6-27b` zonder `:provider`-suffix): draait
  op groene stroom (Eneco) -- hier als 0 gCO2/kWh gerekend. Dat is een
  aanname over de eigen stroomlevering, geen claim dat elke marginale
  elektron CO2-vrij is.
- op afstand (HF-router; in de praktijk vrijwel altijd `:ovhcloud`, zie
  split_router_model()): OVHcloud's eigen Carbon Usage Effectiveness (CUE)
  over 2024 was 0,16 kgCO2e/kWh IT (OVHcloud environmental impact tracker
  methodology, 2025).
"""

from pipeline.hf_pricing import split_router_model

ENERGY_WH_PER_1K_TOKENS = 0.3  # zie moduledocstring; som van prompt+completion tokens
CARBON_INTENSITY_G_PER_KWH_LOCAL = 0  # Eneco groene stroom (eigen aanname, geen meting)
CARBON_INTENSITY_G_PER_KWH_REMOTE = 160  # OVHcloud CUE 2024, kgCO2e/kWh IT -> g/kWh


def _is_local_model(model: str) -> bool:
    """Zelfde `:provider`-heuristiek als hf_pricing.split_router_model():
    een HF-router-modelnaam heeft altijd een `<model>:<provider>`-vorm,
    lokale LM Studio-namen (bv. "qwen/qwen3.6-27b") nooit."""
    model_id, _provider = split_router_model(model)
    return model_id is None


def fetch_co2_estimate(conn):
    """Ruwe CO2-schatting over de hele `llm_calls`-geschiedenis (geen
    topic-filter: dit is een pipeline-brede kostenpost, geen per-topic-cijfer)."""
    rows = conn.execute(
        """SELECT model,
                  COUNT(*) AS n_calls,
                  SUM(COALESCE(prompt_tokens, 0) + COALESCE(completion_tokens, 0)) AS total_tokens,
                  SUM(CASE WHEN prompt_tokens IS NULL THEN 1 ELSE 0 END) AS n_calls_missing_tokens
           FROM llm_calls
           GROUP BY model"""
    ).fetchall()

    buckets = {
        "local": {"n_calls": 0, "total_tokens": 0, "n_calls_missing_tokens": 0},
        "remote": {"n_calls": 0, "total_tokens": 0, "n_calls_missing_tokens": 0},
    }
    for row in rows:
        bucket = buckets["local"] if _is_local_model(row["model"]) else buckets["remote"]
        bucket["n_calls"] += row["n_calls"]
        bucket["total_tokens"] += row["total_tokens"]
        bucket["n_calls_missing_tokens"] += row["n_calls_missing_tokens"]

    carbon_intensity = {"local": CARBON_INTENSITY_G_PER_KWH_LOCAL, "remote": CARBON_INTENSITY_G_PER_KWH_REMOTE}
    breakdown = {}
    total_energy_kwh = 0.0
    total_co2_g = 0.0
    for bron, bucket in buckets.items():
        energy_kwh = bucket["total_tokens"] / 1000 * ENERGY_WH_PER_1K_TOKENS / 1000
        co2_g = energy_kwh * carbon_intensity[bron]
        breakdown[bron] = {**bucket, "energy_kwh": energy_kwh, "co2_g": co2_g}
        total_energy_kwh += energy_kwh
        total_co2_g += co2_g

    return {
        "energy_wh_per_1k_tokens_assumption": ENERGY_WH_PER_1K_TOKENS,
        "carbon_intensity_g_per_kwh": carbon_intensity,
        "total_calls": sum(b["n_calls"] for b in buckets.values()),
        "total_tokens": sum(b["total_tokens"] for b in buckets.values()),
        "total_energy_kwh": total_energy_kwh,
        "total_co2_kg": total_co2_g / 1000,
        "by_source": breakdown,
    }
