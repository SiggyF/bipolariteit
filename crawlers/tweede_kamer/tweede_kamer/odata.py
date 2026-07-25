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


def vergadering_url_for_activiteit(datum):
    target_date = datetime.date.fromisoformat(datum.split("T")[0])
    start = (target_date - datetime.timedelta(days=1)).isoformat()
    end = (target_date + datetime.timedelta(days=1)).isoformat()
    filter_expr = (
        f"Datum ge {start}T00:00:00Z and Datum le {end}T23:59:59Z "
        f"and Kamer eq 'Tweede Kamer' and Soort eq 'Plenair' and Verwijderd eq false"
    )
    return build_url("Vergadering", filter=filter_expr, top=10)


def pick_closest_vergadering(matches, datum):
    if not matches:
        return None
    target_date = datetime.date.fromisoformat(datum.split("T")[0])
    matches = sorted(
        matches,
        key=lambda v: abs((datetime.date.fromisoformat(v["Datum"].split("T")[0]) - target_date).days),
    )
    return matches[0]


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
