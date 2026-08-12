"""Laadt het genormaliseerde JSONL-tussenformaat (pipeline/eval/schema.py)
voor externe argumentatie-eval-datasets.

Voor ELECDEBATE60TO16 zet scripts/convert_elecdebate.py de brondata
(data/raw/elecdebate60to16/pos_{train,test}_set.csv, op te halen via het
Makefile in die map) om naar dit tussenformaat. Zie docs/eval-elecdebate.md."""

import json
from pathlib import Path

from pipeline.eval.schema import EvalRecord


def load_jsonl(path: Path) -> list[EvalRecord]:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(EvalRecord.from_dict(json.loads(line)))
    return records
