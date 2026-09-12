"""
LLM-naamgeving voor UMAP-clusters (uitgelicht uit pipeline/plenary_map/cluster.py,
zodat cluster.py de UMAP/HDBSCAN-berekening blijft en dit bestand puur de LLM-
aanroep is). Bewust in twee stappen gesplitst:

1. `compute_representative_examples()` -- heeft de UMAP-coördinaten/volledige
   documenttekst nodig, draait dus alleen mee in cluster.py zelf (host-only
   vanwege UMAP's geheugengebruik op de volle dataset, zie
   docs/handoff.md). Legt per cluster de representatieve voorbeeldteksten +
   debattitels vast als platte, JSON-serialiseerbare data.
2. `label_clusters_with_llm()` -- werkt uitsluitend op die opgeslagen
   voorbeelden, geen coords/volledige tekstcorpus nodig. Kan dus apart,
   ergens anders (bv. de devcontainer, tegen een gratis remote router)
   draaien, en desgewenst in delen: `limit` begrenst het aantal nieuw te
   labelen clusters per aanroep, en clusters met een al gevulde `duiding`
   worden overgeslagen -- dus herhaald aanroepen op dezelfde data hervat
   waar de vorige poging bleef steken (zie pipeline/plenary_map/label_export.py
   voor de CLI die dit aanstuurt).

Gebruikt dezelfde call_llm() als pipeline/tag_arguments.py, dus ook dezelfde
--base-url/--api-key-semantiek (lokale LM Studio of een remote router zoals de
Hugging Face-router).
"""
import logging

import numpy as np

from pipeline.tag_arguments import call_llm

logger = logging.getLogger(__name__)


def compute_representative_examples(level_ids, level_lists, texts, coords, rows, examples_per_cluster):
    """Voor elk cluster op elk niveau: de `examples_per_cluster` spreekbeurten
    dichtst bij het clustercentroïde, met hun volledige (ongetrimde) tekst en
    debattitel. Geeft een lijst van N dicts terug (grofste niveau eerst),
    elk `{cluster_id: {"texts": [...], "titles": [...]}}` -- puur platte data,
    los van coords/UMAP, geschikt om als JSON weg te schrijven en later
    (zonder UMAP opnieuw te draaien) door label_clusters_with_llm() te laten
    verwerken."""
    examples_by_level = []
    for ids, summaries in zip(level_ids, level_lists):
        level_examples = {}
        for summary in summaries:
            member_idx = np.where(ids == summary["cluster_id"])[0]
            centroid = coords[member_idx].mean(axis=0)
            dists = np.linalg.norm(coords[member_idx] - centroid, axis=1)
            closest = member_idx[np.argsort(dists)[:examples_per_cluster]]
            level_examples[str(summary["cluster_id"])] = {
                "texts": [texts[i] for i in closest],
                "titles": [rows[i]["debate_title"] for i in closest],
            }
        examples_by_level.append(level_examples)
    return examples_by_level


def _build_cluster_naming_prompt(tfidf_terms, example_texts, example_titles):
    terms_str = ", ".join(tfidf_terms) if tfidf_terms else "(geen trefwoorden gevonden)"
    titles_str = "\n".join(f"- {t}" for t in sorted(set(example_titles)) if t) or "(geen debattitels bekend)"
    # `example_texts` is de volledige, ongetrimde documenttekst (zie main()'s
    # `texts = [stripped[i] for i in keep]`, geen aparte truncatie daar) --
    # 1200 tekens (was 400) geeft de LLM meer inhoudelijke context per
    # voorbeeld zonder de prompt onnodig op te blazen (8 voorbeelden default).
    examples_str = "\n\n".join(f'"{t[:1200]}"' for t in example_texts)
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
Naam: <het beleidsonderwerp in zo min mogelijk woorden -- 1 woord is prima
als dat al dekkend is, gebruik 2 woorden alleen als 1 woord het onderwerp
niet duidelijk genoeg maakt>
Duiding: <één zin, wat dit cluster inhoudelijk samenbindt>"""


def generate_cluster_name(base_url, model, reasoning_effort, tfidf_terms, example_texts, example_titles, api_key=None):
    prompt = _build_cluster_naming_prompt(tfidf_terms, example_texts, example_titles)
    # call_llm() (pipeline/tag_arguments.py) vereist max_tokens (geen default) en
    # geeft een LLMResponse-NamedTuple (content, usage, finish_reason) terug --
    # het strikte "Naam: .../Duiding: ..."-tweeregelformaat heeft ruim voldoende
    # aan 200 tokens, mits --llm-reasoning-effort op "none" staat (anders gaat
    # het hele budget op aan onzichtbare <think>-redenering, zie main()'s toelichting).
    response = call_llm(
        base_url, model, prompt, reasoning_effort=reasoning_effort, timeout=120, max_tokens=200, api_key=api_key,
    )
    raw_content = response.content
    name, duiding = None, None
    for line in raw_content.splitlines():
        if line.lower().startswith("naam:"):
            name = line.split(":", 1)[1].strip()
        elif line.lower().startswith("duiding:"):
            duiding = line.split(":", 1)[1].strip()
    return name or raw_content.strip()[:60], duiding or ""


def _label_one(level_idx, cluster_id, terms, example_texts, example_titles, base_url, model, reasoning_effort, api_key):
    """Pure functie (geen shared state) -- dask-mappable, zie
    label_clusters_with_llm_dask(). Geeft de identificerende (level_idx,
    cluster_id) mee terug zodat de aanroeper een voltooide future kan
    koppelen aan de bijbehorende summary, ongeacht de volgorde waarin
    futures binnenkomen."""
    name, duiding = generate_cluster_name(
        base_url, model, reasoning_effort, terms, example_texts, example_titles, api_key=api_key,
    )
    return level_idx, cluster_id, name, duiding


def sync_parent_names_and_tree(level_lists, tree):
    """Zet `parent_name` op elke summary en de namen in `tree` gelijk aan de
    huidige `name`-velden in `level_lists`. Nodig na parallelle (dask)
    labeling, waar clusters niet gegarandeerd grof-naar-fijn worden
    afgehandeld -- een kind kan al klaar zijn vóór zijn ouder, dus
    `parent_name` kan niet simpelweg tijdens het labelen worden bijgewerkt.
    Puur Python, geen LLM-call, dus goedkoop genoeg om na elk gelabeld
    cluster opnieuw te draaien."""
    names_by_level = [{s["cluster_id"]: s["name"] for s in summaries} for summaries in level_lists]
    for level_idx, summaries in enumerate(level_lists):
        if level_idx == 0:
            continue
        parent_names = names_by_level[level_idx - 1]
        for summary in summaries:
            if summary["parent_id"] is not None:
                summary["parent_name"] = parent_names.get(summary["parent_id"], summary["parent_name"])

    def _rename_tree(nodes, level_idx):
        for node in nodes:
            node["name"] = names_by_level[level_idx].get(node["id"], node["name"])
            if node["children"]:
                _rename_tree(node["children"], level_idx + 1)

    _rename_tree(tree, 0)


def _todo_items(level_lists, examples_by_level, limit):
    """Alle clusters zonder `duiding` (dus nog niet gelabeld), als platte
    lijst van (level_idx, cluster_id, terms, example_texts, example_titles)
    -- gedeeld tussen de sequentiële en de dask-parallelle labelfunctie."""
    items = []
    for level_idx, summaries in enumerate(level_lists):
        level_examples = examples_by_level[level_idx]
        for summary in summaries:
            if summary.get("duiding"):
                continue
            examples = level_examples.get(str(summary["cluster_id"]), {"texts": [], "titles": []})
            items.append((level_idx, summary["cluster_id"], summary["terms"], examples["texts"], examples["titles"]))
    return items[:limit] if limit is not None else items


def label_clusters_with_llm(
    level_lists, tree, examples_by_level, base_url, model, reasoning_effort, api_key=None,
    limit=None, on_cluster_labeled=None,
):
    """Sequentiële variant -- zie label_clusters_with_llm_dask() voor de
    parallelle versie (dask). Vervangt de TF-IDF-naam van elk cluster op elk
    niveau (in-place) door een LLM-gegenereerde naam + duiding, op basis van
    `examples_by_level` (zie compute_representative_examples()). De
    TF-IDF-termen zelf blijven bewaard (`terms`-veld) voor een eventueel
    latere "cluster-detail"-weergave (issue vervolgen op #181), alleen `name`
    wordt overschreven.

    Overslaan/hervatten: een cluster met een al gevulde `duiding` wordt niet
    opnieuw gelabeld (idempotent) -- zo kan dit in delen draaien: `limit`
    begrenst hoeveel NIEUWE clusters deze aanroep labelt (None = alles), en
    `on_cluster_labeled(level_idx, cluster_id)` wordt na elk gelukt cluster
    aangeroepen, zodat de aanroeper (bv. na elk cluster, of elke N) het
    resultaat meteen kan wegschrijven i.p.v. pas na de hele batch."""
    summaries_by_key = {(li, s["cluster_id"]): s for li, summaries in enumerate(level_lists) for s in summaries}
    for level_idx, cluster_id, terms, example_texts, example_titles in _todo_items(level_lists, examples_by_level, limit):
        name, duiding = generate_cluster_name(
            base_url, model, reasoning_effort, terms, example_texts, example_titles, api_key=api_key,
        )
        summary = summaries_by_key[(level_idx, cluster_id)]
        summary["name"] = name
        summary["duiding"] = duiding
        logger.info(
            "niveau %d, cluster %d (n=%d): LLM-naam '%s' -- %s",
            level_idx, cluster_id, summary["size"], name, duiding,
        )
        sync_parent_names_and_tree(level_lists, tree)
        if on_cluster_labeled is not None:
            on_cluster_labeled(level_idx, cluster_id)


def label_clusters_with_llm_dask(
    level_lists, tree, examples_by_level, base_url, model, reasoning_effort, client, api_key=None,
    limit=None, on_cluster_labeled=None, price_check=None,
):
    """Dask-parallelle variant van label_clusters_with_llm() -- zelfde
    hervatbaarheid/`limit`/`on_cluster_labeled`-semantiek, maar verdeelt de
    LLM-calls over de dask-scheduler (zie pipeline/dask_client.py) i.p.v.
    sequentieel. `price_check(n_done)`, indien gegeven, wordt na elk voltooid
    cluster aangeroepen en moet True/False teruggeven (False = prijsstijging
    gedetecteerd, resterende taken annuleren) -- zie
    pipeline/hf_pricing.py's price_still_matches()."""
    from dask.distributed import as_completed

    todo = _todo_items(level_lists, examples_by_level, limit)
    summaries_by_key = {(li, s["cluster_id"]): s for li, summaries in enumerate(level_lists) for s in summaries}
    if not todo:
        return
    level_idxs, cluster_ids, terms_list, texts_list, titles_list = zip(*todo)
    futures = client.map(
        _label_one, level_idxs, cluster_ids, terms_list, texts_list, titles_list,
        base_url=base_url, model=model, reasoning_effort=reasoning_effort, api_key=api_key,
    )
    for i, future in enumerate(as_completed(futures), 1):
        level_idx, cluster_id, name, duiding = future.result()
        summary = summaries_by_key[(level_idx, cluster_id)]
        summary["name"] = name
        summary["duiding"] = duiding
        logger.info(
            "niveau %d, cluster %d (n=%d): LLM-naam '%s' -- %s",
            level_idx, cluster_id, summary["size"], name, duiding,
        )
        sync_parent_names_and_tree(level_lists, tree)
        if on_cluster_labeled is not None:
            on_cluster_labeled(level_idx, cluster_id)
        if price_check is not None and not price_check(i):
            remaining = [f for f in futures if not f.done()]
            logger.error(
                "Batch afgebroken na %d/%d clusters wegens prijsstijging (%d resterende taken geannuleerd).",
                i, len(todo), len(remaining),
            )
            client.cancel(remaining)
            break
