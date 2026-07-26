"""
Segmenteert Tweede Kamer VLOS-XML Verslagen (data/raw/tweede_kamer/*.xml)
per sprekerbeurt naar documents + actors rows.

Gebruik:
    uv run python -m pipeline.ingest.ingest_tk --topic stikstof

VLOS-structuur (zie docs/handoff.md): <activiteit onderwerp="...">
bevat <activiteithoofd> -> <activiteitdeel soort="Spreekbeurt"> ->
<activiteititem soort="Woordvoerder"> -> <woordvoerder>, en elke
<woordvoerder> kan <interrumpant>-kinderen bevatten (onderbrekingen door
een andere spreker). Zowel <woordvoerder> als <interrumpant> hebben
dezelfde vorm: een <spreker>-kind en een <tekst>-kind. In plaats van op
tagnamen per nestingdiepte te vertrouwen, zoeken we generiek naar elk
element met zowel een directe <spreker> als <tekst> -- dat dekt beide
gevallen zonder aannames over de diepte.
"""

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from pipeline.db import db
from pipeline.paths import RAW_DIR_TWEEDE_KAMER as RAW_DIR

NS = "{http://www.tweedekamer.nl/ggm/vergaderverslag/v1.0}"


def _local(tag):
    return tag.split("}")[-1]


def _text_of(tekst_el):
    """Voegt alle <alinea>/<alineaitem>-tekst samen, met newlines tussen
    alinea's zodat woorden niet aan elkaar plakken over item-grenzen."""
    lines = []
    for alinea in tekst_el.findall(NS + "alinea"):
        parts = ["".join(item.itertext()).strip() for item in alinea.findall(NS + "alineaitem")]
        line = " ".join(p for p in parts if p)
        if line:
            lines.append(line)
    return "\n".join(lines).strip()


# Nederlandse tussenvoegsels die de TK-bron soms achteraan `achternaam`
# plakt voor sorteerdoeleinden (bv. "Plas van der" i.p.v. "Van der Plas").
# Langste eerst zodat "van der"/"van den" vóór het losse "van" matcht.
# "el" (Arabisch lidwoord, bv. "El Abassi") blijft altijd met hoofdletter,
# in tegenstelling tot Nederlandse tussenvoegsels die verkleinen achter een
# voornaam.
_TUSSENVOEGSELS = ["van der", "van den", "van de", "van 't", "de", "den", "der", "het", "ten", "ter", "van"]
_ALTIJD_HOOFDLETTER = {"el"}


def _reorder_achternaam(achternaam, has_voornaam):
    """Verplaatst een tussenvoegsel dat de bron achteraan `achternaam` zet
    (sorteervolgorde) weer naar voren. Namen die de bron al correct levert
    (bv. "El Abassi") blijven ongewijzigd, omdat hun voorvoegsel niet in
    _TUSSENVOEGSELS staat. Tussenvoegsel is kleine letter als er een
    voornaam voorafgaat ("Caroline van der Plas"), anders met hoofdletter
    ("Van der Plas") -- standaard Nederlandse spellingregel."""
    lower = achternaam.lower()
    for tv in [*_TUSSENVOEGSELS, *_ALTIJD_HOOFDLETTER]:
        suffix = " " + tv
        if lower.endswith(suffix):
            stem = achternaam[: -len(suffix)].strip()
            particle = tv.capitalize() if (tv in _ALTIJD_HOOFDLETTER or not has_voornaam) else tv
            return f"{particle} {stem}"
    return achternaam


def _speaker_name(spreker_el):
    achternaam = spreker_el.findtext(NS + "achternaam")
    voornaam = spreker_el.findtext(NS + "voornaam")
    voornaam = voornaam.strip() if voornaam and voornaam.strip() else None
    if achternaam and achternaam.strip():
        naam = _reorder_achternaam(achternaam.strip(), has_voornaam=voornaam is not None)
        return f"{voornaam} {naam}" if voornaam else naam
    weergavenaam = spreker_el.findtext(NS + "weergavenaam")
    return weergavenaam.strip() if weergavenaam and weergavenaam.strip() else "Onbekend"


def _speaker_party(spreker_el):
    fractie = spreker_el.findtext(NS + "fractie")
    return fractie.strip() if fractie and fractie.strip() else None


def find_matching_activiteiten(root, topic_keyword):
    keyword = topic_keyword.lower()
    matches = []
    for activiteit in root.iter(NS + "activiteit"):
        onderwerp = activiteit.findtext(NS + "onderwerp") or ""
        titel = activiteit.findtext(NS + "titel") or ""
        if keyword in onderwerp.lower() or keyword in titel.lower():
            matches.append(activiteit)
    return matches


def find_speaking_turns(activiteit):
    """Elk element met zowel een directe <spreker> als <tekst> is één
    sprekerbeurt (dekt <woordvoerder> en <interrumpant> generiek)."""
    turns = []
    for el in activiteit.iter():
        spreker = el.find(NS + "spreker")
        tekst = el.find(NS + "tekst")
        if spreker is not None and tekst is not None:
            turns.append((el, spreker, tekst))
    return turns


def build_parent_map(root):
    """xml.etree geeft geen ouder-toegang -- nodig om vanaf een sprekerbeurt
    omhoog te zoeken naar de omsluitende <activiteitdeel> (zie is_voorzitter_turn)."""
    return {child: parent for parent in root.iter() for child in parent}


def is_voorzitter_turn(turn_el, parent_map):
    """Een sprekerbeurt is een voorzitter-beurt als de dichtstbijzijnde
    omsluitende <activiteitdeel> een <titel> heeft die "voorzitter" bevat
    (bv. "Spreekbeurt - De voorzitter"). De <spreker> zelf draagt geen rol-
    markering -- <functie> blijft "lid Tweede Kamer", ook tijdens het
    voorzitten -- dus dit is de enige betrouwbare marker in de brondata."""
    el = turn_el
    while el in parent_map:
        el = parent_map[el]
        if _local(el.tag) == "activiteitdeel":
            titel = el.findtext(NS + "titel") or ""
            return "voorzitter" in titel.lower()
    return False


def get_or_create_topic(conn, topic_keyword):
    row = conn.execute("SELECT id FROM topics WHERE slug = ?", (topic_keyword,)).fetchone()
    if row:
        return row["id"]
    cur = conn.execute(
        "INSERT INTO topics (slug, name, description) VALUES (?, ?, ?)",
        (topic_keyword, topic_keyword, None),
    )
    return cur.lastrowid


def get_or_create_source(conn):
    row = conn.execute(
        "SELECT id FROM sources WHERE type = 'tweede_kamer' AND name = ?",
        ("Tweede Kamer Open Data",),
    ).fetchone()
    if row:
        return row["id"]
    cur = conn.execute(
        "INSERT INTO sources (type, name, url, retrieved_at) VALUES (?, ?, ?, datetime('now'))",
        ("tweede_kamer", "Tweede Kamer Open Data", "https://opendata.tweedekamer.nl"),
    )
    return cur.lastrowid


def get_or_create_actor(conn, name, party):
    row = conn.execute(
        "SELECT id FROM actors WHERE name = ? AND (party = ? OR (party IS NULL AND ? IS NULL))",
        (name, party, party),
    ).fetchone()
    if row:
        return row["id"]
    cur = conn.execute(
        "INSERT INTO actors (name, type, party) VALUES (?, 'person', ?)",
        (name, party),
    )
    return cur.lastrowid


def document_exists(conn, source_id, external_id):
    row = conn.execute(
        "SELECT id FROM documents WHERE source_id = ? AND external_id = ?",
        (source_id, external_id),
    ).fetchone()
    return row is not None


def ingest_file(conn, xml_path, meta_path, topic_keyword):
    metadata = json.loads(meta_path.read_text())
    tree = ET.parse(xml_path)
    root = tree.getroot()
    parent_map = build_parent_map(root)

    topic_id = get_or_create_topic(conn, topic_keyword)
    source_id = get_or_create_source(conn)

    inserted = 0
    for activiteit in find_matching_activiteiten(root, topic_keyword):
        activiteit_titel = activiteit.findtext(NS + "titel") or metadata.get("activiteit_onderwerp")
        activiteit_soort = activiteit.attrib.get("soort")
        activiteit_aanvangstijd = activiteit.findtext(NS + "aanvangstijd") or metadata.get("activiteit_datum")
        activiteit_eindtijd = activiteit.findtext(NS + "eindtijd")
        for turn_el, spreker_el, tekst_el in find_speaking_turns(activiteit):
            content = _text_of(tekst_el)
            if not content:
                continue

            external_id = turn_el.attrib.get("objectid")
            if external_id and document_exists(conn, source_id, external_id):
                continue

            name = _speaker_name(spreker_el)
            party = _speaker_party(spreker_el)
            actor_id = get_or_create_actor(conn, name, party)

            published_at = turn_el.findtext(NS + "markeertijdbegin") or metadata.get("activiteit_datum")
            voorzitter_turn = is_voorzitter_turn(turn_el, parent_map)

            conn.execute(
                """
                INSERT INTO documents
                    (source_id, topic_id, actor_id, external_id, title, content, published_at, raw_ref, url, activiteit_soort, activiteit_aanvangstijd, activiteit_eindtijd, tweedekamer_activiteit_url, is_voorzitter_turn)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id,
                    topic_id,
                    actor_id,
                    external_id,
                    activiteit_titel,
                    content,
                    published_at,
                    str(xml_path.relative_to(RAW_DIR)),
                    metadata.get("source_resource_url"),
                    activiteit_soort,
                    activiteit_aanvangstijd,
                    activiteit_eindtijd,
                    metadata.get("tweedekamer_activiteit_url"),
                    int(voorzitter_turn),
                ),
            )
            inserted += 1

    conn.commit()
    return inserted


def ingest(topic_keyword, raw_dir=RAW_DIR):
    db_path = db.DEFAULT_DB_PATH
    if not db_path.exists():
        db.init_db(db_path)

    conn = db.connect(db_path)
    try:
        total = 0
        xml_files = sorted(raw_dir.glob("*.xml"))
        for xml_path in xml_files:
            meta_path = xml_path.with_suffix(".json")
            if not meta_path.exists():
                print(f"  overslaan (geen metadata): {xml_path.name}")
                continue
            count = ingest_file(conn, xml_path, meta_path, topic_keyword)
            print(f"  {xml_path.name}: {count} sprekerbeurten geïmporteerd")
            total += count
        print(f"Klaar: {total} documenten geïmporteerd voor topic '{topic_keyword}'.")
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True, help="Zelfde topic-keyword als gebruikt bij fetch_tk/scrapy, bv. stikstof")
    args = parser.parse_args()
    ingest(args.topic)
