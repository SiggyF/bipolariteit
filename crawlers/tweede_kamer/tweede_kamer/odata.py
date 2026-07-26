"""
Pure OData URL-building en selectie-heuristieken voor de Tweede Kamer
Open Data API (https://opendata.tweedekamer.nl/documentatie/odata-api).

Geen HTTP hier -- dat doet de spider via Scrapy's Request/Response. Dit
module bevat alleen de empirisch uitgevonden logica (zie docs/handoff.md):

- Er is geen directe foreign key tussen Activiteit en Vergadering. We
  koppelen via een datumheuristiek: zelfde dag (+/- 1) + Kamer='Tweede
  Kamer' + Soort='Plenair', en kiezen bij meerdere kandidaten de
  dichtstbijzijnde datum.
- Vergadering.Datum staat opgeslagen als lokale middernacht met een
  +01:00/+02:00-offset. Een exacte daggrens in UTC (`Z`) mist die rij
  omdat lokale middernacht vóór middernacht UTC valt -- daarom een
  marge van -1/+1 dag in plaats van een exacte daggrens.
- `best_verslag` kiest bij voorkeur Eindpublicatie+Gecorrigeerd, anders
  de eerste Eindpublicatie, anders het eerst gevonden Verslag.
"""

import datetime
import re
import urllib.parse

BASE_URL = "https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0"


def build_url(entity, filter=None, select=None, expand=None, orderby=None, top=None):
    params = {}
    if filter:
        params["$filter"] = filter
    if select:
        params["$select"] = select
    if expand:
        params["$expand"] = expand
    if orderby:
        params["$orderby"] = orderby
    if top:
        params["$top"] = top
    query = urllib.parse.urlencode(params)
    url = f"{BASE_URL}/{entity}"
    return f"{url}?{query}" if query else url


def resource_url(entity, entity_id):
    return f"{BASE_URL}/{entity}/{entity_id}/resource"


def activiteiten_url(topic_keyword, soort, top):
    filter_expr = f"contains(Onderwerp,'{topic_keyword}') and Verwijderd eq false"
    if soort:
        filter_expr += f" and Soort eq '{soort}'"
    return build_url("Activiteit", filter=filter_expr, orderby="Datum desc", top=top)


def vergadering_soort_for_activiteit(activiteit_soort):
    """Vergadering.Soort kent maar twee waarden ('Plenair'/'Commissie',
    geverifieerd live tegen de OData API) -- Activiteit.Soort heeft veel meer
    varianten (bv. "Plenair debat (debat)", "Commissiedebat",
    "Plenair debat (tweeminutendebat)"). 'Commissie' als default voor niet-
    Plenair-activiteiten is een aanname (nog niet tegen elke activiteit_soort
    getest, alleen tegen "Commissiedebat")."""
    if activiteit_soort and activiteit_soort.startswith("Plenair"):
        return "Plenair"
    return "Commissie"


def vergadering_url_for_activiteit(datum, activiteit_soort=None):
    target_date = datetime.date.fromisoformat(datum.split("T")[0])
    start = (target_date - datetime.timedelta(days=1)).isoformat()
    end = (target_date + datetime.timedelta(days=1)).isoformat()
    vergadering_soort = vergadering_soort_for_activiteit(activiteit_soort)
    filter_expr = (
        f"Datum ge {start}T00:00:00Z and Datum le {end}T23:59:59Z "
        f"and Kamer eq 'Tweede Kamer' and Soort eq '{vergadering_soort}' and Verwijderd eq false"
    )
    # top=50: op drukke commissiedagen lopen tientallen commissies parallel
    # (zie pick_closest_vergadering) -- bij Plenair zit er sowieso maar één
    # vergadering per dag in, dus deze cap raakt die stroom nooit.
    return build_url("Vergadering", filter=filter_expr, top=50)


_STOPWOORDEN = {"en", "de", "het", "een", "van", "voor", "over", "met", "in", "op"}


def _title_words(text):
    return {w for w in re.findall(r"[a-z]+", text.lower()) if w not in _STOPWOORDEN and len(w) > 2}


def pick_closest_vergadering(matches, datum, onderwerp=None, vergadering_soort=None):
    """Bij Plenair is er hooguit één Vergadering per dag en heet die sowieso
    generiek (bv. "89e vergadering, woensdag..."), dus datum-nabijheid is de
    enige en volstaande tiebreaker -- titel-matching zou daar juist nooit
    iets vinden en is dus niet aan de orde.

    Bij Commissie lopen op drukke dagen tientallen commissies parallel
    (zelfde datum), én kan een Activiteit zelf al geannuleerd/omgezet zijn
    zonder dat er die dag ook maar íets vergelijkbaars plaatsvond. Twee
    empirische gevallen bevestigen dat datum-nabijheid alléén dan niet
    volstaat, zelfs niet als er maar één kandidaat overblijft:
    - 2025-06-18 (10 same-day kandidaten): zonder titel-tiebreak koos dit
      puur op volgorde de verkeerde ("Vreemdelingen- en asielbeleid" i.p.v.
      "Stikstof en mestbeleid").
    - Een "OMGEZET in schriftelijk overleg"-Activiteit (dus geen sprekers-
      debat die dag) matchte de enige same-day kandidaat die toevallig
      bestond ("Cyberstrategie Defensie") -- compleet ongerelateerd.
    Daarom is voor Commissie een titel/onderwerp-woordoverlap altijd
    verplicht, ook bij precies één kandidaat; zonder overlap geven we bewust
    None terug (gemiste match) in plaats van te gokken (stille verkeerde
    match)."""
    if not matches:
        return None
    target_date = datetime.date.fromisoformat(datum.split("T")[0])
    matches = sorted(
        matches,
        key=lambda v: abs((datetime.date.fromisoformat(v["Datum"].split("T")[0]) - target_date).days),
    )
    closest_diff = abs((datetime.date.fromisoformat(matches[0]["Datum"].split("T")[0]) - target_date).days)
    same_day = [
        v for v in matches
        if abs((datetime.date.fromisoformat(v["Datum"].split("T")[0]) - target_date).days) == closest_diff
    ]
    if vergadering_soort != "Commissie":
        return same_day[0]

    onderwerp_words = _title_words(onderwerp) if onderwerp else set()
    if not onderwerp_words:
        return None

    scored = sorted(
        same_day,
        key=lambda v: len(_title_words(v["Titel"]) & onderwerp_words),
        reverse=True,
    )
    if len(_title_words(scored[0]["Titel"]) & onderwerp_words) > 0:
        return scored[0]
    return None


def verslagen_url_for_vergadering(vergadering_id):
    filter_expr = f"Vergadering_Id eq {vergadering_id} and Verwijderd eq false"
    return build_url("Verslag", filter=filter_expr, orderby="GewijzigdOp desc", top=5)


def best_verslag(verslagen):
    if not verslagen:
        return None
    for v in verslagen:
        if v["Soort"] == "Eindpublicatie" and v["Status"] == "Gecorrigeerd":
            return v
    for v in verslagen:
        if v["Soort"] == "Eindpublicatie":
            return v
    return verslagen[0]


def activiteit_website_url(nummer, soort):
    """Bouwt de publieke tweedekamer.nl-detailpagina voor een Activiteit uit
    Nummer (leesbare code, bv. "2025A03345" -- niet de GUID Id) en Soort.
    Zie docs/tk-data-sources-overview.md sectie 11: officieel gedocumenteerd
    via de OData-FAQ, geverifieerd voor zowel gecorrigeerde als nog niet
    gecorrigeerde debatten (werkt dus ook vlak na een recent debat). Geen
    HTTP hier, puur URL-opbouw -- zelfde stijl als de rest van deze module."""
    if not nummer:
        return None
    if soort and soort.startswith("Plenair"):
        return f"https://www.tweedekamer.nl/debat_en_vergadering/plenaire_vergaderingen/details/activiteit?id={nummer}"
    if soort and "Commissie" in soort:
        return f"https://www.tweedekamer.nl/debat_en_vergadering/commissievergaderingen/details?id={nummer}"
    return None
