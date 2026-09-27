"""
Plaatst een documentdatum in een kamerperiode en een regeringsperiode
(config/politieke-periodes.toml), zodat de frontend daarop kan filteren zonder
zelf datumrekenwerk te doen.

Bewust hard falend: een datum die buiten elke periode valt is een gat in de
toml, en een argument dat stilzwijgend in "geen periode" belandt zou uit elke
gefilterde weergave verdwijnen zonder dat iemand het merkt.
"""

import logging
import tomllib
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

PERIODES_PATH = Path(__file__).parent.parent / "config" / "politieke-periodes.toml"

# Ver in de toekomst i.p.v. None, zodat lopende periodes in dezelfde
# vergelijking meekunnen als afgesloten periodes.
_OPEN_EIND = date.max


class Periode:
    def __init__(self, entry, soort):
        self.naam = entry["naam"]
        self.soort = soort
        self.start = date.fromisoformat(entry["start"])
        self.eind = date.fromisoformat(entry["eind"]) if entry.get("eind") else _OPEN_EIND
        if self.eind < self.start:
            raise ValueError(f"{soort} '{self.naam}': eind ({self.eind}) ligt voor start ({self.start})")

    def bevat(self, dag: date) -> bool:
        return self.start <= dag <= self.eind

    def __repr__(self):
        return f"Periode({self.soort}, {self.naam!r}, {self.start}..{self.eind})"


def _laad_reeks(data, sleutel, soort):
    periodes = [Periode(entry, soort) for entry in data[sleutel]]
    periodes.sort(key=lambda p: p.start)
    for vorige, volgende in zip(periodes, periodes[1:]):
        if vorige.eind >= volgende.start:
            raise ValueError(f"{soort}: '{vorige.naam}' en '{volgende.naam}' overlappen")
    return periodes


def laad_periodes(path=PERIODES_PATH):
    """(kamerperiodes, regeringsperiodes, drempel); de reeksen op startdatum
    gesorteerd, de drempel als ISO-datum."""
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    kamerperiodes = _laad_reeks(data, "kamerperiodes", "kamerperiode")
    return (
        kamerperiodes,
        _laad_reeks(data, "regeringsperiodes", "regeringsperiode"),
        verwerkingsdrempel(data, kamerperiodes),
    )


def zoek(periodes, dag: date, bron=PERIODES_PATH) -> str:
    for periode in periodes:
        if periode.bevat(dag):
            return periode.naam
    soort = periodes[0].soort if periodes else "periode"
    raise ValueError(
        f"{dag} valt buiten elke {soort} in {Path(bron).name} -- vul de ontbrekende periode aan"
    )


def verwerkingsdrempel(data, kamerperiodes) -> str:
    """ISO-datum uit [verwerking].vanaf: alles daarvoor blijft in de database
    staan maar valt buiten de queries die werk ophalen en de export voeden.

    Expliciet in de toml en niet afgeleid als "de op een na laatste
    kamerperiode": die zou meeschuiven zodra er een kamerperiode bijkomt, en
    dan verdwijnen alle al geanalyseerde argumenten van de dan voorlaatste
    Kamer in één klap van de site. Opschuiven hoort een besluit te zijn.

    Wel getoetst aan de kamerperiodes, zodat een typefout of een datum midden
    in een periode meteen opvalt.
    """
    vanaf = data["verwerking"]["vanaf"]
    starts = {p.start.isoformat(): p.naam for p in kamerperiodes}
    if vanaf not in starts:
        raise ValueError(
            f"[verwerking].vanaf = {vanaf!r} is geen startdatum van een kamerperiode "
            f"(bekend: {', '.join(sorted(starts))})"
        )
    return vanaf


class PeriodeIndex:
    """Resolvert publicatiedatums naar periodenamen. Eén keer opbouwen en
    hergebruiken; het inlezen van de toml hoeft niet per argument."""

    def __init__(self, path=PERIODES_PATH):
        self.bron = path
        self.kamerperiodes, self.regeringsperiodes, self.drempel = laad_periodes(path)

    def voor(self, published_at):
        """published_at is naive ISO-tijd uit documents.published_at."""
        if not published_at:
            return {"kamer": None, "regering": None}
        dag = date.fromisoformat(published_at[:10])
        return {
            "kamer": zoek(self.kamerperiodes, dag, self.bron),
            "regering": zoek(self.regeringsperiodes, dag, self.bron),
        }
