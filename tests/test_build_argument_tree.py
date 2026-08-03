import pytest

from pipeline.build_argument_tree import _validate_tree


VALID_IDS = {1, 2, 3, 4, 5}


def test_validate_tree_accepts_flat_arguments():
    tree = {"nodes": [{"argument_id": 1}, {"argument_id": 2}, {"argument_id": 3}, {"argument_id": 4}, {"argument_id": 5}]}
    nodes = _validate_tree(tree, VALID_IDS)
    assert [n["argument_id"] for n in nodes] == [1, 2, 3, 4, 5]
    assert all(n["children"] == [] for n in nodes)


def test_validate_tree_accepts_coordinative_group():
    tree = {"nodes": [
        {"label": "gedeelde reden", "argument_ids": [1, 2], "children": []},
        {"argument_id": 3}, {"argument_id": 4}, {"argument_id": 5},
    ]}
    nodes = _validate_tree(tree, VALID_IDS)
    group = nodes[0]
    assert group["label"] == "gedeelde reden"
    assert group["argument_ids"] == [1, 2]


def test_validate_tree_accepts_subordinative_children():
    tree = {"nodes": [
        {"argument_id": 1, "children": [{"argument_id": 2, "children": [{"argument_id": 3}]}]},
        {"argument_id": 4}, {"argument_id": 5},
    ]}
    nodes = _validate_tree(tree, VALID_IDS)
    assert nodes[0]["children"][0]["argument_id"] == 2
    assert nodes[0]["children"][0]["children"][0]["argument_id"] == 3


def test_validate_tree_rejects_unknown_argument_id():
    tree = {"nodes": [{"argument_id": 999}]}
    with pytest.raises(ValueError, match="onbekend argument_id"):
        _validate_tree(tree, VALID_IDS)


def test_validate_tree_rejects_duplicate_argument_id():
    tree = {"nodes": [{"argument_id": 1}, {"argument_id": 1}, {"argument_id": 2}, {"argument_id": 3}, {"argument_id": 4}, {"argument_id": 5}]}
    with pytest.raises(ValueError, match="meer dan één keer"):
        _validate_tree(tree, VALID_IDS)


def test_validate_tree_rejects_missing_argument_id():
    tree = {"nodes": [{"argument_id": 1}]}
    with pytest.raises(ValueError, match="ontbreken"):
        _validate_tree(tree, VALID_IDS)


def test_validate_tree_rejects_argument_id_that_is_also_a_subordinative_child():
    """Eenzelfde argument mag niet zowel top-level als kind ergens anders zijn --
    dat zou hetzelfde argument twee keer in de boom tekenen."""
    tree = {"nodes": [
        {"argument_id": 1},
        {"argument_id": 2, "children": [{"argument_id": 1}]},
        {"argument_id": 3}, {"argument_id": 4}, {"argument_id": 5},
    ]}
    with pytest.raises(ValueError, match="meer dan één keer"):
        _validate_tree(tree, VALID_IDS)


def test_validate_tree_rejects_group_without_label():
    tree = {"nodes": [{"argument_ids": [1, 2]}, {"argument_id": 3}, {"argument_id": 4}, {"argument_id": 5}]}
    with pytest.raises(ValueError, match="'argument_id' óf 'label'"):
        _validate_tree(tree, VALID_IDS)


def test_validate_tree_rejects_group_with_single_argument():
    tree = {"nodes": [
        {"label": "te kleine groep", "argument_ids": [1]}, {"argument_id": 2}, {"argument_id": 3}, {"argument_id": 4}, {"argument_id": 5},
    ]}
    with pytest.raises(ValueError, match=">=2 argument_ids"):
        _validate_tree(tree, VALID_IDS)


def test_validate_tree_rejects_missing_nodes_key():
    with pytest.raises(ValueError, match="onverwachte JSON-vorm"):
        _validate_tree({"groups": []}, VALID_IDS)
