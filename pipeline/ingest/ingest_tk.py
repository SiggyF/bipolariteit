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
import logging
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from pipeline.db import db

logger = logging.getLogger(__name__)
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


# <fractie> in de VLOS-data is niet altijd consistent: soms de afkorting,
# soms de voluit geschreven naam (bv. "Nieuw Sociaal Contract" i.p.v. "NSC",
# "FvD" i.p.v. "FVD"), afhankelijk van het debat/de periode. Zonder
# normalisatie krijgt dezelfde spreker twee actor-rijen, en splitst dat
# argumenten/documenten over allebei. Zie ook PARTY_ALIASSEN in
# frontend/src/lib/parties.ts (dezelfde normalisatie, voor party-waarden die
# al vóór deze fix zijn geïmporteerd).
PARTIJ_ALIASSEN = {
    "Nieuw Sociaal Contract": "NSC",
    "FvD": "FVD",
}


def _speaker_party(spreker_el):
    fractie = spreker_el.findtext(NS + "fractie")
    fractie = fractie.strip() if fractie and fractie.strip() else None
    return PARTIJ_ALIASSEN.get(fractie, fractie)


def _speaker_role_title(spreker_el):
    """Bewindspersonen (Minister/Staatssecretaris) hebben geen <fractie> --
    ze spreken op dat moment niet namens een Kamerfractie. <spreker soort="...">
    onderscheidt ze van "Tweede Kamerlid"; <functie> geeft de exacte
    portefeuille (bv. "minister van Landbouw, Visserij, Voedselzekerheid en
    Natuur"). NULL voor gewone Kamerleden -- daar zegt de fractie al genoeg."""
    if spreker_el.attrib.get("soort") == "Tweede Kamerlid":
        return None
    functie = spreker_el.findtext(NS + "functie")
    return functie.strip() if functie and functie.strip() else None


_ODATA_BASE = "https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0"
_ODATA_HEADERS = {"User-Agent": "bipolariteit-tk-crawler/0.1 (contact: f.baart@gmail.com; onderzoeksproject)"}
_bewindspersoon_party_cache = {}

# Zeldzame, bewuste uitzondering op de automatische lookup hieronder: Jaimi
# van Essen heeft geen Kamerlidschap (dus geen OData-Persoon-record), en zijn
# Wikidata-positie-item mist zelf weer een label/jurisdictie (dus valt ook
# buiten data/bewindspersonen.toml). Partij staat als losse tekst
# ("Partij: D66") in rijksoverheid.nl/regering/bewindspersonen/jaimi-van-essen,
# geverifieerd op 2026-07-26.
#
# Teun Struycken stond hier eerder ook in: "Teun Struycken is door NSC
# benaderd om in het kabinet-Schoof staatssecretaris Rechtsbescherming te
# worden, maar hij is geen lid van de partij en is dat ook niet van plan te
# worden" (NOS-liveblog, 2024-07-13) -- inmiddels via Wikidata zelf opgelost
# (P102 -> Q327591 "onafhankelijk politicus", 2026-08-01), dus die
# uitzondering is niet meer nodig; data/bewindspersonen.toml levert hem nu
# automatisch als "Onafhankelijk".
BEWINDSPERSOON_PARTY_OVERRIDES = {
    "Jaimi van Essen": "D66",
}

_BEWINDSPERSONEN_TOML = Path(__file__).parent.parent.parent / "data" / "bewindspersonen.toml"
_bewindspersonen_wikidata = None


def _laad_bewindspersonen_wikidata():
    global _bewindspersonen_wikidata
    if _bewindspersonen_wikidata is None:
        import tomllib

        data = tomllib.loads(_BEWINDSPERSONEN_TOML.read_text(encoding="utf-8"))
        _bewindspersonen_wikidata = {p["naam"]: p["partij"] for p in data["bewindspersonen"]}
    return _bewindspersonen_wikidata


def lookup_bewindspersoon_party(name):
    """Bewindspersonen (Minister/Staatssecretaris) hebben geen <fractie> in de
    VLOS-data -- ze spreken op dat moment niet namens een Kamerfractie, maar
    zijn meestal wel via een eerder/huidig Kamerlidmaatschap aan een partij te
    koppelen. Drie lagen, in volgorde: (1) een kleine handmatige
    uitzonderingenlijst voor de zeldzame gevallen die de andere twee lagen niet
    kunnen oplossen, (2) de laatst bekende Kamerzetel via de TK OData-API
    (Persoon -> FractieZetelPersoon -> FractieZetel -> Fractie.Afkorting), (3)
    data/bewindspersonen.toml, gebouwd uit Wikidata voor bewindspersonen van de
    laatste 2 kamerperiodes zonder eigen Kamerzetel (zie
    scripts/fetch_bewindspersonen_wikidata.py). Geeft None terug (echte
    "Onbekend") als geen van de lagen een match heeft -- nooit gokken."""
    if name in BEWINDSPERSOON_PARTY_OVERRIDES:
        return BEWINDSPERSOON_PARTY_OVERRIDES[name]
    if name in _bewindspersoon_party_cache:
        return _bewindspersoon_party_cache[name]

    party = None
    parts = name.split()
    achternaam = parts[-1]
    voornaam = parts[0] if len(parts) > 1 else None
    try:
        # contains i.p.v. eq: Persoon.Achternaam bevat soms het volledige
        # tussenvoegsel+achternaam (bv. "van der Wal"), dan matcht een eq op
        # alleen het laatste woord ("Wal") niet.
        filter_expr = f"contains(Achternaam,'{achternaam}')"
        expand = "FractieZetelPersoon($expand=FractieZetel($expand=Fractie))"
        url = (
            f"{_ODATA_BASE}/Persoon?$filter={urllib.parse.quote(filter_expr)}"
            f"&$expand={urllib.parse.quote(expand)}&$select=Id,Roepnaam,Voornamen,Achternaam"
        )
        req = urllib.request.Request(url, headers=_ODATA_HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
        personen = body.get("value", [])
        if voornaam and len(personen) > 1:
            personen = [
                p for p in personen
                if voornaam.lower() in (p.get("Roepnaam") or "").lower()
                or voornaam.lower() in (p.get("Voornamen") or "").lower()
            ] or personen

        zetels = []
        for persoon in personen:
            for zp in persoon.get("FractieZetelPersoon", []):
                fractie = (zp.get("FractieZetel") or {}).get("Fractie") or {}
                afkorting = fractie.get("Afkorting")
                van = zp.get("Van")
                if afkorting and van:
                    zetels.append((van, afkorting))
        if zetels:
            zetels.sort()
            party = zetels[-1][1]
    except Exception as e:
        logger.warning("kon partij niet opzoeken voor bewindspersoon %r: %s", name, e)

    if not party:
        party = _laad_bewindspersonen_wikidata().get(name)

    _bewindspersoon_party_cache[name] = party
    return party


# Ruim criterium: een debat kan het topic bespreken zonder het keyword in zijn
# eigen onderwerp/titel te dragen (bv. het keyword "abortus" komt 23x voor in
# sprekerbeurten van het debat "Vrouwengezondheid", een eufemisme/koepelterm).
# find_matching_activiteiten matcht daarom op alle tekst binnen de activiteit,
# niet alleen op onderwerp/titel. Dat ruime net vangt ook debatten die het
# keyword incidenteel noemen op een heel andere as (bv. "abortuszorg" als
# onderdeel van ontwikkelingshulp aan slachtoffers van seksueel geweld in
# oorlogsgebieden, geen Nederlands abortusdebat) -- TOPIC_EXCLUDE_ACTIVITEITEN
# is de stapsgewijze exclusielijst daarvoor, per topic bijgehouden zodra zo'n
# fout-positief gevonden wordt.
TOPIC_EXCLUDE_ACTIVITEITEN = {
    "abortus": [
        # Commissiedebat "Bestrijding conflict-gerelateerd seksueel geweld"
        # (28 mei 2026), onderdeel van dossier Buitenlandse Handel en
        # Ontwikkelingssamenwerking: gaat over Nederlandse ontwikkelingshulp
        # (SheDecides/Ipas/UNFPA) aan slachtoffers van seksueel geweld in
        # oorlogsgebieden, niet over het Nederlandse abortusdebat. Een
        # Kamerlid markeert dit debat zelf expliciet als "geen abortusdebat".
        "Bestrijding conflict-gerelateerd seksueel geweld",
    ],
    "asiel": [
        # Arbeidsmigratie is beleidsmatig verwant (zelfde ministerie) maar ligt
        # op een andere as: arbeidsmarktkrapte, uitbuiting en huisvesting van
        # arbeidsmigranten, niet toelating versus bescherming van asielzoekers.
        # PRO/CONTRA zou hier iets anders betekenen dan in de rest van het topic.
        # Let op: exacte titelvergelijking, dus een toekomstig
        # "Tweeminutendebat Arbeidsmigratie (CD 12/3)" valt hier niet onder en
        # moet er los bij.
        "Arbeidsmigratie",
        "Wet toelating terbeschikkingstelling van arbeidskrachten",
    ],
}

# Tweede exclusiegrond, naast de letterlijke titels hierboven: een woord in de
# onderwerp/titel dat het debat als geheel diskwalificeert. Voor asiel is dat
# de ICT-betekenis van "migratie" (datamigratie, cloudmigratie) -- die komt
# binnen doordat het topic het trefwoord "migratie" meeneemt, maar gaat over
# systemen in plaats van mensen. Als woord, niet als substring: "ict" zit ook
# in "conflict" en "restrictief".
TOPIC_EXCLUDE_TITELWOORDEN = {
    "asiel": ["ict", "cloud", "cloudbedrijf", "cloudmigraties", "digid"],
}


def find_matching_activiteiten(root, topic_keyword, also_keywords=()):
    """Retourneert (activiteit, title_match)-paren. title_match=True betekent
    dat het keyword in de onderwerp/titel van de activiteit zelf staat -- een
    overduidelijk op-topic debat, dus alle sprekerbeurten worden meegenomen.
    title_match=False is het ruimere net: het keyword komt ergens in de
    activiteit voor, maar de activiteit zelf gaat over iets anders (bv. het
    eufemisme "Vrouwengezondheid", of een incidentele motie over abortuscijfers
    in een medische-ethiekdebat) -- ingest_file neemt dan alleen de losse
    sprekerbeurten mee die zelf het keyword bevatten, niet het hele debat.

    also_keywords verbreedt waaróp gematcht wordt (bv. also_keywords=["migratie"]
    bij topic "asiel"): een debat dat alleen het tweede woord noemt telt dan mee.
    Net als --also-dir expliciet per geval, nooit impliciet -- een topic mag niet
    stilzwijgend het net van een ander topic overnemen."""
    keywords = [topic_keyword.lower(), *(k.lower() for k in also_keywords)]
    excludes = {x.lower() for x in TOPIC_EXCLUDE_ACTIVITEITEN.get(topic_keyword, [])}
    exclude_woorden = TOPIC_EXCLUDE_TITELWOORDEN.get(topic_keyword, [])
    exclude_patroon = re.compile(r"\b(" + "|".join(exclude_woorden) + r")\b") if exclude_woorden else None
    matches = []
    for activiteit in root.iter(NS + "activiteit"):
        onderwerp = activiteit.findtext(NS + "onderwerp") or ""
        titel = activiteit.findtext(NS + "titel") or ""
        if onderwerp.lower() in excludes or titel.lower() in excludes:
            continue
        kop = f"{onderwerp} {titel}".lower()
        if exclude_patroon is not None and exclude_patroon.search(kop):
            continue
        title_match = any(k in kop for k in keywords)
        if title_match:
            matches.append((activiteit, True))
            continue
        activiteit_text = " ".join(activiteit.itertext()).lower()
        if any(k in activiteit_text for k in keywords):
            matches.append((activiteit, False))
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


def is_voorzitter_turn(turn_el, parent_map, content=None):
    """Een sprekerbeurt is een voorzitter-beurt als de dichtstbijzijnde
    omsluitende <activiteitdeel> een <titel> heeft die "voorzitter" bevat
    (bv. "Spreekbeurt - De voorzitter"). De <spreker> zelf draagt geen rol-
    markering -- <functie> blijft "lid Tweede Kamer", ook tijdens het
    voorzitten.

    Die <titel> ontbreekt echter vaak bij commissiedebatten, waardoor
    procedurele voorzitter-beurten alsnog als inhoudelijke beurt binnenkomen
    (bij topic asiel 1902 van de openstaande documenten). De verslaglegging
    zet de rol in zulke gevallen wél in de tekst zelf: "De voorzitter: ...".
    Die tweede marker vangt de rest af."""
    if content is not None and content.lstrip().lower().startswith("de voorzitter:"):
        return True
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


def ingest_file(conn, xml_path, meta_path, topic_keyword, also_keywords=()):
    metadata = json.loads(meta_path.read_text())
    tree = ET.parse(xml_path)
    root = tree.getroot()
    parent_map = build_parent_map(root)

    topic_id = get_or_create_topic(conn, topic_keyword)
    source_id = get_or_create_source(conn)

    keywords = [topic_keyword.lower(), *(k.lower() for k in also_keywords)]
    inserted = 0
    for activiteit, title_match in find_matching_activiteiten(root, topic_keyword, also_keywords):
        activiteit_titel = activiteit.findtext(NS + "titel") or metadata.get("activiteit_onderwerp")
        activiteit_soort = activiteit.attrib.get("soort")
        activiteit_aanvangstijd = activiteit.findtext(NS + "aanvangstijd") or metadata.get("activiteit_datum")
        activiteit_eindtijd = activiteit.findtext(NS + "eindtijd")
        for turn_el, spreker_el, tekst_el in find_speaking_turns(activiteit):
            content = _text_of(tekst_el)
            if not content:
                continue
            # Bij een ruim-net-treffer (title_match=False) alleen de sprekerbeurten
            # meenemen die zelf het keyword bevatten -- anders zou één incidentele
            # vermelding (bv. een motie over abortuscijfers in een stikstofdebat)
            # het hele, verder onrelateerde debat meeslepen.
            if not title_match and not any(k in content.lower() for k in keywords):
                continue

            external_id = turn_el.attrib.get("objectid")
            if external_id and document_exists(conn, source_id, external_id):
                continue

            name = _speaker_name(spreker_el)
            party = _speaker_party(spreker_el)
            speaker_role_title = _speaker_role_title(spreker_el)
            if party is None and speaker_role_title is not None:
                party = lookup_bewindspersoon_party(name)
            actor_id = get_or_create_actor(conn, name, party)

            published_at = turn_el.findtext(NS + "markeertijdbegin") or metadata.get("activiteit_datum")
            voorzitter_turn = is_voorzitter_turn(turn_el, parent_map, content)

            conn.execute(
                """
                INSERT INTO documents
                    (source_id, topic_id, actor_id, external_id, title, content, published_at, raw_ref, url, activiteit_soort, activiteit_aanvangstijd, activiteit_eindtijd, tweedekamer_activiteit_url, is_voorzitter_turn, speaker_role_title)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    speaker_role_title,
                ),
            )
            inserted += 1

    conn.commit()
    return inserted


def ingest(topic_keyword, raw_dir=RAW_DIR, also_dirs=(), also_keywords=()):
    """Scant standaard alleen raw_dir/<topic_keyword>/ -- de map waar de
    crawler onder dat exacte keyword naartoe schreef. also_dirs is de
    expliciete, per-geval-gekozen uitbreiding voor het ruime-net-criterium
    (bv. also_dirs=["vrouwengezondheid"] om een eufemisme-gecrawlde map ook
    op dit topic te doorzoeken) -- nooit een impliciete scan van de hele
    raw-boom, dat zou topics ongemerkt laten lekken (zie find_matching_activiteiten
    voor de sprekerbeurt-niveau-filtering die dat soort kruisbestuiving afvangt).

    also_dirs verbreedt wélke mappen gescand worden, also_keywords waaróp
    gematcht wordt. Voor een topic met twee gangbare benamingen (bv. "asiel" en
    "migratie") heb je beide nodig: zonder also_keywords levert een puur
    migratiedebat uit de migratie-map nul sprekerbeurten op."""
    db_path = db.DEFAULT_DB_PATH
    if not db_path.exists():
        db.init_db(db_path)

    conn = db.connect(db_path)
    try:
        total = 0
        dirs = [raw_dir / topic_keyword] + [raw_dir / d for d in also_dirs]
        xml_files = sorted(f for d in dirs if d.exists() for f in d.glob("*.xml"))
        for xml_path in xml_files:
            meta_path = xml_path.with_suffix(".json")
            if not meta_path.exists():
                print(f"  overslaan (geen metadata): {xml_path.name}")
                continue
            count = ingest_file(conn, xml_path, meta_path, topic_keyword, also_keywords)
            print(f"  {xml_path.parent.name}/{xml_path.name}: {count} sprekerbeurten geïmporteerd")
            total += count
        print(f"Klaar: {total} documenten geïmporteerd voor topic '{topic_keyword}'.")
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True, help="Zelfde topic-keyword als gebruikt bij fetch_tk/scrapy, bv. stikstof")
    parser.add_argument(
        "--also-dir",
        action="append",
        default=[],
        help="Extra raw_dir/<naam>/-map ook doorzoeken op dit topic (ruime-net-criterium, bv. --also-dir vrouwengezondheid). Herhaalbaar.",
    )
    parser.add_argument(
        "--also-keyword",
        action="append",
        default=[],
        help="Extra trefwoord waarop activiteiten en sprekerbeurten matchen (bv. --also-keyword migratie bij --topic asiel). Herhaalbaar.",
    )
    args = parser.parse_args()
    ingest(args.topic, also_dirs=args.also_dir, also_keywords=args.also_keyword)
