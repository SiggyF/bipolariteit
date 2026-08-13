from pipeline.build_confrontatie_export import build_bands_and_losse


def _tree():
    """Synthetische Gemini-tree met dezelfde structuurpatronen als de echte
    stikstof-output: een direct top-level paar (1 vs 10), een genest paar
    waarbij het contra-argument een kind is van een ander top-level contra-
    argument (2 vs 11, 11 is kind van top-level 20), en een cross-band-geval
    waarbij hetzelfde pro-argument (1) via een kind (3) een tweede keer
    weersproken wordt (3 vs 30) -- dat kind moet dan een verwijskaart
    krijgen i.p.v. een duplicaat van argument 1."""
    return {
        "pro": {
            "nodes": [
                {"argument_id": 1, "gist": "pro hoofdargument", "children": [{"argument_id": 3, "gist": "onderbouwing van 1"}]},
                {"argument_id": 2, "gist": "los pro-argument"},
                {"label": "groep", "arguments": [{"argument_id": 4, "gist": "groepslid a"}, {"argument_id": 5, "gist": "groepslid b"}], "children": []},
            ]
        },
        "contra": {
            "nodes": [
                {"argument_id": 10, "gist": "contra hoofdargument"},
                {"argument_id": 20, "gist": "ander contra-hoofdargument", "children": [{"argument_id": 11, "gist": "onderbouwing van 20"}]},
                {"argument_id": 30, "gist": "los contra-argument"},
                {"argument_id": 40, "gist": "ongebruikt contra-argument"},
            ]
        },
        "oppositions": [
            {"argument_a_id": 1, "argument_b_id": 10, "relation_type": "direct_rebuttal"},
            {"argument_a_id": 2, "argument_b_id": 11, "relation_type": "direct_rebuttal"},
            {"argument_a_id": 3, "argument_b_id": 30, "relation_type": "direct_rebuttal"},
        ],
        "twijfelachtige_classificaties": [],
    }


def test_direct_top_level_pair_gets_two_real_cards():
    result = build_bands_and_losse(_tree())
    band = result["bands"][0]
    assert band["pro"] == {"type": "node", "id": 1, "kids": []}
    assert band["contra"] == {"type": "node", "id": 10, "kids": []}


def test_nested_side_anchors_on_its_top_level_parent():
    result = build_bands_and_losse(_tree())
    band = result["bands"][1]
    # argument 2 (pro, top-level) weerspreekt 11, dat genest is onder top-level 20:
    # de "echte kaart" hoort bij de voorouder (20), niet bij 11 zelf.
    assert band["pro"] == {"type": "node", "id": 2, "kids": []}
    assert band["contra"] == {"type": "node", "id": 20, "kids": []}


def test_second_use_of_same_top_level_ancestor_becomes_a_reference():
    result = build_bands_and_losse(_tree())
    band = result["bands"][2]
    # argument 3 is een kind van top-level 1, dat al "geclaimd" is door band 0 --
    # dus hier een verwijskaart naar band 1 (1-indexed nummer van band 0), niet
    # nogmaals een echte kaart voor argument 1.
    assert band["pro"] == {"type": "ref", "ref_id": 3, "band_nummer": 1}
    assert band["contra"] == {"type": "node", "id": 30, "kids": []}


def test_unopposed_top_level_argument_and_group_end_up_losse():
    result = build_bands_and_losse(_tree())
    assert result["losse_argumenten"] == [40]
    assert result["losse_groepen"] == [
        {"kind": "group", "label": "groep", "samenvatting": None, "member_ids": [4, 5]}
    ]


def test_every_argument_id_is_indexed_exactly_once_in_the_registry():
    result = build_bands_and_losse(_tree())
    assert set(result["registry"].keys()) == {1, 2, 3, 4, 5, 10, 11, 20, 30, 40}


def test_band_thema_and_samenvatting_are_passed_through_when_present():
    tree = _tree()
    tree["oppositions"][0]["thema"] = "Moet er sneller gereduceerd worden?"
    tree["pro"]["nodes"][0]["samenvatting"] = "Snellere reductie is nodig voor natuurherstel."
    result = build_bands_and_losse(tree)
    band = result["bands"][0]
    assert band["thema"] == "Moet er sneller gereduceerd worden?"
    assert result["registry"][1]["samenvatting"] == "Snellere reductie is nodig voor natuurherstel."


def test_band_thema_falls_back_to_mechanical_gist_join_when_absent():
    result = build_bands_and_losse(_tree())
    band = result["bands"][0]
    assert band["thema"] == "pro hoofdargument vs contra hoofdargument"
    assert result["registry"][1]["samenvatting"] is None


def test_opposed_group_member_gets_its_own_card_and_drops_out_of_losse_groepen():
    tree = _tree()
    tree["oppositions"].append({"argument_a_id": 4, "argument_b_id": 40, "relation_type": "direct_rebuttal"})
    result = build_bands_and_losse(tree)
    band = result["bands"][-1]
    # groepslid 4 (pro) wordt hier los weersproken: het is zijn eigen
    # top-level voorouder, dus een gewone "node"-kaart -- geen crash op een
    # niet-bestaande synthetische groeps-id.
    assert band["pro"] == {"type": "node", "id": 4, "kids": []}
    assert band["contra"] == {"type": "node", "id": 40, "kids": []}
    # de groep blijft niet ook nog los staan nu lid 4 al een band-kaart heeft.
    assert result["losse_groepen"] == []
    assert result["losse_argumenten"] == []
