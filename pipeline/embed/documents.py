"""
Documenten ophalen uit de database en embedden met bge-m3, met een
incrementele cache op schijf (data/embeddings/). Dit is de eerste stage van
de plenaire-kaart-pijplijn: embedden -> UMAP -> clusteren -> labelen ->
exporteren. Alleen deze eerste stage staat hier; de rest blijft in
scripts/experiment_umap_documents.py (dat fetch_and_embed() hieruit aanroept
in plaats van deze logica zelf te herhalen).

Bron van de dataset: `documents.content` (ruwe sprekerbeurttekst), zowel de 4
gecureerde topics (topic_id IS NOT NULL) als de topic-onafhankelijke bredere
plenaire/commissie-crawl (topic_id IS NULL, zie
`uv run python -m pipeline.ingest.ingest_tk --plenair-dir <naam>`).

Los te draaien om alvast te embedden (bv. na een nieuwe crawl, vóór UMAP/
clustering-parameters getuned zijn):

    uv run python -m pipeline.embed.documents \\
        --start 2000-01-01 --end 2026-09-09 --label full \\
        --full-range-topics stikstof,abortus,asiel,energietransitie
"""

import argparse
import logging
import re
import time

import numpy as np

from pipeline.db import db
from pipeline.embed.lmstudio import detect_base_url, embed_texts
from pipeline.paths import REPO_ROOT

logger = logging.getLogger(__name__)

CACHE_DIR = REPO_ROOT / "data" / "embeddings"
MODEL = "text-embedding-bge-m3"

# Procedureel, geen inhoudelijk debat -- puntenwolk-ruis, geen onderwerp om
# op te clusteren. Filter hier (niet bij het ingesten) zodat dit zonder
# her-crawl bij te stellen is. Procedurevergadering: agenda/correspondentie-
# afhandeling van een commissie, geen debat. Rondetafelgesprek: externe
# deskundigen aan het woord, geen Kamerdebat tussen fracties.
NOISE_ACTIVITEIT_SOORTEN = (
    "Stemmingen", "Regeling van werkzaamheden", "Opening", "Mededelingen", "Beëdiging",
    "Procedurevergadering", "Rondetafelgesprek",
)

# VLOS-transcripttekst begint bij een sprekerbeurt vaak met de sprekernaam
# letterlijk in de tekst zelf ("De heer Flach (SGP): ...", "Minister Heerma:
# ...", "Kamerlid Kostić (PvdD): ...", "De voorzitter: ..."), niet iets dat
# onze pipeline toevoegt -- confirmed via steekproef op documents.content.
# Zonder dit eraf te halen krijgt het embeddingmodel/de TF-IDF-clustering de
# sprekersnaam als tekstueel signaal mee, en clustert de kaart dan deels op
# wie iets zei i.p.v. alleen waar het over ging (issue #156, live bevestigd).
#
# Eerst geprobeerd als vaste lijst honorifics ("De heer"/"Mevrouw"/"De
# voorzitter") -- bleek onvolledig: "Minister <achternaam>:" en "Kamerlid
# <achternaam>:" (tientallen ministers, en niet-"heer/mevrouw"-vormen) gingen
# er zo doorheen, inclusief de naam. Robuuster: we hebben de echte naam van
# de spreker al (actors.name, via _speaker_name() bij het ingesten) -- strip
# dus op basis van of die naam (achternaam, laatste woord) daadwerkelijk vóór
# de eerste dubbele punt staat, i.p.v. te gokken welke aanspreekvormen er
# allemaal bestaan. "De voorzitter:" blijft een aparte, vaste uitzondering:
# bij het voorzitten noemt de transcript de naam niet, alleen de rol.
VOORZITTER_PREFIX_RE = re.compile(r"^De voorzitter:\s*")
MAX_PREFIX_LEN = 60


def strip_speaker_prefix(content, actor_name):
    m = VOORZITTER_PREFIX_RE.match(content)
    if m:
        return content[m.end():]
    colon_pos = content.find(":")
    if colon_pos == -1 or colon_pos > MAX_PREFIX_LEN:
        return content
    surname = actor_name.rsplit(" ", 1)[-1] if actor_name else None
    if surname and surname in content[:colon_pos]:
        return content[colon_pos + 1:].lstrip()
    return content


def fetch_documents(conn, start_date, end_date, min_content_len, full_range_topic_slugs=()):
    """full_range_topic_slugs: topics die ongeacht start_date/end_date altijd
    volledig meegenomen worden. Nodig voor piekgedreven topics zoals abortus
    (debatten in korte, verspreide pieken i.p.v. doorlopend zoals asiel/
    energietransitie/stikstof) -- een enkele recente datumrange laat die
    pieken bijna volledig buiten de kaart vallen (issue #186, punt 3)."""
    date_or_full_range = "d.published_at >= ? AND d.published_at < ?"
    params = [start_date, end_date]
    if full_range_topic_slugs:
        date_or_full_range = "({}) OR t.slug IN ({})".format(
            date_or_full_range, ",".join("?" * len(full_range_topic_slugs))
        )
        params.extend(full_range_topic_slugs)
    rows = conn.execute(
        """
        SELECT d.id, d.content, d.published_at, d.activiteit_soort, d.title AS debate_title,
               ac.name AS actor_name, ac.party, t.slug AS topic_slug
        FROM documents d
        JOIN actors ac ON ac.id = d.actor_id
        LEFT JOIN topics t ON t.id = d.topic_id
        WHERE ({})
          AND length(d.content) >= ?
          AND (d.activiteit_soort IS NULL OR d.activiteit_soort NOT IN ({}))
          AND d.is_voorzitter_turn = 0
        ORDER BY d.id
        """.format(date_or_full_range, ",".join("?" * len(NOISE_ACTIVITEIT_SOORTEN))),
        (*params, min_content_len, *NOISE_ACTIVITEIT_SOORTEN),
    ).fetchall()
    return rows


def fetch_and_embed(start_date, end_date, min_content_len, full_range_topic_slugs, label, base_url=None, refresh=False):
    """Haalt documenten op, filtert/stript sprekersvoorvoegsels, en embedt
    incrementeel (alleen wat nog niet in de cache staat, zie de toelichting
    bij cached_id_to_vec hieronder). Geeft (rows, texts, vectors, embed_elapsed)
    terug, uitgelijnd op index -- vectors[i] hoort bij rows[i]/texts[i]."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{MODEL}_plenair-{label}.npz"

    conn = db.connect()
    rows = fetch_documents(conn, start_date, end_date, min_content_len, full_range_topic_slugs)
    conn.close()
    if not rows:
        raise SystemExit(f"geen documenten gevonden tussen {start_date} en {end_date}")

    # min_content_len in de SQL (fetch_documents) filtert op de RUWE content
    # -- inclusief het sprekersprefix dat hier pas wordt gestript. Een beurt
    # als "Kamerlid Kostić (PvdD): Dank u wel." haalt zo ruim de 30 tekens,
    # maar houdt na het strippen alleen "Dank u wel." over: te weinig om
    # zinnig op te embedden, en precies dit soort bijna-lege beurten bleek
    # als uitschieter te embedden (issue #156, live bevestigd). Daarom hier
    # nogmaals filteren, nu op de gestripte tekst.
    stripped = [strip_speaker_prefix(r["content"], r["actor_name"]) for r in rows]
    keep = [i for i, t in enumerate(stripped) if len(t) >= min_content_len]
    dropped = len(rows) - len(keep)
    if dropped:
        logger.info(
            "%d van %d beurten alsnog te kort na het strippen van het sprekersprefix (< %d tekens), overgeslagen",
            dropped, len(rows), min_content_len,
        )
    rows = [rows[i] for i in keep]
    texts = [stripped[i] for i in keep]

    current_ids = [r["id"] for r in rows]
    text_by_id = dict(zip(current_ids, texts))

    # Incrementeel embedden: id -> vector, gevuld vanuit de cache en aangevuld
    # met alleen wat ontbreekt (i.p.v. bij ÉÉN ontbrekend id de HELE cache
    # negeren en alles opnieuw embedden -- bij een groeiende dataset, zoals
    # na een nieuwe crawl, was dat een volledige her-embed van tienduizenden
    # al gecachete documenten voor niets).
    cached_id_to_vec = {}
    if not refresh and cache_path.exists():
        data = np.load(cache_path, allow_pickle=True)
        cached_id_to_vec = dict(zip((int(i) for i in data["ids"]), data["vectors"]))

    missing_ids = [doc_id for doc_id in current_ids if doc_id not in cached_id_to_vec]

    embed_elapsed = None
    if missing_ids:
        resolved_base_url = detect_base_url(base_url)
        t0 = time.monotonic()
        missing_vectors = embed_texts(resolved_base_url, [text_by_id[doc_id] for doc_id in missing_ids], MODEL)
        embed_elapsed = time.monotonic() - t0
        logger.info(
            "%d/%d document-embeddings hergebruikt uit cache, %d nieuw opgehaald in %.1fs (%s, model=%s)",
            len(current_ids) - len(missing_ids), len(current_ids), len(missing_ids), embed_elapsed, resolved_base_url, MODEL,
        )
        cached_id_to_vec.update(zip(missing_ids, missing_vectors))
        # Unie opslaan (niet overschrijven met alleen current_ids): zo blijft
        # elke eerder geembedde id herbruikbaar voor een latere, andere
        # --start/--end-query i.p.v. dat de cache bij elke smallere query
        # weer slinkt tot precies die query's ids.
        all_ids = list(cached_id_to_vec.keys())
        np.savez(cache_path, vectors=np.array([cached_id_to_vec[i] for i in all_ids]), ids=all_ids)
    else:
        logger.info("embeddings-cache geladen: %s (alle %d gevraagde vectoren al aanwezig)", cache_path, len(current_ids))

    vectors = np.array([cached_id_to_vec[doc_id] for doc_id in current_ids])
    return rows, texts, vectors, embed_elapsed


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", required=True, help="published_at ondergrens, ISO-datum (inclusief)")
    parser.add_argument("--end", required=True, help="published_at bovengrens, ISO-datum (exclusief)")
    parser.add_argument("--label", required=True, help="korte periode-naam voor de cachebestandsnaam, bv. 2025-heden")
    parser.add_argument(
        "--full-range-topics", default="",
        help="komma-gescheiden topic-slugs die altijd volledig meegenomen worden, ongeacht "
        "--start/--end (bv. abortus: piekgedreven debatten i.p.v. doorlopend, zie issue #186 punt 3)",
    )
    parser.add_argument("--min-content-len", type=int, default=30)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--refresh", action="store_true", help="cache negeren en alles opnieuw embedden")
    args = parser.parse_args()

    full_range_topic_slugs = [s.strip() for s in args.full_range_topics.split(",") if s.strip()]
    rows, texts, vectors, embed_elapsed = fetch_and_embed(
        args.start, args.end, args.min_content_len, full_range_topic_slugs, args.label,
        base_url=args.base_url, refresh=args.refresh,
    )
    logger.info("%d documenten geëmbed/gecached (dim=%d)", len(rows), vectors.shape[1])
    if embed_elapsed is not None:
        logger.info("embedding-tijd deze run: %.1fs", embed_elapsed)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
