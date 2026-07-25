"""
Handhaaft het "we listen and we don't judge"-principe op schema-niveau:
geen enkele kolom in schema.sql mag feitelijke juistheid beoordelen.
"""

import re
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent.parent / "pipeline" / "db" / "schema.sql"
FORBIDDEN_PATTERN = re.compile(r"\b(truth|correct|verified|is_valid)\w*", re.IGNORECASE)


def _column_lines():
    lines = []
    in_table = False
    for line in SCHEMA_PATH.read_text().splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("CREATE TABLE"):
            in_table = True
            continue
        if in_table:
            if stripped.startswith(");"):
                in_table = False
                continue
            lines.append(line)
    return lines


def test_no_truth_or_correctness_columns():
    violations = []
    for line in _column_lines():
        match = FORBIDDEN_PATTERN.search(line)
        if match:
            violations.append(line.strip())

    assert not violations, (
        "Schema bevat een kolom die feitelijke juistheid lijkt te beoordelen, "
        f"dit schendt het 'we listen and we don't judge'-principe: {violations}"
    )


def test_schema_file_exists_and_nonempty():
    assert SCHEMA_PATH.exists()
    assert len(SCHEMA_PATH.read_text().strip()) > 0
