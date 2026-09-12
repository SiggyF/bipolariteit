"""
Vervolg op experiment_umap_arguments.py (issue #156): embedt
`documents.content` (ruwe sprekerbeurttekst) i.p.v. `arguments.quote_text`
over álle plenaire Kamerdebatten, topic-onafhankelijk -- er is bewust geen
LLM-argumentextractie gedraaid voor deze bredere dataset (te duur voor een
onderzoekje, zie pipeline.ingest.ingest_tk.ingest_plenair()). Topic is geen
eigenschap van deze workflow: geen join op topics/topic_id, geen
topic-gebaseerde filtering of labeling. Een latere topic-koppeling (bv.
kruisverwijzing naar de argumentenboom) is een aparte, latere join op de
output hiervan.

Bron van de dataset: `uv run python -m pipeline.ingest.ingest_tk
--plenair-dir <naam>` uit een `verslagen_periode`-crawl
(crawlers/tweede_kamer/tweede_kamer/spiders/verslagen_periode.py).

Puur leesactie op de database. Output: coords+labels als JSON in
data/plenary-map/, voor de losse Cosmograph-HTML-pagina
(index.html in dezelfde map) om interactief te bekijken -- zie die map's
eigen toelichting waarom hier bewust geen matplotlib-PNG (zoals
experiment_umap_arguments.py) of Plotly is gebruikt.

De volle pijplijn is embedden -> UMAP -> clusteren -> labelen -> exporteren,
verdeeld over vier los draaibare stages (elk met zijn eigen geheugen-/
kostenprofiel, zie make embed/make umap/make cluster-plenary-map/make
label-clusters):

1. Embedden (pipeline/embed/documents.py) -- incrementeel gecachet.
2. UMAP (pipeline/plenary_map/umap.py) -- zet de embeddings om in
   2D-coördinaten; dure, host-only stap qua geheugengebruik op de volle
   dataset (zie docs/handoff.md). Schrijft alleen die coördinaten weg.
3. Clusteren (dit bestand): leest de coördinaten van stap 2 (--coords-path,
   verplicht -- UMAP zelf is GEEN onderdeel van dit script), en
   `build_multilevel_clusters()`/`label_multilevel_clusters()` clusteren +
   TF-IDF-labelen ze. Geen bijzonder geheugengebruik, dus overal draaibaar
   (bv. de devcontainer).
4. LLM-naamgeving (pipeline/plenary_map/label_export.py, `make
   label-clusters`) -- werkt op de hier weggeschreven
   cluster-label-input-<label>.json, dus ook overal en in porties te
   draaien (bv. tegen een gratis remote router).

Gebruik:
    uv run python -m pipeline.plenary_map.cluster \
        --start 2025-11-12 --end 2026-08-22 --label 2025-heden \
        --coords-path data/plenary-map/coords-2025-heden.json
"""
import argparse
import json
import logging
import math
import re
from collections import Counter
from pathlib import Path

import numpy as np
import requests
from scipy.spatial import ConvexHull
from shapely.geometry import Polygon
from sklearn.cluster import DBSCAN, HDBSCAN
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

from pipeline.db import db
from pipeline.embed.documents import CACHE_DIR, MODEL, fetch_and_embed, fetch_documents, strip_speaker_prefix
from pipeline.paths import REPO_ROOT
from pipeline.plenary_map.label import compute_representative_examples
from scripts.experiment_umap_arguments import DUTCH_STOPWORDS

logger = logging.getLogger(__name__)

# nltk's Nederlandse stopwoordenlijst blijkt onvolledig -- live bevestigd:
# mist "we"/"wij" volledig, en een reeks andere hoogfrequente voornaamwoorden/
# vulwoorden. Puur functiewoorden, geen enkele onderscheidende waarde op wélk
# schaalniveau dan ook -- vandaar hier los van PARLIAMENTARY_STOPWORDS
# (hieronder), die wél schaalafhankelijk is (zie label_clusters()).
# nltk's Nederlandse stopwoordenlijst blijkt onvolledig -- live bevestigd:
# Partij-aliassen, afkortingen en informele partijbenamingen
PARTY_ALIASES_AND_ABBREVIATIONS = {
    "pvv", "vvd", "nsc", "cda", "d66", "bbb", "sp", "pvdd", "pvda", "groenlinks",
    "gl", "sgp", "fvd", "denk", "christenunie", "cu", "volt", "ja21", "50plus", "bij1",
    "forum", "democratie", "socialistische", "dieren", "fractie", "fracties",
    "fractievoorzitter", "partij", "partijen", "coalitie", "oppositie",
}

# Voornaamwoorden en telwoorden die ontbreken in standaard nltk stopwoorden
DUTCH_PRONOUNS_AND_NUMERALS = {
    "we", "wij", "ons", "onze", "jij", "je", "jou", "jouw", "jullie", "zij", "ze", "haar", "hen",
    "hun", "hem", "hij", "zich", "zichzelf", "mezelf", "mijzelf", "één", "twee", "drie", "vier",
    "vijf", "zes", "zeven", "acht", "negen", "tien", "eerste", "tweede", "derde", "vierde", "vijfde",
    "tweetal", "drietal", "viertal", "vijftal", "zestal", "zevental", "achttal", "negental", "tiental",
}

# Parlementaire instituties, rollen, vergadertermen en procedurele formules.
# Dit zijn zelfstandige naamwoorden in het Nederlands die door Alpino als
# inhoudswoord zouden worden gezien, maar in de Tweede Kamer procedurele ruis zijn.
PARLIAMENTARY_INSTITUTIONAL = {
    # Ambten, rollen en aansprekingen
    "kabinet", "kabinetten", "regering", "regeringen", "kabinetsbeleid", "kabinetsinzet",
    "regeerakkoord", "hoofdlijnenakkoord", "bewindspersoon", "bewindspersonen", "staatssecretaris",
    "staatssecretarissen", "minister", "ministers", "ministerraad", "ministerie", "ministeries",
    "ministeriële", "premier", "vicepremier", "president", "kamerlid", "kamerleden",
    "voorzitter", "voorzitters", "ondervoorzitter", "collega", "collega's", "kamer",
    "mevrouw", "mevrouwen", "meneer", "heer", "heren", "bode", "bodes", "griffier",
    "ambtenaar", "ambtenaren", "ambtenarenkamer",
    # Formaten, stukken & procedurele formules
    "motie", "moties", "amendement", "amendementen", "wetsvoorstel", "wet", "wetten", "wetgeving",
    "debat", "vergadering", "stemming", "stemmingen", "interruptie", "interrupties",
    "schorsing", "schorsen", "beantwoording", "brief", "brieven", "kamerbrief", "beleidsbrief",
    "gesprek", "gesprekken", "toezegging", "toezeggingen", "overleg", "afspraak", "afspraken",
    "stuk", "stukken", "nr", "nummer", "oordeel", "oordeel kamer", "ontraden", "ontraad",
    "ontijdig", "overbodig", "bedankt", "dank", "pardon", "sorry", "excuus", "excuses",
    "stenogram", "stenogrammen", "notulen", "kwartiertje", "ordevoorstel", "orde",
    "handelingen", "vragenuur", "interpellatie", "schriftelijke", "bevestig",
    # Tijdsaanduidingen & algemeenheden
    "jaar", "jaren", "maand", "maanden", "week", "weken", "uur", "minuut", "minuten",
    "seconde", "seconden", "periode", "termijn", "termijnen", "moment", "zomer", "reces",
    "mensen", "land", "nederland", "nederlandse", "overheid", "feit", "feiten",
}


def fetch_actor_and_party_stopwords(conn):
    """Haalt alle actor-voornamen, achternamen en partijnamen/afkortingen op uit de database
    zodat deze systematisch als stopwoord worden uitgesloten van onderwerp-labels."""
    actor_names = [r[0] for r in conn.execute("SELECT name FROM actors WHERE name IS NOT NULL").fetchall()]
    party_names = [r[0] for r in conn.execute("SELECT party FROM actors WHERE party IS NOT NULL").fetchall()]

    stopwords = set()
    for name in actor_names:
        for token in re.findall(r"\b\w+\b", name.lower()):
            if len(token) >= 2:
                stopwords.add(token)
                if token.endswith("s") and len(token) >= 4:
                    stopwords.add(token[:-1])
                if token.endswith("en") and len(token) >= 5:
                    stopwords.add(token[:-2])

    for party in party_names:
        for token in re.findall(r"\b\w+\b", party.lower()):
            if len(token) >= 2:
                stopwords.add(token)

    return stopwords

OUTPUT_DIR = REPO_ROOT / "data" / "plenary-map"
EXPORT_PATH = REPO_ROOT / "data" / "export" / "plenair-map.json"
CLUSTERS_EXPORT_PATH = REPO_ROOT / "data" / "export" / "plenair-map-clusters.json"
HIERARCHY_EXPORT_PATH = REPO_ROOT / "data" / "export" / "plenair-map-hierarchy.json"

# Concept-record van de Zenodo-archivering (docs/handoff.md, 2026-08-29-sessie):
# https://doi.org/10.5281/zenodo.22181704 -- het concept-DOI blijft stabiel over
# alle versies heen, in tegenstelling tot het per-versie-DOI (bv. .../22181705).
ZENODO_CONCEPT_RECID = "22181704"


def detect_next_dataset_version(concept_recid=ZENODO_CONCEPT_RECID, timeout=5):
    """Volgende dataset_version = 1 + aantal bestaande Zenodo-versies onder dit
    concept-record. Geen van de bestaande versies heeft zelf een "version"-
    metadataveld ingevuld (live gecontroleerd), dus aftellen via het aantal
    records is de enige beschikbare bron -- dit is dus een AANNAME (geen
    garantie dat versienummers nooit een gat hebben), niet een harde waarheid.
    Faalt de lookup (geen netwerk, Zenodo down) dan None teruggeven i.p.v.
    de hele run te laten crashen op een niet-essentieel metadataveld -- de
    Zenodo-publicatie zelf blijft toch een bewuste, handmatige stap."""
    try:
        resp = requests.get(
            "https://zenodo.org/api/records",
            params={"q": f"conceptrecid:{concept_recid}", "all_versions": "true", "size": 1},
            timeout=timeout,
        )
        resp.raise_for_status()
        total = resp.json()["hits"]["total"]
        return total + 1
    except (requests.RequestException, KeyError, ValueError) as e:
        logger.warning("kon volgende dataset-versie niet bij Zenodo opzoeken (%s) -- dataset_version blijft None", e)
        return None

def run_clustering(coords, method, eps, min_samples, min_cluster_size):
    """DBSCAN (vast eps) of HDBSCAN (past dichtheid lokaal aan, geen eps
    nodig) op de UMAP-coordinaten. HDBSCAN loste het "94% van alle punten
    in één cluster"-probleem van DBSCAN op deze grotere, sterk wisselend-
    dichte dataset op (issue #156, live bevestigd) -- en levert via
    `dbscan_clustering` een cluster-hiërarchie op meerdere schaalniveaus
    zonder dat je zelf per niveau een aparte eps hoeft te kiezen."""
    if method == "hdbscan":
        clustering = HDBSCAN(min_cluster_size=min_cluster_size).fit(coords)
    else:
        clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(coords)
    return clustering.labels_


def _condensed_tree_children_by_parent(clusterer):
    """Condensed tree (van de `hdbscan`-package, i.t.t. sklearn.cluster.HDBSCAN
    dat geen condensed_tree_ blootgeeft) als {parent_node_id: [(child, child_size), ...]}.
    child_size==1 betekent: child is een losse puntindex die als ruis uit
    parent viel; child_size>1 betekent: child is een nieuwe interne node-id
    (een echte sub-cluster-splitsing)."""
    full_tree = clusterer.condensed_tree_.to_pandas()
    children_by_parent = {}
    for parent, child, size in zip(full_tree["parent"], full_tree["child"], full_tree["child_size"]):
        children_by_parent.setdefault(int(parent), []).append((int(child), int(size)))
    root = int(full_tree["parent"].min())
    return children_by_parent, root


def format_title_from_terms(terms):
    """Formatteert een enkel leesbaar trefwoord uit de top-termen (bv. ['asiel'] -> 'Asiel')."""
    if not terms:
        return "Overig"
    for t in terms:
        toks = t.strip().split()
        if len(toks) == 1:
            return toks[0].title()
    return terms[0].split()[0].title()


def fetch_alpino_non_content_stopwords():
    """Haalt alle niet-inhoudelijke Nederlandse woordvormen (werkwoorden, bijwoorden,
    voegwoorden, voornaamwoorden, tussenwerpsels) automatisch op uit het NLTK Alpino corpus."""
    try:
        import nltk
        nltk.download("alpino", quiet=True)
        from nltk.corpus import alpino
        non_content_tags = {"verb", "adv", "det", "prep", "comp", "num", "pron", "vg", "part", "fixed", "pp"}
        return {
            word.lower() for word, tag in alpino.tagged_words()
            if tag in non_content_tags and tag not in {"noun"}
        }
    except Exception as e:
        logger.warning("Kon Alpino-corpus niet laden voor stopwoorden: %s", e)
        return set()


def compute_cluster_hull(pts: np.ndarray, percentile: float = 92.0):
    """Berekent een compacte convex hull rond een cluster punten in de 2D UMAP-ruimte.

    Filtert eerst de uiterste afstand-uitschieters t.o.v. het zwaartepunt
    om naald-vormige uitsteeksels naar losse ruispunten te voorkomen.
    Geeft (hull_vertices, centroid) terug, of (None, centroid) als er < 3 punten zijn.
    """
    if len(pts) == 0:
        return None, [0.0, 0.0]
    centroid = [round(float(pts[:, 0].mean()), 4), round(float(pts[:, 1].mean()), 4)]
    if len(pts) < 3:
        return None, centroid

    dists = np.linalg.norm(pts - np.array(centroid), axis=1)
    thresh = np.percentile(dists, percentile)
    filtered = pts[dists <= thresh]
    if len(filtered) < 3:
        filtered = pts

    try:
        hull = ConvexHull(filtered)
        vertices = [[round(float(x), 4), round(float(y), 4)] for x, y in filtered[hull.vertices]]
        return vertices, centroid
    except Exception as e:
        logger.debug("Kon convex hull niet berekenen: %s", e)
        return None, centroid


def compute_spatially_diffuse_stopwords(
    texts: list[str],
    coords: np.ndarray,
    min_doc_freq: int = 5,
    max_dispersion_ratio: float = 0.55,
) -> set[str]:
    """Berekent wiskundig diffuse stopwoorden op basis van ruimtelijke spreiding in UMAP.

    Termen die over de hele UMAP-kaart verspreid voorkomen (ratio term_std / global_std > max_dispersion_ratio)
    zijn algemene niet-onderwerp-specifieke woorden (bv. 'dit initiatief', 'kost tijd', 'plaats op')
    en worden automatisch als stopwoord gemarkeerd.
    """
    cv = CountVectorizer(min_df=min_doc_freq, binary=True, ngram_range=(1, 2), token_pattern=r"(?u)\b[^\d\W]\w+\b")
    X = cv.fit_transform(texts)
    feature_names = cv.get_feature_names_out()
    counts = np.asarray(X.sum(axis=0)).flatten()

    sum_coords = X.T.dot(coords)
    mean_coords = sum_coords / counts[:, None]

    sum_coords_sq = X.T.dot(coords ** 2)
    mean_coords_sq = sum_coords_sq / counts[:, None]

    var_x = np.maximum(0, mean_coords_sq[:, 0] - mean_coords[:, 0] ** 2)
    var_y = np.maximum(0, mean_coords_sq[:, 1] - mean_coords[:, 1] ** 2)
    term_spatial_std = np.sqrt(var_x + var_y)

    global_std = np.sqrt(np.var(coords[:, 0]) + np.var(coords[:, 1]))
    if global_std == 0:
        return set()

    dispersion_ratio = term_spatial_std / global_std
    diffuse_mask = dispersion_ratio > max_dispersion_ratio
    diffuse_terms = set(feature_names[diffuse_mask])
    logger.info(
        "Ruimtelijke dispersie-analyse: %d van de %d n-grams gemarkeerd als ruimtelijk diffuus (ratio > %.2f)",
        len(diffuse_terms), len(feature_names), max_dispersion_ratio,
    )
    return diffuse_terms


def label_hierarchical_clusters(
    texts, coords, coarse_ids, fine_ids, top_terms=6, extra_stopwords=None, max_df=0.25
):
    """Berekent hiërarchische TF-IDF-labels en convex hulls.

    - Ruimtelijke dispersiefilter: wiskundige uitsluiting van diffuse woorden over de hele kaart.
    - Grove clusters (domeinen): globale TF-IDF bepaalt overkoepelende thema-termen + buitenste convex hull.
    - Fijne clusters (sub-onderwerpen): contrastieve TF-IDF (fine_mean - coarse_mean) + binnenste convex hull.
    """
    if extra_stopwords is None:
        extra_stopwords = set()

    raw_stops = set(DUTCH_STOPWORDS) | set(extra_stopwords)
    clean_stops = set()
    for s in raw_stops:
        for tok in re.findall(r"(?u)\b[a-zA-ZÀ-ÿ]{2,}\b", s.lower()):
            clean_stops.add(tok)

    if coords is not None:
        diffuse_stops = compute_spatially_diffuse_stopwords(texts, coords, max_dispersion_ratio=0.55)
        for s in diffuse_stops:
            for tok in re.findall(r"(?u)\b[a-zA-ZÀ-ÿ]{2,}\b", s.lower()):
                clean_stops.add(tok)

    tfidf = TfidfVectorizer(
        stop_words=list(clean_stops),
        lowercase=True,
        ngram_range=(1, 2),
        min_df=3,
        max_df=max_df,
        token_pattern=r"(?u)\b[a-zA-ZÀ-ÿ]{3,}\b",
    )
    tfidf_matrix = tfidf.fit_transform(texts)
    bin_matrix = (tfidf_matrix > 0).astype(np.float32)
    global_df = np.asarray(bin_matrix.sum(axis=0)).ravel()
    terms = tfidf.get_feature_names_out()

    # Bereken globale ruimtelijke dispersie per term (lagere dispersie = hogere ruimtelijke concentratie)
    term_global_dispersion = np.ones(len(terms), dtype=np.float32)
    if coords is not None:
        counts = np.asarray(bin_matrix.sum(axis=0)).flatten()
        valid_terms = counts >= 3
        sum_coords = bin_matrix.T.dot(coords)
        mean_coords = np.zeros_like(sum_coords)
        mean_coords[valid_terms] = sum_coords[valid_terms] / counts[valid_terms, None]

        sum_coords_sq = bin_matrix.T.dot(coords ** 2)
        mean_coords_sq = np.zeros_like(sum_coords_sq)
        mean_coords_sq[valid_terms] = sum_coords_sq[valid_terms] / counts[valid_terms, None]

        var_x = np.maximum(0, mean_coords_sq[:, 0] - mean_coords[:, 0] ** 2)
        var_y = np.maximum(0, mean_coords_sq[:, 1] - mean_coords[:, 1] ** 2)
        term_spatial_std = np.sqrt(var_x + var_y)
        global_std = np.sqrt(np.var(coords[:, 0]) + np.var(coords[:, 1]))
        if global_std > 0:
            term_global_dispersion = term_spatial_std / global_std

    def rank_hull_anchored_terms(member_idx, hull, centroid, base_weights=None):
        n_members = len(member_idx)
        if n_members == 0:
            return []

        # Bepaal representatieve documenten (hoekpunten van de convex hull + dichtbij zwaartepunt)
        if coords is not None and centroid is not None:
            c_coords = coords[member_idx]
            dists = np.linalg.norm(c_coords - centroid, axis=1)
            center_doc_indices = member_idx[np.argsort(dists)[:5]]

            hull_doc_indices = []
            if hull is not None and len(hull) >= 3:
                for hp in hull:
                    p_dists = np.linalg.norm(c_coords - hp, axis=1)
                    hull_doc_indices.append(member_idx[np.argmin(p_dists)])
            rep_idx = list(set(center_doc_indices) | set(hull_doc_indices))
        else:
            rep_idx = list(member_idx)

        c_df = np.asarray(bin_matrix[member_idx].sum(axis=0)).ravel()
        rep_df = np.asarray(bin_matrix[rep_idx].sum(axis=0)).ravel()

        # Eis: term moet een wezenlijk deel van het cluster dekken (geen toevalstreffers van 1-2 sprekers)
        min_docs = 2 if n_members < 25 else max(3, int(n_members * 0.02))
        valid = (c_df >= min_docs) & (rep_df >= 1)
        if not np.any(valid):
            valid = (c_df >= min_docs)
        if not np.any(valid):
            valid = (c_df >= 2)
        if not np.any(valid):
            return []

        coverage = c_df[valid] / n_members
        precision = c_df[valid] / np.maximum(1.0, global_df[valid])
        rep_ratio = rep_df[valid] / max(1, len(rep_idx))
        global_compactness = np.maximum(0.01, 1.0 - term_global_dispersion[valid])

        if base_weights is not None:
            contrast_boost = np.maximum(0.1, base_weights[valid])
        else:
            contrast_boost = 1.0

        scores = np.zeros_like(c_df, dtype=np.float32)
        scores[valid] = global_compactness * precision * np.sqrt(coverage) * contrast_boost * (1.0 + 2.0 * rep_ratio)

        top_idx = scores.argsort()[::-1][:top_terms]
        return [terms[i] for i in top_idx if scores[i] > 0]

    # 1. Grove cluster-gemiddelden, labels & convex hulls
    coarse_summaries = {}
    coarse_means = {}
    for coarse_id in sorted(set(coarse_ids) - {-1}):
        member_idx = np.where(np.asarray(coarse_ids) == coarse_id)[0]
        mean_vec = np.asarray(tfidf_matrix[member_idx].mean(axis=0)).ravel()
        coarse_means[coarse_id] = mean_vec

        hull, centroid = (None, [0.0, 0.0])
        if coords is not None:
            hull, centroid = compute_cluster_hull(coords[member_idx], percentile=92.0)

        kws = rank_hull_anchored_terms(member_idx, hull, centroid)

        coarse_summaries[coarse_id] = {
            "cluster_id": int(coarse_id),
            "name": format_title_from_terms(kws),
            "terms": kws,
            "size": len(member_idx),
            "centroid": centroid,
            "hull": hull,
        }

    # 2. Bepaal per fijn cluster het bovenliggende grove cluster (meerderheidsoverlap)
    parent_of_fine = {}
    for fine_id in sorted(set(fine_ids) - {-1}):
        member_idx = np.where(np.asarray(fine_ids) == fine_id)[0]
        coarse_at_members = np.asarray(coarse_ids)[member_idx]
        coarse_at_members = coarse_at_members[coarse_at_members != -1]
        if len(coarse_at_members) > 0:
            parent_of_fine[fine_id] = Counter(coarse_at_members.tolist()).most_common(1)[0][0]
        else:
            parent_of_fine[fine_id] = None

    # 3. Fijne clusters contrastief labelen t.o.v. ouder-cluster + convex hulls
    fine_summaries = {}
    for fine_id in sorted(set(fine_ids) - {-1}):
        member_idx = np.where(np.asarray(fine_ids) == fine_id)[0]
        fine_mean = np.asarray(tfidf_matrix[member_idx].mean(axis=0)).ravel()
        parent_id = parent_of_fine.get(fine_id)

        if parent_id is not None and parent_id in coarse_means:
            contrastive_vec = np.maximum(0, fine_mean - coarse_means[parent_id])
        else:
            contrastive_vec = fine_mean

        hull, centroid = (None, [0.0, 0.0])
        if coords is not None:
            hull, centroid = compute_cluster_hull(coords[member_idx], percentile=90.0)

        kws = rank_hull_anchored_terms(member_idx, hull, centroid, base_weights=contrastive_vec)
        if not kws:
            kws = rank_hull_anchored_terms(member_idx, hull, centroid, base_weights=fine_mean)

        parent_name = coarse_summaries[parent_id]["name"] if (parent_id is not None and parent_id in coarse_summaries) else None

        fine_summaries[fine_id] = {
            "cluster_id": int(fine_id),
            "name": format_title_from_terms(kws),
            "parent_id": int(parent_id) if parent_id is not None else None,
            "parent_name": parent_name,
            "terms": kws,
            "size": len(member_idx),
            "centroid": centroid,
            "hull": hull,
        }

    # 4. Hiërarchieboom bouwen
    children_by_coarse = {cid: [] for cid in coarse_summaries}
    for fine_id, fine in fine_summaries.items():
        pid = fine["parent_id"]
        if pid is not None and pid in children_by_coarse:
            children_by_coarse[pid].append({
                "id": fine["cluster_id"],
                "name": fine["name"],
                "value": fine["size"],
                "terms": fine["terms"],
                "centroid": fine["centroid"],
                "hull": fine["hull"],
            })

    tree = []
    for coarse_id, coarse in sorted(coarse_summaries.items(), key=lambda kv: kv[1]["size"], reverse=True):
        children = sorted(children_by_coarse.get(coarse_id, []), key=lambda c: c["value"], reverse=True)
        tree.append({
            "id": coarse["cluster_id"],
            "name": coarse["name"],
            "value": coarse["size"],
            "terms": coarse["terms"],
            "centroid": coarse["centroid"],
            "hull": coarse["hull"],
            "children": children,
        })

    fine_list = sorted(fine_summaries.values(), key=lambda s: s["size"], reverse=True)
    return coarse_summaries, fine_list, tree


def build_multilevel_clusters(coords, hdbscan_min_cluster_size, level_sizes, dominance_ratio=4.0):
    """Enige HDBSCAN-clusteringpad voor main() (issue #281) -- de vroegere,
    aparte 2-niveau `build_hierarchical_clusters` (coarse via één
    splitsingsronde vanaf de root, fine via `partition_exhaustive`) is
    uitgefaseerd; met `level_sizes` van lengte 2 dekt deze functie ook dat
    geval (zij het met coarse nu via dezelfde exhaustieve partitie als fine,
    zie main()'s toelichting bij het ontbreken van --cluster-level-sizes).

    `level_sizes` is een dalende lijst van min_size_to_name-drempels (grofste
    niveau eerst). In plaats van coarse/fine recursief-per-tak op te bouwen,
    is elk niveau hier een ONAFHANKELIJKE, volledig uitputtende snede van
    dezelfde HDBSCAN condensed tree op zijn eigen drempel (partition_exhaustive,
    de oude fine_partition, nu voor élk niveau i.p.v. alleen het diepste).
    Een enkele afsplitsingsronde vanaf root (zoals de oude coarse_partition)
    volstaat hier expliciet NIET: bij grotere drempels blijft dan bijna alle
    massa in één ongesplitste "hoofdtak" hangen, met een hull die bijna de
    hele kaart beslaat i.p.v. een compacte regio -- live bevestigd in QGIS
    (coarse tot 3 niveaus toonden vrijwel identieke buitenranden i.p.v.
    onderscheidende clusters).

    Dit werkt omdat sneden van dezelfde hiërarchische boom op verschillende
    hoogtes altijd consistent/genest zijn (een kleinere drempel accepteert
    een superset van de splitsingen die een grotere drempel accepteert) --
    nesting hoeft dus niet expliciet per tak afgedwongen te worden zoals in
    de oude recursieve aanpak, en kan achteraf via meerderheidsoverlap
    bepaald worden (zie label_multilevel_clusters), net als de oude
    parent_of_fine-berekening.

    `dominance_ratio`: live in QGIS bleek de "hoofdtak" (het main-branch-
    restje dat via partition_exhaustive nooit een kwalificerende splitsing
    vond) op elk niveau als doodgewoon, groot cluster te verschijnen (bv.
    "Schors", 59% van alle punten op niveau 0, met betekenisloze TF-IDF-
    termen) i.p.v. als ruis. Als het grootste cluster op een niveau meer dan
    `dominance_ratio` keer zo groot is als het op-één-na-grootste, wordt het
    behandeld als zo'n restje en naar -1 (ruis) gezet i.p.v. als genummerd
    cluster meegeteld -- een normale onderwerpsverdeling heeft nooit één
    cluster dat de rest met zo'n marge overvleugelt.

    Geeft `level_ids` terug: een lijst van N even lange int-arrays (label per
    punt in coords, -1=ruis), grofste niveau eerst."""
    import hdbscan as hdbscan_pkg

    n = len(coords)
    clusterer = hdbscan_pkg.HDBSCAN(min_cluster_size=hdbscan_min_cluster_size).fit(coords)
    children_by_parent, root = _condensed_tree_children_by_parent(clusterer)

    def collect_points(node_id):
        if node_id < n:
            return [node_id]
        points = []
        for child, size in children_by_parent.get(node_id, []):
            points.extend([child] if size == 1 else collect_points(child))
        return points

    def partition_exhaustive(node_id, min_size_to_name):
        current, leaves, merged = node_id, [], []
        while True:
            entries = children_by_parent.get(current, [])
            real_children = [(ch, sz) for ch, sz in entries if sz > 1]
            qualifying = [(ch, sz) for ch, sz in real_children if sz >= min_size_to_name]
            merged.extend(ch for ch, sz in entries if sz == 1)
            for child, size in real_children:
                if size < min_size_to_name:
                    merged.extend(collect_points(child))
            if not qualifying:
                leaves.append(merged)
                return leaves
            qualifying.sort(key=lambda cs: cs[1])
            *smaller, (largest, _size) = qualifying
            for child, _size in smaller:
                leaves.extend(partition_exhaustive(child, min_size_to_name))
            current = largest

    n_levels = len(level_sizes)
    level_ids = []
    for level_idx, threshold in enumerate(level_sizes):
        # Elk niveau is een volledige uitputtende snede van dezelfde boom op
        # zijn eigen drempel (niet slechts één afsplitsingsronde vanaf root) --
        # anders blijft bij grotere drempels vrijwel alle massa in één
        # ongesplitste "hoofdtak" hangen, met een hull die bijna de hele
        # kaart beslaat i.p.v. een compacte, herkenbare regio (live gezien in
        # QGIS: niveaus 0-3 toonden alle drie bijna dezelfde buitenrand).
        ids = np.full(n, -1, dtype=int)
        leaves = sorted(partition_exhaustive(root, threshold), key=len, reverse=True)
        n_rejected = 0
        if len(leaves) >= 2 and len(leaves[0]) > dominance_ratio * len(leaves[1]):
            n_rejected = len(leaves[0])
            leaves = leaves[1:]
        for label, pts in enumerate(leaves):
            ids[pts] = label
        logger.info(
            "niveau %d/%d (min_size_to_name=%d): %d clusters%s",
            level_idx + 1, n_levels, threshold, len(set(ids.tolist()) - {-1}),
            f" (hoofdtak van {n_rejected} punten verworpen als ruis)" if n_rejected else "",
        )
        level_ids.append(ids)

    return level_ids


def label_multilevel_clusters(
    texts, coords, level_ids, top_terms=6, extra_stopwords=None, max_df=0.25,
    redundancy_overlap=0.8,
):
    """N-laags veralgemening van label_hierarchical_clusters (die ongewijzigd
    blijft, nog gebruikt door main()'s --cluster-method dbscan-pad). Voor
    platte (niet-hiërarchische) labels op een enkel niveau -- zoals
    notebooks/explore_plenary_umap_clusters.py doet -- volstaat een
    `level_ids`-lijst van lengte 1. `level_ids` is een lijst van N even lange int-arrays (grofste
    niveau eerst, zie build_multilevel_clusters). Niveau 0 krijgt globale
    TF-IDF-labels (net als coarse); elk dieper niveau k>0 krijgt contrastieve
    labels t.o.v. zijn ouder op niveau k-1 (net als fine). "Ouder" wordt
    bepaald via meerderheidsoverlap -- in de praktijk vrijwel altijd 100%
    overlap, niet slechts een meerderheid, omdat elk niveau een snede is van
    dezelfde boom (zie build_multilevel_clusters' docstring).

    Een cluster waarvan de hull minstens `redundancy_overlap` IoU/Jaccard
    (intersection-over-union van de convex hulls, niet puntenaantal-
    verhouding -- die laatste kan flink onderschatten, zie de toelichting
    verderop in deze functie) deelt met de hull van zijn ouder, voegde
    tussen die twee niveaus geometrisch weinig nieuws toe (live gezien:
    "Asielmigratie" dook zo, vrijwel ongewijzigd, op bij 4 opeenvolgende
    niveaus) -- zo'n cluster krijgt `"redundant_with_parent": True`
    (i.p.v. verwijderd te worden, zodat het per-punt cluster_l<n>-veld
    intact blijft) zodat hull/naam-consumenten
    'm kunnen overslaan als niet-nieuwe informatie t.o.v. het vorige niveau.

    Geeft (level_lists, tree) terug: `level_lists` is een lijst van N
    lijsten met summary-dicts (grofste niveau eerst, elk sorteerd op size),
    `tree` is een geneste boom (niveau-0-nodes met recursief geneste
    "children" t/m het diepste niveau)."""
    if extra_stopwords is None:
        extra_stopwords = set()

    raw_stops = set(DUTCH_STOPWORDS) | set(extra_stopwords)
    clean_stops = set()
    for s in raw_stops:
        for tok in re.findall(r"(?u)\b[a-zA-ZÀ-ÿ]{2,}\b", s.lower()):
            clean_stops.add(tok)

    if coords is not None:
        diffuse_stops = compute_spatially_diffuse_stopwords(texts, coords, max_dispersion_ratio=0.55)
        for s in diffuse_stops:
            for tok in re.findall(r"(?u)\b[a-zA-ZÀ-ÿ]{2,}\b", s.lower()):
                clean_stops.add(tok)

    tfidf = TfidfVectorizer(
        stop_words=list(clean_stops),
        lowercase=True,
        ngram_range=(1, 2),
        min_df=3,
        max_df=max_df,
        token_pattern=r"(?u)\b[a-zA-ZÀ-ÿ]{3,}\b",
    )
    tfidf_matrix = tfidf.fit_transform(texts)
    bin_matrix = (tfidf_matrix > 0).astype(np.float32)
    global_df = np.asarray(bin_matrix.sum(axis=0)).ravel()
    terms = tfidf.get_feature_names_out()

    term_global_dispersion = np.ones(len(terms), dtype=np.float32)
    if coords is not None:
        counts = np.asarray(bin_matrix.sum(axis=0)).flatten()
        valid_terms = counts >= 3
        sum_coords = bin_matrix.T.dot(coords)
        mean_coords = np.zeros_like(sum_coords)
        mean_coords[valid_terms] = sum_coords[valid_terms] / counts[valid_terms, None]

        sum_coords_sq = bin_matrix.T.dot(coords ** 2)
        mean_coords_sq = np.zeros_like(sum_coords_sq)
        mean_coords_sq[valid_terms] = sum_coords_sq[valid_terms] / counts[valid_terms, None]

        var_x = np.maximum(0, mean_coords_sq[:, 0] - mean_coords[:, 0] ** 2)
        var_y = np.maximum(0, mean_coords_sq[:, 1] - mean_coords[:, 1] ** 2)
        term_spatial_std = np.sqrt(var_x + var_y)
        global_std = np.sqrt(np.var(coords[:, 0]) + np.var(coords[:, 1]))
        if global_std > 0:
            term_global_dispersion = term_spatial_std / global_std

    def rank_hull_anchored_terms(member_idx, hull, centroid, base_weights=None):
        n_members = len(member_idx)
        if n_members == 0:
            return []
        if coords is not None and centroid is not None:
            c_coords = coords[member_idx]
            dists = np.linalg.norm(c_coords - centroid, axis=1)
            center_doc_indices = member_idx[np.argsort(dists)[:5]]
            hull_doc_indices = []
            if hull is not None and len(hull) >= 3:
                for hp in hull:
                    p_dists = np.linalg.norm(c_coords - hp, axis=1)
                    hull_doc_indices.append(member_idx[np.argmin(p_dists)])
            rep_idx = list(set(center_doc_indices) | set(hull_doc_indices))
        else:
            rep_idx = list(member_idx)

        c_df = np.asarray(bin_matrix[member_idx].sum(axis=0)).ravel()
        rep_df = np.asarray(bin_matrix[rep_idx].sum(axis=0)).ravel()

        min_docs = 2 if n_members < 25 else max(3, int(n_members * 0.02))
        valid = (c_df >= min_docs) & (rep_df >= 1)
        if not np.any(valid):
            valid = (c_df >= min_docs)
        if not np.any(valid):
            valid = (c_df >= 2)
        if not np.any(valid):
            return []

        coverage = c_df[valid] / n_members
        precision = c_df[valid] / np.maximum(1.0, global_df[valid])
        rep_ratio = rep_df[valid] / max(1, len(rep_idx))
        global_compactness = np.maximum(0.01, 1.0 - term_global_dispersion[valid])

        if base_weights is not None:
            contrast_boost = np.maximum(0.1, base_weights[valid])
        else:
            contrast_boost = 1.0

        scores = np.zeros_like(c_df, dtype=np.float32)
        scores[valid] = global_compactness * precision * np.sqrt(coverage) * contrast_boost * (1.0 + 2.0 * rep_ratio)

        top_idx = scores.argsort()[::-1][:top_terms]
        return [terms[i] for i in top_idx if scores[i] > 0]

    n_levels = len(level_ids)
    level_summaries = [dict() for _ in range(n_levels)]
    level_means = [dict() for _ in range(n_levels)]

    for level_idx, ids in enumerate(level_ids):
        ids_arr = np.asarray(ids)
        for cluster_id in sorted(set(ids_arr.tolist()) - {-1}):
            member_idx = np.where(ids_arr == cluster_id)[0]
            mean_vec = np.asarray(tfidf_matrix[member_idx].mean(axis=0)).ravel()
            level_means[level_idx][cluster_id] = mean_vec

            hull, centroid = (None, [0.0, 0.0])
            if coords is not None:
                hull, centroid = compute_cluster_hull(coords[member_idx], percentile=92.0 if level_idx == 0 else 90.0)

            parent_id = None
            base_weights = None
            if level_idx > 0:
                parent_at_members = np.asarray(level_ids[level_idx - 1])[member_idx]
                parent_at_members = parent_at_members[parent_at_members != -1]
                if len(parent_at_members) > 0:
                    parent_id = Counter(parent_at_members.tolist()).most_common(1)[0][0]
                parent_mean = level_means[level_idx - 1].get(parent_id) if parent_id is not None else None
                base_weights = np.maximum(0, mean_vec - parent_mean) if parent_mean is not None else mean_vec

            kws = rank_hull_anchored_terms(member_idx, hull, centroid, base_weights=base_weights)
            if not kws and base_weights is not None:
                kws = rank_hull_anchored_terms(member_idx, hull, centroid, base_weights=mean_vec)

            parent_name = None
            if level_idx > 0 and parent_id is not None and parent_id in level_summaries[level_idx - 1]:
                parent_name = level_summaries[level_idx - 1][parent_id]["name"]

            level_summaries[level_idx][cluster_id] = {
                "cluster_id": int(cluster_id),
                "level": level_idx,
                "name": format_title_from_terms(kws),
                "parent_id": int(parent_id) if parent_id is not None else None,
                "parent_name": parent_name,
                "terms": kws,
                "size": len(member_idx),
                "centroid": centroid,
                "hull": hull,
                "redundant_with_parent": False,
                "contained_by_sibling": None,
            }

    def _hull_polygon(hull):
        if not hull or len(hull) < 3:
            return None
        poly = Polygon(hull)
        if not poly.is_valid:
            poly = poly.buffer(0)
        return poly if not poly.is_empty else None

    for level_idx in range(1, n_levels):
        for summary in level_summaries[level_idx].values():
            # Geometrische overlap (IoU/Jaccard op de convex hulls), NIET
            # puntenaantal-verhouding: een kind kan een flink deel van zijn
            # ouders leden kwijtraken (interne, niet-rand-punten) zonder dat
            # de hull-oppervlakte daardoor merkbaar krimpt -- een convex hull
            # wordt alleen door de buitenste/rand-punten bepaald. Live
            # bevestigd in QGIS: een paar met 79.5% puntenaantal-overlap
            # bleek 97-98% van elkaars hull-oppervlakte te delen (dus
            # duidelijk wél redundant), wat de eerdere puntenaantal-based
            # check ten onrechte niet als redundant markeerde.
            parent_id = summary["parent_id"]
            if parent_id is None:
                continue
            parent_summary = level_summaries[level_idx - 1][parent_id]
            child_poly = _hull_polygon(summary["hull"])
            parent_poly = _hull_polygon(parent_summary["hull"])
            if child_poly is None or parent_poly is None:
                continue
            intersection_area = child_poly.intersection(parent_poly).area
            union_area = child_poly.area + parent_poly.area - intersection_area
            iou = intersection_area / union_area if union_area > 0 else 0.0
            if iou >= redundancy_overlap:
                summary["redundant_with_parent"] = True

    # Same-level containment (zie scripts/validate_cluster_hierarchy.py):
    # `partition_exhaustive` garandeert disjuncte PUNTENSETS per cluster op
    # een niveau, maar niet disjuncte convex hulls -- een ruimtelijk verspreid/
    # concaaf cluster se hull kan een kleiner, compact cluster op hetzelfde
    # niveau geometrisch volledig omsluiten, ook zonder gedeelde punten. Op
    # hetzelfde niveau horen clusters een partitie te zijn (naast elkaar),
    # niet genest -- dat is dus altijd een render-artefact, in tegenstelling
    # tot ouder/kind-nesting (hierboven, IoU-redundantie), wat net het
    # bedoelde beeld is. Lichte mitigatie i.p.v. een concave-hull-herbouw van
    # compute_cluster_hull(): het KLEINERE cluster vlaggen, niet de
    # hull-geometrie zelf aanpassen -- een renderstap kan dan zelf kiezen om
    # zulke contouren over te slaan of anders te stijlen.
    for level_idx in range(n_levels):
        summaries = list(level_summaries[level_idx].values())
        polygons = [(s, _hull_polygon(s["hull"])) for s in summaries]
        for i, (summary_a, poly_a) in enumerate(polygons):
            if poly_a is None:
                continue
            for summary_b, poly_b in polygons[i + 1:]:
                if poly_b is None:
                    continue
                if poly_a.contains(poly_b):
                    summary_b["contained_by_sibling"] = summary_a["cluster_id"]
                elif poly_b.contains(poly_a):
                    summary_a["contained_by_sibling"] = summary_b["cluster_id"]

    def to_node(summary):
        return {
            "id": summary["cluster_id"],
            "name": summary["name"],
            "value": summary["size"],
            "terms": summary["terms"],
            "centroid": summary["centroid"],
            "hull": summary["hull"],
            "redundant_with_parent": summary["redundant_with_parent"],
            "contained_by_sibling": summary["contained_by_sibling"],
            "children": [],
        }

    nodes_by_level = [
        {cid: to_node(summary) for cid, summary in level_summaries[level_idx].items()}
        for level_idx in range(n_levels)
    ]
    for level_idx in range(1, n_levels):
        for cid, node in nodes_by_level[level_idx].items():
            parent_id = level_summaries[level_idx][cid]["parent_id"]
            if parent_id is not None and parent_id in nodes_by_level[level_idx - 1]:
                nodes_by_level[level_idx - 1][parent_id]["children"].append(node)
    for level_nodes in nodes_by_level:
        for node in level_nodes.values():
            node["children"].sort(key=lambda c: c["value"], reverse=True)

    tree = sorted(nodes_by_level[0].values(), key=lambda n: n["value"], reverse=True)
    level_lists = [
        sorted(level_summaries[level_idx].values(), key=lambda s: s["size"], reverse=True)
        for level_idx in range(n_levels)
    ]
    return level_lists, tree


def load_umap_coords(path: Path, rows) -> np.ndarray:
    """Leest een write_umap_coords()-bestand terug, uitgelijnd op `rows`
    (dezelfde volgorde als `texts`/`vectors` in main() -- de rest van de
    pijplijn indexeert coords/texts/rows overal parallel op positie, niet op
    id). Een ontbrekend id (verkeerde --start/--end/--label t.o.v. de
    coords-export) geeft gewoon een KeyError."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return np.array([data[str(row["id"])] for row in rows], dtype=np.float64)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", required=True, help="published_at ondergrens, ISO-datum (inclusief)")
    parser.add_argument("--end", required=True, help="published_at bovengrens, ISO-datum (exclusief)")
    parser.add_argument("--label", required=True, help="korte periode-naam voor bestandsnamen, bv. 2025-heden")
    parser.add_argument(
        "--dataset-version", type=int, default=None,
        help="versienummer van deze dataset-run, meegeschreven als \"dataset_version\" in de "
        "frontend-export (plenair-map.json) en clusters-export (plenair-map-clusters.json). "
        "Zonder deze vlag: automatisch opgezocht bij Zenodo (aantal bestaande versies onder "
        "concept-record 22181704, plus 1) -- zie detect_next_dataset_version(). Dat is een "
        "AANNAME (Zenodo's eigen \"version\"-metadataveld staat nog nergens ingevuld), dus "
        "expliciet --dataset-version blijft de betrouwbare optie als het ertoe doet. De "
        "Zenodo-publicatie zelf blijft hoe dan ook een bewuste, handmatige stap.",
    )
    parser.add_argument("--min-content-len", type=int, default=30)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--refresh", action="store_true", help="cache negeren en embeddings herberekenen")
    parser.add_argument(
        "--export-frontend",
        action="store_true",
        help="ook een lean JSON naar data/export/plenair-map.json schrijven (frontend-input, "
        "onderwerpen/index.astro). Nog een handmatige stap, geen make-target -- pas als "
        "pipeline-stage overwegen ná een interpreteerbaar resultaat op de volle dataset.",
    )
    parser.add_argument(
        "--export-suffix",
        default="",
        help="voegt <suffix> toe aan de export-bestandsnamen (plenair-map<suffix>.json enz.), "
        "i.p.v. het bestaande plenair-map.json te overschrijven -- bv. --export-suffix -full "
        "voor een volledigere dataset naast de bestaande, op ~40k punten performance-getunede "
        "PlenairMap.vue-export (die blijft ongewijzigd, zie TiledPlenairMap.vue/pipeline.tiling "
        "voor het renderpad dat wél een groter puntenaantal aankan).",
    )
    parser.add_argument("--skip-clustering", action="store_true", help="clustering + TF-IDF-labeling overslaan")
    parser.add_argument("--cluster-method", choices=["hdbscan", "dbscan"], default="hdbscan")
    parser.add_argument(
        "--dbscan-eps", type=float, default=0.25,
        help="alleen bij --cluster-method dbscan. PR #166 gebruikte 0.15 op een losse, kleinere "
        "puntenwolk (één topic, 3555 punten). 0.5 op de volle ~99k-punten-dataset gaf 94%% van "
        "alle punten in één cluster -- veel te grof. Nog steeds tunen op het resultaat.",
    )
    parser.add_argument("--dbscan-min-samples", type=int, default=15)
    parser.add_argument(
        "--hdbscan-min-cluster-size", type=int, default=15,
        help="alleen bij --cluster-method hdbscan: granulariteit van de onderliggende condensed "
        "tree waarover build_multilevel_clusters() wandelt (zie die functie's docstring). "
        "Vervangt de vroegere aparte coarse(200)/fine(15)-drempels, die op deze data telkens "
        "instortten tot 1-3 dominante clusters -- zie docs/hierarchische-clustering-plenaire-spreekbeurten.md.",
    )
    parser.add_argument(
        "--cluster-min-size-to-name", type=int, default=200,
        help="hoeveel spreekbeurten een afgesplitste subtak minstens moet hebben om een eigen "
        "cluster te worden. Genegeerd als --cluster-level-sizes is opgegeven; zonder die vlag "
        "wordt dit voor beide niveaus (coarse en fine) gebruikt -- zie --cluster-level-sizes.",
    )
    parser.add_argument(
        "--cluster-level-sizes", default=None,
        help="komma-gescheiden, DALENDE lijst van min_size_to_name-drempels, één per niveau "
        "(grofste eerst) -- bv. '4000,1500,500,150,50' voor 5 niveaus. Zonder deze vlag: 2 "
        "niveaus op [--cluster-min-size-to-name, --cluster-min-size-to-name] (let op: dit is "
        "GEEN 1-op-1 vervanging van de vroegere coarse/fine-tweedeling, zie de toelichting in "
        "main()). Zie build_multilevel_clusters()/label_multilevel_clusters().",
    )
    parser.add_argument(
        "--cluster-dominance-ratio", type=float, default=4.0,
        help="alleen bij --cluster-method hdbscan: als het grootste cluster op een niveau meer dan "
        "dit veelvoud van het op-één-na-grootste is, wordt het als ruis (-1) behandeld i.p.v. als "
        "genummerd cluster -- zie build_multilevel_clusters().",
    )
    parser.add_argument(
        "--cluster-redundancy-overlap", type=float, default=0.8,
        help="alleen bij --cluster-method hdbscan: minimale IoU/Jaccard (intersection-over-union "
        "van de convex hulls, NIET puntenaantal-verhouding -- die kan de werkelijke geometrische "
        "overlap flink onderschatten) tussen een cluster en zijn ouder-cluster (vorig niveau) om "
        "als 'geen echte splitsing' te gelden -- gemarkeerd als \"redundant_with_parent\" i.p.v. "
        "verwijderd, zodat het per-punt cluster_l<n>-veld intact blijft maar hull/naam-consumenten "
        "'m kunnen overslaan.",
    )
    parser.add_argument("--cluster-top-terms", type=int, default=8, help="aantal TF-IDF-termen per cluster-label")
    parser.add_argument(
        "--cluster-llm-examples-per-cluster", type=int, default=8,
        help="representatieve spreekbeurten per cluster om vast te leggen voor de LLM-naamgevingsprompt "
        "(zie pipeline/plenary_map/label_export.py -- de LLM-call zelf gebeurt niet meer in dit script).",
    )
    parser.add_argument(
        "--coords-path", required=True,
        help="pad naar een pipeline.plenary_map.umap --export-coords-bestand van dezelfde "
        "--start/--end/--label-documentenselectie (UMAP zelf is geen onderdeel meer van dit script).",
    )
    args = parser.parse_args()

    if args.dataset_version is None:
        args.dataset_version = detect_next_dataset_version()
        if args.dataset_version is not None:
            logger.info("dataset_version automatisch bepaald via Zenodo: %d", args.dataset_version)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Fetch + strippen + incrementeel embedden zit nu in pipeline/embed/documents.py
    # (eerste stage van de pijplijn, los te draaien met `uv run python -m
    # pipeline.embed.documents`) -- hier alleen nog aanroepen, niet meer inline.
    rows, texts, vectors, embed_elapsed = fetch_and_embed(
        args.start, args.end, args.min_content_len, args.label,
        base_url=args.base_url, refresh=args.refresh,
    )

    conn = db.connect()
    db_stopwords = fetch_actor_and_party_stopwords(conn)
    # Topic is geen eigenschap van de embed-/clusterworkflow (fetch_and_embed
    # hierboven doet geen join op topics/topic_id, zie #288) -- alleen hier,
    # als aparte, latere stap puur t.b.v. de topic-legenda/kleuring bij het
    # visualiseren (plot-html/frontend-export), joinen we topic terug op de
    # al opgehaalde document-ids.
    # Geen WHERE id IN (...): bij honderdduizenden document-ids overschrijdt
    # dat sqlite's parameterlimiet (live bevestigd: "too many SQL variables").
    # De hele id->slug-mapping is twee smalle kolommen -- goedkoop genoeg om
    # in één keer op te halen i.p.v. te chunken.
    topic_rows = conn.execute("SELECT d.id, t.slug FROM documents d LEFT JOIN topics t ON t.id = d.topic_id").fetchall()
    topic_by_id = {r["id"]: r["slug"] or "plenair" for r in topic_rows}
    conn.close()

    logger.info("%d documenten tussen %s en %s", len(texts), args.start, args.end)

    # UMAP zelf (pipeline.plenary_map.umap, host-only qua geheugengebruik op
    # de volle dataset, zie docs/handoff.md) is geen onderdeel meer van dit
    # script -- alleen de coördinaten daarvan inlezen. `vectors` (van
    # fetch_and_embed hierboven) wordt hier dus niet gebruikt, alleen
    # rows/texts voor de TF-IDF-labeling/representatieve voorbeelden.
    coords = load_umap_coords(Path(args.coords_path), rows)
    logger.info("UMAP-coördinaten geladen uit %s", args.coords_path)

    alpino_stopwords = fetch_alpino_non_content_stopwords()
    all_stopwords = (
        set(DUTCH_STOPWORDS)
        | DUTCH_PRONOUNS_AND_NUMERALS
        | PARTY_ALIASES_AND_ABBREVIATIONS
        | PARLIAMENTARY_INSTITUTIONAL
        | db_stopwords
        | alpino_stopwords
    )

    if args.cluster_level_sizes:
        level_sizes = [int(x) for x in args.cluster_level_sizes.split(",") if x.strip()]
        if len(level_sizes) < 2:
            raise SystemExit("--cluster-level-sizes moet minstens 2 drempels bevatten")
        if sorted(level_sizes, reverse=True) != level_sizes:
            raise SystemExit("--cluster-level-sizes moet dalend zijn (grofste niveau eerst)")
    else:
        # Zonder --cluster-level-sizes: 2 niveaus op dezelfde drempel (oud
        # CLI-gedrag). Let op: dit is GEEN 1-op-1 vervanging van de vroegere
        # build_hierarchical_clusters-coarse (die coarse via één
        # splitsingsronde vanaf de root bepaalde, niet via dezelfde
        # exhaustieve partitie als fine) -- een productie-drempelpaar dat
        # weer een vergelijkbaar coarse-beeld geeft, moet empirisch opnieuw
        # bepaald worden (zie issue #281).
        level_sizes = [args.cluster_min_size_to_name, args.cluster_min_size_to_name]

    cluster_ids, cluster_summaries, hierarchy, all_level_ids = None, None, None, None
    if not args.skip_clustering:
        if args.cluster_method == "hdbscan":
            # Enige HDBSCAN-clusteringpad (build_multilevel_clusters/
            # label_multilevel_clusters), voorheen gesplitst in een apart
            # vast-2-niveau-pad (build_hierarchical_clusters) en een N-laags
            # pad -- samengevoegd zodat de restgroep- en overlap-mitigaties
            # (dominance_ratio/redundant_with_parent/contained_by_sibling)
            # ook de standaard coarse/fine-export bereiken (issue #281,
            # t.b.v. #186 punt 2 en 4). build_hierarchical_clusters/
            # label_hierarchical_clusters zelf blijven bestaan, uitsluitend
            # nog voor notebooks/explore_plenary_umap_clusters.py.
            level_ids = build_multilevel_clusters(
                coords, args.hdbscan_min_cluster_size, level_sizes,
                dominance_ratio=args.cluster_dominance_ratio,
            )
            level_lists, hierarchy = label_multilevel_clusters(
                texts,
                coords,
                level_ids,
                top_terms=args.cluster_top_terms,
                extra_stopwords=all_stopwords,
                max_df=0.25,
                redundancy_overlap=args.cluster_redundancy_overlap,
            )

            # Representatieve voorbeelden vastleggen (geen LLM-call, puur de
            # UMAP-afhankelijke berekening) -- de LLM-naamgeving zelf is GEEN
            # onderdeel meer van dit script (voorheen --skip-llm-naming): die
            # draait uitsluitend via het aparte pipeline/plenary_map/
            # label_export.py (make label-clusters), zodat de dure, host-only
            # UMAP-fit (geheugengebruik, zie docs/handoff.md) nooit meer in
            # dezelfde run zit als de LLM-naamgeving, die juist prima los,
            # elders (bv. de devcontainer tegen een gratis remote router) en
            # in meerdere porties kan draaien. `name` blijft hier dus de
            # TF-IDF-naam (label_multilevel_clusters), `duiding` ontbreekt
            # tot label_export.py 'm invult.
            examples_by_level = compute_representative_examples(
                level_ids, level_lists, texts, coords, rows, args.cluster_llm_examples_per_cluster,
            )
            examples_path = OUTPUT_DIR / f"cluster-label-input-{args.label}.json"
            examples_path.write_text(json.dumps(examples_by_level, ensure_ascii=False), encoding="utf-8")
            logger.info("representatieve voorbeelden voor LLM-naamgeving geschreven naar %s", examples_path)

            cluster_ids = level_ids[-1]
            all_level_ids = level_ids
            cluster_summaries = {
                # coarse/fine blijven top-level sleutels voor backward compat
                # (PlenairMap.vue), verrijkt met de nieuwe vlagvelden; levels
                # bevat de volledige N-laagse lijst (architectenadvies #281 §5).
                "coarse": level_lists[0],
                "fine": level_lists[-1],
                "levels": level_lists,
                "dataset_version": args.dataset_version,
            }

            def _log_domain(node, depth=0):
                if depth > 2:
                    return
                indent = "  " * depth + ("└─ " if depth else "")
                terms_str = ", ".join(node["terms"][:4])
                logger.info("%s%s (n=%d) [%s]", indent, node["name"], node["value"], terms_str)
                for child in node["children"][:5]:
                    _log_domain(child, depth + 1)

            for domain in hierarchy:
                _log_domain(domain)
        else:
            fine_ids = run_clustering(coords, "dbscan", args.dbscan_eps, args.dbscan_min_samples, None)
            coarse_summaries, fine_summaries, hierarchy = label_hierarchical_clusters(
                texts,
                coords,
                fine_ids,
                fine_ids,
                top_terms=args.cluster_top_terms,
                extra_stopwords=all_stopwords,
                max_df=0.25,
            )
            cluster_ids = fine_ids
            cluster_summaries = {
                "coarse": list(coarse_summaries.values()),
                "fine": fine_summaries,
                "dataset_version": args.dataset_version,
            }

    points = []
    for i, (row, (x, y)) in enumerate(zip(rows, coords)):
        points.append({
            "id": row["id"],
            "x": float(x),
            "y": float(y),
            "topic": topic_by_id.get(row["id"], "plenair"),
            "text": texts[i][:160],
            "actor": row["actor_name"],
            "party": row["party"] or "onbekend",
            "activiteit_soort": row["activiteit_soort"],
            "debate_title": row["debate_title"],
            "published_at": row["published_at"],
            "cluster": int(cluster_ids[i]) if cluster_ids is not None else None,
            "cluster_levels": [int(level[i]) for level in all_level_ids] if all_level_ids is not None else None,
        })

    def _suffixed(path):
        return path.with_name(f"{path.stem}{args.export_suffix}{path.suffix}") if args.export_suffix else path

    if cluster_summaries is not None:
        clusters_path = OUTPUT_DIR / f"clusters-{args.label}.json"
        clusters_path.write_text(json.dumps(cluster_summaries, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("%d cluster-labels geschreven naar %s", len(cluster_summaries), clusters_path)
        if args.export_frontend:
            clusters_export_path = _suffixed(CLUSTERS_EXPORT_PATH)
            clusters_export_path.parent.mkdir(parents=True, exist_ok=True)
            clusters_export_path.write_text(json.dumps(cluster_summaries, ensure_ascii=False), encoding="utf-8")

    if hierarchy is not None:
        hierarchy_path = OUTPUT_DIR / f"hierarchy-{args.label}.json"
        hierarchy_path.write_text(json.dumps(hierarchy, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("hiërarchie (%d grove clusters) geschreven naar %s", len(hierarchy), hierarchy_path)
        if args.export_frontend:
            hierarchy_export_path = _suffixed(HIERARCHY_EXPORT_PATH)
            hierarchy_export_path.parent.mkdir(parents=True, exist_ok=True)
            hierarchy_export_path.write_text(json.dumps(hierarchy, ensure_ascii=False), encoding="utf-8")

    html_path = OUTPUT_DIR / f"plot-{args.label}.html"
    write_plot_html(points, html_path, title=f"UMAP (bge-m3) -- alle plenaire debatten, {args.label}")
    logger.info("%d punten geschreven naar %s", len(points), html_path)
    if embed_elapsed is not None:
        logger.info("timing: embeddings %.1fs (missende ids alsnog opgehaald)", embed_elapsed)

    if args.export_frontend:
        write_frontend_export(points, export_path=_suffixed(EXPORT_PATH), dataset_version=args.dataset_version)


# Cloudflare Workers staat max. 25 MiB per asset toe (zie ook
# frontend/src/pages/tags/[sleutel].astro se geschiedenis, commit 350491c --
# zelfde probleem, andere pagina). Bij ~99k punten kwam het naieve
# array-of-objects-formaat op ~42 MiB uit: (a) elke veldnaam
# ("activiteit_soort", "debate_title", ...) wordt letterlijk herhaald per
# punt in JSON, en (b) actor/partij/debattitel/activiteit_soort/topic
# herhalen zich massaal (honderden-duizenden beurten uit dezelfde ~200
# debatten van dezelfde ~150 sprekers). Lookup-tabellen + een compacte
# array per punt (geen veldnamen, geen herhaalde strings) lost beide op.
def write_frontend_export(points, export_path=EXPORT_PATH, dataset_version=None):
    n = len(points)
    # Geen percentiel-trim meer (was 0.5-99.5, daarna 0.01-99.99): zelfs de
    # laatste, veel losser bereik hield exact evenveel punten over als de
    # oorspronkelijke trim (132.921) -- de uitschieters (bv. "Voorzitter." --
    # na het strippen van de sprekersprefix nauwelijks nog tekst over om
    # zinnig op te embedden) zitten kennelijk in een dichte bulk die breder is
    # dan 0.01%, dus een percentielgrens alleen maakte geen verschil. Ook
    # zorgde het trimmen zelf voor een mismatch tussen de tile-grid-extent (op
    # de export gebaseerd) en de cluster-hulls (op de volle, ongetrimde
    # puntenset gebaseerd) -- zie de L3-201-bug (buiten-bereik coördinaat na
    # herschaling, live gezien in QGIS). Alleen niet-eindige coördinaten (NaN/
    # inf, zouden de tile-grid-bounds kapotmaken) worden nog geweerd.
    kept = [p for p in points if math.isfinite(p["x"]) and math.isfinite(p["y"])]
    logger.info("%d/%d punten met eindige coördinaten gehouden voor frontend-export", len(kept), n)

    topics_lu, actors_lu, parties_lu, debates_lu, soorten_lu = {}, {}, {}, {}, {}

    def idx(lookup, value):
        if value not in lookup:
            lookup[value] = len(lookup)
        return lookup[value]

    rows = []
    for p in kept:
        row = [
            p["id"],
            round(p["x"], 4),
            round(p["y"], 4),
            idx(topics_lu, p["topic"]),
            idx(actors_lu, p["actor"]),
            idx(parties_lu, p["party"]),
            idx(debates_lu, p["debate_title"] or ""),
            idx(soorten_lu, p["activiteit_soort"] or ""),
            p["published_at"],
            p["text"][:100],
            p["cluster"],
        ]
        # Optioneel 12e element: cluster-id per niveau (grofste eerst), alleen
        # aanwezig bij N-laagse clustering (--cluster-level-sizes). De
        # bestaande 11-elementen-vorm (o.a. PlenairMap.vue's vaste
        # RawExport-type) blijft ongewijzigd wanneer dit ontbreekt.
        if p.get("cluster_levels") is not None:
            row.append(p["cluster_levels"])
        rows.append(row)

    export = {
        "topics": list(topics_lu),
        "actors": list(actors_lu),
        "parties": list(parties_lu),
        "debates": list(debates_lu),
        "soorten": list(soorten_lu),
        "points": rows,
        "dataset_version": dataset_version,
    }
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(json.dumps(export, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    size_mb = export_path.stat().st_size / 1024 / 1024
    logger.info("frontend-export geschreven naar %s (%.1f MiB)", export_path, size_mb)
    if size_mb > 25:
        logger.warning(
            "EXPORT BOVEN DE 25 MiB CLOUDFLARE WORKERS-ASSETLIMIET (%.1f MiB) -- "
            "build zal breken, verdere verkleining nodig", size_mb,
        )


def write_plot_html(points, out_path, title):
    """Interactieve scatter met ECharts (CDN, geen build-stap) -- zelfde
    chartlib als de rest van de site (frontend/package.json,
    TagCorrespondenceMap.vue), bewust niet Plotly of iets anders erbij: één
    technologie voor hetzelfde soort punt-cloud-visualisatie. Hover toont
    spreker/partij/tekstfragment per punt. Eén serie per topic, zodat de
    legenda per topic aan/uit te klikken is (handig om de 4 gecureerde
    topics visueel te isoleren binnen de bredere plenaire wolk)."""
    topics = sorted({p["topic"] for p in points})
    palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f"]
    series = []
    for i, topic in enumerate(topics):
        pts = [p for p in points if p["topic"] == topic]
        series.append({
            "name": f"{topic} (n={len(pts)})",
            "type": "scatter",
            "symbolSize": 5 if topic == "plenair" else 7,
            "large": True,
            "largeThreshold": 2000,
            "itemStyle": {"color": palette[i % len(palette)], "opacity": 0.6},
            "data": [
                {
                    "value": [p["x"], p["y"]],
                    "actor": p["actor"],
                    "party": p["party"],
                    "activiteit_soort": p["activiteit_soort"] or "",
                    "debate_title": p["debate_title"] or "",
                    "published_at": p["published_at"],
                    "text": p["text"],
                }
                for p in pts
            ],
        })

    option = {
        "title": {"text": title},
        "tooltip": {
            "trigger": "item",
            "formatter": "__TOOLTIP_FORMATTER__",
        },
        "legend": {"top": 30},
        "grid": {"top": 80},
        "xAxis": {"scale": True},
        "yAxis": {"scale": True},
        "series": series,
    }
    option_json = json.dumps(option, ensure_ascii=False)
    # ECharts tooltip.formatter kan geen JS-functie in JSON meesturen -- na
    # het serialiseren de placeholder vervangen door een echte functie die
    # bij een scatter-punt (params.data) de metadata opmaakt.
    formatter_js = (
        "function(params) {"
        "  const d = params.data;"
        "  return `${d.actor} (${d.party}) -- ${d.activiteit_soort} -- ${d.published_at}<br>"
        "<em>${d.debate_title}</em><br>${d.text}`;"
        "}"
    )
    option_json = option_json.replace('"__TOOLTIP_FORMATTER__"', formatter_js)

    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@6.1.0/dist/echarts.min.js"></script>
<style>body {{ font-family: sans-serif; margin: 0; }} #plot {{ width: 100vw; height: 100vh; }}</style>
</head><body>
<div id="plot"></div>
<script>
const chart = echarts.init(document.getElementById("plot"));
chart.setOption({option_json});
window.addEventListener("resize", () => chart.resize());
</script>
</body></html>"""
    out_path.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
