"""
Schrijft een gouden fixture voor de TypeScript-correspondentieanalyse:
de contingentietabel plus de coordinaten en inertie die `prince` erop geeft.
De TS-implementatie in frontend/src/lib/correspondence.ts wordt hiertegen
getoetst, zodat de port aantoonbaar hetzelfde rekent als de Python-versie die
hij vervangt.

Puur lezen -- geen schrijfacties naar de database.

Twee dingen bewust anders dan de productiecode:

* `engine="scipy"` i.p.v. de default. Prince gebruikt normaal
  `sklearn.randomized_svd` met een seed; dat is een benadering en de tekens
  hangen aan die seed. Voor een fixture wil je exacte LAPACK.
* Daarna leggen we onze eigen tekenconventie op (zie `_canonieke_tekens`),
  identiek aan `canonicalSigns` in TypeScript. Zonder dat zou de test alleen
  op-teken-na kunnen vergelijken, en juist het teken is wat we willen borgen.

Gebruik:
    PYTHONPATH=. uv run python scripts/dump_ca_fixture.py
"""

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import prince

from pipeline.build_static_data import fetch_party_tag_counts
from pipeline.db import db
from pipeline.periodes import PeriodeIndex

logger = logging.getLogger(__name__)

UITVOER = Path(__file__).parent.parent / "frontend" / "src" / "lib" / "__fixtures__" / "ca-stikstof.json"

MIN_PARTY_TOTAL = 3
MIN_TAG_TOTAL = 2
N_COMPONENTS = 3


def _canonieke_tekens(F, G, rijlabels):
    """Orienteer elke component zo dat de rij met de grootste absolute
    coordinaat op die as positief is; bij gelijkspel de alfabetisch eerste.

    Toegepast op F en G tegelijk -- alleen de rijen spiegelen zou de
    rij-kolomrelatie breken die de biplot betekenis geeft.

    Bewust niet massagewogen: in CA geldt r'F = 0 en c'G = 0 exact, dus elke
    zwaartepunttoets degenereert naar nul.
    """
    for k in range(F.shape[1]):
        kolom = np.abs(F[:, k])
        top = np.max(kolom)
        kandidaten = [i for i in range(len(kolom)) if np.isclose(kolom[i], top)]
        i = min(kandidaten, key=lambda idx: rijlabels[idx])
        if F[i, k] < 0:
            F[:, k] *= -1
            G[:, k] *= -1
    return F, G


def main():
    conn = db.connect()
    index = PeriodeIndex()
    topic = conn.execute("SELECT id FROM topics WHERE slug = 'stikstof'").fetchone()
    if topic is None:
        raise SystemExit("topic 'stikstof' niet gevonden")

    rows = fetch_party_tag_counts(conn, topic["id"], index.drempel)
    df = pd.DataFrame([(r["party"], r["sleutel"], r["n"]) for r in rows], columns=["party", "sleutel", "n"])

    party_totals = df.groupby("party")["n"].sum()
    tag_totals = df.groupby("sleutel")["n"].sum()
    df = df[
        df["party"].isin(party_totals[party_totals >= MIN_PARTY_TOTAL].index)
        & df["sleutel"].isin(tag_totals[tag_totals >= MIN_TAG_TOTAL].index)
    ]
    table = df.pivot_table(index="party", columns="sleutel", values="n", aggfunc="sum", fill_value=0)

    ca = prince.CA(n_components=N_COMPONENTS, engine="scipy").fit(table)
    F = ca.row_coordinates(table).values.astype(float)
    G = ca.column_coordinates(table).values.astype(float)
    rijlabels = list(table.index)
    F, G = _canonieke_tekens(F, G, rijlabels)

    # Alle percentages, niet alleen de eerste drie: de test controleert dat ze
    # samen 100 zijn, wat de klassieke fout afvangt waarbij de som van de top-k
    # singuliere waarden als noemer wordt gebruikt i.p.v. de totale inertie.
    volledig = prince.CA(n_components=min(table.shape) - 1, engine="scipy").fit(table)

    UITVOER.parent.mkdir(parents=True, exist_ok=True)
    UITVOER.write_text(
        json.dumps(
            {
                "_herkomst": "scripts/dump_ca_fixture.py -- niet met de hand bewerken",
                "rowLabels": rijlabels,
                "colLabels": list(table.columns),
                "counts": table.values.astype(int).tolist(),
                "rowTotals": [int(party_totals[p]) for p in rijlabels],
                "colTotals": [int(tag_totals[t]) for t in table.columns],
                "inertiaPct": [float(v) for v in ca.percentage_of_variance_[:N_COMPONENTS]],
                "inertiaPctAll": [float(v) for v in volledig.percentage_of_variance_],
                "F": F.tolist(),
                "G": G.tolist(),
            },
            ensure_ascii=False,
            indent=1,
        )
    )
    logger.info(
        "%d partijen x %d tags, inertie %s -> %s",
        len(rijlabels), len(table.columns),
        [round(v, 1) for v in ca.percentage_of_variance_[:N_COMPONENTS]], UITVOER,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
