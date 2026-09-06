"""
Hoeveel pipeline-werk scheelt het om ons te beperken tot de huidige en vorige
kamerperiode? Telt documenten en argumenten per kamerperiode, uitgesplitst
naar wat al gedaan is en wat er nog openstaat (Stage 1 extractie, Stage 1b
tagging, Stage 2 redactie-check).

Puur tellen, geen schrijfacties.

    uv run python scripts/periode_workload.py
"""

import logging
from collections import defaultdict

from pipeline.db import db
from pipeline.periodes import PeriodeIndex

logger = logging.getLogger(__name__)


def main():
    conn = db.connect()
    index = PeriodeIndex()

    # Documenten met hun verwerkingsstatus. published_at kan leeg zijn; die
    # krijgen een eigen bucket i.p.v. stilzwijgend bij een periode te landen.
    # "wachtrij" spiegelt fetch_pending_documents in extract_arguments.py:
    # voorzitter-turns worden nooit geëxtraheerd en horen dus niet in een
    # schatting van resterend werk.
    documents = conn.execute(
        """SELECT d.id, d.published_at,
                  d.extraction_attempted_at IS NOT NULL AS extracted,
                  d.extraction_attempted_at IS NULL AND d.is_voorzitter_turn = 0 AS pending
           FROM documents d"""
    ).fetchall()

    arguments = conn.execute(
        """SELECT d.published_at, ar.tagged_at IS NOT NULL AS tagged
           FROM arguments ar JOIN documents d ON d.id = ar.document_id"""
    ).fetchall()

    stats = defaultdict(lambda: defaultdict(int))

    for row in documents:
        periode = _periode(index, row["published_at"])
        stats[periode]["documenten"] += 1
        stats[periode]["geëxtraheerd"] += bool(row["extracted"])
        stats[periode]["wachtrij"] += bool(row["pending"])

    for row in arguments:
        periode = _periode(index, row["published_at"])
        stats[periode]["argumenten"] += 1
        stats[periode]["getagd"] += bool(row["tagged"])

    kamerperiodes = [p.naam for p in index.kamerperiodes]
    huidig_en_vorig = set(kamerperiodes[-2:])

    volgorde = [naam for naam in kamerperiodes if naam in stats]
    volgorde += sorted(naam for naam in stats if naam not in kamerperiodes)

    header = f"{'kamerperiode':<26}{'docs':>7}{'geëxtr.':>9}{'wachtrij':>10}{'argum.':>8}{'getagd':>8}{'te taggen':>11}"
    print(header)
    print("-" * len(header))
    for naam in volgorde:
        s = stats[naam]
        markering = "  " if naam in huidig_en_vorig else " *"
        print(
            f"{naam:<24}{markering}{s['documenten']:>7}{s['geëxtraheerd']:>9}"
            f"{s['wachtrij']:>10}{s['argumenten']:>8}"
            f"{s['getagd']:>8}{s['argumenten'] - s['getagd']:>11}"
        )

    print("\n* = valt buiten de huidige en vorige kamerperiode\n")

    behouden = {naam: s for naam, s in stats.items() if naam in huidig_en_vorig}
    vervalt = {naam: s for naam, s in stats.items() if naam not in huidig_en_vorig}

    def totaal(groep, sleutel):
        return sum(s[sleutel] for s in groep.values())

    for label, sleutel in [
        ("documenten", "documenten"),
        ("nog te extraheren documenten", None),
        ("argumenten", "argumenten"),
        ("nog te taggen argumenten", None),
    ]:
        if sleutel:
            hou, weg = totaal(behouden, sleutel), totaal(vervalt, sleutel)
        elif "extraheren" in label:
            hou, weg = totaal(behouden, "wachtrij"), totaal(vervalt, "wachtrij")
        else:
            hou = totaal(behouden, "argumenten") - totaal(behouden, "getagd")
            weg = totaal(vervalt, "argumenten") - totaal(vervalt, "getagd")
        som = hou + weg
        aandeel = f"{100 * weg / som:.1f}%" if som else "n.v.t."
        print(f"{label:<32} behouden {hou:>6}   vervalt {weg:>6}   ({aandeel} minder)")


def _periode(index, published_at):
    if not published_at:
        return "(geen publicatiedatum)"
    return index.voor(published_at)["kamer"]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
