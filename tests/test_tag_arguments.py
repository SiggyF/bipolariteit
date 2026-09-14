import json
import sqlite3
from collections import Counter
from pathlib import Path

import pytest

from pipeline.tag_arguments import (
    _GEEN_TAG,
    QF_AMBIGU,
    QF_GEEN_FRAGMENT,
    QF_GELDIG,
    QF_GELDIG_MEERDELIG,
    QF_NIET_GEVONDEN,
    _coerce_tag_entry,
    _extract_json,
    _validate_tags,
    classify_quote_fragment,
    fetch_quote_fragment_backfill_arguments,
    fetch_untagged_arguments,
    insert_llm_tags,
)

SCHEMA_PATH = Path(__file__).parent.parent / "pipeline" / "db" / "schema.sql"

QUOTE_TEXT = "Mensen zijn gebaat bij een stabiele overheid, en veel meer mensen zijn gebaat bij een stabiele markt."


def test_classify_quote_fragment_geen_fragment_for_none_or_empty():
    assert classify_quote_fragment(None, QUOTE_TEXT) == QF_GEEN_FRAGMENT
    assert classify_quote_fragment("  ", QUOTE_TEXT) == QF_GEEN_FRAGMENT


def test_classify_quote_fragment_geldig_for_unique_verbatim_substring():
    assert classify_quote_fragment("een stabiele overheid", QUOTE_TEXT) == QF_GELDIG


def test_classify_quote_fragment_niet_gevonden_for_paraphrase():
    assert classify_quote_fragment("een wankele regering", QUOTE_TEXT) == QF_NIET_GEVONDEN


def test_classify_quote_fragment_ambigu_for_substring_occurring_twice():
    # "gebaat bij een stabiele" komt twee keer voor (overheid/markt) -- welke
    # bedoeld is, is niet af te leiden, dus afkeuren i.p.v. gokken.
    assert classify_quote_fragment("gebaat bij een stabiele", QUOTE_TEXT) == QF_AMBIGU


def test_classify_quote_fragment_geldig_meerdelig_for_ellipsis_joined_parts():
    fragment = "Mensen zijn gebaat... veel meer mensen zijn gebaat"
    assert classify_quote_fragment(fragment, QUOTE_TEXT) == QF_GELDIG_MEERDELIG


def test_classify_quote_fragment_niet_gevonden_when_one_ellipsis_part_missing():
    fragment = "Mensen zijn gebaat... dit deel staat er niet"
    assert classify_quote_fragment(fragment, QUOTE_TEXT) == QF_NIET_GEVONDEN


def test_coerce_tag_entry_accepts_new_object_with_quote_fragment():
    entry = {"sleutel": "Stijl-Herhaling", "reden": "reden hier", "quote_fragment": "een fragment"}
    assert _coerce_tag_entry(entry) == ("Stijl-Herhaling", "reden hier", "een fragment")


def test_coerce_tag_entry_accepts_bare_string_without_quote_fragment():
    assert _coerce_tag_entry("Stijl-Herhaling") == ("Stijl-Herhaling", None, None)


def test_coerce_tag_entry_returns_geen_tag_sentinel_for_null_forms():
    assert _coerce_tag_entry({"sleutel": None}) is _GEEN_TAG
    assert _coerce_tag_entry({"sleutel": "null"}) is _GEEN_TAG


def test_coerce_tag_entry_ignores_non_string_quote_fragment():
    entry = {"sleutel": "Stijl-Herhaling", "reden": "r", "quote_fragment": 123}
    assert _coerce_tag_entry(entry) == ("Stijl-Herhaling", "r", None)


VALID_TAGS = {
    "stijlmiddelen": ("meervoud", "Stijlmiddelen", {"Stijl-Herhaling", "Stijl-Metafoor"}),
}


def test_validate_tags_keeps_quote_fragment_when_geldig():
    parsed = {
        "stijlmiddelen": [
            {"sleutel": "Stijl-Herhaling", "reden": "r", "quote_fragment": "een stabiele overheid"},
        ]
    }
    accepted = _validate_tags(parsed, VALID_TAGS, QUOTE_TEXT)
    assert accepted == [("Stijl-Herhaling", "r", "een stabiele overheid")]


def test_validate_tags_drops_quote_fragment_when_not_verbatim():
    parsed = {
        "stijlmiddelen": [
            {"sleutel": "Stijl-Herhaling", "reden": "r", "quote_fragment": "een wankele regering"},
        ]
    }
    accepted = _validate_tags(parsed, VALID_TAGS, QUOTE_TEXT)
    assert accepted == [("Stijl-Herhaling", "r", None)]


def test_validate_tags_keeps_tag_without_quote_fragment_as_whole_quote():
    parsed = {"stijlmiddelen": [{"sleutel": "Stijl-Herhaling", "reden": "r", "quote_fragment": None}]}
    accepted = _validate_tags(parsed, VALID_TAGS, QUOTE_TEXT)
    assert accepted == [("Stijl-Herhaling", "r", None)]


def test_validate_tags_updates_qf_stats_counter():
    parsed = {
        "stijlmiddelen": [
            {"sleutel": "Stijl-Herhaling", "reden": "r", "quote_fragment": "een stabiele overheid"},
            {"sleutel": "Stijl-Metafoor", "reden": "r2", "quote_fragment": "een wankele regering"},
        ]
    }
    qf_stats = Counter()
    _validate_tags(parsed, VALID_TAGS, QUOTE_TEXT, qf_stats=qf_stats)
    assert qf_stats[QF_GELDIG] == 1
    assert qf_stats[QF_NIET_GEVONDEN] == 1


def test_extract_json_repairs_stray_closing_brace_after_enkel_field():
    # Echt LLM-antwoord (Qwen/Qwen3.8-27B:ovhcloud, asiel-topic, zie
    # llm_calls.id 32155/gelijkaardig): "metadiscussie" is een enkel-veld
    # (single object), en het model voegt een overtollige '}' toe direct na
    # het sluiten ervan, vóór de komma naar het volgende top-level veld.
    # json_repair (https://github.com/mangiucugna/json_repair) lost dit op
    # i.p.v. een zelfgeschreven regex per waargenomen generatiefout.
    raw = """{
      "metadiscussie": {
        "sleutel": "Meta-Agenda-Tijdigheid",
        "reden": "een reden",
          "quote_fragment": "een fragment"
        }
      },
      "morele_fundamenten": []
    }"""
    parsed = _extract_json(raw)
    assert parsed["metadiscussie"]["sleutel"] == "Meta-Agenda-Tijdigheid"
    assert parsed["morele_fundamenten"] == []


def test_extract_json_repairs_wrong_bracket_type_after_enkel_field():
    # Echt gezien (arg 2157, asiel): het enkel-veld sluit correct af met '}',
    # gevolgd door een overtollige, extra ']' i.p.v. nóg een '}'.
    raw = """{
      "metadiscussie": {
        "sleutel": "Meta-Agenda-Tijdigheid",
        "reden": "een reden",
        "quote_fragment": "een fragment"
      }
      ],
      "morele_fundamenten": []
    }"""
    parsed = _extract_json(raw)
    assert parsed["metadiscussie"]["sleutel"] == "Meta-Agenda-Tijdigheid"
    assert parsed["morele_fundamenten"] == []


def test_extract_json_repairs_response_missing_a_key():
    # Echt gezien (llm_calls.id 7041): het model laat quote_fragment
    # helemaal weg (alleen sleutel+reden) maar heeft dezelfde dubbele-
    # sluithaak-fout.
    raw = """{
      "redeneerschema": {
        "sleutel": "Walton-Expertise",
        "reden": "een reden"
        }
      },
      "stijlmiddelen": []
    }"""
    parsed = _extract_json(raw)
    assert parsed["redeneerschema"]["sleutel"] == "Walton-Expertise"
    assert parsed["stijlmiddelen"] == []


def test_extract_json_leaves_legitimate_json_alone():
    # Een enkel-veld als allerlaatste top-level sleutel eindigt legitiem met
    # twee sluithaken op rij, en een array-van-objecten sluit legitiem af met
    # '} ... ],' (element dicht, dan de array) -- geen van beide mag ooit
    # nodig hebben om via het reparatiepad te lopen (json.loads slaagt al).
    raw = """{
      "cultureel_ideologische_breuklijn": [
        {"sleutel": "Ideologie-TAN", "reden": "r", "quote_fragment": "f"}
      ],
      "redeneerschema": {
        "sleutel": "Walton-Regel",
        "reden": "r",
        "quote_fragment": null
      }
    }"""
    parsed = _extract_json(raw)
    assert parsed["cultureel_ideologische_breuklijn"][0]["sleutel"] == "Ideologie-TAN"
    assert parsed["redeneerschema"]["sleutel"] == "Walton-Regel"


def test_extract_json_still_raises_for_unrelated_malformed_json():
    # json_repair geeft voor volledig onherkenbare tekst iets terug dat geen
    # (niet-leeg) object is (bv. een lijst) -- _extract_json laat dan de
    # oorspronkelijke JSONDecodeError doorbubbelen i.p.v. die rommel te
    # accepteren als geldig resultaat.
    with pytest.raises(json.JSONDecodeError):
        _extract_json("dit is helemaal geen JSON, gewoon een lopende zin.")


def test_extract_json_rejects_genuinely_truncated_response():
    # Echt gezien (llm_calls.id 2394): de respons kapt af midden in een
    # stringwaarde (bv. door max_tokens), zonder de omsluitende structuur af
    # te sluiten. json_repair KAN dit sluiten (het gokt de ontbrekende quote/
    # sluithaken), maar dat betekent per definitie dat het laatste, afgekapte
    # tag-object onvolledige data bevat (hier ontbreekt quote_fragment
    # volledig) -- zo'n gok mag nooit stilzwijgend als geldig resultaat
    # worden geaccepteerd. Zie _TRUNCATION_REPAIR_MARKER.
    raw = """{
      "type_bewijsvoering": [
        {
          "sleutel": "Bewijs-Anekdotisch",
          "reden": "De spreker beroept zich op een anekdote die niet is afgemaakt en zomaar doorloopt"""
    with pytest.raises(json.JSONDecodeError):
        _extract_json(raw)


def _fresh_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text())
    return conn


def _seed_argument(conn, argument_id=1, tagged_at=None):
    """Bouwt de minimale rij-keten (topic/source/document/actor/argument) op
    voor argument_id, en de twee tags die de backfill-tests gebruiken."""
    conn.execute("INSERT INTO topics (id, slug, name) VALUES (1, 'stikstof', 'Stikstof')")
    conn.execute(
        "INSERT INTO sources (id, type, name, retrieved_at) VALUES (1, 'tweede_kamer', 'TK', '2026-01-01T00:00:00Z')"
    )
    conn.execute(
        "INSERT INTO actors (id, name, type, party) VALUES (1, 'Actor Een', 'person', 'Partij X')"
    )
    conn.execute(
        """INSERT INTO documents (id, source_id, topic_id, published_at)
           VALUES (1, 1, 1, '2026-01-01T00:00:00Z')"""
    )
    conn.execute(
        """INSERT INTO arguments
               (id, document_id, topic_id, actor_id, stance, typology, quote_text, extracted_at, tagged_at)
           VALUES (?, 1, 1, 1, 'pro', 'factual', ?, '2026-01-01T00:00:00Z', ?)""",
        (argument_id, QUOTE_TEXT, tagged_at),
    )
    for sleutel in ("Stijl-Herhaling", "Stijl-Metafoor"):
        conn.execute(
            "INSERT INTO labelgroepen (naam, perspectief, beschrijving, selectie) VALUES (?, 'p', 'b', 'meervoud')",
            (f"lg-{sleutel}",),
        )
        conn.execute(
            "INSERT INTO tags (sleutel, labelgroep, beschrijving) VALUES (?, ?, 'b')",
            (sleutel, f"lg-{sleutel}"),
        )
    return conn


def test_insert_llm_tags_fills_missing_quote_fragment_without_touching_other_rows():
    conn = _seed_argument(_fresh_conn(), tagged_at="2026-01-01T00:00:00Z")
    # Simuleert een argument getagd vóór issue #109: quote_fragment_status
    # blijft NULL (nooit beoordeeld), niet gezet in deze INSERT.
    conn.execute(
        """INSERT INTO argument_tags (argument_id, tag_sleutel, created_by, reden, quote_fragment, assigned_at)
           VALUES (1, 'Stijl-Herhaling', 'llm', 'oude reden', NULL, '2025-01-01T00:00:00Z')"""
    )
    # Een tweede tag die al opgelost is als "hele quote" (legitiem NULL) --
    # moet ongemoeid blijven, niet weer als kandidaat behandeld worden.
    conn.execute(
        """INSERT INTO argument_tags (argument_id, tag_sleutel, created_by, reden, quote_fragment, quote_fragment_status, assigned_at)
           VALUES (1, 'Stijl-Metafoor', 'llm', 'bestaande reden', NULL, 'hele_quote', '2025-01-01T00:00:00Z')"""
    )
    before = {row["tag_sleutel"]: dict(row) for row in conn.execute("SELECT * FROM argument_tags")}

    insert_llm_tags(
        conn, 1,
        [
            ("Stijl-Herhaling", "nieuwe reden van de herrun", "aangevuld fragment"),
            ("Stijl-Metafoor", "nieuwe reden van de herrun", None),
        ],
    )

    after = {row["tag_sleutel"]: dict(row) for row in conn.execute("SELECT * FROM argument_tags")}
    assert len(after) == 2

    # Ontbrekend quote_fragment wordt aangevuld, id/reden/assigned_at blijven origineel.
    herhaling = after["Stijl-Herhaling"]
    assert herhaling["quote_fragment"] == "aangevuld fragment"
    assert herhaling["quote_fragment_status"] == "fragment"
    assert herhaling["reden"] == "oude reden"
    assert herhaling["id"] == before["Stijl-Herhaling"]["id"]
    assert herhaling["assigned_at"] == before["Stijl-Herhaling"]["assigned_at"]

    # Een al opgeloste quote_fragment_status wordt nooit overschreven.
    metafoor = after["Stijl-Metafoor"]
    assert metafoor["quote_fragment_status"] == "hele_quote"
    assert metafoor["reden"] == "bestaande reden"


def test_insert_llm_tags_never_touches_manual_rows():
    conn = _seed_argument(_fresh_conn(), tagged_at="2026-01-01T00:00:00Z")
    conn.execute(
        """INSERT INTO argument_tags (argument_id, tag_sleutel, created_by, reden, quote_fragment, assigned_at)
           VALUES (1, 'Stijl-Herhaling', 'manual', 'handmatig toegekend', NULL, '2025-01-01T00:00:00Z')"""
    )

    insert_llm_tags(conn, 1, [("Stijl-Herhaling", "llm-reden", "llm-fragment")])

    row = dict(conn.execute("SELECT * FROM argument_tags WHERE tag_sleutel = 'Stijl-Herhaling'").fetchone())
    assert row["created_by"] == "manual"
    assert row["quote_fragment"] is None
    assert row["reden"] == "handmatig toegekend"


def test_insert_llm_tags_still_inserts_genuinely_new_tag():
    conn = _seed_argument(_fresh_conn(), tagged_at="2026-01-01T00:00:00Z")

    insert_llm_tags(conn, 1, [("Stijl-Metafoor", "reden", "fragment")])

    rows = conn.execute("SELECT * FROM argument_tags").fetchall()
    assert len(rows) == 1
    assert rows[0]["tag_sleutel"] == "Stijl-Metafoor"


def test_fetch_quote_fragment_backfill_arguments_only_returns_tagged_arguments_missing_fragment():
    conn = _seed_argument(_fresh_conn(), tagged_at="2026-01-01T00:00:00Z")
    conn.execute(
        """INSERT INTO argument_tags (argument_id, tag_sleutel, created_by, reden, quote_fragment, assigned_at)
           VALUES (1, 'Stijl-Herhaling', 'llm', 'r', NULL, '2025-01-01T00:00:00Z')"""
    )

    candidates = fetch_quote_fragment_backfill_arguments(conn, topic_id=1, limit=10)
    assert [row["id"] for row in candidates] == [1]


def test_fetch_quote_fragment_backfill_arguments_skips_untagged_and_complete_arguments():
    conn = _seed_argument(_fresh_conn(), tagged_at=None)
    # Ongetagd argument (tagged_at IS NULL): geen backfill-kandidaat, ook al
    # is er geen quote_fragment -- dat hoort via de normale flow te lopen.
    assert fetch_quote_fragment_backfill_arguments(conn, topic_id=1, limit=10) == []

    conn.execute("UPDATE arguments SET tagged_at = '2026-01-01T00:00:00Z' WHERE id = 1")
    conn.execute(
        """INSERT INTO argument_tags (argument_id, tag_sleutel, created_by, reden, quote_fragment, quote_fragment_status, assigned_at)
           VALUES (1, 'Stijl-Herhaling', 'llm', 'r', 'al gevuld fragment', 'fragment', '2025-01-01T00:00:00Z')"""
    )
    # Getagd, quote_fragment_status al opgelost: ook geen kandidaat.
    assert fetch_quote_fragment_backfill_arguments(conn, topic_id=1, limit=10) == []


def test_fetch_quote_fragment_backfill_arguments_excludes_resolved_whole_quote_tags():
    # Regressie: een tag die al is opgelost als "hele_quote" (legitiem
    # quote_fragment=NULL, zie schema.sql) mag geen oneindige kandidaat
    # blijven voor een volgende --backfill-quote-fragment-run -- dat was de
    # bug vóór quote_fragment_status bestond (destijds via een tag_prompt_
    # version-vergelijking "opgelost", nu rechtstreeks aan de rij zelf te zien).
    conn = _seed_argument(_fresh_conn(), tagged_at="2026-01-01T00:00:00Z")
    conn.execute(
        """INSERT INTO argument_tags (argument_id, tag_sleutel, created_by, reden, quote_fragment, quote_fragment_status, assigned_at)
           VALUES (1, 'Stijl-Herhaling', 'llm', 'r', NULL, 'hele_quote', '2025-01-01T00:00:00Z')"""
    )

    assert fetch_quote_fragment_backfill_arguments(conn, topic_id=1, limit=10) == []
    assert fetch_quote_fragment_backfill_arguments(conn, topic_id=1, limit=10, ids=[1]) == []


def test_fetch_untagged_arguments_unaffected_by_backfill_state():
    """Regressie: de normale --ids/scan-flow (fetch_untagged_arguments) blijft
    ongewijzigd -- een al getagd argument met ontbrekend quote_fragment mag
    daar nooit via naar binnen sluipen, dat loopt uitsluitend via
    --backfill-quote-fragment."""
    conn = _seed_argument(_fresh_conn(), tagged_at="2026-01-01T00:00:00Z")
    conn.execute(
        """INSERT INTO argument_tags (argument_id, tag_sleutel, created_by, reden, quote_fragment, assigned_at)
           VALUES (1, 'Stijl-Herhaling', 'llm', 'r', NULL, '2025-01-01T00:00:00Z')"""
    )
    assert fetch_untagged_arguments(conn, topic_id=1, limit=10, vanaf="2000-01-01") == []
