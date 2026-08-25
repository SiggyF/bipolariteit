"""
Cardinaliteit per labelgroep uit data/tags.toml: onze eigen inschatting van
welke labelgroepen enkelvoudig (precies één tag) versus meervoudig (nul of
meer tags) zijn -- tags.toml zelf legt dit niet vast. Bewust in code i.p.v.
in tags.toml, zodat de onderzoeker het bestand kan blijven bewerken zonder
deze structuurkeuze te hoeven begrijpen of onderhouden.
"""

LABELGROEP_SELECTIE = {
    "Redeneerschema": "enkel",  # één primair redeneerschema per argument
    "Debatzetten": "meervoud",  # geen, één of meerdere debatzetten kunnen samen voorkomen
    "Stijlmiddelen": "meervoud",  # meerdere stijlmiddelen kunnen tegelijk voorkomen in één argument
    "Framing-Focus": "enkel",  # episodisch/thematisch is per definitie exclusief
    "Generieke Nieuwsframes": "meervoud",  # frames kunnen samen voorkomen (bv. conflict + economisch)
    "Issue Arena": "enkel",  # één bron-arena per document
    "Actor Type": "enkel",  # één actor-hoedanigheid per document
    "Cultureel-Ideologische Breuklijn": "meervoud",  # culturele as (GAL/TAN) en economische as (Links/Rechts) zijn onafhankelijk
    "Morele Fundamenten": "meervoud",  # meerdere morele pijlers kunnen samen aangeroepen worden
    "Type Bewijsvoering": "meervoud",  # bewijstypen kunnen gecombineerd worden
    "Parlementaire Context": "enkel",  # één debatvorm per document
    "Metadiscussie": "enkel",  # een uiting is objectniveau (geen tag) of precies één metadiscussie-aspect
}
DEFAULT_SELECTIE = "meervoud"  # veilige default voor nog niet ingedeelde (nieuwe) labelgroepen

# Labelgroepen die deterministisch (zonder LLM) uit reeds bekende DB-data
# worden afgeleid -- zie pipeline/tag_arguments.py::assign_derived_tags.
# Blijven uit de LLM-catalogus/prompt om tokens/output-schema klein te houden.
DERIVED_LABELGROEPEN = {"Issue Arena", "Actor Type", "Parlementaire Context"}


def selectie_for(labelgroep_naam: str) -> str:
    return LABELGROEP_SELECTIE.get(labelgroep_naam, DEFAULT_SELECTIE)


def field_name_for(labelgroep_naam: str) -> str:
    """bv. 'Cultureel-Ideologische Breuklijn' -> 'cultureel_ideologische_breuklijn'."""
    return labelgroep_naam.lower().replace("-", "_").replace(" ", "_")
