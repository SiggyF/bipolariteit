"""
Zuivere (geen LLM, geen DB) samenvoeglogica voor de argumentenboom-pipeline
(issue #252): combineert de concept-boom van de structureringsstap
(pipeline/prompts/argument_tree_gemini.md) met de twee onafhankelijke
beoordelingen van de redactiestap (pipeline/prompts/boomredactie.md, één
per kant) tot het eindresultaat dat pipeline/schemas/argument_tree.schema.json
valideert.

Regel: een relatie die door beide kanten onderschreven wordt telt als
stevig (weak_link=false, confidence=1.0); door precies één kant onderschreven
blijft ze staan maar wordt gemarkeerd (weak_link=true, confidence=0.5); door
geen van beide onderschreven verdwijnt ze -- geen relatie in de boom die
niemand overeind houdt. `scheme` van de structureringsstap blijft leidend,
tenzij beide kanten het onafhankelijk eens zijn over een andere waarde.

Zie scripts/agy_run_confrontatie_tree.py voor de orkestratie (de drie
LLM-calls + validatie eromheen).
"""


def merge_reviews(structured, pro_review, contra_review):
    """`structured` is de output van de structureringsstap (nodes/relations/
    coordinatieve_groepen/twijfelachtige_classificaties, zonder
    weak_link/beoordeeld_door/confidence). `pro_review`/`contra_review` zijn
    elk {"beoordelingen": [{"relation_index", "onderschrijft", "scheme"}]},
    één entry per relatie in `structured["relations"]`, op dezelfde index.

    Retourneert een dict die voldoet aan argument_tree.schema.json."""
    pro_by_index = {b["relation_index"]: b for b in pro_review["beoordelingen"]}
    contra_by_index = {b["relation_index"]: b for b in contra_review["beoordelingen"]}

    final_relations = []
    for i, relation in enumerate(structured["relations"]):
        pro_b = pro_by_index.get(i)
        contra_b = contra_by_index.get(i)
        pro_ok = bool(pro_b and pro_b["onderschrijft"])
        contra_ok = bool(contra_b and contra_b["onderschrijft"])
        if not pro_ok and not contra_ok:
            continue

        beoordeeld_door = [kant for kant, ok in (("pro", pro_ok), ("contra", contra_ok)) if ok]
        weak_link = len(beoordeeld_door) == 1

        scheme = relation.get("scheme")
        if pro_ok and contra_ok:
            pro_scheme = pro_b.get("scheme")
            contra_scheme = contra_b.get("scheme")
            if pro_scheme and pro_scheme == contra_scheme:
                scheme = pro_scheme

        final_relations.append({
            "relation_type": relation["relation_type"],
            "target_argument_id": relation["target_argument_id"],
            "premise_argument_ids": relation["premise_argument_ids"],
            "thema": relation.get("thema"),
            "scheme": scheme,
            "weak_link": weak_link,
            "beoordeeld_door": beoordeeld_door,
            "confidence": 0.5 if weak_link else 1.0,
        })

    return {
        "nodes": [
            {"argument_id": n["argument_id"], "gist": n["gist"], "samenvatting": n.get("samenvatting")}
            for n in structured["nodes"]
        ],
        "relations": final_relations,
        "coordinatieve_groepen": structured.get("coordinatieve_groepen", []),
        "twijfelachtige_classificaties": structured.get("twijfelachtige_classificaties", []),
    }
