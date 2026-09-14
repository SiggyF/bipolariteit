import sqlite3
from pathlib import Path

from pipeline.co2_estimate import (
    CARBON_INTENSITY_G_PER_KWH_LOCAL,
    CARBON_INTENSITY_G_PER_KWH_REMOTE,
    ENERGY_WH_PER_1K_TOKENS,
    fetch_co2_estimate,
)
from pipeline.llm_log import record_llm_call

SCHEMA_PATH = Path(__file__).parent.parent / "pipeline" / "db" / "schema.sql"


def _fresh_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text())
    conn.execute("INSERT INTO topics (id, slug, name) VALUES (1, 'stikstof', 'Stikstof')")
    return conn


def test_fetch_co2_estimate_splits_local_and_remote_by_provider_suffix():
    conn = _fresh_conn()
    # Lokale LM Studio-naam (geen `:provider`-suffix): local.
    record_llm_call(
        conn, stage="extraction", topic_id=1, model="qwen/qwen3.6-27b",
        prompt_version="v1", started_at="2026-01-01T00:00:00Z", duration_s=1.0,
        status="ok", usage={"prompt_tokens": 800, "completion_tokens": 200},
    )
    # HF-router-naam (`:ovhcloud`-suffix): remote.
    record_llm_call(
        conn, stage="tagging", topic_id=1, model="Qwen/Qwen3.8-27B:ovhcloud",
        prompt_version="v1", started_at="2026-01-01T00:00:01Z", duration_s=1.0,
        status="ok", usage={"prompt_tokens": 700, "completion_tokens": 300},
    )

    estimate = fetch_co2_estimate(conn)

    assert estimate["total_calls"] == 2
    assert estimate["total_tokens"] == 2000
    assert estimate["by_source"]["local"]["total_tokens"] == 1000
    assert estimate["by_source"]["remote"]["total_tokens"] == 1000

    expected_local_kwh = 1000 / 1000 * ENERGY_WH_PER_1K_TOKENS / 1000
    expected_remote_kwh = 1000 / 1000 * ENERGY_WH_PER_1K_TOKENS / 1000
    assert estimate["by_source"]["local"]["energy_kwh"] == expected_local_kwh
    assert estimate["by_source"]["remote"]["energy_kwh"] == expected_remote_kwh
    assert estimate["total_energy_kwh"] == expected_local_kwh + expected_remote_kwh


def test_fetch_co2_estimate_local_calls_carry_zero_carbon_intensity():
    conn = _fresh_conn()
    record_llm_call(
        conn, stage="extraction", topic_id=1, model="qwen/qwen3.6-27b",
        prompt_version="v1", started_at="2026-01-01T00:00:00Z", duration_s=1.0,
        status="ok", usage={"prompt_tokens": 1000, "completion_tokens": 0},
    )

    estimate = fetch_co2_estimate(conn)

    assert estimate["carbon_intensity_g_per_kwh"]["local"] == CARBON_INTENSITY_G_PER_KWH_LOCAL
    assert estimate["by_source"]["local"]["co2_g"] == 0
    assert estimate["total_co2_kg"] == 0


def test_fetch_co2_estimate_remote_calls_use_ovhcloud_carbon_intensity():
    conn = _fresh_conn()
    record_llm_call(
        conn, stage="tagging", topic_id=1, model="Qwen/Qwen3.8-27B:ovhcloud",
        prompt_version="v1", started_at="2026-01-01T00:00:00Z", duration_s=1.0,
        status="ok", usage={"prompt_tokens": 1000, "completion_tokens": 0},
    )

    estimate = fetch_co2_estimate(conn)

    energy_kwh = 1000 / 1000 * ENERGY_WH_PER_1K_TOKENS / 1000
    expected_co2_g = energy_kwh * CARBON_INTENSITY_G_PER_KWH_REMOTE
    assert estimate["by_source"]["remote"]["co2_g"] == expected_co2_g
    assert estimate["total_co2_kg"] == expected_co2_g / 1000


def test_fetch_co2_estimate_counts_calls_with_missing_token_usage():
    conn = _fresh_conn()
    # error-call zonder usage (net als bij een gefaalde JSON-parse, zie
    # tag_arguments.py's _tag_one()-foutpad): telt mee als call, niet als tokens.
    record_llm_call(
        conn, stage="tagging", topic_id=1, model="Qwen/Qwen3.8-27B:ovhcloud",
        prompt_version="v1", started_at="2026-01-01T00:00:00Z", duration_s=1.0,
        status="error", error_message="parse-fout",
    )

    estimate = fetch_co2_estimate(conn)

    assert estimate["total_calls"] == 1
    assert estimate["total_tokens"] == 0
    assert estimate["by_source"]["remote"]["n_calls_missing_tokens"] == 1
