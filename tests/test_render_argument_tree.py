import shutil

import pytest

from pipeline.render_argument_tree import build_d2_source, render_svg

SAMPLE_TREE = {
    "arguments": {
        "1": {"quote_text": "Argument één.", "actor_name": "Jan Jansen", "actor_party": "GL"},
        "2": {"quote_text": "Argument twee, met \"aanhalingstekens\".", "actor_name": "Anne An", "actor_party": None},
        "3": {"quote_text": "Argument drie.", "actor_name": "Piet Piet", "actor_party": "PvdD"},
        "10": {"quote_text": "Contra-argument.", "actor_name": "Klaas Klaas", "actor_party": "BBB"},
    },
    "stances": [
        {"stance": "pro", "argument_count": 3, "nodes": [
            {"argument_id": 1, "children": [{"argument_id": 2}]},
            {"argument_id": 3},
        ]},
        {"stance": "contra", "argument_count": 1, "nodes": [{"argument_id": 10}]},
    ],
    "oppositions": [{"argument_a_id": 10, "argument_b_id": 3, "confidence": 0.6}],
}


def test_build_d2_source_contains_all_argument_shapes():
    src = build_d2_source(SAMPLE_TREE)
    for argument_id in ("apro_1", "apro_2", "apro_3", "acontra_10"):
        assert f"{argument_id}:" in src


def test_build_d2_source_escapes_embedded_quotes():
    src = build_d2_source(SAMPLE_TREE)
    assert '\\"aanhalingstekens\\"' in src


def test_build_d2_source_draws_subordinative_edge_upward_from_child_to_parent():
    src = build_d2_source(SAMPLE_TREE)
    assert 'apro_2 -> apro_1: "onderbouwt"' in src


def test_build_d2_source_draws_opposition_edge_with_full_cross_stance_path():
    src = build_d2_source(SAMPLE_TREE)
    assert 'contra.acontra_10 -> pro.apro_3: "weerlegt"' in src


def test_build_d2_source_skips_opposition_with_argument_outside_tree():
    tree = dict(SAMPLE_TREE, oppositions=[{"argument_a_id": 10, "argument_b_id": 999, "confidence": 0.1}])
    src = build_d2_source(tree)
    assert "weerlegt" not in src


def test_build_d2_source_omits_empty_stance():
    tree = dict(SAMPLE_TREE, stances=[SAMPLE_TREE["stances"][0], {"stance": "unclear", "argument_count": 0, "nodes": []}])
    src = build_d2_source(tree)
    assert 'unclear: "Onduidelijk"' not in src


@pytest.mark.skipif(shutil.which("d2") is None, reason="d2-CLI niet geïnstalleerd")
def test_render_svg_compiles_sample_tree(tmp_path):
    src = build_d2_source(SAMPLE_TREE)
    out_path = tmp_path / "boom.svg"
    render_svg(src, out_path)
    assert out_path.exists()
    assert "<svg" in out_path.read_text()


def test_render_svg_raises_clear_error_without_d2_binary(tmp_path, monkeypatch):
    monkeypatch.setattr("pipeline.render_argument_tree.shutil.which", lambda _name: None)
    src = build_d2_source(SAMPLE_TREE)
    with pytest.raises(RuntimeError, match="d2-CLI niet gevonden"):
        render_svg(src, tmp_path / "boom.svg")
