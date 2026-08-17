import sqlite3
from pathlib import Path

from pipeline.build_static_data import _speaker_event_url, fetch_llm_call_stats, fetch_recent_llm_calls
from pipeline.extract_arguments import PROMPT_VERSION as EXTRACT_PROMPT_VERSION
from pipeline.llm_log import record_llm_call

SCHEMA_PATH = Path(__file__).parent.parent / "pipeline" / "db" / "schema.sql"


def test_speaker_event_url_strips_video_suffix_and_encodes_timestamp():
    video_url = "https://debatdirect.tweedekamer.nl/2026-07-01/landbouw/plenaire-zaal/stikstof-13-30/video"
    url = _speaker_event_url(video_url, "2026-07-01T17:12:59")
    assert url == (
        "https://debatdirect.tweedekamer.nl/2026-07-01/landbouw/plenaire-zaal/stikstof-13-30"
        "?event=speaker2026-07-01T17%3A12%3A59%2B0200"
    )


def test_speaker_event_url_uses_winter_offset_for_cet_dates():
    video_url = "https://debatdirect.tweedekamer.nl/2025-02-20/huisvesting/plenaire-zaal/stikstofontwikkelingen-15-00/video"
    url = _speaker_event_url(video_url, "2025-02-20T16:04:53")
    assert "%2B0100" in url  # CET (winter), niet CEST


def test_speaker_event_url_returns_none_without_video_url():
    assert _speaker_event_url(None, "2026-07-01T17:12:59") is None


def test_speaker_event_url_returns_none_without_published_at():
    assert _speaker_event_url("https://debatdirect.tweedekamer.nl/x/video", None) is None


def test_speaker_event_url_prefers_anchor_at_over_published_at():
    # published_at kan uren afwijken van de werkelijke spreektijd (issue
    # #148-vervolg) -- anchor_at (het events-API-Tier-1-anker) moet dan
    # winnen, niet alleen als tie-break.
    video_url = "https://debatdirect.tweedekamer.nl/2026-07-01/landbouw/plenaire-zaal/stikstof-13-30/video"
    url = _speaker_event_url(video_url, "2026-07-01T13:49:28", "2026-07-01T16:52:20+02:00")
    assert "%2B0200" in url
    assert "2026-07-01T16%3A52%3A20" in url
    assert "13%3A49%3A28" not in url


def test_speaker_event_url_falls_back_to_published_at_without_anchor():
    video_url = "https://debatdirect.tweedekamer.nl/2026-07-01/landbouw/plenaire-zaal/stikstof-13-30/video"
    url = _speaker_event_url(video_url, "2026-07-01T17:12:59", None)
    assert "17%3A12%3A59" in url


def test_speaker_event_url_uses_speaker_event_type_by_default():
    video_url = "https://debatdirect.tweedekamer.nl/2026-07-01/landbouw/plenaire-zaal/stikstof-13-30/video"
    url = _speaker_event_url(video_url, "2026-07-01T17:12:59")
    assert url.split("?event=")[1].startswith("speaker")


def test_speaker_event_url_uses_interrupter_event_type_for_interruptions():
    # Issue #148-vervolg: een interruptie kreeg altijd het hardgecodeerde
    # "speaker"-eventType mee, waarvoor Debat Direct op dat tijdstip geen
    # match kon vinden (er bestaat daar geen "speaker"-event) -- de deep
    # link sprong daardoor terug naar het begin van het debat. Geverifieerd
    # live tegen debatdirect.tweedekamer.nl dat "interrupter" wel seekt.
    video_url = "https://debatdirect.tweedekamer.nl/2026-07-01/landbouw/plenaire-zaal/stikstof-13-30/video"
    url = _speaker_event_url(video_url, "2026-07-01T13:49:28", turn_type="interrumpant")
    assert url.split("?event=")[1].startswith("interrupter")


def test_speaker_event_url_uses_chairman_event_type_for_voorzitter_turns():
    video_url = "https://debatdirect.tweedekamer.nl/2026-07-01/landbouw/plenaire-zaal/stikstof-13-30/video"
    url = _speaker_event_url(video_url, "2026-07-01T13:49:28", turn_type="woordvoerder", is_voorzitter_turn=True)
    assert url.split("?event=")[1].startswith("chairman")


def _fresh_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text())
    conn.execute(
        "INSERT INTO topics (id, slug, name, description) VALUES (1, 'stikstof', 'Stikstof', 'pro versus contra')"
    )
    conn.execute(
        "INSERT INTO sources (id, type, name, retrieved_at) VALUES (1, 'tweede_kamer', 'TK', '2026-01-01T00:00:00Z')"
    )
    conn.execute("INSERT INTO actors (id, name, type, party) VALUES (1, 'Test Kamerlid', 'person', 'PartijX')")
    conn.execute(
        "INSERT INTO documents (id, source_id, topic_id, actor_id, content) VALUES (1, 1, 1, 1, 'de sprekerbeurt')"
    )
    return conn


def test_fetch_llm_call_stats_aggregates_per_stage_and_model():
    conn = _fresh_conn()
    record_llm_call(
        conn, stage="extraction", topic_id=1, document_id=1, model="model-a",
        prompt_version="v1", started_at="2026-01-01T00:00:00Z", duration_s=2.0,
        status="ok", usage={"completion_tokens": 10},
    )
    record_llm_call(
        conn, stage="extraction", topic_id=1, document_id=1, model="model-a",
        prompt_version="v1", started_at="2026-01-01T00:00:01Z", duration_s=4.0,
        status="error", error_message="boom",
    )
    record_llm_call(
        conn, stage="tagging", topic_id=1, document_id=1, model="model-b",
        prompt_version="v1", started_at="2026-01-01T00:00:02Z", duration_s=1.0,
        status="ok", usage={"completion_tokens": 3},
    )

    stats = fetch_llm_call_stats(conn, topic_id=1)
    by_stage_model = {(row["stage"], row["model"]): row for row in stats}

    extraction = by_stage_model[("extraction", "model-a")]
    assert extraction["n_calls"] == 2
    assert extraction["total_duration_s"] == 6.0
    assert extraction["avg_duration_s"] == 3.0
    assert extraction["n_errors"] == 1
    assert extraction["total_completion_tokens"] == 10

    tagging = by_stage_model[("tagging", "model-b")]
    assert tagging["n_calls"] == 1
    assert tagging["n_errors"] == 0


def test_fetch_recent_llm_calls_reconstructs_prompt_and_respects_limit():
    conn = _fresh_conn()
    topic_row = conn.execute("SELECT id, name, description FROM topics WHERE id = 1").fetchone()

    for i in range(3):
        record_llm_call(
            conn, stage="extraction", topic_id=1, document_id=1, model="model-a",
            prompt_version=EXTRACT_PROMPT_VERSION, started_at=f"2026-01-01T00:00:0{i}Z", duration_s=1.0,
            response=f"respons-{i}", status="ok",
        )

    calls = fetch_recent_llm_calls(conn, topic_row, limit=2)

    assert len(calls) == 2
    # Meest recente eerst (hoogste id).
    assert calls[0]["response"] == "respons-2"
    assert "de sprekerbeurt" in calls[0]["prompt"]
    assert "Test Kamerlid" in calls[0]["prompt"]
    assert calls[0]["prompt_outdated"] is False


def test_fetch_recent_llm_calls_flags_outdated_prompt_version():
    conn = _fresh_conn()
    topic_row = conn.execute("SELECT id, name, description FROM topics WHERE id = 1").fetchone()
    record_llm_call(
        conn, stage="extraction", topic_id=1, document_id=1, model="model-a",
        prompt_version="een-oude-hash-die-niet-meer-bestaat", started_at="2026-01-01T00:00:00Z",
        duration_s=1.0, response="respons", status="ok",
    )

    calls = fetch_recent_llm_calls(conn, topic_row)

    assert calls[0]["prompt_outdated"] is True
