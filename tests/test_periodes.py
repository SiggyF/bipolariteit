import pytest

from pipeline.periodes import PERIODES_PATH, PeriodeIndex, laad_periodes, zoek


@pytest.fixture(scope="module")
def index():
    return PeriodeIndex()


def test_toml_parst_en_bevat_beide_reeksen():
    kamerperiodes, regeringsperiodes = laad_periodes()
    assert kamerperiodes, f"geen kamerperiodes in {PERIODES_PATH.name}"
    assert regeringsperiodes, f"geen regeringsperiodes in {PERIODES_PATH.name}"


def test_reeksen_sluiten_aan_zonder_gat():
    """Een gat zou argumenten stilzwijgend buiten elke periode laten vallen."""
    for periodes in laad_periodes():
        for vorige, volgende in zip(periodes, periodes[1:]):
            assert (volgende.start - vorige.eind).days == 1, (
                f"gat of overlap tussen '{vorige.naam}' en '{volgende.naam}'"
            )


@pytest.mark.parametrize(
    "published_at,kamer,regering",
    [
        # De vier maanden die daadwerkelijk in het stikstof-corpus voorkomen.
        ("2023-02-23T14:00:00", "Tweede Kamer 2021-2023", "Kabinet-Rutte IV"),
        ("2025-02-12T10:30:00", "Tweede Kamer 2023-2025", "Kabinet-Schoof"),
        ("2025-05-20T13:00:00", "Tweede Kamer 2023-2025", "Kabinet-Schoof"),
        ("2026-07-01T13:43:39", "Tweede Kamer 2025-heden", "Kabinet-Jetten"),
    ],
)
def test_bekende_datums_landen_in_de_juiste_periode(index, published_at, kamer, regering):
    assert index.voor(published_at) == {"kamer": kamer, "regering": regering}


def test_grenzen_zijn_inclusief(index):
    """De dag van beediging hoort al bij het nieuwe kabinet, de dag ervoor nog
    bij het oude -- anders valt precies de wisseldag ertussenuit."""
    assert index.voor("2026-02-23T09:00:00")["regering"] == "Kabinet-Jetten"
    assert index.voor("2026-02-22T23:00:00")["regering"] == "Kabinet-Schoof"


def test_datum_buiten_elke_periode_faalt_hard(index):
    with pytest.raises(ValueError, match="valt buiten elke"):
        zoek(index.regeringsperiodes, __import__("datetime").date(1900, 1, 1))


def test_zonder_publicatiedatum_geen_periode(index):
    assert index.voor(None) == {"kamer": None, "regering": None}
