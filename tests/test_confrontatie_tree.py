import json

from jsonschema import Draft202012Validator

from pipeline.confrontatie_tree import drop_degenerate_coordinatieve_groepen, merge_engagement_checks
from pipeline.paths import REPO_ROOT

SCHEMA = json.loads((REPO_ROOT / "pipeline" / "schemas" / "argument_tree.schema.json").read_text())


def _structured():
    return {
        "nodes": [
            {"argument_id": 159, "gist": "innovatieve sturing", "samenvatting": None},
            {"argument_id": 163, "gist": "mestoverschot", "samenvatting": None},
            {"argument_id": 1280, "gist": "depositiesturing", "samenvatting": None},
        ],
        "relations": [
            {"relation_type": "support", "premise_argument_ids": [163], "target_argument_id": 159, "scheme": None},
            {
                "relation_type": "conflict", "premise_argument_ids": [1280], "target_argument_id": 159,
                "thema": "Volstaat innovatieve sturing?", "scheme": "direct_rebuttal",
            },
        ],
        "coordinatieve_groepen": [],
        "twijfelachtige_classificaties": [],
    }


def test_relation_that_passes_the_engagement_check_is_kept():
    structured = _structured()
    checks = [
        {"relation_index": 0, "engageert": True, "reden": "163 noemt een expliciete oorzaak voor 159."},
        {"relation_index": 1, "engageert": True, "reden": "1280 gaat rechtstreeks in op de kern van 159."},
    ]

    result = merge_engagement_checks(structured, checks)

    assert len(result["relations"]) == 2
    for relation in result["relations"]:
        assert relation["reden"]


def test_relation_that_fails_the_engagement_check_is_dropped():
    structured = _structured()
    checks = [
        {"relation_index": 0, "engageert": False, "reden": "163 raakt niet de kern van 159."},
        {"relation_index": 1, "engageert": True, "reden": "1280 gaat rechtstreeks in op de kern van 159."},
    ]

    result = merge_engagement_checks(structured, checks)

    assert len(result["relations"]) == 1
    assert result["relations"][0]["relation_type"] == "conflict"


def test_relation_missing_from_checks_is_dropped():
    structured = _structured()
    checks = [
        {"relation_index": 1, "engageert": True, "reden": "1280 gaat rechtstreeks in op de kern van 159."},
    ]

    result = merge_engagement_checks(structured, checks)

    assert len(result["relations"]) == 1
    assert result["relations"][0]["relation_type"] == "conflict"


def test_scheme_override_applied_when_check_provides_one():
    structured = _structured()
    checks = [
        {"relation_index": 0, "engageert": True, "reden": "..."},
        {"relation_index": 1, "engageert": True, "reden": "...", "scheme": "frame_shift"},
    ]

    result = merge_engagement_checks(structured, checks)

    conflict_relation = next(r for r in result["relations"] if r["relation_type"] == "conflict")
    assert conflict_relation["scheme"] == "frame_shift"


def test_scheme_falls_back_to_structuring_step_when_check_gives_none():
    structured = _structured()
    checks = [
        {"relation_index": 0, "engageert": True, "reden": "..."},
        {"relation_index": 1, "engageert": True, "reden": "..."},
    ]

    result = merge_engagement_checks(structured, checks)

    conflict_relation = next(r for r in result["relations"] if r["relation_type"] == "conflict")
    assert conflict_relation["scheme"] == "direct_rebuttal"


def test_drop_degenerate_coordinatieve_groepen_removes_single_member_groups():
    structured = _structured()
    structured["coordinatieve_groepen"] = [
        {"label": "geldige groep", "samenvatting": None, "argument_ids": [159, 163]},
        {"label": "verdwaald argument", "samenvatting": None, "argument_ids": [1280]},
    ]

    result = drop_degenerate_coordinatieve_groepen(structured, "asiel")

    assert len(result["coordinatieve_groepen"]) == 1
    assert result["coordinatieve_groepen"][0]["label"] == "geldige groep"


def test_drop_degenerate_coordinatieve_groepen_leaves_valid_groups_untouched():
    structured = _structured()
    structured["coordinatieve_groepen"] = [
        {"label": "geldige groep", "samenvatting": None, "argument_ids": [159, 163, 1280]},
    ]

    result = drop_degenerate_coordinatieve_groepen(structured)

    assert result["coordinatieve_groepen"] == structured["coordinatieve_groepen"]


def test_drop_degenerate_coordinatieve_groepen_does_not_mutate_input():
    structured = _structured()
    structured["coordinatieve_groepen"] = [
        {"label": "verdwaald argument", "samenvatting": None, "argument_ids": [1280]},
    ]

    drop_degenerate_coordinatieve_groepen(structured)

    assert len(structured["coordinatieve_groepen"]) == 1


def test_merged_output_validates_against_schema():
    structured = _structured()
    checks = [
        {"relation_index": 0, "engageert": True, "reden": "163 noemt een expliciete oorzaak voor 159."},
        {"relation_index": 1, "engageert": True, "reden": "1280 gaat rechtstreeks in op de kern van 159."},
    ]

    result = merge_engagement_checks(structured, checks)

    Draft202012Validator(SCHEMA).validate(result)
