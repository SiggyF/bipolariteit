"""
Plaatst een documentdatum in een kamerperiode en een regeringsperiode
(data/politieke-periodes.toml), zodat de frontend daarop kan filteren zonder
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

PERIODES_PATH = Path(__file__).parent.parent / "data" / "politieke-periodes.toml"

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
    """(kamerperiodes, regeringsperiodes), beide op startdatum gesorteerd."""
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return (
        _laad_reeks(data, "kamerperiodes", "kamerperiode"),
        _laad_reeks(data, "regeringsperiodes", "regeringsperiode"),
    )


def zoek(periodes, dag: date) -> str:
    for periode in periodes:
        if periode.bevat(dag):
            return periode.naam
    soort = periodes[0].soort if periodes else "periode"
    raise ValueError(
        f"{dag} valt buiten elke {soort} in {PERIODES_PATH.name} -- vul de ontbrekende periode aan"
    )


class PeriodeIndex:
    """Resolvert publicatiedatums naar periodenamen. Eén keer opbouwen en
    hergebruiken; het inlezen van de toml hoeft niet per argument."""

    def __init__(self, path=PERIODES_PATH):
        self.kamerperiodes, self.regeringsperiodes = laad_periodes(path)

    def voor(self, published_at):
        """published_at is naive ISO-tijd uit documents.published_at."""
        if not published_at:
            return {"kamer": None, "regering": None}
        dag = date.fromisoformat(published_at[:10])
        return {"kamer": zoek(self.kamerperiodes, dag), "regering": zoek(self.regeringsperiodes, dag)}
