# Aanvraag: architectuurinput voor samenvoegen clustering-verbeteringen (posterpad → hoofdlijn)

Zie [issue #281](https://github.com/SiggyF/bipolariteit/issues/281) voor de tracking; dit bestand is het zelfstandige pakketje om mee te werken.

## Aanleiding

[Issue #186](https://github.com/SiggyF/bipolariteit/issues/186) (plenaire kaart) heeft twee resterende open punten:

2. Classificatie/labels van de "overig plenair"-restgroep (diffuse, niet-geclassificeerde punten).
4. Overlappende coarse/fine-cluster-hulls.

Tijdens het bouwen van de A0-printposter ([#215](https://github.com/SiggyF/bipolariteit/issues/215)) is voor allebei een oplossingsrichting ontwikkeld en geverifieerd. Alleen: die oplossing zit **uitsluitend in het posterpad**, niet in de productiekaart. Dit document vraagt om architectuurinput over hoe dat samengevoegd wordt, in plaats van dat er stilzwijgend een aanname wordt gedaan.

## Huidige situatie: twee gescheiden paden

| | Productiepad | Posterpad |
|---|---|---|
| Gebruikt door | `frontend/src/components/PlenairMap.vue` (`/onderwerpen/`) | `frontend/src/components/TiledPlenairMap.vue` (losse testpagina, [#259](https://github.com/SiggyF/bipolariteit/issues/259)) |
| Databron | `data/export/plenair-map.json` | `.pmtiles` via `pipeline/tiling/` |
| Clusterfunctie | `build_hierarchical_clusters` (`scripts/experiment_umap_documents.py:228`) | `build_multilevel_clusters` (`scripts/experiment_umap_documents.py:641`) |
| Labelfunctie | `label_hierarchical_clusters` (`scripts/experiment_umap_documents.py:431`) | `label_multilevel_clusters` (`scripts/experiment_umap_documents.py:737`) |
| Niveaus | vast 2 (coarse/fine) | N, configureerbaar (`--cluster-level-sizes`) |
| Restgroep-mitigatie | geen | dominantie-afwijzing: cluster >4x zo groot als het één-na-grootste → ruis (regel 665-673, 719-726) |
| Overlap-mitigatie | geen | `contained_by_sibling` (same-level containment-vlag, regel 903/961/963/975) + `redundant_with_parent` (IoU-redundantie tussen niveaus, regel 750-761) |
| Output | platte `coarse`/`fine`-lijsten per punt | `level_ids` (lijst van N arrays) + geneste `tree` + de vlagvelden hierboven |

De twee outputformaten zijn **niet 1-op-1 compatibel**. `PlenairMap.vue` en `TiledPlenairMap.vue` gebruiken op dit moment geen van beide de `contained_by_sibling`/`redundant_with_parent`-vlaggen in hun hull-rendering (nul treffers bij grep in beide bestanden) — alleen het statische posterpad (`render_design_preview.py:100`, matplotlib-preview voor de A0-print) verwerkt ze al.

## De architectuurvraag

1. **Wordt `build_multilevel_clusters`/`label_multilevel_clusters` de nieuwe standaard voor beide paden?** Zo ja: de oude `build_hierarchical_clusters`/`label_hierarchical_clusters` kunnen dan uitfaseren (let op: `notebooks/explore_plenary_umap_clusters.py` importeert de oude functies rechtstreeks). Zo nee: wat is de reden om twee clusteringimplementaties te blijven onderhouden?
2. **Hoe landen `contained_by_sibling`/`redundant_with_parent` concreet in interactieve hull-rendering?** Opties die in `render_design_preview.py` en `docs/handoff.md:105` als mogelijkheden genoemd zijn: gevlagde hulls simpelweg niet tekenen, ze anders stijlen (bv. gestippeld), of alsnog de hull-geometrie herberekenen (concave hulls/alpha-shapes) — met de kanttekening dat die laatste optie destijds bewust vermeden is voor het (eenmalige) printproduct, maar voor een blijvende interactieve kaart een andere afweging kan zijn.
3. **Verhouding tot #259.** Kan restgroep/overlap-mitigatie landen in `PlenairMap.vue` (huidige productie) los van de bredere #259-vraag of `TiledPlenairMap.vue` ooit de productiekaart vervangt? Of is dit issue pas zinvol te doen ná die beslissing (bv. omdat de mitigatie beter in de tile-encodering zelf hoort dan in twee losse Vue-componenten)?
4. **Outputformaatcompatibiliteit.** Vergt dit een nieuw/uitgebreid contract voor `data/export/plenair-map.json` (bv. `coarse`/`fine` behouden voor backward compat, `levels` + vlagvelden erbij), of een volledige omzetting?

## Relevante bestanden

- `scripts/experiment_umap_documents.py` — beide clustering-/labelfunctie-paren, zie regelnummers hierboven.
- `frontend/src/components/PlenairMap.vue` — hull-tekencode productiepad (`hullArea()`, `distanceToHullBoundaryScreen()`).
- `frontend/src/components/TiledPlenairMap.vue` — hull-tekencode posterpad (regel 231-240, toont vooralsnog alleen coarse-hulls).
- `pipeline/tiling/` (`grid.py`, `encode.py`, `build_pyramid.py`) — tile-pyramide-architectuur.
- `scripts/validate_cluster_hierarchy.py`, `scripts/export_clusters_geojson.py` — topologie-validatie en GeoJSON-export die de nieuwe vlaggen al gebruiken.
- `docs/handoff.md:92-241` — volledige sessielog van het posterwerk waarin dit is ontstaan.

## Niet in scope

- De A0-printposter zelf (#215) — blijft een eigen, statisch renderpad (`datashader`/QGIS/Illustrator), ongeacht de uitkomst hier.
- De volledige afbouw van `TiledPlenairMap.vue` tot productiealternatief (#259) — dat is een aparte, bredere beslissing; dit document vraagt alleen hoe de *clustering-verbeteringen* de hoofdlijn bereiken.
