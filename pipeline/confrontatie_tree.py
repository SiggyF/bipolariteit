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


def merge_review_neutraal(structured, review):
    """Tweede experimentele variant (na de verworpen pro/contra-rolversie
    hierboven, zie sessie-overleg: een LLM die een "kant" aanneemt bleek
    label-gedreven te oordelen -- 8 van de 8 conflict-relaties kregen
    "target wint" ongeacht inhoud, puur omdat target toevallig altijd de
    pro-stance-positie was). Deze variant gebruikt ÉÉN neutrale beoordelaar
    zonder kant/rol (zie pipeline/prompts/boomredactie.md), die per relatie
    een feitelijke vraag beantwoordt (expliciete verwijzing? logische
    samenhang?) i.p.v. een normatief "wie wint"-oordeel.

    `review` is {"beoordelingen": [{"relation_index", "sterkte", "type",
    "reden", "scheme"}]}, één entry per relatie in structured["relations"].
    `sterkte in ("zwak", "geen")` behoudt de relatie (met `sterkte`/`type`/
    `reden`); `sterkte == "geen"` laat 'm vervallen."""
    by_index = {b["relation_index"]: b for b in review["beoordelingen"]}

    final_relations = []
    for i, relation in enumerate(structured["relations"]):
        b = by_index.get(i)
        if b is None or b.get("sterkte") == "geen":
            continue
        scheme = relation.get("scheme")
        if b.get("scheme"):
            scheme = b["scheme"]
        final_relations.append({
            **relation,
            "scheme": scheme,
            "sterkte": b["sterkte"],
            "type": b.get("type"),
            "reden": b.get("reden"),
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


def _classify_symmetrie(pro_pt, pro_tp, contra_pt, contra_tp):
    """Experimenteel (branch experiment/252-bidirectionele-weerlegging): bij
    een `conflict`-relatie beoordelen beide redacteuren nu TWEE richtingen
    (weerlegt premise target, weerlegt target premise) i.p.v. één
    "onderschrijft". Classificeert het resulterende patroon van 4 booleans.

    `pro_pt` = pro-redacteur over "premise weerlegt target", etc."""
    premise_target = pro_pt and contra_pt
    target_premise = pro_tp and contra_tp
    if premise_target and target_premise:
        return "wederzijds_erkend"
    if premise_target and not (pro_tp or contra_tp):
        return "eenzijdig_premise"
    if target_premise and not (pro_pt or contra_pt):
        return "eenzijdig_target"
    # Het schoolvoorbeeld van polarisatie: elke redacteur onderschrijft de
    # weerlegging alleen als die de eigen kant gelijk geeft, en wijst de
    # weerlegging vanuit de tegenstander af.
    if pro_pt and not pro_tp and contra_tp and not contra_pt:
        return "gepolariseerd"
    if not pro_pt and pro_tp and contra_pt and not contra_tp:
        return "gepolariseerd"
    if not any([pro_pt, pro_tp, contra_pt, contra_tp]):
        return None  # geen enkel signaal -- relatie verdwijnt, zoals bij merge_reviews()
    return "gemengd"


def merge_reviews_bidirectioneel(structured, pro_review, contra_review):
    """Experimentele variant van merge_reviews() (issue #252, zie
    docs-overleg): voor `conflict`-relaties geven beide redacteuren niet één
    "onderschrijft" maar twee gerichte oordelen (weerlegt premise target?
    weerlegt target premise?), zie pipeline/prompts/boomredactie.md. Dat
    levert 4 booleans per conflict-relatie op, waaruit een rijker
    `symmetrie`-signaal volgt dan het simpele `weak_link` (zie
    _classify_symmetrie) -- met name het "gepolariseerd"-geval (beide kanten
    erkennen alleen de eigen weerlegging) is inhoudelijk interessanter dan
    "weak_link" laat zien.

    `support`-relaties blijven ongewijzigd (enkel `onderschrijft`, zelfde
    logica als merge_reviews())."""
    pro_by_index = {b["relation_index"]: b for b in pro_review["beoordelingen"]}
    contra_by_index = {b["relation_index"]: b for b in contra_review["beoordelingen"]}

    final_relations = []
    for i, relation in enumerate(structured["relations"]):
        pro_b = pro_by_index.get(i, {})
        contra_b = contra_by_index.get(i, {})

        if relation["relation_type"] == "support":
            pro_ok = bool(pro_b.get("onderschrijft"))
            contra_ok = bool(contra_b.get("onderschrijft"))
            if not pro_ok and not contra_ok:
                continue
            beoordeeld_door = [kant for kant, ok in (("pro", pro_ok), ("contra", contra_ok)) if ok]
            final_relations.append({
                **relation,
                "weak_link": len(beoordeeld_door) == 1,
                "beoordeeld_door": beoordeeld_door,
                "confidence": 0.5 if len(beoordeeld_door) == 1 else 1.0,
            })
            continue

        pro_pt, pro_tp = bool(pro_b.get("weerlegt_premise_target")), bool(pro_b.get("weerlegt_target_premise"))
        contra_pt, contra_tp = bool(contra_b.get("weerlegt_premise_target")), bool(contra_b.get("weerlegt_target_premise"))
        symmetrie = _classify_symmetrie(pro_pt, pro_tp, contra_pt, contra_tp)
        if symmetrie is None:
            continue

        scheme = relation.get("scheme")
        if pro_pt and contra_pt:
            pro_scheme, contra_scheme = pro_b.get("scheme"), contra_b.get("scheme")
            if pro_scheme and pro_scheme == contra_scheme:
                scheme = pro_scheme

        final_relations.append({
            **relation,
            "scheme": scheme,
            "symmetrie": symmetrie,
            "weerlegt_premise_target": {"pro": pro_pt, "contra": contra_pt},
            "weerlegt_target_premise": {"pro": pro_tp, "contra": contra_tp},
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
