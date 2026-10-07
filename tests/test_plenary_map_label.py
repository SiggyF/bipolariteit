"""Tests voor pipeline/plenary_map/label.py (issue #356-plan: medoids in echte
embeddingruimte + niveau-bewuste, parent-geconditioneerde prompt)."""

import numpy as np

from pipeline.plenary_map.label import _build_cluster_naming_prompt, compute_representative_examples


def test_compute_representative_examples_picks_vector_nearest_to_centroid():
    # 3 punten in cluster 0: twee bijna identiek, één duidelijke uitschieter.
    vectors = np.array([
        [1.0, 0.0, 0.0],
        [0.9, 0.1, 0.0],
        [0.0, 1.0, 0.0],
    ])
    ids = np.array([0, 0, 0])
    level_ids = [ids]
    level_lists = [[{"cluster_id": 0}]]
    texts = ["a", "b", "outlier"]
    rows = [{"debate_title": "d1"}, {"debate_title": "d2"}, {"debate_title": "d3"}]

    examples = compute_representative_examples(level_ids, level_lists, texts, vectors, rows, examples_per_cluster=2)

    picked = examples[0]["0"]["texts"]
    assert "outlier" not in picked
    assert set(picked) == {"a", "b"}


def test_prompt_level1_has_no_parent_differentiation_instruction():
    prompt = _build_cluster_naming_prompt(["stikstof"], ["tekst"], ["titel"], parent_label=None)
    assert "Bovenliggende categorie" not in prompt
    assert "overkoepelende naam" in prompt


def test_prompt_level2_references_parent_and_forbids_repeating_it():
    prompt = _build_cluster_naming_prompt(["sancties"], ["tekst"], ["titel"], parent_label="Israël")
    assert 'Bovenliggende categorie: "Israël"' in prompt
    assert "Israël" in prompt
    assert "herhaal niet simpelweg" in prompt.lower()
