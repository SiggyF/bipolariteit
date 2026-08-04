"""
Tests voor de VLOS-XML segmentatielogica in pipeline/ingest/ingest_tk.py:
- naam-reconstructie (de TK-bron plakt tussenvoegsels soms achteraan
  `achternaam` voor sorteerdoeleinden, bv. "Plas van der" i.p.v. "Van der
  Plas" -- zie docs/handoff.md)
- topic-match filter op activiteit-niveau
- generieke sprekerbeurt-detectie (woordvoerder + interrumpant)
"""

import xml.etree.ElementTree as ET

from pipeline.ingest.ingest_tk import (
    NS,
    _speaker_name,
    build_parent_map,
    find_matching_activiteiten,
    find_speaking_turns,
    is_voorzitter_turn,
)

AANVANGSTIJD = "2026-07-01T10:00:00"
EINDTIJD = "2026-07-01T12:00:00"


def _spreker(achternaam=None, voornaam=None, weergavenaam=None):
    xml = f"""<spreker xmlns="http://www.tweedekamer.nl/ggm/vergaderverslag/v1.0">
        {f'<achternaam>{achternaam}</achternaam>' if achternaam else ''}
        {f'<voornaam>{voornaam}</voornaam>' if voornaam else ''}
        {f'<weergavenaam>{weergavenaam}</weergavenaam>' if weergavenaam else ''}
    </spreker>"""
    return ET.fromstring(xml)


def test_speaker_name_reorders_trailing_tussenvoegsel():
    assert _speaker_name(_spreker(achternaam="Plas van der", voornaam="Caroline")) == "Caroline van der Plas"
    assert _speaker_name(_spreker(achternaam="Berg van den", voornaam="Joba")) == "Joba van den Berg"
    assert _speaker_name(_spreker(achternaam="Groot de", voornaam="Tjeerd")) == "Tjeerd de Groot"


def test_speaker_name_capitalizes_particle_without_voornaam():
    assert _speaker_name(_spreker(achternaam="Plas van der")) == "Van der Plas"


def test_speaker_name_leaves_already_correct_order_untouched():
    # de bron levert dit voorvoegsel soms al vooraan (arabisch lidwoord "El")
    assert _speaker_name(_spreker(achternaam="El Abassi", voornaam="Ismail")) == "Ismail El Abassi"


def test_speaker_name_reorders_arabic_prefix_when_trailing():
    # maar soms plakt de bron "El" ook achteraan, net als een tussenvoegsel
    assert _speaker_name(_spreker(achternaam="Boujdaini El", voornaam="Sarah")) == "Sarah El Boujdaini"


def test_speaker_name_falls_back_to_weergavenaam_without_achternaam():
    assert _speaker_name(_spreker(weergavenaam="Onbekende Spreker")) == "Onbekende Spreker"


VLOS_ROOT = f"""<vlosCoreDocument xmlns="http://www.tweedekamer.nl/ggm/vergaderverslag/v1.0">
  <vergadering>
    <activiteit objectid="act-1">
      <onderwerp>Debat over stikstof en natuur</onderwerp>
      <aanvangstijd>{AANVANGSTIJD}</aanvangstijd>
      <eindtijd>{EINDTIJD}</eindtijd>
      <activiteitdeel>
        <activiteititem>
          <woordvoerder objectid="turn-1">
            <spreker><achternaam>Paulusma</achternaam><voornaam>Wieke</voornaam></spreker>
            <tekst><alinea><alineaitem>Eerste opmerking.</alineaitem></alinea></tekst>
            <interrumpant objectid="turn-2">
              <spreker><achternaam>Plas van der</achternaam><voornaam>Caroline</voornaam></spreker>
              <tekst><alinea><alineaitem>Een interruptie.</alineaitem></alinea></tekst>
            </interrumpant>
          </woordvoerder>
        </activiteititem>
      </activiteitdeel>
    </activiteit>
    <activiteit objectid="act-2">
      <onderwerp>Opening</onderwerp>
      <activiteitdeel>
        <activiteititem>
          <woordvoerder objectid="turn-3">
            <spreker><achternaam>Bosma</achternaam><voornaam>Martin</voornaam></spreker>
            <tekst><alinea><alineaitem>Niet over het onderwerp.</alineaitem></alinea></tekst>
          </woordvoerder>
        </activiteititem>
      </activiteitdeel>
    </activiteit>
  </vergadering>
</vlosCoreDocument>"""


def test_find_matching_activiteiten_filters_on_topic_keyword():
    root = ET.fromstring(VLOS_ROOT)
    matches = find_matching_activiteiten(root, "stikstof")
    assert len(matches) == 1
    activiteit, title_match = matches[0]
    assert activiteit.attrib["objectid"] == "act-1"
    assert title_match is True


TWEE_BENAMINGEN_ROOT = """<vlosCoreDocument xmlns="http://www.tweedekamer.nl/ggm/vergaderverslag/v1.0">
  <vergadering>
    <activiteit objectid="act-asiel">
      <onderwerp>Debat over de asielketen</onderwerp>
    </activiteit>
    <activiteit objectid="act-migratie">
      <onderwerp>Debat over arbeidsmigratie</onderwerp>
    </activiteit>
  </vergadering>
</vlosCoreDocument>"""


def test_also_keywords_widens_the_match_to_a_second_name_for_the_topic():
    # Een topic met twee gangbare benamingen: zonder also_keywords blijft het
    # migratiedebat buiten beeld, ook al staat het in dezelfde raw-map.
    root = ET.fromstring(TWEE_BENAMINGEN_ROOT)

    zonder = find_matching_activiteiten(root, "asiel")
    assert [a.attrib["objectid"] for a, _ in zonder] == ["act-asiel"]

    met = find_matching_activiteiten(root, "asiel", also_keywords=["migratie"])
    assert [a.attrib["objectid"] for a, _ in met] == ["act-asiel", "act-migratie"]
    assert all(title_match for _, title_match in met)


ICT_MIGRATIE_ROOT = """<vlosCoreDocument xmlns="http://www.tweedekamer.nl/ggm/vergaderverslag/v1.0">
  <vergadering>
    <activiteit objectid="act-ict">
      <onderwerp>Migraties van overheids-ICT naar het buitenland</onderwerp>
    </activiteit>
    <activiteit objectid="act-conflict">
      <onderwerp>Conflict en restrictief migratiebeleid</onderwerp>
    </activiteit>
  </vergadering>
</vlosCoreDocument>"""


def test_exclude_titelwoorden_skips_ict_migration_but_not_words_containing_ict():
    # "ict" als woord sluit het datamigratie-debat uit; als substring zou het
    # ook "conflict" en "restrictief" raken -- precies de debatten die we willen.
    root = ET.fromstring(ICT_MIGRATIE_ROOT)
    matches = find_matching_activiteiten(root, "asiel", also_keywords=["migratie"])
    assert [a.attrib["objectid"] for a, _ in matches] == ["act-conflict"]


def test_voorzitter_turn_recognized_from_the_text_when_the_titel_is_missing():
    # Bij commissiedebatten ontbreekt de <activiteitdeel>-titel vaak; de
    # verslaglegging zet de rol dan alleen in de tekst zelf.
    root = ET.fromstring(VLOS_ROOT)
    activiteit, _title_match = find_matching_activiteiten(root, "stikstof")[0]
    turn_el, _spreker, _tekst = find_speaking_turns(activiteit)[0]
    parent_map = build_parent_map(root)

    assert is_voorzitter_turn(turn_el, parent_map) is False
    assert is_voorzitter_turn(turn_el, parent_map, "De voorzitter: Kort antwoord.") is True
    assert is_voorzitter_turn(turn_el, parent_map, "Mevrouw Podt (D66): Voorzitter, ik ...") is False


def test_find_speaking_turns_includes_woordvoerder_and_interrumpant():
    root = ET.fromstring(VLOS_ROOT)
    activiteit, _title_match = find_matching_activiteiten(root, "stikstof")[0]
    turns = find_speaking_turns(activiteit)
    turn_ids = {el.attrib["objectid"] for el, _, _ in turns}
    assert turn_ids == {"turn-1", "turn-2"}


def test_activiteit_aanvangstijd_and_eindtijd_readable_on_debate_level():
    # debat-brede start-/eindtijd (voor de video_url/Debat Direct-matchheuristiek,
    # zie docs/handoff.md), niet te verwarren met een sprekerbeurt's eigen
    # markeertijdbegin -- die zit op woordvoerder-niveau, niet op activiteit-niveau.
    root = ET.fromstring(VLOS_ROOT)
    activiteit, _title_match = find_matching_activiteiten(root, "stikstof")[0]
    assert activiteit.findtext(NS + "aanvangstijd") == AANVANGSTIJD
    assert activiteit.findtext(NS + "eindtijd") == EINDTIJD
