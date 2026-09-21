"""
Zuivere (geen LLM, geen DB) samenvoeglogica voor de argumentenboom-pipeline
(issue #252): combineert de concept-boom van de structureringsstap
(pipeline/prompts/argument_tree_gemini.md) met de losse, per-relatie
redactiechecks (pipeline/prompts/boomredactie_rebuttal_detection.md voor
`conflict`, pipeline/prompts/boomredactie_support_check.md voor `support`)
tot het eindresultaat dat pipeline/schemas/argument_tree.schema.json
valideert.

Voorgeschiedenis (zie issue #252, branch experiment/252-bidirectionele-
weerlegging): dit verving een eerdere, tweezijdige pro/contra-redactie
(twee LLM's beoordelen dezelfde relatie vanuit een toegewezen kant,
onenigheid = weak_link-signaal). Vier verschillende varianten daarvan --
rolgebonden, neutraal met 2/3 categorieen, per-relatie geisoleerd -- bleken
niet te discrimineren: het model convergeerde steeds naar exact hetzelfde
label voor alle relaties in een topic, met wel specifieke maar niet-
onderscheidende onderbouwing. Onderzoek (docs/research/) wijst dit aan als
een bekend fenomeen: LLM-as-judge is onbetrouwbaar bij interpretatieve/
normatieve vragen ("houdt deze weerlegging logisch stand?"), maar blijft
betrouwbaar bij feitelijke/functionele vragen ("reageert dit argument
aantoonbaar op de kern van het andere?", vergelijkbaar met IBM Project
Debater se "rebuttal detection"). Die laatste vraag, elke relatie in een
eigen geisoleerde call (geen batch -- minder onderlinge leakage, zie ook
scripts/agy_run_tagging_batch.py), discrimineert wel: getest op alle vier
topics, 18/28 True bij conflict-relaties, 8/16 True bij support-relaties
op stikstof, met steeds specifieke, per paar kloppende onderbouwing.

Regel: een relatie waarvan de check "nee" antwoordt (het premise-argument
engageert niet aantoonbaar met de kern van het target-argument) verdwijnt
uit de boom -- geen weak_link-tussenvorm meer, want er is geen onenigheid
meer om te meten, alleen een feitelijke ja/nee-constatering per relatie.

Zie scripts/argument_tree/agy_run_confrontatie_tree.py voor de orkestratie (1 structureer-
call + N losse redactiechecks + validatie).
"""

import logging

logger = logging.getLogger(__name__)


def drop_degenerate_coordinatieve_groepen(structured, topic_slug=None):
    """Verwijdert `coordinatieve_groepen`-entries met < 2 `argument_ids` uit
    de output van de structureringsstap (schema eist `minItems: 2`, zie
    pipeline/schemas/argument_tree.schema.json -- een groep van 1 is per
    definitie geen bundeling van onafhankelijk hetzelfde punt makende
    argumenten). Geconstateerd bij handmatige validatie van de asiel-boom
    (issue #254): Gemini volgt de instructie hier niet altijd.

    Muteert `structured` niet, retourneert een nieuwe dict. De losgemaakte
    argumenten blijven gewoon als node staan, alleen niet meer gegroepeerd."""
    groepen = structured.get("coordinatieve_groepen", [])
    behouden, verworpen = [], []
    for groep in groepen:
        (behouden if len(groep.get("argument_ids", [])) >= 2 else verworpen).append(groep)

    for groep in verworpen:
        logger.warning(
            "coordinatieve_groepen%s: groep '%s' met %d lid/leden verworpen (schema eist >=2): %s",
            f" ({topic_slug})" if topic_slug else "",
            groep.get("label", "?"), len(groep.get("argument_ids", [])), groep.get("argument_ids"),
        )

    return {**structured, "coordinatieve_groepen": behouden}


def merge_engagement_checks(structured, checks):
    """`structured` is de output van de structureringsstap (nodes/relations/
    coordinatieve_groepen/twijfelachtige_classificaties, zonder `reden`).
    `checks` is een lijst, één entry per relatie in `structured["relations"]`
    op dezelfde index: {"relation_index", "engageert": bool, "reden": str,
    "scheme": str|None (alleen relevant bij conflict, optioneel)}.

    Retourneert een dict die voldoet aan argument_tree.schema.json."""
    by_index = {c["relation_index"]: c for c in checks}

    final_relations = []
    for i, relation in enumerate(structured["relations"]):
        check = by_index.get(i)
        if check is None or not check.get("engageert"):
            continue

        scheme = relation.get("scheme")
        if check.get("scheme"):
            scheme = check["scheme"]

        final_relations.append({
            "relation_type": relation["relation_type"],
            "target_argument_id": relation["target_argument_id"],
            "premise_argument_ids": relation["premise_argument_ids"],
            "thema": relation.get("thema"),
            "scheme": scheme,
            "reden": check.get("reden", ""),
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
