import pytest

from pipeline.build_argument_tree import _validate_tree


VALID_IDS = {1, 2, 3, 4, 5}


def arg(argument_id, gist="korte gist", children=None):
    node = {"argument_id": argument_id, "gist": gist}
    if children is not None:
        node["children"] = children
    return node


def test_validate_tree_accepts_flat_arguments():
    tree = {"nodes": [arg(1), arg(2), arg(3), arg(4), arg(5)]}
    nodes = _validate_tree(tree, VALID_IDS)
    assert [n["argument_id"] for n in nodes] == [1, 2, 3, 4, 5]
    assert all(n["gist"] == "korte gist" for n in nodes)
    assert all(n["children"] == [] for n in nodes)


def test_validate_tree_accepts_coordinative_group():
    tree = {"nodes": [
        {"label": "gedeelde reden", "arguments": [
            {"argument_id": 1, "gist": "eerste gist"},
            {"argument_id": 2, "gist": "tweede gist"},
        ], "children": []},
        arg(3), arg(4), arg(5),
    ]}
    nodes = _validate_tree(tree, VALID_IDS)
    group = nodes[0]
    assert group["label"] == "gedeelde reden"
    assert group["arguments"] == [
        {"argument_id": 1, "gist": "eerste gist"},
        {"argument_id": 2, "gist": "tweede gist"},
    ]


def test_validate_tree_accepts_subordinative_children():
    tree = {"nodes": [
        arg(1, children=[arg(2, children=[arg(3)])]),
        arg(4), arg(5),
    ]}
    nodes = _validate_tree(tree, VALID_IDS)
    assert nodes[0]["children"][0]["argument_id"] == 2
    assert nodes[0]["children"][0]["children"][0]["argument_id"] == 3


def test_validate_tree_rejects_unknown_argument_id():
    tree = {"nodes": [arg(999)]}
    with pytest.raises(ValueError, match="onbekend argument_id"):
        _validate_tree(tree, VALID_IDS)


def test_validate_tree_rejects_duplicate_argument_id():
    tree = {"nodes": [arg(1), arg(1), arg(2), arg(3), arg(4), arg(5)]}
    with pytest.raises(ValueError, match="meer dan één keer"):
        _validate_tree(tree, VALID_IDS)


def test_validate_tree_rejects_missing_argument_id():
    tree = {"nodes": [arg(1)]}
    with pytest.raises(ValueError, match="ontbreken"):
        _validate_tree(tree, VALID_IDS)


def test_validate_tree_rejects_argument_id_that_is_also_a_subordinative_child():
    """Eenzelfde argument mag niet zowel top-level als kind ergens anders zijn --
    dat zou hetzelfde argument twee keer in de boom tekenen."""
    tree = {"nodes": [
        arg(1),
        arg(2, children=[arg(1)]),
        arg(3), arg(4), arg(5),
    ]}
    with pytest.raises(ValueError, match="meer dan één keer"):
        _validate_tree(tree, VALID_IDS)


def test_validate_tree_rejects_group_without_label():
    tree = {"nodes": [{"arguments": [{"argument_id": 1, "gist": "a"}, {"argument_id": 2, "gist": "b"}]}, arg(3), arg(4), arg(5)]}
    with pytest.raises(ValueError, match="'argument_id' óf 'label'"):
        _validate_tree(tree, VALID_IDS)


def test_validate_tree_rejects_group_with_single_argument():
    tree = {"nodes": [
        {"label": "te kleine groep", "arguments": [{"argument_id": 1, "gist": "a"}]}, arg(2), arg(3), arg(4), arg(5),
    ]}
    with pytest.raises(ValueError, match=">=2 arguments"):
        _validate_tree(tree, VALID_IDS)


def test_validate_tree_rejects_missing_nodes_key():
    with pytest.raises(ValueError, match="onverwachte JSON-vorm"):
        _validate_tree({"groups": []}, VALID_IDS)


def test_validate_tree_rejects_missing_gist():
    tree = {"nodes": [{"argument_id": 1}, arg(2), arg(3), arg(4), arg(5)]}
    with pytest.raises(ValueError, match="ontbrekende of lege gist"):
        _validate_tree(tree, VALID_IDS)


def test_validate_tree_rejects_gist_that_is_a_full_sentence():
    tree = {"nodes": [
        arg(1, gist="Dit is een veel te lange gist die eigenlijk een hele zin is en geen 3-4 woorden"),
        arg(2), arg(3), arg(4), arg(5),
    ]}
    with pytest.raises(ValueError, match="gist te lang"):
        _validate_tree(tree, VALID_IDS)


def test_validate_tree_rejects_group_member_without_gist():
    tree = {"nodes": [
        {"label": "gedeelde reden", "arguments": [{"argument_id": 1}, {"argument_id": 2, "gist": "b"}]},
        arg(3), arg(4), arg(5),
    ]}
    with pytest.raises(ValueError, match="ontbrekende of lege gist"):
        _validate_tree(tree, VALID_IDS)
