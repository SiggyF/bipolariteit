"""Tests voor scripts/check_cluster_label_quality.py (issue #356-plan)."""

from scripts.check_cluster_label_quality import (
    find_duplicate_labels,
    find_overlong_labels,
    find_parent_child_tautologies,
    find_person_or_party_labels,
)


def _summary(cluster_id, name, parent_name=None):
    return {"cluster_id": cluster_id, "name": name, "parent_name": parent_name}


def test_find_duplicate_labels_flags_repeated_name():
    level_lists = [
        [_summary(1, "Stikstof"), _summary(2, "Asielbeleid")],
        [_summary(3, "stikstof"), _summary(4, "Visserij")],
    ]
    dup = find_duplicate_labels(level_lists)
    assert "stikstof" in dup
    assert sorted(dup["stikstof"]) == [(0, 1), (1, 3)]
    assert "visserij" not in dup


def test_find_parent_child_tautologies_detects_substring_overlap():
    level_lists = [
        [_summary(1, "Israël")],
        [_summary(2, "Israël-sancties", parent_name="Israël"), _summary(3, "Nederzettingen", parent_name="Israël")],
    ]
    findings = find_parent_child_tautologies(level_lists)
    assert len(findings) == 1
    assert findings[0][:3] == (1, 2, "Israël-sancties")


def test_find_person_or_party_labels_matches_db_tokens():
    level_lists = [[_summary(1, "PVV-kritiek"), _summary(2, "Stikstof")]]
    findings = find_person_or_party_labels(level_lists, {"pvv", "kritiek"})
    assert len(findings) == 1
    assert findings[0][0:3] == (0, 1, "PVV-kritiek")


def test_find_overlong_labels_respects_max_words():
    level_lists = [[_summary(1, "Conflictgerelateerd seksueel geweld"), _summary(2, "Sudan")]]
    findings = find_overlong_labels(level_lists, max_words=2)
    assert len(findings) == 1
    assert findings[0][:3] == (0, 1, "Conflictgerelateerd seksueel geweld")
