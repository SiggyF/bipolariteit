"""
Bouwt data/bewindspersonen.toml: ministers/staatssecretarissen relevant voor
de laatste 2 kamerperiodes (Tweede Kamer 2023-2025 en 2025-heden, samen
[verwerking].vanaf = 2023-12-06 in data/politieke-periodes.toml) met hun
partij, via Wikidata. SINDS (zie hieronder) ligt op 2022 -- de start van
Kabinet-Rutte IV -- niet op de kamerperiode zelf, omdat een bewindspersoon
zijn functie vóór de exportdrempel kan zijn gestart en die tot erna kan
hebben behouden. Nodig omdat bewindspersonen in de VLOS-brondata geen
<fractie> hebben (ze spreken niet namens een Kamerfractie) -- de meesten zijn
via de TK OData Persoon-API te herleiden (zie
pipeline.ingest.ingest_tk.lookup_bewindspersoon_party), maar een deel heeft
geen Kamerlidschap en dus geen OData-Persoon-record. Dit bestand is de
fallback daarvoor.

Twee SPARQL-queries:
1. Alle posities die een subklasse zijn van minister (Q83307) of
   staatssecretaris (Q1847103), met jurisdictie Nederland (Q55) of Koninkrijk
   der Nederlanden (Q29999) -- beide komen voor, zie de eigenaardigheid dat
   individuele Wikidata-positie-items niet consistent één van de twee kiezen
   -- gehouden sinds 2022 (zie SINDS).
2. Voor alle gevonden personen: hun partij-lidmaatschappen (P102) met
   begin/einddatum, om de partij op het moment van de functie te bepalen
   (niet zomaar de eerste/laatste partij ooit).

Niet elke bewindspersoon is op deze manier op te lossen (te incompleet
gemodelleerd in Wikidata, bv. Jaimi van Essen wiens positie-item geen label
of jurisdictie heeft) -- die blijven een handmatige uitzondering in
pipeline.ingest.ingest_tk.BEWINDSPERSOON_PARTY_OVERRIDES.

Gebruik:
    uv run python scripts/fetch_bewindspersonen_wikidata.py
"""

import re
import tomllib
from pathlib import Path

import requests

SPARQL_URL = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "bipolariteit-wikidata-fetch/0.1 (contact: f.baart@gmail.com; onderzoeksproject)"}
OUT_PATH = Path(__file__).parent.parent / "data" / "bewindspersonen.toml"

# De relevante kamerperiodes zijn Tweede Kamer 2023-2025 en 2025-heden (samen
# [verwerking].vanaf = 2023-12-06 in data/politieke-periodes.toml -- alleen
# documenten van die datum af worden geexporteerd). SINDS ligt bewust eerder
# (start Kabinet-Rutte IV, 2022-01-10): een bewindspersoon kan zijn functie
# vóór de drempel gestart zijn en tot erna hebben behouden, dus zijn positie-
# startdatum in Wikidata kan vóór 2023-12-06 liggen terwijl hij nog wel in een
# geexporteerd document spreekt.
SINDS = 2022

# Wikidata geeft volledige partijnamen; genormaliseerd naar de afkortingen die
# de rest van de DB gebruikt (actors.party, via TK OData Fractie.Afkorting).
PARTY_NORMALIZE = {
    "BoerBurgerBeweging": "BBB",
    "Christen-Democratisch Appèl": "CDA",
    "Democraten 66": "D66",
    "Nieuw Sociaal Contract": "NSC",
    "Partij van de Vrijheid": "PVV",
    "Partij voor de Vrijheid": "PVV",
    "Volkspartij voor Vrijheid en Democratie": "VVD",
    "onafhankelijk politicus": "Onafhankelijk",
}


def _sparql(query):
    resp = requests.get(SPARQL_URL, params={"query": query}, headers={**HEADERS, "Accept": "application/sparql-results+json"}, timeout=60)
    resp.raise_for_status()
    return resp.json()["results"]["bindings"]


def fetch_positions():
    query = """
        SELECT ?person ?personLabel ?positionLabel ?start WHERE {
            VALUES ?class { wd:Q83307 wd:Q1847103 }
            VALUES ?jurisdiction { wd:Q55 wd:Q29999 }
            ?position wdt:P279* ?class .
            ?position wdt:P1001 ?jurisdiction .
            ?person p:P39 ?stmt .
            ?stmt ps:P39 ?position .
            ?stmt pq:P580 ?start .
            FILTER(YEAR(?start) >= %d)
            SERVICE wikibase:label { bd:serviceParam wikibase:language "nl,en". }
        } ORDER BY ?personLabel
    """ % SINDS
    by_person = {}
    for b in _sparql(query):
        qid = b["person"]["value"].split("/")[-1]
        by_person.setdefault(qid, {"name": b["personLabel"]["value"], "positions": []})
        by_person[qid]["positions"].append((b["start"]["value"], b["positionLabel"]["value"]))
    return by_person


def fetch_parties(person_qids):
    values = " ".join(f"wd:{qid}" for qid in person_qids)
    query = f"""
        SELECT ?person ?party ?partyLabel ?start ?end WHERE {{
            VALUES ?person {{ {values} }}
            ?person p:P102 ?stmt .
            ?stmt ps:P102 ?party .
            OPTIONAL {{ ?stmt pq:P580 ?start }}
            OPTIONAL {{ ?stmt pq:P582 ?end }}
            SERVICE wikibase:label {{ bd:serviceParam wikibase:language "nl,en". }}
        }}
    """
    by_person = {}
    for b in _sparql(query):
        qid = b["person"]["value"].split("/")[-1]
        party = b.get("partyLabel", {}).get("value")
        if not party:
            continue
        start = b.get("start", {}).get("value")
        end = b.get("end", {}).get("value")
        by_person.setdefault(qid, []).append((start, end, party))
    return by_person


def party_at(memberships, at_date):
    """Partij die op at_date actief was; bij geen overlap de partij met de
    dichtstbijzijnde start vóór at_date (bv. geen einddatum ingevuld ondanks
    een latere partijwisseling)."""
    overlapping = [m for m in memberships if (m[0] is None or m[0] <= at_date) and (m[1] is None or m[1] >= at_date)]
    if overlapping:
        overlapping.sort(key=lambda m: m[0] or "")
        return overlapping[-1][2]
    started_before = sorted((m for m in memberships if m[0] and m[0] <= at_date), key=lambda m: m[0])
    return started_before[-1][2] if started_before else None


def main():
    positions_by_person = fetch_positions()
    parties_by_person = fetch_parties(positions_by_person.keys())

    rows = []
    skipped = []
    for qid, info in sorted(positions_by_person.items(), key=lambda kv: kv[1]["name"]):
        name = info["name"]
        if re.fullmatch(r"Q\d+", name):
            # Geen label in nl/en -- SERVICE wikibase:label valt dan terug op
            # de kale QID zelf. Zo'n naam matcht nooit een VLOS-sprekernaam.
            skipped.append((name, "geen Wikidata-label"))
            continue
        latest_start, latest_pos = sorted(info["positions"])[-1]
        functie = "staatssecretaris" if "staatssecretaris" in latest_pos.lower() else "minister"
        party = party_at(parties_by_person.get(qid, []), latest_start)
        if not party:
            skipped.append((name, latest_pos))
            continue
        rows.append((name, PARTY_NORMALIZE.get(party, party), functie, latest_pos))

    print(f"{len(rows)} bewindspersonen met partij, {len(skipped)} zonder (blijven ongemoeid):")
    for name, pos in skipped:
        print(f"  {name} -- {pos}")

    lines = [
        "# Ministers/staatssecretarissen van de laatste 2 kamerperiodes (Kabinet-",
        "# Rutte IV, Kabinet-Schoof, Kabinet-Jetten), gebouwd uit Wikidata --",
        "# gegenereerd door scripts/fetch_bewindspersonen_wikidata.py, niet met de",
        "# hand bijgehouden. Gebruikt door pipeline/ingest/ingest_tk.py als laatste",
        "# fallback wanneer de TK OData Persoon-API geen Kamerlidschap kent",
        "# (bewindspersonen zonder eigen Kamerzetel).",
        "",
    ]
    for name, party, functie, functietitel in rows:
        lines += [
            "[[bewindspersonen]]",
            f'naam = "{name}"',
            f'partij = "{party}"',
            f'functie = "{functie}"',
            f'functietitel = "{functietitel}"',
            "",
        ]
    OUT_PATH.write_text("\n".join(lines))
    print(f"geschreven: {OUT_PATH}")

    # Valideer meteen dat het resultaat geldige TOML is.
    tomllib.loads(OUT_PATH.read_text())


if __name__ == "__main__":
    main()
