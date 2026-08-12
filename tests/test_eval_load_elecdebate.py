"""Tests voor pipeline/eval/load_elecdebate.py en schema.py (issue #62).
Gebruikt een handgeschreven, duidelijk synthetische fixture -- geen echte
ELECDEBATE60TO16-inhoud (dat bestand staat nog niet in de repo, zie
docs/eval-elecdebate.md)."""

import json

from pipeline.eval.load_elecdebate import load_jsonl
from pipeline.eval.schema import EvalRecord, FallacySpan, Span

SYNTHETIC_RECORDS = [
    {
        "text": "Mijn tegenstander is een leugenaar. Bovendien is zijn plan slecht voor de economie.",
        "speaker": "Synthetische Spreker A",
        "spans": [{"start": 37, "end": 84}],
        "fallacies": [{"start": 0, "end": 36, "label": "AdHominem"}],
    },
    {
        "text": "Denk aan onze kinderen: dit beleid vernietigt hun toekomst.",
        "speaker": "Synthetische Spreker B",
        "spans": [{"start": 0, "end": 61}],
        "fallacies": [{"start": 0, "end": 61, "label": "AppealtoEmotion"}],
    },
    {
        "text": "Een neutrale zin zonder enig argument of drogreden.",
        "speaker": None,
        "spans": [],
        "fallacies": [],
    },
]


def _write_fixture(tmp_path):
    path = tmp_path / "sample_synthetic.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for record in SYNTHETIC_RECORDS:
            f.write(json.dumps(record) + "\n")
    return path


def test_load_jsonl_roundtrips_records(tmp_path):
    path = _write_fixture(tmp_path)
    records = load_jsonl(path)
    assert len(records) == 3
    assert records[0].speaker == "Synthetische Spreker A"
    assert records[0].spans == [Span(37, 84)]
    assert records[0].fallacies == [FallacySpan(0, 36, "AdHominem")]
    assert records[2].speaker is None
    assert records[2].spans == []


def test_load_jsonl_skips_blank_lines(tmp_path):
    path = tmp_path / "with_blanks.jsonl"
    path.write_text(json.dumps(SYNTHETIC_RECORDS[0]) + "\n\n" + json.dumps(SYNTHETIC_RECORDS[1]) + "\n", encoding="utf-8")
    records = load_jsonl(path)
    assert len(records) == 2


def test_eval_record_to_dict_from_dict_roundtrip():
    original = EvalRecord.from_dict(SYNTHETIC_RECORDS[0])
    assert EvalRecord.from_dict(original.to_dict()) == original
