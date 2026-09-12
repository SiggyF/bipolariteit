#!/usr/bin/env python
# coding: utf-8

# In[18]:


"""
Startpunt voor issue #181 (clusterpositionering & clusterlabels): data en
een voorbeeldanalyse klaargezet voor een senior onderzoeker, zodat die zelf
verder kan experimenteren zonder eerst de hele pipeline te hoeven doorgronden.

In het kort: haalt een steekproef spreekbeurten op, embedt + UMAP't ze, en
clustert ze hiërarchisch door zelf de HDBSCAN-condensed-tree top-down af te
wandelen (in plaats van één vaste clusterdrempel, die op deze data telkens
instort tot 1-3 dominante clusters -- zie hieronder). Elk gevonden cluster
krijgt TF-IDF-trefwoorden en een LLM-gegenereerde naam. Voor de volledige
uitleg (waarom deze aanpak, hoe de drempel het aantal clusters bepaalt,
kosten van de LLM-naamgeving, bekende beperkingen) zie
docs/hierarchische-clustering-plenaire-spreekbeurten.md.

Wat dit script doet, in volgorde:
  1. Een steekproef spreekbeurten (`documents`) uit de database halen.
  2. De bijbehorende bge-m3-embeddings laden -- bij voorkeur uit de bestaande
     cache (`data/embeddings/text-embedding-bge-m3_plenair-combined/`,
     ~98.9k spreekbeurten, geproduceerd door
     pipeline/plenary_map/cluster.py), zodat je zonder LM Studio te
     starten meteen kunt experimenteren. Ontbrekende ids worden zo nodig
     alsnog live geëmbed.
  3. UMAP op die steekproef draaien -> 2D-coördinaten.
  4. HDBSCAN-clustering op de UMAP-coördinaten.
  5. Per cluster twee soorten labels genereren, naast elkaar:
     a) TF-IDF-trefwoorden (de bestaande aanpak, zie issue #181 punt 2 --
        "vaak nog suboptimaal").
     b) Een LLM-gegenereerde clusternaam + korte duiding, op basis van de
        top-termen en een handvol representatieve spreekbeurten. Dit is het
        `LLM-gebaseerde cluster-samenvatting`-idee uit de issue, hier als
        werkend voorbeeld i.p.v. alleen als voorstel.
  6. Eén tabel (pandas DataFrame) met beide labelsoorten naast elkaar, zodat
     je ze visueel kunt vergelijken.

Waarom een los script i.p.v. rechtstreeks pipeline/plenary_map/cluster.py
aanpassen: dat script draait de volle ~99k-punten-dataset en schrijft naar de
productie-export (data/export/plenair-map*.json, frontend-input). Dit script
hergebruikt zijn kernfuncties (fetch_documents, strip_speaker_prefix,
run_clustering, label_multilevel_clusters, ...) maar werkt op een kleine,
snel te herhalen steekproef en schrijft nergens naar productie-output.

Let op -- een steekproef geeft grovere clusters dan de volle dataset: een
kleine steekproef van een paar duizend spreekbeurten uit de ~99k is ruwweg
30x ijler verspreid over de UMAP-kaart dan de volle dataset. Vaste HDBSCAN-
drempels (zowel één vlakke drempel als een vaste coarse/fine-tweedeling,
beide ook geprobeerd) blijken hier niet te werken: op elke schaal die is
uitgeprobeerd trekt HDBSCAN's "eom"-selectie het grootste deel van de
punten in één dominante klomp (live geverifieerd, zowel op een steekproef
van 3000 als op de volle periode van 39.630 punten).

Stap 4 wandelt daarom zelf de volledige HDBSCAN-hiërarchie (de condensed
tree) top-down af: één hoofdtak splitst geleidelijk kleinere subtakken af.
Bij elke splitsing krijgt de kleinste subtak een eigen naam -- áls hij groot
genoeg is (>= CLUSTER_MIN_SIZE_TO_NAME, anders versmelt hij met de rest) --
en wordt zelf ook weer op dezelfde manier verder doorzocht op interne
sub-splitsingen (bv. een al afgesplitste kleinere categorie die zelf later
in twee sub-categorieën uiteenvalt -- live bevestigd op deze data: een
afgesplitste groep van 302 spreekbeurten bleek zelf weer in twee groepen
van 144 en 147 te splitsen). Zo ontstaat een echte, meerlagige hiërarchie
i.p.v. een platte lijst clusters. Zie build_cluster_tree() hieronder. Stap 4
tekent ook de condensed tree van de clusterer zodat je die hiërarchie zelf
kunt inspecteren.

Vereisten:
  - De database moet aanwezig zijn (data/bipolariteit.db) -- staat er al.
  - Voor stap 5b (LLM-clusternamen) moet een lokale LM Studio-server draaien
    met een chat-model geladen (zie scripts/detect_llm_base_url.sh). Zonder
    LM Studio lukken stappen 1-4 en 5a gewoon; stap 5b geeft dan een
    duidelijke foutmelding i.p.v. stil te falen.

Gebruik:
    uv run python notebooks/explore_plenary_umap_clusters.py
`pipeline`/`scripts` zijn overal importeerbaar (ongeacht cwd) omdat het
project via `uv sync` editable is geïnstalleerd (zie
`[build-system]`/`[tool.hatch.build.targets.wheel]` in pyproject.toml) --
geen `PYTHONPATH=.` meer nodig.

Dit bestand is met `jupyter nbconvert --to script` gegenereerd uit
explore_plenary_umap_clusters.ipynb (die het notebook, met de laatst
gedraaide output, blijft bewaren). Dit `.py`-bestand is nu de actieve
werkkopie -- wijzigingen hier gaan niet automatisch terug het notebook in.

Kleinere/grotere steekproef, ander tijdvak, ander aantal clusters: pas de
CONFIG-constanten hieronder aan.
"""


# In[19]:


import logging
import random

import hdbscan
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pipeline.db import db
from pipeline.embed.documents import load_embedding_cache
from pipeline.tag_arguments import call_llm
from scripts.experiment_umap_arguments import detect_base_url, embed_texts, run_umap
from pipeline.plenary_map.cluster import (
    CACHE_DIR,
    DUTCH_PRONOUNS_AND_NUMERALS,
    MODEL,
    PARLIAMENTARY_INSTITUTIONAL,
    PARTY_ALIASES_AND_ABBREVIATIONS,
    DUTCH_STOPWORDS,
    fetch_actor_and_party_stopwords,
    fetch_alpino_non_content_stopwords,
    fetch_documents,
    label_multilevel_clusters,
    strip_speaker_prefix,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Tijdvak: zelfde brede plenaire dataset als pipeline/plenary_map/cluster.py
# (zie dat script's docstring voor hoe die data is geïngest).
START_DATE = "2025-11-12"
END_DATE = "2026-08-22"

SAMPLE_SIZE = 50_000  # aantal spreekbeurten in de steekproef; hoger = representatiever, trager (42.473 beschikbaar in START_DATE-END_DATE, dus dit pakt de volledige periode)
RANDOM_SEED = 42  # voor reproduceerbare steekproef en UMAP-uitkomst
MIN_CONTENT_LEN = 30

# Clustering op de steekproef: geen vaste coarse/fine-tweedeling (ook
# geprobeerd -- HDBSCAN_MIN_CLUSTER_SIZE_COARSE=200/FINE=15, zoals
# pipeline/plenary_map/cluster.py -- maar op deze schaal (~40k punten)
# collapst coarse=200 zelf ook weer naar één dominant domein van 94% van de
# punten, live gemeten). In plaats daarvan: wandel de volledige HDBSCAN-
# hiërarchie (de condensed tree) top-down af. Die boom is één lange
# "hoofdtak" die geleidelijk kleinere zijtakken afsplitst (live gezien in de
# condensed-tree-plot). Bij elke splitsing krijgt de kleinste van de twee
# subclusters een naam -- als hij groot genoeg is (>= CLUSTER_MIN_SIZE_TO_NAME,
# anders versmelt hij met "overig") -- en gaan we verder de grootste
# (nog ongesplitste) tak in. Zo blijft er één "overig"-groep over die pas
# aan het eind (waar de hoofdtak zelf geen zinnige verdere splitsing meer
# heeft) een eigen naam krijgt. Zie walk_and_assign_clusters() hieronder.
HDBSCAN_MIN_CLUSTER_SIZE = 15  # granulariteit van de onderliggende boom
CLUSTER_MIN_SIZE_TO_NAME = 200  # live getest: geeft ~48 genoemde clusters op 39.630 punten
CLUSTER_TOP_TERMS = 8

# Voorbeeld-spreekbeurten per cluster om aan de LLM te geven voor de
# clusternaam -- niet te veel (prompt-lengte/snelheid), wel genoeg voor
# context (issue #181: "top centrale spreekbeurten en debattitels"). Alleen
# de genoemde clusters krijgen een LLM-naam ("overig" niet) -- op deze
# schaal zijn dat er tientallen i.p.v. honderden, en een losse LLM-call
# kost ~7s (live gemeten), dus honderden
# clusters langsgaan zou tientallen minuten kosten voor weinig extra
# inzicht.
LLM_EXAMPLES_PER_CLUSTER = 8
LLM_CHAT_MODEL = "qwen/qwen3.6-27b"  # zelfde default als pipeline/tag_arguments.py --model
# "none" schakelt reasoning-tokens uit -- zonder deze parameter verstookt
# qwen3.6-27b het volledige max_tokens-budget van call_llm() (1000, hardcoded
# in pipeline/tag_arguments.py) aan een onzichtbare "<think>"-redenering en
# blijft er niets over voor het eigenlijke Naam:/Duiding:-antwoord (live
# bevestigd: lege content, 677 reasoning_tokens op een simpel testprompt).
# Zie docs/handoff.md ("Belangrijke ontdekking: reasoning_effort") voor de
# volledige toelichting.
LLM_REASONING_EFFORT = "none"

# Bestaande volledige embeddingcache (pipeline/plenary_map/cluster.py
# --label combined) -- als de steekproef-ids hierin zitten, is embedden
# overbodig. Val terug op live embedden voor wat ontbreekt.
FULL_CACHE_PATH = CACHE_DIR / f"{MODEL}_plenair-combined"


# In[20]:


conn = db.connect()
rows = fetch_documents(conn, START_DATE, END_DATE, MIN_CONTENT_LEN)
db_stopwords = fetch_actor_and_party_stopwords(conn)
conn.close()
logger.info("%d spreekbeurten gevonden tussen %s en %s", len(rows), START_DATE, END_DATE)

random.seed(RANDOM_SEED)
sample_rows = random.sample(rows, min(SAMPLE_SIZE, len(rows)))
sample_rows.sort(key=lambda r: r["id"])  # deterministische volgorde, onafhankelijk van de sample-trekking
logger.info("steekproef: %d spreekbeurten", len(sample_rows))

# Sprekersprefix eraf (issue #156: anders clustert het model deels op wie
# iets zei i.p.v. waar het over ging) en nogmaals filteren op lengte, zie
# pipeline/plenary_map/cluster.py::main() voor de toelichting.
stripped = [strip_speaker_prefix(r["content"], r["actor_name"]) for r in sample_rows]
keep = [i for i, t in enumerate(stripped) if len(t) >= MIN_CONTENT_LEN]
sample_rows = [sample_rows[i] for i in keep]
texts = [stripped[i] for i in keep]
logger.info("%d spreekbeurten over na het strippen van het sprekersprefix", len(texts))


# In[21]:


texts[:5]


# In[22]:


def load_embeddings_for_sample(ids, texts):
    """Probeert embeddings uit de bestaande volledige cache te hergebruiken
    (ID-subset lookup, zie pipeline/plenary_map/cluster.py::main() voor
    het origineel van dit patroon); embedt live wat ontbreekt."""
    id_to_vector = load_embedding_cache(FULL_CACHE_PATH)
    if id_to_vector:
        logger.info(
            "volledige embeddingcache geladen: %s (%d vectoren beschikbaar)",
            FULL_CACHE_PATH, len(id_to_vector),
        )

    missing_idx = [i for i, doc_id in enumerate(ids) if doc_id not in id_to_vector]
    if missing_idx:
        logger.info("%d/%d steekproef-ids niet in de cache -- live embedden via LM Studio", len(missing_idx), len(ids))
        base_url = detect_base_url(None)
        missing_texts = [texts[i] for i in missing_idx]
        missing_vectors = embed_texts(base_url, missing_texts, MODEL)
        for i, vec in zip(missing_idx, missing_vectors):
            id_to_vector[ids[i]] = vec
    else:
        logger.info("alle steekproef-ids gevonden in de cache -- geen LM Studio nodig voor embeddings")

    return np.array([id_to_vector[doc_id] for doc_id in ids])


sample_ids = [r["id"] for r in sample_rows]
vectors = load_embeddings_for_sample(sample_ids, texts)


# In[23]:


vectors[0]


# In[24]:


coords = run_umap(vectors, seed=RANDOM_SEED)
logger.info("UMAP klaar: %s", coords.shape)


# In[25]:


clusterer = hdbscan.HDBSCAN(min_cluster_size=HDBSCAN_MIN_CLUSTER_SIZE).fit(coords)

# De condensed tree als parent/child-tabel: child_size==1 rijen zijn losse
# puntindices die als ruis uit `parent` vallen; child_size>1 rijen zijn
# echte sub-cluster-splitsingen (child is dan een nieuwe interne node-id,
# vanaf len(coords) omhoog).
full_tree = clusterer.condensed_tree_.to_pandas()
children_by_parent = {}
for parent, child, size in zip(full_tree["parent"], full_tree["child"], full_tree["child_size"]):
    children_by_parent.setdefault(int(parent), []).append((int(child), int(size)))


def collect_points(node_id):
    """Alle onderliggende puntindices onder node_id (recursief, incl. ruis-drops)."""
    if node_id < len(coords):
        return [node_id]
    points = []
    for child, size in children_by_parent.get(node_id, []):
        points.extend([child] if size == 1 else collect_points(child))
    return points


def build_cluster_tree(node_id, min_size_to_name, depth=0, parent_id=None):
    """Wandelt de hoofdtak vanaf node_id top-down af. Bij elke splitsing
    waarvan de kleinste subtak >= min_size_to_name is, krijgt die subtak een
    eigen naam -- en wordt zelf ook weer op dezelfde manier doorzocht op
    verdere interne splitsingen (bv. een al afgesplitste kleinere categorie
    die zelf later in tweeën valt). Subtakken die te klein zijn versmelten
    met de rest. Zodra de huidige hoofdtak zelf geen splitsing meer heeft
    waarvan de kleinste kant groot genoeg is, wordt wat daar nog van over is
    (incl. de versmolten te-kleine subtakken) zelf ook één (eind)cluster.
    Geeft een platte lijst leaf-clusters terug: dicts met points, depth,
    parent_id."""
    current, leaves, merged_points = node_id, [], []
    while True:
        entries = children_by_parent.get(current, [])
        real_children = [(ch, sz) for ch, sz in entries if sz > 1]
        qualifying = [(ch, sz) for ch, sz in real_children if sz >= min_size_to_name]
        merged_points.extend(ch for ch, sz in entries if sz == 1)  # losse ruis-drops
        for child, size in real_children:
            if size < min_size_to_name:
                merged_points.extend(collect_points(child))
        if not qualifying:
            leaves.append({"points": merged_points, "depth": depth, "parent_id": parent_id})
            return leaves
        qualifying.sort(key=lambda cs: cs[1])
        *smaller, (largest, _largest_size) = qualifying
        for child, _size in smaller:
            leaves.extend(build_cluster_tree(child, min_size_to_name, depth=depth + 1, parent_id=current))
        current = largest


root_node = int(full_tree["parent"].min())
leaf_clusters = build_cluster_tree(root_node, CLUSTER_MIN_SIZE_TO_NAME)
# grootste eerst -- puur voor leesbaarheid in de latere overview/logging
leaf_clusters.sort(key=lambda leaf: len(leaf["points"]), reverse=True)

cluster_ids = np.full(len(coords), -1, dtype=int)
for label, leaf in enumerate(leaf_clusters):
    cluster_ids[leaf["points"]] = label
    leaf["label"] = label

assert (cluster_ids != -1).all(), "niet elk punt aan een leaf-cluster toegewezen"
n_clusters = len(leaf_clusters)
depths = [leaf["depth"] for leaf in leaf_clusters]
logger.info(
    "boomwandeling: %d clusters (min_size_to_name=%d), dieptebereik %d-%d",
    n_clusters, CLUSTER_MIN_SIZE_TO_NAME, min(depths), max(depths),
)

# Condensed tree van de volledige clusterer -- laat zien welke splitsingen
# de wandeling wel/niet als apart cluster benoemt.
try:
    fig, ax = plt.subplots(figsize=(12, 6))
    clusterer.condensed_tree_.plot(select_clusters=True, axis=ax)
    ax.set_title(f"HDBSCAN condensed tree (min_cluster_size={HDBSCAN_MIN_CLUSTER_SIZE})")
    fig.tight_layout()
    CONDENSED_TREE_PATH = "notebooks/explore_plenary_umap_clusters_condensed_tree.png"
    fig.savefig(CONDENSED_TREE_PATH, dpi=150)
    logger.info("condensed tree opgeslagen als %s", CONDENSED_TREE_PATH)
except Exception:
    logger.warning("condensed tree kon niet getekend worden (te veel clusters?) -- overgeslagen", exc_info=True)


# In[26]:


coords[0]


# In[27]:


alpino_stopwords = fetch_alpino_non_content_stopwords()
all_stopwords = (
    set(DUTCH_STOPWORDS)
    | DUTCH_PRONOUNS_AND_NUMERALS
    | PARTY_ALIASES_AND_ABBREVIATIONS
    | PARLIAMENTARY_INSTITUTIONAL
    | db_stopwords
    | alpino_stopwords
)
# Eén schaalniveau (de genoemde clusters uit de boomwandeling hierboven):
# een lijst van precies 1 level_ids-array geeft platte (niet-hiërarchische)
# TF-IDF-labels terug (issue #281: build_hierarchical_clusters/
# label_hierarchical_clusters zijn uitgefaseerd in pipeline/plenary_map/cluster.py,
# label_multilevel_clusters is nu het enige clusteringpad). Geen topic_labels
# meer (issue #288: topic is geen eigenschap van de embed-/clusterworkflow).
level_lists, _ = label_multilevel_clusters(
    texts, coords, [cluster_ids],
    top_terms=CLUSTER_TOP_TERMS, extra_stopwords=all_stopwords,
)
cluster_summaries = level_lists[0]
tfidf_terms_by_cluster = {s["cluster_id"]: s["terms"] for s in cluster_summaries}


# In[28]:


def build_cluster_naming_prompt(tfidf_terms, example_texts, example_titles):
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


def generate_llm_cluster_name(base_url, model, tfidf_terms, example_texts, example_titles):
    prompt = build_cluster_naming_prompt(tfidf_terms, example_texts, example_titles)
    raw_content, _usage = call_llm(base_url, model, prompt, reasoning_effort=LLM_REASONING_EFFORT, timeout=120)
    name, duiding = None, None
    for line in raw_content.splitlines():
        if line.lower().startswith("naam:"):
            name = line.split(":", 1)[1].strip()
        elif line.lower().startswith("duiding:"):
            duiding = line.split(":", 1)[1].strip()
    return name or raw_content.strip()[:60], duiding or ""


llm_base_url = detect_base_url(None)
llm_results = {}
for cluster_id in sorted(set(cluster_ids) - {-1}):
    member_idx = np.where(cluster_ids == cluster_id)[0]
    # Representatieve punten: dichtst bij het clustercentroïde in de
    # UMAP-ruimte, zelfde idee als rank_hull_anchored_terms() in
    # pipeline/plenary_map/cluster.py maar dan voor tekstvoorbeelden
    # i.p.v. TF-IDF-termen.
    centroid = coords[member_idx].mean(axis=0)
    dists = np.linalg.norm(coords[member_idx] - centroid, axis=1)
    closest = member_idx[np.argsort(dists)[:LLM_EXAMPLES_PER_CLUSTER]]

    example_texts = [texts[i] for i in closest]
    example_titles = [sample_rows[i]["debate_title"] for i in closest]
    name, duiding = generate_llm_cluster_name(
        llm_base_url, LLM_CHAT_MODEL, tfidf_terms_by_cluster.get(cluster_id, []), example_texts, example_titles,
    )
    llm_results[cluster_id] = {"llm_naam": name, "llm_duiding": duiding}
    logger.info("domein %d (n=%d): LLM-naam '%s' -- %s", cluster_id, len(member_idx), name, duiding)


# In[29]:


depth_by_cluster = {leaf["label"]: leaf["depth"] for leaf in leaf_clusters}

overview_rows = []
for cluster_id in sorted(set(cluster_ids) - {-1}):
    member_idx = np.where(cluster_ids == cluster_id)[0]
    overview_rows.append({
        "cluster_id": cluster_id,
        "diepte": depth_by_cluster[cluster_id],
        "n_spreekbeurten": len(member_idx),
        "tfidf_termen": ", ".join(tfidf_terms_by_cluster.get(cluster_id, [])),
        "llm_naam": llm_results[cluster_id]["llm_naam"],
        "llm_duiding": llm_results[cluster_id]["llm_duiding"],
    })

if not overview_rows:
    logger.warning(
        "geen clusters gevonden (alles ruis) -- steekproef vergroten (SAMPLE_SIZE) of "
        "HDBSCAN_MIN_CLUSTER_SIZE verlagen"
    )
clusters_overview = pd.DataFrame(overview_rows, columns=["cluster_id", "diepte", "n_spreekbeurten", "tfidf_termen", "llm_naam", "llm_duiding"])
# hiërarchisch gesorteerd: diepte 0 (direct van de hoofdtak afgesplitst)
# eerst, dieper-geneste (bv. een al afgesplitste categorie die zelf verder
# splitst) daaronder, binnen elke diepte groter eerst.
clusters_overview = clusters_overview.sort_values(["diepte", "n_spreekbeurten"], ascending=[True, False]).reset_index(drop=True)
print(clusters_overview.to_string(index=False))

# Losse DataFrame met alle steekproefpunten (id, coördinaten, cluster,
# metadata) -- handig startpunt voor verdere analyse in een echte notebook
# (bv. spreekbeurten per cluster opzoeken, of clustergrenzen visueel
# inspecteren met scatterplots).
points_overview = pd.DataFrame({
    "id": sample_ids,
    "x": coords[:, 0],
    "y": coords[:, 1],
    "cluster": cluster_ids,
    "actor": [r["actor_name"] for r in sample_rows],
    "party": [r["party"] for r in sample_rows],
    "debate_title": [r["debate_title"] for r in sample_rows],
    "published_at": [r["published_at"] for r in sample_rows],
    "text": texts,
})
logger.info("points_overview: %d rijen, klaar voor verdere analyse", len(points_overview))


# In[30]:


# Scatterplot van de UMAP-clusterkaart: ruis (-1) in lichtgrijs op de
# achtergrond, elk echt cluster in een eigen kleur met de LLM-naam in de
# legenda -- snel visueel beeld van waar de clusters liggen en hoe
# uitgesproken (of juist diffuus) hun grenzen zijn.
fig, ax = plt.subplots(figsize=(9, 7))
cmap = plt.get_cmap("tab10")

noise_mask = cluster_ids == -1
if noise_mask.any():
    ax.scatter(coords[noise_mask, 0], coords[noise_mask, 1], s=6, color="lightgrey", alpha=0.5, label=f"ruis (n={noise_mask.sum()})")

for i, cluster_id in enumerate(sorted(set(cluster_ids) - {-1})):
    mask = cluster_ids == cluster_id
    naam = llm_results.get(cluster_id, {}).get("llm_naam") or f"cluster {cluster_id}"
    ax.scatter(coords[mask, 0], coords[mask, 1], s=8, alpha=0.7, color=cmap(i % 10), label=f"{naam} (n={mask.sum()})")

ax.set_title(f"UMAP-clustermap (steekproef, n={len(coords)})")
ax.set_xlabel("UMAP-dimensie 1")
ax.set_ylabel("UMAP-dimensie 2")
ax.legend(markerscale=2, fontsize=8, loc="best")
fig.tight_layout()

# Zonder notebook (geen inline display) toont plt.show() niets als het
# script via `uv run python ...` op de command line draait -- er is geen
# GUI-backend. Wegschrijven naar een bestand zodat je hem kunt openen.
PLOT_PATH = "notebooks/explore_plenary_umap_clusters.png"
fig.savefig(PLOT_PATH, dpi=150)
logger.info("clustermap opgeslagen als %s", PLOT_PATH)

