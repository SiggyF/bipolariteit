"""
Bewaakt de vorm van data/tags.toml (de door de argumentatie-onderzoeker
aangeleverde taxonomie): moet parsen, geen dubbele sleutels, en elke tag
moet een sleutel + beschrijving hebben.
"""

import tomllib
from pathlib import Path

TAGS_TOML_PATH = Path(__file__).parent.parent / "data" / "tags.toml"


def _load():
    with TAGS_TOML_PATH.open("rb") as f:
        return tomllib.load(f)


def test_tags_toml_exists_and_parses():
    assert TAGS_TOML_PATH.exists()
    taxonomy = _load()
    assert "perspectieven" in taxonomy
    assert len(taxonomy["perspectieven"]) > 0


def test_every_tag_has_sleutel_and_beschrijving():
    taxonomy = _load()
    for perspectief in taxonomy["perspectieven"]:
        assert perspectief.get("naam")
        assert perspectief.get("beschrijving")
        for labelgroep in perspectief["labelgroepen"]:
            assert labelgroep.get("naam")
            assert labelgroep.get("beschrijving")
            assert len(labelgroep["tags"]) > 0
            for tag in labelgroep["tags"]:
                assert tag.get("sleutel"), f"lege sleutel in labelgroep {labelgroep['naam']!r}"
                assert tag.get("beschrijving"), f"lege beschrijving voor sleutel {tag.get('sleutel')!r}"


def test_no_duplicate_sleutels():
    taxonomy = _load()
    sleutels = [
        tag["sleutel"]
        for perspectief in taxonomy["perspectieven"]
        for labelgroep in perspectief["labelgroepen"]
        for tag in labelgroep["tags"]
    ]
    duplicates = {s for s in sleutels if sleutels.count(s) > 1}
    assert not duplicates, f"dubbele sleutel(s) in tags.toml: {duplicates}"
