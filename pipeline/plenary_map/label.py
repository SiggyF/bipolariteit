"""
LLM-naamgeving voor UMAP-clusters (uitgelicht uit pipeline/plenaire_kaart/cluster.py,
zodat cluster.py de UMAP/HDBSCAN-berekening blijft en dit bestand puur de LLM-
aanroep is -- herbruikbaar zonder de hele clustering opnieuw te draaien, zodra
een losse re-labeling-workflow op een al opgeslagen clusterbestand bestaat).

Gebruikt dezelfde call_llm() als pipeline/tag_arguments.py, dus ook dezelfde
--base-url/--api-key-semantiek (lokale LM Studio of een remote router zoals de
Hugging Face-router).
"""
import logging

import numpy as np

from pipeline.tag_arguments import call_llm

logger = logging.getLogger(__name__)


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


def _generate_llm_cluster_name(base_url, model, reasoning_effort, tfidf_terms, example_texts, example_titles, api_key=None):
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


def label_clusters_with_llm(
    level_ids, level_lists, tree,
    texts, coords, rows, base_url, model, reasoning_effort, examples_per_cluster, api_key=None,
):
    """Vervangt de TF-IDF-naam van elk cluster op elk niveau (in-place) door
    een LLM-gegenereerde naam + duiding, op basis van representatieve
    spreekbeurten (dichtst bij het clustercentroïde) + debattitels. De
    TF-IDF-termen zelf blijven bewaard (`terms`-veld) voor een eventueel
    latere "cluster-detail"-weergave (issue vervolgen op #181), alleen `name`
    wordt overschreven. `level_ids`/`level_lists` zijn N-lang (grofste niveau
    eerst, zie build_multilevel_clusters/label_multilevel_clusters in
    pipeline/plenaire_kaart/cluster.py) -- werkt per niveau van grof naar fijn
    zodat een dieper niveau's `parent_name` altijd de AL VERVANGEN ouder-naam
    kan opzoeken. Werkt ook `tree` (voor plenair-map-hierarchy.json) bij, op
    willekeurige diepte: `to_node()` kopieert `name` op bouwmoment (vóór
    LLM-naamgeving) naar de boomknoop, dus zonder deze naderhand-patch zou de
    hierarchy-export de oude TF-IDF-namen blijven tonen ook al is
    `summary["name"]` allang vervangen."""
    def representative_examples(member_idx):
        centroid = coords[member_idx].mean(axis=0)
        dists = np.linalg.norm(coords[member_idx] - centroid, axis=1)
        closest = member_idx[np.argsort(dists)[:examples_per_cluster]]
        return [texts[i] for i in closest], [rows[i]["debate_title"] for i in closest]

    total = sum(len(summaries) for summaries in level_lists)
    logger.info(
        "LLM-naamgeving voor %d clusters over %d niveaus (~%ds geschat, %.1fs/cluster live gemeten)",
        total, len(level_lists), total * 7, 7.0,
    )

    names_by_level = []
    for level_idx, (ids, summaries) in enumerate(zip(level_ids, level_lists)):
        names_by_id = {}
        for summary in summaries:
            member_idx = np.where(ids == summary["cluster_id"])[0]
            example_texts, example_titles = representative_examples(member_idx)
            name, duiding = _generate_llm_cluster_name(
                base_url, model, reasoning_effort, summary["terms"], example_texts, example_titles, api_key=api_key,
            )
            summary["name"] = name
            summary["duiding"] = duiding
            if level_idx > 0 and summary["parent_id"] is not None:
                summary["parent_name"] = names_by_level[level_idx - 1].get(summary["parent_id"], summary["parent_name"])
            names_by_id[summary["cluster_id"]] = name
            logger.info(
                "niveau %d, cluster %d (n=%d): LLM-naam '%s' -- %s",
                level_idx, summary["cluster_id"], summary["size"], name, duiding,
            )
        names_by_level.append(names_by_id)

    def _rename_tree(nodes, level_idx):
        for node in nodes:
            node["name"] = names_by_level[level_idx].get(node["id"], node["name"])
            if node["children"]:
                _rename_tree(node["children"], level_idx + 1)

    _rename_tree(tree, 0)
