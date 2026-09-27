"""
Documenten ophalen uit de database en embedden met bge-m3, met een
incrementele cache op schijf (data/embeddings/). Dit is de eerste stage van
de plenaire-kaart-pijplijn: embedden -> UMAP -> clusteren -> labelen ->
exporteren. Alleen deze eerste stage staat hier; de rest blijft in
pipeline/plenary_map/cluster.py (dat fetch_and_embed() hieruit aanroept
in plaats van deze logica zelf te herhalen).

Bron van de dataset: `documents.content` (ruwe sprekerbeurttekst), topic-
onafhankelijk -- geen join op topics/topic_id. Als een punt later een
topic-koppeling nodig heeft, is dat een aparte, latere join op de output
hiervan, geen onderdeel van deze workflow.

Los te draaien om alvast te embedden (bv. na een nieuwe crawl, vóór UMAP/
clustering-parameters getuned zijn):

    uv run python -m pipeline.embed.documents \\
        --start 2000-01-01 --end 2026-09-09 --label full
"""

import argparse
import logging
import re
import time
import uuid

import numpy as np
import pyarrow as pa
import pyarrow.dataset as pa_dataset
import pyarrow.parquet as pq

from pipeline.db import db
from pipeline.embed.lmstudio import detect_base_url, embed_texts
from pipeline.paths import REPO_ROOT

logger = logging.getLogger(__name__)

CACHE_DIR = REPO_ROOT / "data" / "embeddings"
MODEL = "text-embedding-bge-m3"


def load_embedding_cache(cache_dir):
    """Leest alle parquet-delen in cache_dir als één dataset in. Rechtstreeks
    via pyarrow (niet pandas): een vector als Python-list-van-floats kost al
    gauw 6-10x zoveel geheugen als de ruwe float32-data (elke float wordt een
    los Python-object) -- op de volle ~768k-documenten-schaal (~3 GB ruwe
    data) was dat genoeg om de embed-run OOM te laten crashen (exit 137)
    ná afloop van het eigenlijke (dure) embedden.

    Batch-voor-batch in een voorgealloceerde matrix lezen i.p.v. eerst de
    hele dataset naar één pyarrow Table (`.to_table()`) -- dat laatste bleek
    zelf óók een probleem: `Dataset.to_batches()`/`.to_table()` prefetcht
    standaard meerdere fragmenten/batches vooruit (readahead), wat op deze
    schaal het piekgeheugen ~3x zo hoog maakte als de data zelf (~9,3 GB
    voor ~3,1 GB ruwe vectoren, live gemeten) -- nog los van het feit dat
    `.to_table()` daarna nog een `combine_chunks()`-kopie nodig heeft.
    `batch_readahead=0`/`fragment_readahead=0`/`use_threads=False` op de
    Scanner (i.p.v. Dataset direct) schakelt die prefetch uit; gemeten
    piekgeheugen daalde daarmee naar de daadwerkelijke datagrootte."""
    if not cache_dir.exists() or not any(cache_dir.glob("*.parquet")):
        return {}
    dataset = pa_dataset.dataset(cache_dir, format="parquet")
    n_rows = dataset.count_rows()
    scanner = dataset.scanner(columns=["id", "vector"], use_threads=False, batch_readahead=0, fragment_readahead=0)

    ids = np.empty(n_rows, dtype=np.int64)
    matrix = None
    offset = 0
    for batch in scanner.to_batches():
        n = batch.num_rows
        if n == 0:
            continue
        if matrix is None:
            dim = batch.column("vector").type.list_size
            matrix = np.empty((n_rows, dim), dtype=np.float32)
        ids[offset : offset + n] = batch.column("id").to_numpy()
        matrix[offset : offset + n] = batch.column("vector").values.to_numpy(zero_copy_only=False).reshape(n, -1)
        offset += n

    return {int(doc_id): matrix[i] for i, doc_id in enumerate(ids)}


def _append_batch(cache_dir, ids_batch, vectors_batch):
    """Schrijft één batch als los parquet-bestand (append i.p.v. de hele
    cache herschrijven), zodat elke batch meteen op schijf staat en een
    onderbreking halverwege niet eerder opgehaalde batches kost. Vector-kolom
    expliciet als fixed_size_list<float32> (i.p.v. via pandas een generieke
    list<double>) -- compacter op schijf én, belangrijker, de vorm die
    load_embedding_cache() zonder Python-object-omweg kan terugcasten naar
    een aaneengesloten numpy-array."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    vectors_arr = np.asarray(vectors_batch, dtype=np.float32)
    flat = pa.array(vectors_arr.reshape(-1), type=pa.float32())
    vector_col = pa.FixedSizeListArray.from_arrays(flat, vectors_arr.shape[1])
    table = pa.table({"id": pa.array(list(ids_batch), type=pa.int64()), "vector": vector_col})
    pq.write_table(table, cache_dir / f"part-{uuid.uuid4().hex}.parquet")


# Alleen echte Kamerdebatten tussen fracties. Whitelist i.p.v. blocklist
# (op verzoek): laat naast de overduidelijk procedurele soorten (Stemmingen,
# Regeling van werkzaamheden, Opening, Mededelingen, Beëdiging,
# Procedurevergadering) ook Rondetafelgesprek/Hoorzitting/Technische
# briefing buiten beschouwing -- externe deskundigen aan het woord, geen
# Kamerleden onderling. Laat daarmee ook Notaoverleg (52.868 rijen,
# inhoudelijk vergelijkbaar met Wetgevingsoverleg) en de kleinere
# restcategorieën (Interpellatiedebat, Gesprek, Afscheid, ...) buiten
# beschouwing -- filter hier (niet bij het ingesten) zodat dit zonder
# her-crawl bij te stellen is. Rijen zonder activiteit_soort (NULL) blijven
# wel meegenomen (onbekend, niet expliciet uitgesloten).
WANTED_ACTIVITEIT_SOORTEN = (
    "Plenair debat", "Commissiedebat", "Algemeen overleg", "Wetgevingsoverleg", "Vragenuur",
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


def fetch_documents(conn, start_date, end_date, min_content_len):
    """Topic-onafhankelijk: geen join op topics/topic_id, geen topic-gebaseerde
    datumrange-uitzondering. Topic is geen eigenschap van de embed-/cluster-
    workflow -- als een punt later een topic-koppeling nodig heeft (bv. voor
    kruisverwijzing naar de argumentenboom), hoort dat een aparte, latere
    join te zijn op de output van deze functie, niet iets dat hier al wordt
    meegehaald of dat de selectie van documenten beinvloedt."""
    rows = conn.execute(
        """
        SELECT d.id, d.content, d.published_at, d.activiteit_soort, d.title AS debate_title,
               ac.name AS actor_name, ac.party
        FROM documents d
        JOIN actors ac ON ac.id = d.actor_id
        WHERE d.published_at >= ? AND d.published_at < ?
          AND length(d.content) >= ?
          AND (d.activiteit_soort IS NULL OR d.activiteit_soort IN ({}))
          AND d.is_voorzitter_turn = 0
        ORDER BY d.id
        """.format(",".join("?" * len(WANTED_ACTIVITEIT_SOORTEN))),
        (start_date, end_date, min_content_len, *WANTED_ACTIVITEIT_SOORTEN),
    ).fetchall()
    return rows


def fetch_and_embed(start_date, end_date, min_content_len, label, base_url=None, refresh=False):
    """Haalt documenten op, filtert/stript sprekersvoorvoegsels, en embedt
    incrementeel (alleen wat nog niet in de cache staat, zie de toelichting
    bij cached_id_to_vec hieronder). Geeft (rows, texts, vectors, embed_elapsed)
    terug, uitgelijnd op index -- vectors[i] hoort bij rows[i]/texts[i]."""
    cache_dir = CACHE_DIR / f"{MODEL}_plenair-{label}"
    if refresh and cache_dir.exists():
        for part in cache_dir.glob("*.parquet"):
            part.unlink()

    conn = db.connect()
    rows = fetch_documents(conn, start_date, end_date, min_content_len)
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
    cached_id_to_vec = load_embedding_cache(cache_dir)

    missing_ids = [doc_id for doc_id in current_ids if doc_id not in cached_id_to_vec]

    embed_elapsed = None
    if missing_ids:
        resolved_base_url = detect_base_url(base_url)

        def on_batch(start_index, batch_vectors):
            batch_ids = missing_ids[start_index : start_index + len(batch_vectors)]
            cached_id_to_vec.update(zip(batch_ids, batch_vectors))
            _append_batch(cache_dir, batch_ids, batch_vectors)

        t0 = time.monotonic()
        embed_texts(resolved_base_url, [text_by_id[doc_id] for doc_id in missing_ids], MODEL, on_batch=on_batch)
        embed_elapsed = time.monotonic() - t0
        logger.info(
            "%d/%d document-embeddings hergebruikt uit cache, %d nieuw opgehaald in %.1fs (%s, model=%s)",
            len(current_ids) - len(missing_ids), len(current_ids), len(missing_ids), embed_elapsed, resolved_base_url, MODEL,
        )
    else:
        logger.info("embeddings-cache geladen: %s (alle %d gevraagde vectoren al aanwezig)", cache_dir, len(current_ids))

    vectors = np.array([cached_id_to_vec[doc_id] for doc_id in current_ids])
    return rows, texts, vectors, embed_elapsed


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", required=True, help="published_at ondergrens, ISO-datum (inclusief)")
    parser.add_argument("--end", required=True, help="published_at bovengrens, ISO-datum (exclusief)")
    parser.add_argument("--label", required=True, help="korte periode-naam voor de cachebestandsnaam, bv. 2025-heden")
    parser.add_argument("--min-content-len", type=int, default=30)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--refresh", action="store_true", help="cache negeren en alles opnieuw embedden")
    args = parser.parse_args()

    rows, texts, vectors, embed_elapsed = fetch_and_embed(
        args.start, args.end, args.min_content_len, args.label,
        base_url=args.base_url, refresh=args.refresh,
    )
    logger.info("%d documenten geëmbed/gecached (dim=%d)", len(rows), vectors.shape[1])
    if embed_elapsed is not None:
        logger.info("embedding-tijd deze run: %.1fs", embed_elapsed)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
