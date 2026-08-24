"""
Vervolg op experiment_umap_arguments.py (issue #156): past de 4 gecureerde
topics (stikstof, abortus, asiel, energietransitie) binnen de bredere
ruimte van álle plenaire Kamerdebatten uit dezelfde periode? Embedt
`documents.content` (ruwe sprekerbeurttekst) i.p.v. `arguments.quote_text`
-- er is bewust geen LLM-argumentextractie gedraaid voor de bredere,
topic-onafhankelijke dataset (te duur voor een onderzoekje, zie
pipeline.ingest.ingest_tk.ingest_plenair()).

Bron van de bredere dataset: documents met topic_id IS NULL, ingelezen via
`uv run python -m pipeline.ingest.ingest_tk --plenair-dir <naam>` uit een
`verslagen_periode`-crawl (crawlers/tweede_kamer/tweede_kamer/spiders/
verslagen_periode.py) -- topic-onafhankelijk, dus geen keyword-filter.
De 4 topics' eigen documenten (topic_id IS NOT NULL) worden er zonder
her-crawl bij gehaald, simpelweg via hetzelfde published_at-datumfilter.

Puur leesactie op de database. Output: coords+labels als JSON in
docs/poc/umap-documenten/, voor de losse Cosmograph-HTML-pagina
(index.html in dezelfde map) om interactief te bekijken -- zie die map's
eigen toelichting waarom hier bewust geen matplotlib-PNG (zoals
experiment_umap_arguments.py) of Plotly is gebruikt.

Gebruik:
    uv run python scripts/experiment_umap_documents.py \
        --start 2025-11-12 --end 2026-08-22 --label 2025-heden \
        --full-range-topics abortus
"""
import argparse
import json
import logging
import re
import time
from collections import Counter

import numpy as np
from scipy.spatial import ConvexHull
from sklearn.cluster import DBSCAN, HDBSCAN
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

from pipeline.db import db
from pipeline.paths import REPO_ROOT
from pipeline.tag_arguments import call_llm
from scripts.experiment_umap_arguments import DUTCH_STOPWORDS, detect_base_url, embed_texts, run_umap

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

OUTPUT_DIR = REPO_ROOT / "docs" / "poc" / "umap-documenten"
CACHE_DIR = REPO_ROOT / "data" / "embeddings"
EXPORT_PATH = REPO_ROOT / "data" / "export" / "plenair-map.json"
CLUSTERS_EXPORT_PATH = REPO_ROOT / "data" / "export" / "plenair-map-clusters.json"
HIERARCHY_EXPORT_PATH = REPO_ROOT / "data" / "export" / "plenair-map-hierarchy.json"
MODEL = "text-embedding-bge-m3"

# Procedureel, geen inhoudelijk debat -- puntenwolk-ruis, geen onderwerp om
# op te clusteren. Filter hier (niet bij het ingesten) zodat dit zonder
# her-crawl bij te stellen is.
NOISE_ACTIVITEIT_SOORTEN = ("Stemmingen", "Regeling van werkzaamheden", "Opening", "Mededelingen", "Beëdiging")


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


def build_hierarchical_clusters(coords, hdbscan_min_cluster_size, min_size_to_name):
    """Vervangt vaste coarse/fine HDBSCAN-drempels door een boomwandeling
    over de HDBSCAN condensed tree (zie notebooks/explore_plenary_umap_clusters.py
    en docs/hierarchische-clustering-plenaire-spreekbeurten.md voor de
    volledige uitleg/motivatie -- vaste drempels bleken op deze data telkens
    in te storten tot 1-3 dominante clusters, ook op de volledige dataset).

    Coarse-niveau: wandelt alleen de hoofdtak af (niet-recursief); bij elke
    splitsing waarvan de kleinste kant >= min_size_to_name is, wordt die kant
    een eigen coarse-domein (met zijn VOLLEDIGE, nog niet verder-gesplitste
    puntenverzameling); te kleine subtakken versmelten met de rest van de
    hoofdtak. Zodra de hoofdtak zelf geen zinnige splitsing meer heeft, wordt
    wat overblijft (incl. versmolten restjes) het laatste coarse-domein.

    Fine-niveau: binnen elk coarse-domein wordt dezelfde wandeling recursief
    toegepast (dus ook op al benoemde subtakken, die zelf weer kunnen
    splitsen -- bv. een subtak van 302 spreekbeurten bleek zelf in twee
    groepen van 144 en 147 te splitsen) tot er geen zinnige splitsing meer
    over is; dat laatste restje hoort dan bij hetzelfde coarse-domein.

    Geeft (coarse_ids, fine_ids) terug: twee even lange arrays (int, één
    label per punt in coords), analoog aan run_clustering()'s labels_.
    fine_ids nest altijd binnen coarse_ids (elk fine-cluster hoort bij precies
    één coarse-domein)."""
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

    def coarse_partition():
        current, branches, carried = root, [], []
        while True:
            entries = children_by_parent.get(current, [])
            real_children = [(ch, sz) for ch, sz in entries if sz > 1]
            qualifying = [(ch, sz) for ch, sz in real_children if sz >= min_size_to_name]
            carried.extend(ch for ch, sz in entries if sz == 1)
            for child, size in real_children:
                if size < min_size_to_name:
                    carried.extend(collect_points(child))
            if not qualifying:
                branches.append((current, carried, True))
                return branches
            qualifying.sort(key=lambda cs: cs[1])
            *smaller, (largest, _size) = qualifying
            for child, _size in smaller:
                branches.append((child, [], False))
            current = largest
            # let op: `carried` NIET resetten -- moet over de hele wandeling
            # blijven optellen, anders raken eerder opgevangen te-kleine
            # subtakken zoek zodra er weer een kwalificerende afsplitsing volgt.

    def fine_partition(node_id):
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
                leaves.extend(fine_partition(child))
            current = largest

    coarse_branches = coarse_partition()
    coarse_ids = np.full(n, -1, dtype=int)
    fine_ids = np.full(n, -1, dtype=int)
    fine_label = 0
    for coarse_label, (node_id, carried, is_terminal) in enumerate(coarse_branches):
        own_pts = [] if is_terminal else collect_points(node_id)
        coarse_ids[own_pts + carried] = coarse_label

        fine_leaves = fine_partition(node_id)
        if is_terminal and carried:
            # de te-kleine subtakken die tijdens de coarse-wandeling zijn
            # opgevangen horen bij hetzelfde "overgebleven" fine-cluster
            if fine_leaves:
                fine_leaves[-1] = fine_leaves[-1] + carried
            else:
                fine_leaves = [carried]
        for leaf_pts in fine_leaves:
            fine_ids[leaf_pts] = fine_label
            fine_label += 1

    logger.info(
        "boomwandeling: %d coarse-domeinen, %d fine-sub-onderwerpen (min_cluster_size=%d, min_size_to_name=%d)",
        len(coarse_branches), fine_label, hdbscan_min_cluster_size, min_size_to_name,
    )
    return coarse_ids, fine_ids


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
    texts, coords, coarse_ids, fine_ids, topic_labels, top_terms=6, extra_stopwords=None, max_df=0.25
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
        topic_counts = Counter(topic_labels[i] for i in member_idx)

        coarse_summaries[coarse_id] = {
            "cluster_id": int(coarse_id),
            "name": format_title_from_terms(kws),
            "terms": kws,
            "size": len(member_idx),
            "centroid": centroid,
            "hull": hull,
            "topic_breakdown": dict(topic_counts.most_common()),
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

        topic_counts = Counter(topic_labels[i] for i in member_idx)
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
            "topic_breakdown": dict(topic_counts.most_common()),
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
                "topic_breakdown": fine["topic_breakdown"],
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
            "topic_breakdown": coarse["topic_breakdown"],
            "children": children,
        })

    fine_list = sorted(fine_summaries.values(), key=lambda s: s["size"], reverse=True)
    return coarse_summaries, fine_list, tree


def _build_cluster_naming_prompt(tfidf_terms, example_texts, example_titles):
    terms_str = ", ".join(tfidf_terms) if tfidf_terms else "(geen trefwoorden gevonden)"
    titles_str = "\n".join(f"- {t}" for t in sorted(set(example_titles)) if t) or "(geen debattitels bekend)"
    examples_str = "\n\n".join(f'"{t[:400]}"' for t in example_texts)
    return f"""Je krijgt trefwoorden en voorbeeldfragmenten uit spreekbeurten uit
Tweede Kamerdebatten, allemaal uit hetzelfde cluster van een UMAP-kaart
(spreekbeurten die semantisch dicht bij elkaar liggen). Geef een korte,
inhoudelijke naam voor het onderwerp van dit cluster.

TF-IDF-trefwoorden: {terms_str}

Debattitels waarin deze spreekbeurten voorkwamen:
{titles_str}

Voorbeeldfragmenten:
{examples_str}

Antwoord in exact dit formaat, zonder verdere uitleg:
Naam: <2-4 woorden, het beleidsonderwerp>
Duiding: <één zin, wat dit cluster inhoudelijk samenbindt>"""


def _generate_llm_cluster_name(base_url, model, reasoning_effort, tfidf_terms, example_texts, example_titles):
    prompt = _build_cluster_naming_prompt(tfidf_terms, example_texts, example_titles)
    raw_content, _usage = call_llm(base_url, model, prompt, reasoning_effort=reasoning_effort, timeout=120)
    name, duiding = None, None
    for line in raw_content.splitlines():
        if line.lower().startswith("naam:"):
            name = line.split(":", 1)[1].strip()
        elif line.lower().startswith("duiding:"):
            duiding = line.split(":", 1)[1].strip()
    return name or raw_content.strip()[:60], duiding or ""


def label_clusters_with_llm(
    coarse_ids, fine_ids, coarse_summaries, fine_list, tree,
    texts, coords, rows, base_url, model, reasoning_effort, examples_per_cluster,
):
    """Vervangt de TF-IDF-naam van elk coarse- en fine-cluster (in-place) door
    een LLM-gegenereerde naam + duiding, op basis van representatieve
    spreekbeurten (dichtst bij het clustercentroïde) + debattitels. De
    TF-IDF-termen zelf blijven bewaard (`terms`-veld) voor een eventueel
    latere "cluster-detail"-weergave (issue vervolgen op #181), alleen
    `name` wordt overschreven. Werkt ook `tree` (voor plenair-map-hierarchy.json)
    en fine_list se `parent_name`-verwijzingen bij zodat alles consistent
    naar de nieuwe namen wijst."""
    def representative_examples(member_idx):
        centroid = coords[member_idx].mean(axis=0)
        dists = np.linalg.norm(coords[member_idx] - centroid, axis=1)
        closest = member_idx[np.argsort(dists)[:examples_per_cluster]]
        return [texts[i] for i in closest], [rows[i]["debate_title"] for i in closest]

    total = len(coarse_summaries) + len(fine_list)
    logger.info("LLM-naamgeving voor %d clusters (~%ds geschat, %.1fs/cluster live gemeten)", total, total * 7, 7.0)

    llm_names_by_coarse_id = {}
    for coarse_id, summary in coarse_summaries.items():
        member_idx = np.where(coarse_ids == coarse_id)[0]
        example_texts, example_titles = representative_examples(member_idx)
        name, duiding = _generate_llm_cluster_name(
            base_url, model, reasoning_effort, summary["terms"], example_texts, example_titles,
        )
        summary["name"] = name
        summary["duiding"] = duiding
        llm_names_by_coarse_id[coarse_id] = name
        logger.info("coarse-domein %d (n=%d): LLM-naam '%s' -- %s", coarse_id, summary["size"], name, duiding)

    for summary in fine_list:
        member_idx = np.where(fine_ids == summary["cluster_id"])[0]
        example_texts, example_titles = representative_examples(member_idx)
        name, duiding = _generate_llm_cluster_name(
            base_url, model, reasoning_effort, summary["terms"], example_texts, example_titles,
        )
        summary["name"] = name
        summary["duiding"] = duiding
        if summary["parent_id"] is not None:
            summary["parent_name"] = llm_names_by_coarse_id.get(summary["parent_id"], summary["parent_name"])
        logger.info("fine-sub-onderwerp %d (n=%d): LLM-naam '%s' -- %s", summary["cluster_id"], summary["size"], name, duiding)

    fine_by_id = {s["cluster_id"]: s for s in fine_list}
    for coarse_node in tree:
        coarse_node["name"] = llm_names_by_coarse_id.get(coarse_node["id"], coarse_node["name"])
        for child in coarse_node["children"]:
            fine_summary = fine_by_id.get(child["id"])
            if fine_summary is not None:
                child["name"] = fine_summary["name"]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", required=True, help="published_at ondergrens, ISO-datum (inclusief)")
    parser.add_argument("--end", required=True, help="published_at bovengrens, ISO-datum (exclusief)")
    parser.add_argument("--label", required=True, help="korte periode-naam voor bestandsnamen, bv. 2025-heden")
    parser.add_argument(
        "--full-range-topics", default="",
        help="komma-gescheiden topic-slugs die altijd volledig meegenomen worden, ongeacht "
        "--start/--end (bv. abortus: piekgedreven debatten i.p.v. doorlopend, zie issue #186 punt 3)",
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
        "tree waarover build_hierarchical_clusters() wandelt (zie die functie's docstring). "
        "Vervangt de vroegere aparte coarse(200)/fine(15)-drempels, die op deze data telkens "
        "instortten tot 1-3 dominante clusters -- zie docs/hierarchische-clustering-plenaire-spreekbeurten.md.",
    )
    parser.add_argument(
        "--cluster-min-size-to-name", type=int, default=200,
        help="hoeveel spreekbeurten een afgesplitste subtak minstens moet hebben om een eigen "
        "coarse/fine-cluster te worden tijdens de boomwandeling; kleinere subtakken versmelten "
        "met de rest. Live getest op een steekproef van ~40k punten: 200 -> 31 coarse/48 fine.",
    )
    parser.add_argument("--cluster-top-terms", type=int, default=8, help="aantal TF-IDF-termen per cluster-label")
    parser.add_argument(
        "--skip-llm-naming", action="store_true",
        help="LLM-naamgeving overslaan (TF-IDF-naam blijft dan staan) -- handig zonder LM Studio, "
        "of om snel alleen de clustering/hulls te controleren.",
    )
    parser.add_argument("--llm-chat-model", default="qwen/qwen3.6-27b", help="zelfde default als pipeline/tag_arguments.py --model")
    parser.add_argument(
        "--llm-reasoning-effort", default="none",
        help='"none" schakelt reasoning-tokens uit -- zonder deze parameter verstookt qwen3.6-27b '
        "het volledige max_tokens-budget van call_llm() aan een onzichtbare <think>-redenering en "
        "blijft er niets over voor het eigenlijke antwoord (live bevestigd, zie docs/handoff.md).",
    )
    parser.add_argument("--llm-examples-per-cluster", type=int, default=8, help="representatieve spreekbeurten per cluster in de LLM-naamgevingsprompt")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{MODEL}_plenair-{args.label}.npz"

    full_range_topic_slugs = [s.strip() for s in args.full_range_topics.split(",") if s.strip()]

    conn = db.connect()
    rows = fetch_documents(conn, args.start, args.end, args.min_content_len, full_range_topic_slugs)
    db_stopwords = fetch_actor_and_party_stopwords(conn)
    conn.close()
    if not rows:
        raise SystemExit(f"geen documenten gevonden tussen {args.start} en {args.end}")

    # min_content_len in de SQL (fetch_documents) filtert op de RUWE content
    # -- inclusief het sprekersprefix dat hier pas wordt gestript. Een beurt
    # als "Kamerlid Kostić (PvdD): Dank u wel." haalt zo ruim de 30 tekens,
    # maar houdt na het strippen alleen "Dank u wel." over: te weinig om
    # zinnig op te embedden, en precies dit soort bijna-lege beurten bleek
    # als uitschieter te embedden (issue #156, live bevestigd). Daarom hier
    # nogmaals filteren, nu op de gestripte tekst.
    stripped = [strip_speaker_prefix(r["content"], r["actor_name"]) for r in rows]
    keep = [i for i, t in enumerate(stripped) if len(t) >= args.min_content_len]
    dropped = len(rows) - len(keep)
    if dropped:
        logger.info(
            "%d van %d beurten alsnog te kort na het strippen van het sprekersprefix (< %d tekens), overgeslagen",
            dropped, len(rows), args.min_content_len,
        )
    rows = [rows[i] for i in keep]
    texts = [stripped[i] for i in keep]

    topic_labels = [r["topic_slug"] or "plenair" for r in rows]
    logger.info(
        "%d documenten tussen %s en %s (%d binnen de 4 topics, %d overig plenair)",
        len(texts), args.start, args.end,
        sum(1 for l in topic_labels if l != "plenair"),
        sum(1 for l in topic_labels if l == "plenair"),
    )

    current_ids = [r["id"] for r in rows]
    cached_vectors = None
    if not args.refresh and cache_path.exists():
        data = np.load(cache_path, allow_pickle=True)
        cached_id_list = list(data["ids"])
        if cached_id_list == current_ids:
            cached_vectors = data["vectors"]
            logger.info("embeddings-cache geladen: %s (exacte match, %d vectoren)", cache_path, len(cached_vectors))
        else:
            cached_id_set = set(cached_id_list)
            missing = set(current_ids) - cached_id_set
            if not missing:
                id_to_idx = {doc_id: idx for idx, doc_id in enumerate(cached_id_list)}
                indices = [id_to_idx[doc_id] for doc_id in current_ids]
                cached_vectors = data["vectors"][indices]
                logger.info("embeddings-cache geladen via ID-subset: %s (%d/%d vectoren)", cache_path, len(cached_vectors), len(cached_id_list))
            else:
                logger.warning(
                    "embeddings-cache %s mist %d van de %d gevraagde document-ids -- cache genegeerd, opnieuw embedden",
                    cache_path, len(missing), len(current_ids),
                )

    if cached_vectors is not None:
        vectors = cached_vectors
        embed_elapsed = None
    else:
        base_url = detect_base_url(args.base_url)
        t0 = time.monotonic()
        vectors = embed_texts(base_url, texts, MODEL)
        embed_elapsed = time.monotonic() - t0
        logger.info("embeddings opgehaald in %.1fs (%s, model=%s)", embed_elapsed, base_url, MODEL)
        np.savez(cache_path, vectors=vectors, ids=current_ids)

    t0 = time.monotonic()
    coords = run_umap(vectors)
    umap_elapsed = time.monotonic() - t0
    logger.info("UMAP in %.1fs", umap_elapsed)

    alpino_stopwords = fetch_alpino_non_content_stopwords()
    all_stopwords = (
        set(DUTCH_STOPWORDS)
        | DUTCH_PRONOUNS_AND_NUMERALS
        | PARTY_ALIASES_AND_ABBREVIATIONS
        | PARLIAMENTARY_INSTITUTIONAL
        | db_stopwords
        | alpino_stopwords
    )

    cluster_ids, cluster_summaries, hierarchy = None, None, None
    if not args.skip_clustering:
        if args.cluster_method == "hdbscan":
            coarse_ids, fine_ids = build_hierarchical_clusters(
                coords, args.hdbscan_min_cluster_size, args.cluster_min_size_to_name,
            )
            coarse_summaries, fine_summaries, hierarchy = label_hierarchical_clusters(
                texts,
                coords,
                coarse_ids,
                fine_ids,
                topic_labels,
                top_terms=args.cluster_top_terms,
                extra_stopwords=all_stopwords,
                max_df=0.25,
            )

            if not args.skip_llm_naming:
                llm_base_url = detect_base_url(args.base_url)
                label_clusters_with_llm(
                    coarse_ids, fine_ids, coarse_summaries, fine_summaries, hierarchy,
                    texts, coords, rows, llm_base_url, args.llm_chat_model,
                    args.llm_reasoning_effort, args.llm_examples_per_cluster,
                )

            cluster_ids = fine_ids
            cluster_summaries = {
                "coarse": list(coarse_summaries.values()),
                "fine": fine_summaries,
            }

            for coarse in hierarchy:
                logger.info("Domein '%s' (n=%d, %d sub-onderwerpen):", coarse["name"], coarse["value"], len(coarse["children"]))
                for child in coarse["children"][:5]:
                    terms_str = ", ".join(child["terms"][:4])
                    logger.info("  └─ %s (n=%d) [%s]", child["name"], child["value"], terms_str)
        else:
            fine_ids = run_clustering(coords, "dbscan", args.dbscan_eps, args.dbscan_min_samples, None)
            coarse_summaries, fine_summaries, hierarchy = label_hierarchical_clusters(
                texts,
                coords,
                fine_ids,
                fine_ids,
                topic_labels,
                top_terms=args.cluster_top_terms,
                extra_stopwords=all_stopwords,
                max_df=0.25,
            )
            cluster_ids = fine_ids
            cluster_summaries = {
                "coarse": list(coarse_summaries.values()),
                "fine": fine_summaries,
            }

    points = []
    for i, (row, (x, y), topic_label) in enumerate(zip(rows, coords, topic_labels)):
        points.append({
            "id": row["id"],
            "x": float(x),
            "y": float(y),
            "topic": topic_label,
            "text": texts[i][:160],
            "actor": row["actor_name"],
            "party": row["party"] or "onbekend",
            "activiteit_soort": row["activiteit_soort"],
            "debate_title": row["debate_title"],
            "published_at": row["published_at"],
            "cluster": int(cluster_ids[i]) if cluster_ids is not None else None,
        })

    if cluster_summaries is not None:
        clusters_path = OUTPUT_DIR / f"clusters-{args.label}.json"
        clusters_path.write_text(json.dumps(cluster_summaries, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("%d cluster-labels geschreven naar %s", len(cluster_summaries), clusters_path)
        if args.export_frontend:
            CLUSTERS_EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
            CLUSTERS_EXPORT_PATH.write_text(json.dumps(cluster_summaries, ensure_ascii=False), encoding="utf-8")

    if hierarchy is not None:
        hierarchy_path = OUTPUT_DIR / f"hierarchy-{args.label}.json"
        hierarchy_path.write_text(json.dumps(hierarchy, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("hiërarchie (%d grove clusters) geschreven naar %s", len(hierarchy), hierarchy_path)
        if args.export_frontend:
            HIERARCHY_EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
            HIERARCHY_EXPORT_PATH.write_text(json.dumps(hierarchy, ensure_ascii=False), encoding="utf-8")

    html_path = OUTPUT_DIR / f"plot-{args.label}.html"
    write_plot_html(points, html_path, title=f"UMAP (bge-m3) -- alle plenaire debatten, {args.label}")
    logger.info("%d punten geschreven naar %s", len(points), html_path)
    if embed_elapsed is not None:
        logger.info(
            "timing: embeddings %.1fs, UMAP %.1fs, totaal %.1fs",
            embed_elapsed, umap_elapsed, embed_elapsed + umap_elapsed,
        )

    if args.export_frontend:
        write_frontend_export(points)


# Cloudflare Workers staat max. 25 MiB per asset toe (zie ook
# frontend/src/pages/tags/[sleutel].astro se geschiedenis, commit 350491c --
# zelfde probleem, andere pagina). Bij ~99k punten kwam het naieve
# array-of-objects-formaat op ~42 MiB uit: (a) elke veldnaam
# ("activiteit_soort", "debate_title", ...) wordt letterlijk herhaald per
# punt in JSON, en (b) actor/partij/debattitel/activiteit_soort/topic
# herhalen zich massaal (honderden-duizenden beurten uit dezelfde ~200
# debatten van dezelfde ~150 sprekers). Lookup-tabellen + een compacte
# array per punt (geen veldnamen, geen herhaalde strings) lost beide op.
def write_frontend_export(points):
    xs = sorted(p["x"] for p in points)
    ys = sorted(p["y"] for p in points)
    n = len(xs)
    # Uitschieters (bv. "Voorzitter." -- na het strippen van de
    # sprekersprefix nauwelijks nog tekst over om zinnig op te embedden)
    # trekken de as-schaal helemaal open en persen de rest van de wolk in een
    # hoekje. Buiten het 0.5-99.5-percentielbereik: niet getoond, niet
    # geëxporteerd (scheelt ook weer wat bestandsgrootte).
    x_lo, x_hi = xs[int(n * 0.005)], xs[int(n * 0.995)]
    y_lo, y_hi = ys[int(n * 0.005)], ys[int(n * 0.995)]
    kept = [p for p in points if x_lo <= p["x"] <= x_hi and y_lo <= p["y"] <= y_hi]
    logger.info("%d/%d punten binnen 0.5-99.5 percentiel gehouden voor frontend-export", len(kept), n)

    topics_lu, actors_lu, parties_lu, debates_lu, soorten_lu = {}, {}, {}, {}, {}

    def idx(lookup, value):
        if value not in lookup:
            lookup[value] = len(lookup)
        return lookup[value]

    rows = []
    for p in kept:
        rows.append([
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
        ])

    export = {
        "topics": list(topics_lu),
        "actors": list(actors_lu),
        "parties": list(parties_lu),
        "debates": list(debates_lu),
        "soorten": list(soorten_lu),
        "points": rows,
    }
    EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXPORT_PATH.write_text(json.dumps(export, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    size_mb = EXPORT_PATH.stat().st_size / 1024 / 1024
    logger.info("frontend-export geschreven naar %s (%.1f MiB)", EXPORT_PATH, size_mb)
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
