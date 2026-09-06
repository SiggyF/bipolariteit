import json

from jsonschema import Draft202012Validator

from pipeline.confrontatie_tree import merge_reviews
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


def _review(beoordelingen):
    return {"beoordelingen": beoordelingen}


def test_relation_endorsed_by_both_sides_is_not_weak():
    structured = _structured()
    pro = _review([
        {"relation_index": 0, "onderschrijft": True, "scheme": None},
        {"relation_index": 1, "onderschrijft": True, "scheme": None},
    ])
    contra = _review([
        {"relation_index": 0, "onderschrijft": True, "scheme": None},
        {"relation_index": 1, "onderschrijft": True, "scheme": None},
    ])

    result = merge_reviews(structured, pro, contra)

    assert len(result["relations"]) == 2
    for relation in result["relations"]:
        assert relation["weak_link"] is False
        assert relation["confidence"] == 1.0
        assert relation["beoordeeld_door"] == ["pro", "contra"]


def test_relation_endorsed_by_one_side_becomes_weak_link():
    structured = _structured()
    pro = _review([
        {"relation_index": 0, "onderschrijft": True, "scheme": None},
        {"relation_index": 1, "onderschrijft": True, "scheme": None},
    ])
    contra = _review([
        {"relation_index": 0, "onderschrijft": False, "scheme": None},
        {"relation_index": 1, "onderschrijft": True, "scheme": None},
    ])

    result = merge_reviews(structured, pro, contra)

    assert len(result["relations"]) == 2
    support_relation = next(r for r in result["relations"] if r["relation_type"] == "support")
    assert support_relation["weak_link"] is True
    assert support_relation["confidence"] == 0.5
    assert support_relation["beoordeeld_door"] == ["pro"]


def test_relation_endorsed_by_neither_side_is_dropped():
    structured = _structured()
    pro = _review([
        {"relation_index": 0, "onderschrijft": False, "scheme": None},
        {"relation_index": 1, "onderschrijft": True, "scheme": None},
    ])
    contra = _review([
        {"relation_index": 0, "onderschrijft": False, "scheme": None},
        {"relation_index": 1, "onderschrijft": True, "scheme": None},
    ])

    result = merge_reviews(structured, pro, contra)

    assert len(result["relations"]) == 1
    assert result["relations"][0]["relation_type"] == "conflict"


def test_scheme_override_only_applied_when_both_sides_independently_agree():
    structured = _structured()
    pro = _review([
        {"relation_index": 0, "onderschrijft": True, "scheme": None},
        {"relation_index": 1, "onderschrijft": True, "scheme": "frame_shift"},
    ])
    contra = _review([
        {"relation_index": 0, "onderschrijft": True, "scheme": None},
        {"relation_index": 1, "onderschrijft": True, "scheme": "thematic"},
    ])

    result = merge_reviews(structured, pro, contra)

    conflict_relation = next(r for r in result["relations"] if r["relation_type"] == "conflict")
    # pro en contra zijn het oneens over de scheme-bijstelling -> origineel blijft staan
    assert conflict_relation["scheme"] == "direct_rebuttal"


def test_scheme_override_applied_when_both_sides_agree():
    structured = _structured()
    pro = _review([
        {"relation_index": 0, "onderschrijft": True, "scheme": None},
        {"relation_index": 1, "onderschrijft": True, "scheme": "frame_shift"},
    ])
    contra = _review([
        {"relation_index": 0, "onderschrijft": True, "scheme": None},
        {"relation_index": 1, "onderschrijft": True, "scheme": "frame_shift"},
    ])

    result = merge_reviews(structured, pro, contra)

    conflict_relation = next(r for r in result["relations"] if r["relation_type"] == "conflict")
    assert conflict_relation["scheme"] == "frame_shift"


def test_merged_output_validates_against_schema():
    structured = _structured()
    pro = _review([
        {"relation_index": 0, "onderschrijft": True, "scheme": None},
        {"relation_index": 1, "onderschrijft": False, "scheme": None},
    ])
    contra = _review([
        {"relation_index": 0, "onderschrijft": True, "scheme": None},
        {"relation_index": 1, "onderschrijft": True, "scheme": None},
    ])

    result = merge_reviews(structured, pro, contra)

    Draft202012Validator(SCHEMA).validate(result)
