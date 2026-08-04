"""
Herhaalbaarheidsmeting Stage 1: draait al geëxtraheerde documenten nóg een keer
door hetzelfde model en vergelijkt de uitkomst met wat er in de database staat.

Waarom: docs/batch-experiment.md vond 14 van de 20 documenten anders tussen twee
runs, maar kon niet vaststellen of dat door het bundelen van documenten kwam of
door gewone run-to-run-variatie van het model -- er was geen herhaalmeting met
identieke opzet. Dit script levert dat ontbrekende cijfer: zelfde prompt, zelfde
model, één document per call, alleen een andere run.

Schrijft niets naar de database (puur leesactie), zodat de bestaande extractie
onaangetast blijft.

Gebruik:
    PYTHONPATH=. uv run python scripts/agy_repeat_extraction.py --topic asiel --limit 20
"""

import argparse
import collections
import logging

from pipeline.db import db
from pipeline.extract_arguments import _build_prompt, _extract_json, _validate_argument
from scripts.agy_run_extraction_batch import run_agy

logger = logging.getLogger(__name__)


def fetch_documents_with_arguments(conn, topic_slug, limit):
    """Documenten die al minstens één argument opleverden -- alleen daar zegt
    een herhaling iets over de stabiliteit van stance/typologie."""
    return conn.execute(
        """SELECT d.id, d.content, a.name AS actor_name, a.party AS actor_party
           FROM documents d
           JOIN actors a ON a.id = d.actor_id
           JOIN topics t ON t.id = d.topic_id
           WHERE t.slug = ?
             AND EXISTS (SELECT 1 FROM arguments ar WHERE ar.document_id = d.id)
           ORDER BY d.id
           LIMIT ?""",
        (topic_slug, limit),
    ).fetchall()


def stored_arguments(conn, document_id):
    rows = conn.execute(
        "SELECT stance, typology, quote_text FROM arguments WHERE document_id = ? ORDER BY id",
        (document_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def compare(eerder, opnieuw):
    """Drie niveaus: zelfde aantal argumenten, zelfde stance-verdeling, zelfde
    citaten. Stance is het zwaarst -- daar hangt de hele PRO/CONTRA-as op."""
    aantal_gelijk = len(eerder) == len(opnieuw)
    stance_gelijk = collections.Counter(a["stance"] for a in eerder) == collections.Counter(
        a["stance"] for a in opnieuw
    )
    citaten_gelijk = {a["quote_text"] for a in eerder} == {a["quote_text"] for a in opnieuw}
    return aantal_gelijk, stance_gelijk, citaten_gelijk


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", default="asiel")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--model", default="gemini-3.6-flash-low")
    args = parser.parse_args()

    conn = db.connect()
    topic = conn.execute(
        "SELECT id, name, description FROM topics WHERE slug = ?", (args.topic,)
    ).fetchone()
    documents = fetch_documents_with_arguments(conn, args.topic, args.limit)
    logger.info("Model: %s | %d documenten met bestaande argumenten", args.model, len(documents))

    n_aantal = n_stance = n_citaten = n_fouten = 0
    for doc in documents:
        prompt = _build_prompt(
            topic["name"], topic["description"], doc["actor_name"], doc["actor_party"], doc["content"]
        )
        try:
            stdout, stderr = run_agy(prompt, args.model)
            if not stdout:
                raise ValueError(f"leeg antwoord (stderr: {stderr[:200]})")
            parsed = _extract_json(stdout)
        except Exception as exc:
            logger.error("[doc %5d] FOUT: %s", doc["id"], exc)
            n_fouten += 1
            continue

        opnieuw = []
        for arg in parsed.get("arguments", []):
            try:
                _validate_argument(arg)
            except ValueError:
                continue
            opnieuw.append({"stance": arg["stance"], "typology": arg["typology"], "quote_text": arg["quote_text"]})

        eerder = stored_arguments(conn, doc["id"])
        aantal_gelijk, stance_gelijk, citaten_gelijk = compare(eerder, opnieuw)
        n_aantal += aantal_gelijk
        n_stance += stance_gelijk
        n_citaten += citaten_gelijk
        logger.info(
            "[doc %5d] eerder %d arg (%s) | opnieuw %d arg (%s) | aantal=%s stance=%s citaten=%s",
            doc["id"], len(eerder), ",".join(a["stance"] for a in eerder),
            len(opnieuw), ",".join(a["stance"] for a in opnieuw),
            aantal_gelijk, stance_gelijk, citaten_gelijk,
        )

    conn.close()
    n = len(documents) - n_fouten
    if n:
        logger.info("Herhaalbaarheid over %d documenten (%d fout(en)):", n, n_fouten)
        logger.info("  zelfde aantal argumenten: %d/%d", n_aantal, n)
        logger.info("  zelfde stance-verdeling:  %d/%d", n_stance, n)
        logger.info("  identieke citaten:        %d/%d", n_citaten, n)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
