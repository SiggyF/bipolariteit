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
    level_lists, tree, examples_by_level, base_url, model, reasoning_effort, api_key=None,
    limit=None, on_cluster_labeled=None,
):
    """Vervangt de TF-IDF-naam van elk cluster op elk niveau (in-place) door
    een LLM-gegenereerde naam + duiding, op basis van `examples_by_level`
    (zie compute_representative_examples()) + debattitels. De TF-IDF-termen
    zelf blijven bewaard (`terms`-veld) voor een eventueel latere
    "cluster-detail"-weergave (issue vervolgen op #181), alleen `name` wordt
    overschreven. `level_lists` is N-lang (grofste niveau eerst, zie
    build_multilevel_clusters/label_multilevel_clusters in
    pipeline/plenary_map/cluster.py) -- werkt per niveau van grof naar fijn
    zodat een dieper niveau's `parent_name` altijd de AL VERVANGEN ouder-naam
    kan opzoeken. Werkt ook `tree` (voor plenair-map-hierarchy.json) bij, op
    willekeurige diepte.

    Overslaan/hervatten: een cluster met een al gevulde `duiding` wordt niet
    opnieuw gelabeld (idempotent) -- zo kan dit in delen draaien: `limit`
    begrenst hoeveel NIEUWE clusters deze aanroep labelt (None = alles), en
    `on_cluster_labeled(level_idx, cluster_id)` wordt na elk gelukt cluster
    aangeroepen, zodat de aanroeper (bv. na elk cluster, of elke N) het
    resultaat meteen kan wegschrijven i.p.v. pas na de hele batch."""
    remaining = limit
    names_by_level = []
    for level_idx, summaries in enumerate(level_lists):
        names_by_id = {}
        level_examples = examples_by_level[level_idx]
        for summary in summaries:
            already_done = bool(summary.get("duiding"))
            if already_done:
                names_by_id[summary["cluster_id"]] = summary["name"]
                continue
            if remaining is not None and remaining <= 0:
                continue
            examples = level_examples.get(str(summary["cluster_id"]), {"texts": [], "titles": []})
            name, duiding = _generate_llm_cluster_name(
                base_url, model, reasoning_effort, summary["terms"],
                examples["texts"], examples["titles"], api_key=api_key,
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
            if remaining is not None:
                remaining -= 1
            if on_cluster_labeled is not None:
                on_cluster_labeled(level_idx, summary["cluster_id"])
        names_by_level.append(names_by_id)

    def _rename_tree(nodes, level_idx):
        for node in nodes:
            node["name"] = names_by_level[level_idx].get(node["id"], node["name"])
            if node["children"]:
                _rename_tree(node["children"], level_idx + 1)

    _rename_tree(tree, 0)
