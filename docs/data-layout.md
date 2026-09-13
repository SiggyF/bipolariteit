# Data-layout: wat hoort waar (issue #316)

Overzicht van elke databestemming van dit project: wat erin hoort, welk
`make`-target het vult, via welk kanaal het publiek wordt (indien van
toepassing), en waarom. Bedoeld als scan-baar naslagwerk, niet als
uitputtende changelog — voor de historische toelichting per kanaal zie
[handoff.md](handoff.md), voor de publicatiemechaniek in detail
[release.md](release.md) (secties "Argumentdata publiceren" en "Grote
bestanden -> Zenodo + Hugging Face").

## De vier bestemmingen

| Bestemming | Rol | Kanaal |
| --- | --- | --- |
| Hoofdrepo (`data/`, git) | lean brondata + frontend-input die met een release meeleeft | gewoon gecommit |
| `bipolariteit/bipolariteit-data` | compacte hosting voor bipolariteit.org | submodule `data/export/gepubliceerd/` → jsDelivr, `make publish-data` |
| Zenodo | archief van gegenereerde data (DOI/versionering) | `make publish-zenodo`, draft → handmatig publiceren |
| Hugging Face | grote, cloud-optimized datasets die we live serveren (bv. pmtiles) | `make publish-huggingface`, direct live |

Daarnaast drie categorieën die niet via een publicatiekanaal gaan:

- **Lokaal-only, regenereerbaar**: `data/raw/`, `data/embeddings/`,
  `data/subtitles/`, `data/debate_events/`. Cache/tussenproduct van de
  pijplijn, hoeft nergens gepubliceerd te worden.
- **Handgeschreven brondata**: `data/tags.toml`, `data/bewindspersonen.toml`,
  `data/politieke-periodes.toml`, `data/topic-descriptions/`,
  `config/cluster_label_overrides.toml`. Geen pijplijn-output — handmatig
  onderhouden invoer, gewoon in git.
- **Privé, mag niet publiek**: `data/bipolariteit.db`. Bevat naast publieke
  Kamerstukken ook LLM-call-logs (prompts/responses). Geen enkel
  publicatiekanaal; alleen `make backup-db` naar dezelfde-machine-map. Zie
  issue #301 voor een offsite-backupplan (Google Drive of een privé
  Hugging Face-dataset — die laatste kan de auth/upload-logica van
  `scripts/publish_huggingface.py` hergebruiken, met een apart, privé
  dataset-repo).

## 1. Hoofdrepo — `data/`

### Handgeschreven brondata (altijd tracked)

`bewindspersonen.toml`, `politieke-periodes.toml`, `tags.toml`,
`topic-descriptions/*.md`, `cluster-label-anchors.parquet` (gegenereerd door
`scripts/build_cluster_label_anchors.py`, maar bewust getrackt als
snapshot — pairt met de handmatige `config/cluster_label_overrides.toml`).

### `data/export/` — frontend-input

Gevuld door `make export` (`pipeline/build_static_data.py`) en
`make cluster-plenary-map`/`make label-clusters` (`pipeline/plenary_map/`):

| Pad | Bron | Gebruikt door |
| --- | --- | --- |
| `topics/*.json`, `topics-index.json`, `status.json` | `build_static_data.py` | vrijwel alle Astro-pagina's (build-time) |
| `llm_calls/*.json` | idem | `pages/prompts/*.astro` |
| `argument-trees/*.json` | `pipeline/build_confrontatie_export.py` (`make redactie`) | `pages/onderwerpen/[slug].astro` |
| `eval/*.json` | `scripts/convert_elecdebate.py` + benchmark | `pages/validatie-rapportage*.astro` |
| `plenair-map.json`, `-clusters.json`, `-hierarchy.json` | `pipeline/plenary_map/cluster.py --export-frontend` | client-side fetch (`PlenairMap.vue`), en gekopieerd naar de submodule |
| `plenair-map.pmtiles`, `plenair-map-grid.json` | `pipeline/tiling/build_pyramid.py` (`make tiles`) | `TiledPlenairMap.vue`, via Hugging Face (§4) — niet de submodule |

**Wees, wordt opgeruimd (issue #316):** `plenair-map-debates.json` — geschreven
door `build_static_data.py`, door niets gelezen.

**Niet in git** (gitignored, zie `.gitignore` voor de volledige regels):
`*.pmtiles`, alle `*-full*`-varianten (bestemd voor Zenodo/Hugging Face, niet
voor de website), `a0-map/` (op een handvol herbruikbare artefacten na, zie
hieronder), `argument-docs/`, `design-handoff/`, `agy_confrontatie_tree.log`,
`zenodo/` (de gedeelde bundelmap, zie §3).

### `data/plenary-map/` — pijplijn-tussenproducten

Gevuld door `make umap` (coords) en `make cluster-plenary-map`
(clusters/hierarchy/plot). Per `--label` (`sample10pct`, `combined`,
`2025-09-heden`, `full`, ...) staan `clusters-<label>.json`,
`hierarchy-<label>.json` en `plot-<label>.html` getrackt — dit zijn de
kleine/middelgrote labels, bedoeld als "bekijk dit"-demo naast de
frontend-export. Niet getrackt: `coords-*.json`/`cluster-label-input-*.json`
(pure tussenproducten, tot 30 MiB) en `plot-full.html` (250+ MiB).

**Let op de naamconventie**: bestanden met `-full` als suffix
(`clusters-full.geojson`, `grid-full.json`) horen bij de Zenodo/Hugging
Face-route, niet bij deze `--label`-reeks — zie `.gitignore`'s
`data/plenary-map/*-full.geojson`/`grid-*.json`-regels.

### `data/export/a0-map/` — A0-printposter (issue #215)

De renderpijplijn in `scripts/a0_map/` produceert honderden MB aan
tussenproducten (rasters, previews, LaTeX-restanten). Alleen de kleine,
herbruikbare artefacten zijn getrackt:

- `colofon.html`/`.md`, `legenda.html` — bron voor `render_a0_widgets.py`'s
  PNG-render (**niet** `colofon.tex`, dat is een dode LaTeX-voorganger).
- `methodology_workflow.d2`/`.svg` — het methodologiediagram.
- `clusters.qml`, `clusters_frosted_glass.qml`, `points.qml` — QGIS-stijlen.
- `a0-umap.qgz`, `a0-umap-frosted-glass.qgz`,
  `a0-umap-frosted-glass-rotated.qgz` — QGIS-projectbestanden.
- `cielab_legend_widget.svg` — het kleurenlegenda-widget.

`data/export/a0-map/maps/` (~540 MB, gitignored) is **geen dood gewicht**:
het is de hardcoded default-input van vrijwel elk script in
`scripts/a0_map/` (`export_clusters_geojson.py`,
`generate_a0_color_raster.py`, `plot_pca_dimensions.py`, ...). Niet
verwijderen, wel lokaal-only.

De grote renders (`density_*_300dpi*.tif`, `a0-map*.pdf`/`.png`,
`a0-map-4k.psd`) horen op Zenodo (zie §3), niet in git.

## 2. `bipolariteit/bipolariteit-data` — publieke submodule

`data/export/gepubliceerd/` is een git submodule
(`.gitmodules` → `https://github.com/bipolariteit/bipolariteit-data.git`).
De hoofdrepo blijft privé; dit is de afgeleide data die toch al publiek in de
site zit.

Gevuld door:

1. `make export-public-data` (`frontend/scripts/export_public_data.ts`,
   leest `data/export/topics/*.json`) → `perspectieven/` (lean-gestript),
   `onderwerpen/`, `debatten/`, `tags/` (ongestript), plus een kopie van
   `plenair-map.json`/`-clusters.json`/`-videos.json`.
2. `scripts/build_shorts_sample.py` → `shorts/` (geen make-target, handmatig).

Gepubliceerd met `make publish-data` (`scripts/publish_data.py`): commit +
push naar `bipolariteit/bipolariteit-data@main`, jsDelivr-cache-purge, én een
auto-gemergde PR in de hoofdrepo voor de resterende `data/export/`-
wijzigingen (submodule-pointer + eventuele export-JSON's) — zie
"Waarschuwing" hieronder.

Geserveerd via jsDelivr's GitHub-CDN
(`cdn.jsdelivr.net/gh/bipolariteit/bipolariteit-data@main/...`), CORS voor
alle origins, geen eigen hosting nodig. **jsDelivr weigert bestanden boven
20 MB** (`403 File size exceeded the configured limit of 20 MB`,
geverifieerd) — zie de losse issue hieronder, acht bestanden zitten daar nu
boven.

⚠️ **Waarschuwing (de directe aanleiding voor #316):**
`scripts/publish_data.py::open_main_repo_pr()` commit **alles** wat
`git status --porcelain -- data/export` in de hoofdrepo meldt, zonder
grootte- of patroonfilter. `.gitignore` is de enige bescherming — zo lekte
ooit een 125 MiB `-full-v2`-export mee (PR #315).

**`--export-suffix` staat sinds issue #316 vast op `''` of `'-full'`**
(`pipeline/plenary_map/cluster.py`/`label_export.py`, argparse `choices`) —
geen vrije tekst meer. Een los getypte versiesuffix als `-full-v2` gaf niet
alleen `.gitignore`-gaten, maar liet ook oude generaties permanent
achter op Zenodo: `publish_zenodo.py::create_new_version()` kopieert een
nieuwe versie altijd inclusief alle bestanden van de vorige, en
`remove_stale_files()` vervangt alléén bestanden met exact dezelfde naam.
Met een vaste naam per run vervangt elke nieuwe `-full`-publicatie de
vorige daadwerkelijk, in plaats van er telkens een nieuwe naast te zetten.
Wil je een oude `-full`-generatie behouden voor vergelijk? Archiveer 'm
eerst expliciet (`make publish-zenodo`) vóórdat je 'm lokaal overschrijft
— niet via een verzonnen suffix.

Dezelfde reden lag onder de inconsistente grid-bestandsnamen
(`plenair-map-full-grid.json` vs. `-grid-full.json`, zie §1): `--grid-out`
in `pipeline/tiling/build_pyramid.py` werd los getypt. Sinds #316 wordt het
standaard afgeleid van `--out` (`<stem>-grid.json`) — alleen expliciet
zetten voor een bewust afwijkend pad.

## 3. Zenodo — archief

`scripts/publish_zenodo.py`, concept-record
[10.5281/zenodo.22181704](https://doi.org/10.5281/zenodo.22181704) (huidige
publieke versie: 22181705). Uploadt standaard alles in de gedeelde
bundelmap `data/export/zenodo/` (zie §4), maakt een nieuwe versie aan als
kopie van de vorige (bestaande bestanden blijven staan tenzij gelijknamig
vervangen), en blijft een **draft** — publiceren is een bewuste handmatige
stap in de Zenodo-UI. Vereist `ZENODO_TOKEN`.

Dat copy-forward-gedrag is bewust voor de ruwe crawl-XML (elke
`raw_xml__<onderwerp>.zip` hoort een groeiend archief per onderwerp te zijn
— een hercrawl overschrijft 'm gewoon onder dezelfde naam) maar ongewenst
voor afgeleide artefacten: die horen bij elke versie **vervangen** te
worden, niet te stapelen. Zorg dus dat elke categorie een vaste bestandsnaam
gebruikt (zie hierboven, `--export-suffix`) in plaats van een naam die per
run verandert — anders blijven oude, overbodige generaties voor altijd in
élke latere versie zitten.

**Huidige dekking** (record 22181705): 13 raw-XML-zips per crawl-zoekterm,
één `embeddings__..._plenair-full.npz` (1,1 GiB, ouder npz-formaat — de
actuele cache in `data/embeddings/` is parquet), en vier
`derived__plenair-map-*`-bestanden uit de augustus-generatie.

**Bekende gaten** (nog niet gearchiveerd):

- `data/export/a0-map/`: geen enkel A0-renderartefact staat op Zenodo.
- Élke `.pmtiles`.
- 4 van de 17 mappen onder `data/raw/tweede_kamer/` — juist de grootste
  (`_plenair_2017-2024`, `_commissie_2017-2024`, `_commissie_2024-2025-gat`,
  `_plenair_2025-gat`, samen ~2,2 GB). Deze bestaan nergens anders.

**Bestandsstructuur is nu plat en niet afdwingbaar**: de huidige
`raw_xml__`/`derived__`/`embeddings__`-prefixen staan alleen in de
bestandsnamen zelf, niet in `publish_zenodo.py` (die uploadt gewoon
`path.name`), en alle ~19 bestanden staan zo onder elkaar in één platte
lijst. Zenodo's bucket-API is S3-achtig: een bestandsnaam mag `/` bevatten,
en Zenodo toont de map vóór de laatste `/` als een map in de
bestandenlijst (geen echte geneste buckets, wel een bruikbare boomweergave,
en elk bestand blijft individueel downloadbaar — in tegenstelling tot een
zip). Bij de eerstvolgende herstructurering (PR 3): categorie-prefixen
vervangen door echte paden, bv. `raw_xml/tweede_kamer_abortus.zip`,
`derived/plenair-map-full.json`, `a0-map/density_color_a0_300dpi_rotated.tif`.
Eerst met één bestand op de draft testen — dit is afgeleid S3-gedrag, geen
expliciet gedocumenteerde Zenodo-feature.

## 4. Hugging Face — live grote data

`scripts/publish_huggingface.py`, dataset-repo
`SiggyF/bipolariteit-pmtiles` (publiek). Zelfde bron als Zenodo
(`data/export/zenodo/`, ondanks de naam ook de Hugging Face-bundel — bewust
gedeeld zodat beide publicatiestappen niet uit de pas kunnen lopen), maar
bestanden worden **direct overschreven** zonder aparte publiceerstap: dit is
de live-databron, niet het archief. Vereist `HUGGINGFACE_TOKEN` — let op:
dit is het publicatietoken, niet `HUGGINGFACE_INFERENCE_TOKEN` dat voor
router-/inference-calls gebruikt wordt.

Gekozen boven jsDelivr/git omdat CORS + HTTP Range bevestigd werken op HF's
dataset-CDN voor bestanden ver boven de 100 MB-/20 MB-grenzen van
GitHub/jsDelivr (issue #293).

Bestanden komen te staan onder een submap per dataset (`--repo-subdir`,
default `plenair-map`) in plaats van plat naast elkaar — in tegenstelling
tot Zenodo's platte S3-bucket (§3) ondersteunt de Hugging Face Hub-API
`path_in_repo` als een echt pad. Nu zowel de kleine als de volle-dataset-
bundel in dezelfde repo staan, voorkomt dat een herhaling van de platte-
lijst-rommel die Zenodo had.

`make tiles-full` vult de bundelmap:
`plenair-map-full.pmtiles`, `-full-grid.json`, `-full.json`,
`-clusters-full.json`, `-hierarchy-full.json`.

**De kleine `plenair-map.pmtiles`/`plenair-map-grid.json` gaan hier ook
naartoe** (issue #316) — pmtiles horen bij Hugging Face, niet bij de
compacte jsDelivr-hosting, ook al zou het kleine bestand (~50 MiB) onder
jsDelivr's 20 MB-limiet sowieso al niet passen. `make tiles` schrijft ze
naar `data/export/` zoals altijd; `make publish-tiles` publiceert ze naar
dezelfde `SiggyF/bipolariteit-pmtiles`-repo (los van de `-full`-bundel, dus
zonder dat elke kleine kaartupdate de hele volle-dataset-bundel opnieuw
hoeft). `TiledPlenairMap.vue` fetcht ze via `resolveTilesBaseUrl()`
(`frontend/src/lib/dataBaseUrl.ts`), een losse basis-URL naast
`resolveDataBaseUrl()` voor de rest van de submodule-data. De bestanden
zijn uit `data/export/gepubliceerd/` (de submodule) verwijderd.

## Bekende openstaande problemen (niet in dit issue opgelost)

- **jsDelivr's 20 MB-limiet**: acht live bestanden in de submodule zitten
  erboven, waaronder alle vier de perspectiefpagina's (`tags/`-bestanden tot
  30,7 MB). Zie het aparte issue voor de oplossingsrichting
  (server-side/build-time aggregatie i.p.v. de volledige argumentenlijst
  client-side fetchen).
- **DB-backup**: zie issue #301.
- **Zenodo-dekkingsgaten**: zie §3 hierboven.
