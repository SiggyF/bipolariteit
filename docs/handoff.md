# Handoff — Bipolariteit MVP

Status per 2026-07-27. Zie `docs/plan.md` voor het volledige, goedgekeurde architectuurplan. Dit document is voor het vervolg: wat staat er al, wat is er onderweg ontdekt, en wat is de volgende concrete stap.

## Stand bij einde sessie (2026-09-12/13, gratis HF-router-batches + nieuw topic oekraine + plenaire-kaart-pijplijn gepromoveerd) — begin hier bij een nieuwe sessie

**Aanleiding**: de Hugging Face-router bleek `Qwen/Qwen3.8-27B` via OVHcloud tijdelijk voor $0/M tokens aan te bieden (bevestigd via `/v1/models`-API én de gebruiker's eigen billing-dashboard; `is_free: false` in de API, dus vermoedelijk een niet-afgemaakte pricing-entry van de provider, geen bewuste actie — archiefbewijs in `reference_ovhcloud_pricing_archive`-memory). Dat is de rode draad van de hele sessie: zoveel mogelijk achterstallig LLM-werk erdoorheen jagen zolang het gratis is, met een prijsstijging-vangnet zodat een onopgemerkte wijziging niet alsnog kosten oplevert.

### Parallelle extractie/tagging + prijsbewaking (PR #297, gemerged)

- `pipeline/extract_arguments.py`/`pipeline/tag_arguments.py` kregen `--parallel` (verdeelt LLM-calls over de dask-scheduler, zie `pipeline/dask_client.py`) en `--api-key` (nodig voor de HF-router, i.t.t. lokale LM Studio).
- `pipeline/hf_pricing.py` (nieuw): `get_baseline_pricing()`/`price_still_matches()` -- checkt elke 100 items of de prijs niet gestegen is t.o.v. de start van de batch; bij een stijging worden de resterende dask-taken geannuleerd. Alleen actief tegen `router.huggingface.co`, no-op voor lokale backends.
- Resultaatverwerking is nu incrementeel (`process_result()`-closure, aangeroepen per binnenkomend dask-future via `as_completed()`), niet meer "verzamel alles, verwerk pas aan het eind".
- Dask-worker-threads verhoogd van 8 (= aantal cores) naar 10 (`.devcontainer/devcontainer.json`, PR #307, gemerged): deze workload is netwerk-IO-bound, niet CPU-bound. 12 threads gaf HTTP 429 (rate limit) bij de HF-router, 10 niet.
- In losse batches (steeds handmatig gestart, geen doorlopende achtergrondtaak) zijn zo alle vier bestaande topics verder ge-extraheerd/getagd: stikstof, abortus, asiel en energietransitie staan alle vier op 0 openstaande extractie en (op een paar losse fouten na) 0 openstaande tagging.

### Nieuw curated topic: oekraine (PR #302, #306 gemerged)

- Description onderhandeld op basis van twee steekproeven van gecrawlde NAVO/Oekraïne/Rusland-argumenten, 7 assen (defensie-uitgaven, wapenleveranties, opvang, Rusland-houding, NAVO-aanwezigheid, inkoopstrategie, geografische reikwijdte) -- zie `data/topic-descriptions/oekraine.md`.
- **Databug gevonden en gefixed**: de eerste documentkoppeling (678 documenten) bleek voor 674 daarvan titel "Vragenuur" te zijn -- inhoudelijk grotendeels niets met Oekraïne te maken, puur toeval-treffers. `scripts/db/relink_oekraine_by_title.py` (nieuw, PR #306) koppelt in plaats daarvan op de daadwerkelijke debattitel (`oekra`/`navo`/`rusland`/`poetin`, met een `irak`/`iran`/`isra`-uitsluiting voor NAVO-missiebegrotingen) -- resultaat: 1290 documenten ontkoppeld, 14.727 (echte) documenten gekoppeld. Extractie daarna: 46 → 778 argumenten in de eerste volle batch, ratio steeg van 6,8% naar 77,8% (in lijn met de andere topics).
- Nog niet afgemaakt: verdere extractie/tagging van oekraine (13.7k documenten in totaal, meerdere batches nodig) -- laatst bekende stand: alle documenten binnen de huidige `[verwerking].vanaf`-drempel zijn ge-extraheerd, tagging loopt nog achter.
- Losse issues aangemaakt voor later: #303 (Makefile `extract`/`tag`-targets missen `MODEL`/`API_KEY`/`PARALLEL`-vars, moest daardoor de Python-module rechtstreeks aanroepen), #309 (er is geen manier om argumenten met een verouderde prompt-versie gericht te hertaggen -- `--ids-file` respecteert altijd `tagged_at IS NULL`), #308 (Mona Keijzer: partij-veld/logo, klein, losstaand).

### Plenaire-kaart-pijplijn gepromoveerd uit experiment-status (PR #310, **nog niet gemerged** -- gebruiker reviewt hem morgen)

`scripts/experiment_umap_documents.py` was allang geen experiment meer (13 andere bestanden verwezen er al naar). Nu verplaatst naar `pipeline/plenary_map/`, en opgesplitst in vier losse stages/modules/Makefile-targets (was: alles in één script):

1. **`make embed`** (bestond al) -- documenten embedden, `data/embeddings/`.
2. **`make umap`** (`pipeline/plenary_map/umap.py`) -- UMAP-fit, host-only qua geheugengebruik (NN-descent op ~732k x 1024-dim gaf herhaaldelijk OOM, ook bij 32GB in de devcontainer -- alleen de host, 64GB, trekt 'm). Schrijft alleen `data/plenary-map/coords-<label>.json` weg (`{doc_id: [x, y]}`). Praat NIET met LM Studio bij een volledige embeddingscache-hit.
3. **`make cluster-plenary-map`** (`pipeline/plenary_map/cluster.py`) -- leest die coördinaten (`--coords-path`, verplicht, geen UMAP meer hier), HDBSCAN-clustering (`--cluster-level-sizes`, bv. `4000,1200,350,100,30`) + TF-IDF-labels. **Bleek zelf óók geheugenzwaar** op de volle dataset (TF-IDF over alle ~732k documentteksten + een ruimtelijke-dispersie-stopwoordanalyse) -- gaf Error 137 in de devcontainer, moest alsnog naar de host. De aanname "clustering is licht, overal draaibaar" klopte dus niet voor de volledige-dataset-schaal.
4. **`make label-clusters`** (`pipeline/plenary_map/label_export.py`) -- LLM-naamgeving, met `--parallel` (dask) + dezelfde prijsbewaking als extract/tag hierboven. Werkt op de door stap 3 weggeschreven `cluster-label-input-<label>.json` (representatieve voorbeeldteksten per cluster, vooraf berekend zodat deze stap geen UMAP-coördinaten nodig heeft) -- dus overal draaibaar, en hervatbaar (`duiding` al gevuld = overslaan, `LIMIT_CLUSTERS` voor porties).

**Resultaat van een volledige run**: 3636 clusters over 5 niveaus, allemaal LLM-benoemd (Qwen3.8-27B via de HF-router, dask-parallel, ~10 min i.p.v. de geschatte uren sequentieel). Kleinste cluster op het fijnste niveau: exact 30 (de ingestelde ondergrens) -- er zit dus nog ruimte voor een 6e, fijner niveau (bv. drempel 15, de `--hdbscan-min-cluster-size`-bodem) als dat gewenst is, niet gedaan in deze sessie.

**Output verplaatst**: `docs/poc/umap-documenten/` → `data/plenary-map/` (nu dit geen experiment meer is, hoort de output niet meer in `docs/poc/` thuis). Kleine/demo-bestanden (`clusters-*.json`, `hierarchy-*.json`, kleinere `plot-*.html`'s) blijven ingecheckt zoals voorheen; de nieuwe, op-de-volle-dataset grote tussenproducten (`coords-*.json`, `cluster-label-input-*.json`) zijn nu ook gitignored, zelfde redenering als de al bestaande `plot-full.html`-uitzondering.

**Losstaande observatie, niet uitgezocht**: gebruiker merkte op dat sommige clusters lijken te worden bepaald door wie er wordt aangesproken (een persoon) i.p.v. het inhoudelijke onderwerp -- geen concreet voorbeeld nog gevonden/genoteerd, wel de moeite waard om bij een volgende clustering-sessie op te letten (mogelijk een gat in `fetch_actor_and_party_stopwords()`'s dekking, of een echt clustering-artefact).

**Backup**: alle output van deze run (coords, cluster-label-input, clusters, hierarchy, plus de frontend-`-full-v2`-exports) staat als Zenodo-draft (concept-record 22181704, deposition [22730827](https://zenodo.org/deposit/22730827)) -- nog niet gepubliceerd, puur archief-backup.

**Issue #311** (SVD-voorreductie 1024→~100 dims om UMAP's geheugengebruik te verlagen): getest en de hoop bleek niet te kloppen -- voor 95% verklaarde variantie zijn ~400 componenten nodig (2,6x kleiner dan 1024, niet de gehoopte 10x). Resultaat als comment op het issue gezet, geen verdere actie ondernomen (business case te zwak).

**Nog te doen, volgende sessie**:
- **PR #310 reviewen en mergen** (gebruiker doet dit morgen) -- daarna pas is de bovenstaande refactor definitief.
- De nieuwe clustering/labeling (`data/export/plenair-map-{,clusters-,hierarchy-}full-v2.json`) staat nog NIET live -- `make tiles-full` (tegelpyramide) + `make publish-zenodo`/`make publish-huggingface` + de site-deploy moeten nog gedraaid worden om 'm daadwerkelijk te publiceren. Tot die tijd blijft de oude `-full`-export (zonder de gefixte hiërarchie) live.
- Oekraine verder extraheren/taggen (zie hierboven).
- Issues #299 (topic_id single-value → many-to-many), #300 (crawler multi-topic), #301 (offsite DB-backup), #303, #308, #309, #311 (zie boven) staan nog open, geen van alle opgepakt.
- Prijs op de HF-router in de gaten houden -- kan elk moment weer normaal gaan rekenen (zoals eerder ook al eens kortstondig gebeurde).

## Stand bij einde sessie (2026-09-12, video-shorts vereenvoudigd naar landscape, issue #268) — begin hier bij een nieuwe sessie

Vervolg op de sessie hieronder: op verzoek van de gebruiker is de verticale
9:16-crop (en daarmee de hele OpenCV-gezichtsdetectie) losgelaten. De 4
huidige steekproefclips in `bipolariteit-data` (`shorts/`) zijn nu gewoon
landscape (960x540, originele 16:9), zonder crop. `scripts/build_shorts_sample.py`
is dienovereenkomstig vereenvoudigd (`render_clip` schaalt alleen nog,
geen `extract_frame`/`detect_speaker_x_fraction`/`build_crop_x_expr` meer),
`opencv-python-headless` is uit `pyproject.toml`/`uv.lock`. De
selectie-restricties die alleen voor de crop-betrouwbaarheid bestonden
(`turn_type='woordvoerder'`, alleen plenaire zaal) zijn ook losgelaten —
zonder crop maakt de cameravoering niet meer uit, dus commissiezalen en
interrupties doen nu ook mee. Nog steeds niet gebouwd: de eigenlijke
homepage-previewcomponent uit issue #268 zelf.

## Stand bij einde sessie (2026-09-07 avond, video-shorts steekproef, issue #268) — begin hier bij een nieuwe sessie

**Resultaat van de avond staat in geen verhouding tot de tijd die erin ging.** Concreet opgeleverd: 8 verticale (9:16) preview-clips + `manifest.json` in `bipolariteit-data` (`shorts/`), plus twee kleine, op zichzelf staande fixes die tussendoor zijn meegenomen (ffmpeg in de devcontainer, en een bug waarbij de debatdatum nergens zichtbaar was — zie onder). Dat is veel minder dan er in een avond had gepast; de reden staat hieronder, zonder het mooier te maken dan het was.

**Procesfout, niet verdoezelen**: het overgrote deel van de sessie ging op aan het kiezen van een crop-positioneringsmethode voor de verticale video, niet aan de video's zelf:
1. Eerste aanpak: een vision-LLM (qwen/qwen3.6-27b via LM Studio) laten kijken naar een frame en de positie van de spreker laten teruggeven. Werkte een enkele keer in een handmatige test, maar liep in de batch-run herhaaldelijk vast — timeouts, lege antwoorden, en minutenlange hangs zonder duidelijke oorzaak. Er is te lang doorgeknutseld aan deze aanpak (hogere timeouts, meer tokens, een retry) in plaats van na de eerste paar mislukkingen de aanpak zelf ter discussie te stellen.
2. Onderweg ook een tijdelijke "fallback naar center-crop bij mislukte detectie" gebouwd, terwijl de gebruiker expliciet had aangegeven geen fallbacks te willen — moest terugdraaien en de foutafhandeling opnieuw doen (mislukte detectie = clip overslaan, niet gokken).
3. Pas na expliciete, herhaalde ongeduld-signalen van de gebruiker overgestapt op een lokale OpenCV Haar-cascade-detectie — geen netwerk, milliseconden per frame, en meteen stabiel. Dit had de eerste keuze moeten zijn: geen externe afhankelijkheid, geen latency-risico, en achteraf ruim voldoende nauwkeurig (8/10 bruikbaar op de eerste run, na een gerichte fix — alleen plenaire zaal, geen interrupties — voor de twee mislukkingen).
4. Ook de review zelf ging moeizaam: afbeeldingen getoond via de tool-uitvoer kwamen niet aan bij de gebruiker, en pas na meerdere keren "ik zie niks" is overgestapt op bestanden direct in de workspace zetten. Had eerder getest moeten worden of beeldweergave uberhaupt aankwam, in plaats van dezelfde methode een aantal keer te herhalen.

**Wat wél goed ging**: de selectielogica (tags + interruptiebonus, alleen `turn_type='woordvoerder'`, alleen plenaire zaal) werkte in één keer goed en leverde herkenbare, emotioneel geladen fragmenten op (BBB/stikstof, asielcommissiedebatten, abortus). Ook de twee losstaande fixes (ffmpeg-devcontainer, debatdatum) waren scherp afgebakend en snel geverifieerd.

**Nog te doen** (issue #268 zelf is dus nog niet gebouwd, alleen de datasteekproef ervoor):
- Geen frontend-pagina/component toont deze shorts nog — de eigenlijke homepage-preview (waar issue #268 om vraagt) moet nog gebouwd worden.
- De huidige steekproef is klein (8 clips, 5 sprekers deels dubbel) en beperkt tot de plenaire zaal — met de nu werkende, snelle OpenCV-pipeline (~10s/clip, geen LLM-latency) is opschalen naar een groter aantal debatten in principe goedkoop; commissiezalen zijn bewust uitgesloten (camera toont daar vaak niet de spreker, zie `scripts/build_shorts_sample.py`'s moduledocstring) en zouden een andere aanpak nodig hebben om ook mee te nemen.
- Bij het opschalen: het frame voor gezichtsdetectie wordt nu op het exacte begin van de clip gepakt, wat één keer een brede overzichtsopname trof i.p.v. de close-up (uitzending zoomt soms pas na een seconde of twee in) — een frame iets later in de clip nemen is een goedkope verbetering, niet gedaan in deze sessie.
## Stand bij einde sessie (2026-09-10, embedcache naar parquet + OOM-crash op de volle-dataset-embed opgelost, issue #281) — begin hier bij een nieuwe sessie

**Context**: op `feature/281-embed-pipeline-en-crawl-fixes` (1 bestaande commit, nog niet gepusht/PR'd; issue #281 zelf staat nog open). `make embed` op de volle dataset (`--start 2000-01-01 --end vandaag --label full`, ~767.700 documenten na filtering) crashte met `Error 137` (SIGKILL, OOM) — ná het eigenlijke, dure embedden (632.110 nieuwe vectoren in 21.021,9s, plus 135.590 al gecacet), dus in het samenvoegen tot het eindresultaat.

**Drie samenlopende oorzaken gevonden** (de eerste twee fixes bleken elk op zich onvoldoende -- pas na alle drie draaide `make embed` daadwerkelijk zonder crash, geverifieerd):
1. De incrementele embedcache (`pipeline/embed/documents.py`, deze sessie eerder al van één groot `.npz`-bestand naar losse, append-bare parquet-delen omgebouwd — zodat een onderbreking mid-run niet alle al opgehaalde batches kost) las die parquet-delen via **pandas** in. Een vector-kolom als Python-list-van-floats kost 6-10x zoveel geheugen als de ruwe float32-data (elke float wordt een los Python-object) — op ~768k × 1024-dim is dat het verschil tussen ~3 GB en 20-30 GB. **Fix**: rechtstreeks via pyarrow lezen/schrijven, vector-kolom expliciet als `fixed_size_list<float32>` i.p.v. via pandas een generieke `list<double>`.
2. De onderbroken run had voor het `full`-label **19.754 losse parquet-bestanden** geschreven (één per batch van 32), omdat `_append_batch()` na élke batch meteen wegschrijft. Compactie naar minder bestánden bleek niet genoeg: `pyarrow.dataset.to_batches(batch_size=...)` respecteert de onderliggende row-group-grootte van de bronbestanden en negeert de gevraagde batch_size bij het lezen -- de eerste compactiepoging leverde 8 bestanden met **nog steeds 19.768 row groups** op (de kleine batches zaten alsnog in het bestand, alleen niet meer als apart bestand). **Fix**: bij het compacteren zelf rijen accumuleren tot een drempel (~100k) vóór wegschrijven (`pa.concat_tables` + `row_group_size=`), niet vertrouwen op `to_batches()`'s batch_size. Resultaat: 8 bestanden, 11 echte row groups.
3. Zelfs met (1) en (2) gefixt bleef laden van de volle cache **~9-11 GB piekgeheugen kosten voor ~3,1 GB ruwe data** (~3x overhead), ook via kale pyarrow (`Dataset.to_table()`/`to_batches()`) -- stap-voor-stap geprofileerd (`resource.getrusage().ru_maxrss`) tot de oorzaak gevonden: **`Dataset`-scanning prefetcht standaard fragmenten/batches vooruit (readahead)**, onafhankelijk van de leessnelheid van de consument. **Fix**: `Dataset.scanner(..., use_threads=False, batch_readahead=0, fragment_readahead=0)` i.p.v. `Dataset.to_batches()`/`.to_table()` rechtstreeks, batch-voor-batch in een voorgealloceerde numpy-matrix kopiëren. Piekgeheugen voor het laden van de volle `full`-cache (767.743 vectoren): van ~11,5 GB naar **~6,0 GB**.

**Geverifieerd, écht dit keer**: `make embed` op de volle dataset (2000-01-01 tot vandaag, alle topics, 767.700 documenten) draait nu door zonder crash -- `embeddings-cache geladen ... (alle 767700 gevraagde vectoren al aanwezig)` gevolgd door `767700 documenten geëmbed/gecached (dim=1024)`, geen Error 137 meer.

**Nog niet gedaan, bewust**:
- `_append_batch()` flusht nog steeds na élke batch van 32, dus zal bij een volgende grote from-scratch-run (bv. een heel nieuw label) opnieuw duizenden losse bestanden/kleine row groups produceren zoals hierboven. Zou een buffer moeten krijgen (bv. pas wegschrijven per ~2000-5000 documenten) vóór een volgende grote run vanaf nul, anders herhaalt het patroon (compacteren achteraf blijft mogelijk maar is extra werk).
- Nog geen commit/PR van dit werk (branch `feature/281-embed-pipeline-en-crawl-fixes`, 1 bestaande commit, nog niet gepusht; geen PR).

---

**Vervolg dezelfde sessie -- UMAP op de volle dataset, devcontainer-memory ontoereikend, verhuisd naar host**:

`scripts/experiment_umap_documents.py` (dezelfde ~768k-documenten-run) crashte herhaaldelijk met OOM in de devcontainer, ook nadat het Docker Desktop-geheugenbudget van 15 GB naar 32 GB werd opgehoogd (Resources-instelling, VM-breed, los van deze repo) -- `umap.UMAP`'s nearest-neighbor-opbouw (NN-descent) op ~768k x 1024-dim piekte daar nog steeds tegen de limiet aan (cgroup `oom_kill`-teller bevestigde dit meermaals). **Fix in code**: `low_memory=True` toegevoegd aan `run_umap()` (`scripts/experiment_umap_arguments.py`) -- helpt, maar bleek op 32 GB nog niet genoeg. **Definitieve fix**: gebruiker draaide de run op de host (macOS, 64 GB) in plaats van in de devcontainer-sandbox -- lukte daar wel. Belangrijk voor een volgende keer: dit is dezelfde soort geheugendruk als de eerdere `make embed`-crashes, maar in een heel ander codepad (UMAP/sklearn i.p.v. de parquet-cache) -- de structurele oplossing (meer devcontainer-geheugen, of deze stap principieel op host draaien) is nog geen definitief besluit, alleen een werkende omweg.

**Tiling (`make tiles`/`pipeline/tiling/build_pyramid.py`) had drie eigen, losse problemen, ook pas op host succesvol afgerond**:
1. dask (`--group tiling`) stond niet geïnstalleerd/draaide niet in de devcontainer (`postStartCommand` had het nooit gestart na een container-restart) -- handmatig `dask scheduler`/`dask worker` opnieuw opgestart, één keer met een kapotte shared-venv-install onderweg (zie hieronder).
2. **Shared-venv-corruptie, opnieuw** (zelfde patroon als een eerdere sessie, nu opnieuw gebeurd): `uv sync --group tiling`/`uv run` vanuit deze Linux-devcontainer-sandbox tegen dezelfde gemounte `.venv` als de macOS-host gebruikt corrumpeerde de venv (numba/llvmlite/umap-learn zijn platform-specifieke compiled packages) -- host kreeg `ModuleNotFoundError: No module named 'umap.distances'`. Hersteld met `rm -rf .venv && uv sync` op de host. **Les, nog scherper dan de vorige keer**: geen `uv run`/`uv sync` meer vanuit de devcontainer als de gebruiker tegelijk zelf op de host werkt -- dit is nu twee keer misgegaan.
3. `build_pyramid.py`'s `dask.compute(*encode_tasks)` (blocking, gathert alle 16.546 tegel-taken in geheugen vóór er iets weggeschreven wordt) veroorzaakte herhaalde worker-OOM's/herstarts in de devcontainer, met **totale terugval van voltooide taken** bij elke crash (geen tussentijdse persistentie) -- een client-nanny-herstart alleen redt de taken niet. Precies voorspeld door een bestaand codecommentaar (`build_pyramid.py:115-120`: "met meer punten... alleen maar erger wordt"). Niet gefixt (zou `client.compute()` + `as_completed()`-streaming vergen i.p.v. blocking `dask.compute()`), enkel omzeild door op host (64 GB) te draaien. Issue #287 (architectuurreview) noemt bovendien een ándere, losstaande `make tiles`-breuk (`morecantile`/`pydantic`-incompatibiliteit op Python 3.14) die deze sessie niet is tegengekomen -- vermoedelijk toeval in dependency-resolutie, niet gefixt of onderzocht.

**Topic losgekoppeld van de embed-/clusterworkflow (op expliciet verzoek, issue #288 aangemaakt voor het vervolg)**:
- `pipeline/embed/documents.py`: `fetch_documents()`/`fetch_and_embed()` doen geen join meer op `topics`/`topic_id`, geen `topic_slug`-selectie, geen `full_range_topic_slugs`-parameter/vlag meer.
- **`NOISE_ACTIVITEIT_SOORTEN` (blocklist) vervangen door `WANTED_ACTIVITEIT_SOORTEN` (whitelist)**, op expliciet verzoek: alleen `Plenair debat`/`Commissiedebat`/`Algemeen overleg`/`Wetgevingsoverleg`/`Vragenuur` (+ NULL) blijven over. Dat sluit ook `Notaoverleg` (52.868 rijen) en de kleine restcategorieën uit, niet alleen de drie expliciet genoemde (`Rondetafelgesprek`/`Hoorzitting`/`Technische briefing`) -- gevolg: 767.700 -> 731.985 punten in de nieuwe run.
- `scripts/experiment_umap_documents.py`: `topic_labels`/`topic_breakdown` volledig verwijderd uit de clusterlabel-functies (`label_hierarchical_clusters`/`label_multilevel_clusters`, incl. de `to_node()`/`build_cluster_tree()`-boomopbouw -- kostte twee ronden losse `KeyError`-fixes, telkens een gemiste plek). Topic wordt nog wél teruggekoppeld, maar puur als late, losse join vlak vóór het bouwen van `points` (t.b.v. de topic-legenda/kleuring in `PlenairMap.vue`/`TiledPlenairMap.vue`, die dat gedrag ongewijzigd behouden) -- niet meer als eigenschap van de fetch-/clusterworkflow zelf. Die late join deed eerst `WHERE d.id IN (...)` met ~732k losse parameters -- sqlite's parameterlimiet overschreden (`too many SQL variables`) -- gefixt door gewoon de hele `id->slug`-mapping in één keer op te halen (twee smalle kolommen, goedkoop) i.p.v. te filteren/chunken.
- `frontend/src/components/PlenairMap.vue`/`PlenairBenchmark.vue` hebben nog een `topic_breakdown`-TS-type gedeclareerd maar gebruiken het nergens (gecontroleerd) -- geen impact, wel een dooie typedeclaratie voor een volgende opruiming.

**Eindresultaat, geverifieerd op host**: volledige pijplijn (embedcache hergebruikt, geen her-embed nodig -- 731.985/731.985 al aanwezig) -> UMAP -> N-laagse clustering (390 grove clusters) -> `docs/poc/umap-documenten/{clusters,hierarchy,plot}-full.{json,html}` -> `data/export/plenair-map-full.json` (118,9 MiB, ruim boven de 25 MiB Cloudflare-grens maar dat is verwacht/onschadelijk -- dit bestand voedt alleen de tiling-stap, wordt niet direct als Workers-asset geserveerd) -> `data/export/plenair-map-full.pmtiles` (14.843 tegels). Niet gepreviewd in de frontend (zou `data/export/gepubliceerd/` moeten raken, en daar stond al een niet-gerelateerde, ongecommitte wijziging -- bewust niet aangeraakt).

**Nog niet gedaan / openstaand voor een volgende sessie**:
- Niets van dit alles is gecommit of in een PR gezet (nog steeds branch `feature/281-embed-pipeline-en-crawl-fixes`).
- `build_pyramid.py`'s blocking-gather-geheugenprobleem (zie hierboven) niet gefixt, alleen omzeild via host.
- `_append_batch()`'s ontbrekende flush-batching (uit het eerste deel van deze entry) nog steeds niet gedaan.
- Issue #288: topic als losse, latere join formaliseren (nu een ad-hoc implementatie in `main()`, geen herbruikbare functie).
- De `.pmtiles` niet visueel geïnspecteerd/gevalideerd (alleen succesvolle build bevestigd via tegelaantal).

**Volgende sessie, concrete eerste stap**: beslissen over commit/PR-indeling van dit werk (waarschijnlijk meerdere losse commits: parquet-cache-fix, topic-decoupling+whitelist-filter, UMAP `low_memory`-fix), dan pas verder (tiles visueel inspecteren, of de blocking-gather-fix in `build_pyramid.py` alsnog doen).

## Stand bij einde sessie (2026-09-07, redactiemethode herzien: neutrale per-relatie engagement-check i.p.v. tweezijdige pro/contra-redactie, issue #252) — begin hier bij een nieuwe sessie

**Kernbeslissing van deze sessie**: de tweezijdige pro/contra-redactie uit de vorige sessie (zie de entry hieronder, geshipt in PR #278) bleek bij de eerste échte live-run **niet te discrimineren**. Vier verschillende varianten daarvan zijn getest (rolgebonden pro/contra, neutraal met 2 categorieën, neutraal met 3 categorieën, per-relatie geïsoleerd) en elke keer convergeerde het model naar hetzelfde label voor alle relaties in een topic, met wel specifieke maar niet-onderscheidende onderbouwing. Een vijfde variant — een zuiver feitelijke, functionele vraag zonder rol of geldigheidsoordeel ("engageert dit argument aantoonbaar met de kern van het andere?", vergelijkbaar met IBM Project Debater's "rebuttal detection") — discrimineerde wél, getest op alle vier topics (conflict: 18/28 True; support: 8/16 True op stikstof), en is nu de geïmplementeerde, geverifieerde aanpak. Onderzoeksliteratuur (zie hieronder) bevestigt dit als een bekend fenomeen: LLM-as-judge stort in bij interpretatieve/normatieve taken, blijft betrouwbaar bij feitelijke/structurele taken.

**Branch-status, belangrijk voor de volgende sessie**: dit werk staat op `experiment/252-bidirectionele-weerlegging` (8 commits boven `feature/252-aif-relation-schema`, 35 bestanden diff), **niet gemerged en geen PR**. `feature/252-aif-relation-schema` heeft al een open PR (**#278**) met de oude, inmiddels weerlegde tweezijdige-redactie-aanpak — die PR moet worden bijgewerkt of vervangen vóór merge, niet zomaar gemerged zoals hij nu is. Eerste stap volgende sessie: beslissen hoe deze twee branches samenkomen (PR #278 updaten met deze branch, of een nieuwe PR openen vanaf `experiment/252-bidirectionele-weerlegging` en #278 sluiten).

**Hoe we hier kwamen (kort, vier iteraties in één sessie)**:
1. Live run van de PR #278-aanpak op stikstof: van 8 voorgestelde kern-tegenstellingen overleefden er maar 1-3, terwijl abortus (kleiner topic) er 9 had. Onderzoek naar de 8 conflict-relaties liet zien dat alle 8 toevallig dezelfde vorm hadden (target=pro-argument, premise/aanvaller=contra-argument), en de pro-redacteur kende in alle overlevende gevallen consequent "winst" toe aan het pro-argument — een rol-/labelgebonden bias, geen inhoudelijk oordeel.
2. Een neutrale beoordelaar zonder rol, met interpretatieve categorieën (`logische_ondermijning`, later ook `afweging`), bleek hetzelfde euvel te hebben: telkens 8 van de 8 relaties identiek geclassificeerd, ook bij elke relatie in een eigen geïsoleerde call (dus geen batch-/besmettingseffect).
3. Onderzoeksprompt opgesteld (`docs/research/prompt-llm-judge-betrouwbaarheid-argumentenboom.md`) en het resulterende rapport (`docs/research/Betrouwbaarheid LLM Argumentrelaties.md`, extern gegenereerd) bevestigde de werkhypothese: LLM-as-judge is onbetrouwbaar bij normatieve taken (bij politiek debat zijn vrijwel alle argumentparen zowel als "logische tegenspraak" als als "afweging" te beargumenteren — geen categoriefout van het model, maar een principiële onderbepaaldheid van het materiaal, pragma-dialectisch onderbouwd via Van Eemeren). Aanbeveling 4 (architecturale scheiding van structuur en kwaliteitsoordeel, naar IBM Project Debater's "rebuttal detection") bleek wél te werken.
4. De gevalideerde aanpak volledig doorgevoerd naar productiecode (niet alleen los getest), alle vier topics opnieuw gegenereerd, frontend/schema/tests bijgewerkt, `/over` + `docs/pipeline.md` gecorrigeerd.

**Wat concreet is aangepast t.o.v. PR #278's aanpak**:
- `pipeline/confrontatie_tree.py`: `merge_engagement_checks()` vervangt `merge_reviews()`. Een relatie waarvan de check "nee" antwoordt verdwijnt; de rest krijgt een `reden` (korte, per-relatie onderbouwing) i.p.v. `weak_link`/`beoordeeld_door`/`confidence` — geen tussenvorm meer, want er is geen onenigheid meer om te meten.
- `pipeline/schemas/argument_tree.schema.json`: relaties hebben nu `reden` i.p.v. de drie oude velden.
- `scripts/agy_run_confrontatie_tree.py`: orkestratie doet nu 1 structureer-call + **N losse redactiechecks** (was 1 + 2) — elke relatie in een eigen, geïsoleerde call. Bewuste keuze, vergelijkbaar met hoe `scripts/agy_run_tagging_batch.py` per item werkt: getest en vergeleken met batchen (alle relaties in 1 call), batchen bleek 3 van de 8 antwoorden te laten omklappen t.o.v. losse calls voor identiek dezelfde relaties.
- `pipeline/prompts/boomredactie_rebuttal_detection.md` (conflict) en `boomredactie_support_check.md` (support) vervangen `boomredactie.md` (blijft in de repo staan als historisch artefact van de verworpen aanpak, niet meer aangeroepen door productiecode).
- Frontend: het "⚠ zwakke koppeling"-badge (`ArgumentConfrontatieKaart.vue`, `ArgumentTree.vue`) is **verwijderd** — geen onenigheid meer om te tonen, alleen een ja/nee-check per relatie. `Kid`/`Band`-types dragen nu `reden` i.p.v. `weak_link`.
- `scripts/pipeline_status.py`, `pipeline/build_static_data.py`, `frontend/src/pages/status.astro`: `weak_link`-telling uit de statusrapportage verwijderd.
- **Bug gevonden tijdens verificatie**: `argument_tree_gemini.md`'s eigen voorbeeld-JSON stond met kleine letter (`"gist": "vergunningverlening loopt vast"`), en het model volgde dat letterlijk — alle vandaag gegenereerde gists kwamen zonder hoofdletter uit de LLM (was hoofdletter vóór deze sessie). Prompt gecorrigeerd (expliciete instructie + hoofdletter-voorbeeld) voor toekomstige runs; `.ack-gist::first-letter { text-transform: uppercase }` als CSS-vangnet zodat de al gegenereerde data er meteen correct uitziet zonder opnieuw te hoeven draaien.

**Live geverifieerd, dit keer écht** (in tegenstelling tot de vorige sessie, waar agy-login niet lukte): agy werkte deze sessie wel (host, buiten deze devcontainer-sandbox). Onderweg wat gedoe met een agy-versie-upgrade (1.1.11 -> 1.1.27 tijdens de sessie) die de eerder gedocumenteerde scoped `permissions.allow`-regels brak (nieuwe `find`-aanroep, en gescoopte `command(<naam>)`-regels bleken bij deze versie sowieso onbetrouwbaar te matchen) — uiteindelijk opgelost met een brede `command(*)`/`read_file(*)`-regel in de host-settings.json (niet in code). Ook `--print-timeout` toegevoegd (agy's eigen default van 5 min liep vast bij het grootste topic), en een lokale (non-Docker) agy-fallback voor sandboxes zonder docker. Alle vier topics zijn zo écht opnieuw gegenereerd: stikstof 6 confrontatie-banden (was 1 met de PR #278-aanpak), asiel 3 (was 2), abortus 6 (was 9, maar nu aantoonbaar onderbouwd i.p.v. gestapeld zonder discriminerend filter), energietransitie 3 (was 1). Visueel bevestigd via Playwright (host-Chrome-container): banden renderen correct, geen badge meer, geen nieuwe console-errors.

**Belangrijke procesfout deze sessie, niet verdoezelen**: meerdere keren `uv run python -c "..."` gedraaid vanuit deze Linux-devcontainer-sandbox tegen dezelfde gedeelde `.venv`-map die de gebruiker op macOS gebruikt voor de echte agy-runs — dat corrumpeert de venv (platform-specifieke compiled packages als sklearn/numpy door elkaar geïnstalleerd/gelinkt), en heeft minstens één keer een venv-rebuild op de host getriggerd die de gebruiker moest herstellen (`rm -rf .venv && uv sync`). Vanaf nu: verificatie op gedeelde JSON-bestanden via `Read`/`jq`/`grep`, geen `uv run` als de gebruiker tegelijkertijd zelf `make`/`uv` op de host draait.

**Bewust nog niet gedaan**:
- PR #278 is niet bijgewerkt of gesloten — zie "branch-status" hierboven, dit is de belangrijkste openstaande actie.
- `llm_calls`-logging voor de redactiecalls is nog steeds niet aangesloten (zelfde gat als vorige sessie, geen regressie).
- Geen `AIF.sql`/AIFdb-corpus-validatie van de nieuwe engagement-check-aanpak (zou een mooie externe validatiestap zijn, zie ook de onderzoeksvraag over IAA in `docs/research/prompt-llm-judge-betrouwbaarheid-argumentenboom.md`).
- Aanbeveling 3 uit het onderzoeksrapport (impliciete waardepremisse expliciet laten maken door het model, i.p.v. een label forceren) is niet uitgeprobeerd — inhoudelijk het interessantste vervolgspoor voor een toekomstige sessie, past goed bij de missie van de site (waarom praten twee kanten langs elkaar heen) in plaats van bij een simpel pass/fail-filter.
- `scripts/test_*.py`-bestanden van vandaag (`test_bidirectionele_redactie.py`/`test_redactie_per_relatie.py`/`test_rebuttal_detection.py`/`test_support_check.py`) zijn eenmalige onderzoeksscripts, geen onderdeel van de reguliere testsuite (`uv run pytest tests/` raapt ze niet op, ze staan in `scripts/` met een `--topic`-CLI, niet in `tests/`) — bewust laten staan als reproduceerbare documentatie van het onderzoek. `test_rebuttal_detection_batch.py`/`boomredactie_rebuttal_detection_batch.md` (de geteste-en-afgewezen batchvariant) zijn wél verwijderd, op verzoek -- de bevinding staat al vastgelegd in issue #252 en hierboven, het script zelf voegde daarna niets meer toe.

**Volgende sessie, concrete eerste stap**: PR #278 en `experiment/252-bidirectionele-weerlegging` samenbrengen (zie branch-status), dan pas verder bouwen. Overweeg daarna aanbeveling 3 (impliciete premisse expliciet maken) als volgende inhoudelijke stap, gezien de sterke connectie met wat deze site probeert te laten zien.

## Stand bij einde sessie (2026-09-06, redactie wordt de boomstap + AIF-relatiemodel, issue #252) — begin hier bij een nieuwe sessie

**Kernbeslissing van deze sessie**: `pipeline/redactie_check.py` (Stage 2, bedoeld als corpus-brede bias-check) bleek nooit echt te draaien -- 5 `redactie_reviews`-rijen op 5.283 documenten (0,09%), 0 gelogde `llm_calls`. Redactie is niet weggegooid maar **verplaatst**: een stap in de argumentenboom zetten *is* nu de redactionele handeling zelf, uitgevoerd door een pro- en een contra-redacteur die onafhankelijk dezelfde concept-boom beoordelen (niet de vier taxonomie-perspectieven, expliciet gecorrigeerd tijdens het plannen). Reden om dit specifiek bij de boom te leggen en niet bij losse tags: een tag hangt aan één sprekerbeurt en is aan het citaat zelf te controleren; de boom selecteert en ordent (~1976 -> ~30 argumenten, gekoppeld tot banden) en juist daar kan bias ontstaan.

Plan-bestand van deze sessie (niet in git): `de-workflow-argumentenboom.md`-achtige naam, zie sessie-eigen `/home/vscode/.claude/plans/`.

**Nieuwe workflow** (vervangt `make confrontatie-tree` + `make redactie`, nu allebei samengevoegd onder `make redactie`):
1. **Structureren** (`pipeline/prompts/argument_tree_gemini.md`, herschreven): één Gemini-call selecteert + bouwt een concept-boom (`nodes`/`relations`/`coordinatieve_groepen`/`twijfelachtige_classificaties`), vast uitvoercontract i.p.v. het oude "kies zelf een structuur"-verzoek (dat overigens een echt gat bleek: `build_bands_and_losse` las met `.get("pro", {})`, dus een hernoemde topsleutel gaf een **lege boom zonder foutmelding**).
2. **Redactie, twee keer** (nieuw `pipeline/prompts/boomredactie.md`, parameter `{kant}`): pro- en contra-redacteur beoordelen elk, onafhankelijk, elke relatie uit stap 1 op dezelfde concept-boom (`relation_index`-gebaseerd, geen argumenttekst-parafrasering).
3. **Samenvoegen + valideren** (nieuw `pipeline/confrontatie_tree.py::merge_reviews`, zuivere Python, geen LLM): beide kanten eens -> relatie staat, `weak_link=false`; precies één kant eens -> relatie blijft staan maar `weak_link=true`; geen van beide -> relatie **verdwijnt** (geen relatie in de boom die niemand overeind houdt). Resultaat gevalideerd tegen `pipeline/schemas/argument_tree.schema.json` vóór wegschrijven.

**AIF-datamodel** (gevonden na een korte deep-dive op verzoek van de gebruiker, "kijk wat argtech gebruikt", #177): het Argument Interchange Format modelleert een relatie niet als een gelabelde edge maar als een eigen object (RA-node = steun, CA-node = conflict) met premisse(n) en één doel -- dekt zo coördinatieve groepen (meerdere argumenten die een claim gezamenlijk dragen) natiever dan een platte `{from,to,relation_type}`-edge. Officiële bronnen geverifieerd: AIF-spec (arg-tech.org), het officiële `AIF.sql`-schema, en Lawrence & Reed (2019) *Argument Mining: A Survey* (Computational Linguistics 45(4)) -- die laatste bevestigt ook AIFdb Corpora als bruikbare externe validatieset (14.000+ argumentkaarten, 14 talen) en onderbouwt methodisch waarom semantische similarity (bge-m3, niet syntax/signaalwoorden) het sterkste support/attack-classificatiesignaal is.

- Nieuw `pipeline/schemas/argument_relations.schema.json`: projectonafhankelijk geschreven (Engelse descriptions, geen verwijzing naar onze eigen tabellen -- expliciet verzoek "mag wel in onze namespace, maar algemeen bruikbaar"), AIF-kern (support/conflict, `premise_argument_ids`, `scheme`, `weak_link`, `confidence`).
- Nieuw `pipeline/schemas/argument_tree.schema.json`: boom-specifieke superset (`nodes`, `relations` + `thema`/`beoordeeld_door`, `coordinatieve_groepen`, `twijfelachtige_classificaties`) -- **bewust gedupliceerd** i.p.v. cross-file `$ref`, zodat elk schema zelfstandig valideert zonder schema-registry.
- **Zijspoor teruggedraaid**: eerder in deze sessie een `argument_oppositions` -> `aif_relations`/`aif_relation_premises`-migratie gebouwd (schema + live-DB-migratie + hernoeming), voordat duidelijk werd dat de zichtbare boom die tabel helemaal niet leest (`build_confrontatie_export.py` leest uitsluitend de Gemini-tree-JSON). Compleet teruggedraaid (tabellen gedropt, migratiescript verwijderd) toen de scope naar "redactie = boomstap" verschoof.

**Wat concreet is aangepast**:
- `pipeline/build_confrontatie_export.py`: `_flatten_stance`/`_mark_descendants` vervangen door `_build_registry` (leest `nodes`/`relations`, `stance` komt nu uit de DB i.p.v. uit de tree-JSON, die kent geen kant-indeling meer). `kids` is niet langer een platte lijst id's maar een lijst `{id, weak_link, scheme}`-objecten -- anders verdwijnt het #252-signaal juist bij onderbouwingen. `oppositie` per band draagt nu `scheme`/`weak_link`/`confidence` i.p.v. het oude `relation_type` (nooit gelezen door de frontend, geverifieerd met een grep).
- `pipeline/redactie_check.py` + `pipeline/prompts/redactie_bias_check.md` **verwijderd**, met alle uitlopers: `argument_oppositions`/`redactie_reviews`-tabellen (schema.sql + live DB), `export_argument_doc.py`'s `--include-known-oppositions`/`fetch_oppositions`, `build_static_data.py`'s `fetch_oppositions`/`fetch_redactie_reviews`/de `redactie`-prompt-reconstructie, `scripts/pipeline_status.py`'s redactie-tellingen (vervangen door `argumentenboom_banden`/`argumentenboom_weak_link`, gelezen uit de JSON-export, geen DB-query), `scripts/periode_workload.py`'s ongebruikte redactie-telling, `scripts/backfill_voorzitter_turns.py`'s cascade-delete op de verdwenen tabel. `frontend/src/pages/status.astro`'s "Documenten redactie-gecheckt"-balk vervangen door een boom-statusregel. `Argument.oppositions`/`Argument.document.redactie_review` (frontend `types.ts`/`leanArgument.ts`/testfixtures) verwijderd -- geverifieerd ongebruikt in alle `.vue`/`.astro`-rendering vóór verwijdering.
- Frontend: `ArgumentTree.vue`/`ArgumentConfrontatieKaart.vue` tonen nu een "⚠ zwakke koppeling"-marker op elke kaart wiens relatie `weak_link=true` heeft (kid-onderbouwing én band-oppositie).
- Tests: `tests/test_confrontatie_tree.py` (nieuw, 6 tests voor `merge_reviews`, puur Python/geen LLM), `tests/test_build_confrontatie_export.py` herschreven naar het nieuwe invoerformaat (**assertions ongewijzigd**, dat was het hele punt van de herbouw). `uv run pytest tests/` groen (149).
- **Bijvangst, "own de bugs" (niet afschuiven ook al leek het pre-existing)**: `frontend/src/lib/correspondence.test.ts` had 5 falende tests door een stale `prince`-gouden-fixture (data was gegroeid sinds de fixture voor het laatst gegenereerd was). `make ca-fixture` opnieuw gedraaid, alle 85 frontend-tests weer groen.

**Live geverifieerd, met een addertje**: geen werkende agy-login in deze sessie (`~/.gemini/bin/agy` bestaat lokaal, versie 1.1.19, maar geen OAuth-sessie; ook geen Docker beschikbaar in de devcontainer voor de oude `docker/agy`-route). Om de nieuwe `build_confrontatie_export.py` + frontend-marker toch tegen échte data te verifiëren: het bestaande, getrackte `data/export/argument-trees/stikstof.json` (oud formaat) tijdelijk terugvertaald naar het nieuwe schema (scratchpad-script, niet gecommit), er echt doorheen gedraaid, en de marker met Playwright/de host-Chrome-container bevestigd zichtbaar (zie #271 voor die devcontainer-koppeling). Daarna de originele, getrackte `stikstof.json` teruggezet (`git checkout --`) -- er is geen namaak-data gecommit.

**Bewuste, niet-verholen breaking change**: de drie getrackte `data/export/argument-trees/{stikstof,abortus,asiel}.json`-bestanden staan nu in het **oude** formaat (platte kid-id's, `oppositie.relation_type` i.p.v. `scheme`/`weak_link`) en zijn dus incompatibel met de nieuwe `ArgumentTree.vue`. **Vóór de volgende live-deploy moet `make redactie TOPIC=<slug>` opnieuw draaien voor alle 3 topics** (vereist een werkende agy-login, zie `docker/agy/Dockerfile` of de lokale `~/.gemini/bin/agy`-route). Tot die tijd zou de site crashen op de argumentenboom-pagina's.

**Bewust nog niet gedaan**:
- `/over`-pagina's workflowstap 5 ("Bias-check") en `docs/pipeline.md`'s redactie-sectie **niet** herschreven -- pas doen zodra de nieuwe stap daadwerkelijk gedraaid heeft (zelfde principe als de AIF-bronvermelding: de pagina citeert alleen wat al gebeurt).
- `llm_calls`-logging voor de drie nieuwe agy-calls (structureren + 2× redactie) is niet aangesloten -- de bestaande agy-scripts loggen sowieso niet naar `llm_calls` (die tabel is voor de lokale LM-Studio-route), dus dit is geen regressie, maar wel een gat als je verwerkingstijd per model ooit voor de boomstap wilt zien op `/status`.
- `llm_calls.stage`-CHECK-constraint in `schema.sql` bevat nog altijd `'redactie'` als toegestane waarde (0 historische rijen, nooit meer geschreven) -- bewust laten staan, een CHECK wijzigen vereist tabelherbouw (SQLite) en de waarde is onschadelijk-ongebruikt.
- Optie A vs. B voor de kids-kant was al vroeg in de sessie een open vraag (Gemini-prompt zelf laten typeren vs. achteraf samenvoegen met een DB-tabel) -- opgelost door de scope-verschuiving: er is geen aparte DB-tabel meer, dus optie A (alles in de Gemini/redactie-JSON-flow) is de facto gekozen voor zowel kids als opposities.

**Volgende sessie, concrete eerste stap**: agy-login afronden (interactief, buiten deze devcontainer-sandbox om) en `make redactie TOPIC=stikstof` als eerste echte end-to-end-run draaien. Controleer daarbij met name: hoeveel relaties `weak_link=true` krijgen (bij alles-of-niets is er iets mis met `boomredactie.md`, zie de verificatie-sectie van het sessie-plan), en of `nodes[]`/`relations[]` daadwerkelijk schema-valide JSON teruggeeft zonder handmatig bijschaven.

## Stand bij einde sessie (2026-08-31, A0-printposter #215 vervolg: platte GeoJSON-exportmodus) — begin hier bij een nieuwe sessie

Eerste designer-feedbackronde (`docs/design/a0-map/`, zie sessie hieronder) doorgenomen; geen nieuwe designer-input sindsdien binnengekomen. Volgende stap uit de open-lijst opgepakt: de platte/niet-geprojecteerde GeoJSON-exportmodus.

- **`scripts/a0_map/export_clusters_geojson.py --flat`** (nieuw, naast de bestaande `--grid <pad>`-modus, nu een mutually-exclusive-group): slaat `make_rescaler`/de EPSG:3857->WGS84-terugprojectie helemaal over en schrijft de rauwe UMAP-grid-eenheden direct als GeoJSON-coördinaten (`flat_rescale`, alleen afronden). Die reprojectie bestond alleen om uit te lijnen met hoe generieke MVT/PMTiles-viewers de puntenlaag interpreteren (zie het commentaar bij `WEB_MERCATOR_HALF_EXTENT`) -- voor de print-pijplijn is er geen viewer, dus geen reden voor de heen-en-weer-reis. Resultaat: dezelfde ruimte/eenheden als `plenair-map-<suffix>.json`'s punten en dus als `render_design_preview.py` (`render()`'s `load_points()` gebruikt de punten ook al ongewijzigd), dus clusterlaag en puntenwolk lijnen 1:1 uit zonder Mercator-vervorming. QGIS moet zo'n bestand na import expliciet als projectloos/lokale coördinaten behandelen, niet als EPSG:4326 (RFC7946 kent geen `crs`-member meer om dat te declareren).
- Geverifieerd: `--flat` op `plenair-map-clusters-full.json` levert 573 features (zelfde telling als `--grid`), coördinaten liggen in dezelfde grootorde als de brondata-punten (bv. x≈13,35 t.o.v. punten-x-range); bestaande `--grid`-modus ongewijzigd (regressietest gedraaid); `--grid`/`--flat` correct mutually exclusive+required. `uv run pytest tests/` blijft groen (140 tests, geen bestaande tests voor dit script specifiek).
- **Volgende stap**: de daadwerkelijke `datashader`-puntenwolk-rasterrender op A0/300dpi (twee losse rasters, overig vs. de vier topics, per de designer-specs in `docs/design/README.md`), dan QGIS-compositie met deze platte GeoJSON-clusterlaag ernaast, dan de eerste echte A0-PDF-export.

## Stand bij einde sessie (2026-08-30, dataprep-afronding #257 + start A0-printposter #215) — begin hier bij een nieuwe sessie

**Afgerond: dataprep-issue [#257](https://github.com/SiggyF/bipolariteit/issues/257), gesloten.** Losgeknipt van #215 (printposter) en #186 (productiekaart) zodat geen van beide op elkaar hoeft te wachten -- beide trekken voortaan uit hetzelfde gearchiveerde databestand.

- **Labeling-bugfix + N-niveau-generalisatie** (`scripts/experiment_umap_documents.py`): `label_clusters_with_llm()`'s `call_llm()`-aanroep miste `max_tokens` (geen default in `pipeline/tag_arguments.py`) en unpackte een 3-velden `LLMResponse`-NamedTuple naar 2 losse waarden -- vermoedelijk nooit werkend geweest voor deze aanroep. Gefixt, en de functie gegeneraliseerd van hardcoded coarse/fine naar willekeurige N niveaus (`level_ids`/`level_lists`, per-niveau van grof naar fijn, met generieke recursieve `tree`-patch i.p.v. een 2-niveau-specifieke). Representatieve tekstfragmenten in de naamgevingsprompt verruimd van 400 naar 1200 tekens (bevestigd: `texts` was al de volledige, ongetrimde documenttekst). Naamgevingsprompt aangepast naar "zo min mogelijk woorden, 1 als dat kan" (was altijd 2-4 woorden) op expliciet verzoek. Volledige run over alle 5 niveaus (833 clusters, ~4 uur lokaal) geeft nu zinnige, korte namen ("Stikstof", "Ter Apel", "Zorgtoegankelijkheid") i.p.v. de oude TF-IDF-garbage ("Schors", "Seh", "Krullen").
- **Same-level-containment-mitigatie**: nieuw `contained_by_sibling`-veld per cluster (`build_multilevel_clusters`), vlagt het kleinere cluster bij een geometrische containment-violatie op hetzelfde niveau (291 gevlagd op de volle dataset, consistent met `scripts/validate_cluster_hierarchy.py`'s 319-violaties-rapport -- klein verschil omdat de validator per-paar rapporteert, de vlag per cluster). Lichte mitigatie (vlaggen, geen hull-geometrie-herbouw zoals concave hulls/alpha-shapes) -- bewuste keuze omdat dit een eenmalig printproduct is, geen onderhouden interactieve feature.
- **Percentieltrim volledig verwijderd** uit `write_frontend_export`: bleek zelfs bij een 200x lossere drempel (0.01-99.99 i.p.v. 0.5-99.5) exact hetzelfde puntenaantal te houden -- de uitschieters (bijna-lege beurten als "Voorzitter.") zaten in een dichtere bulk dan gedacht. Nu alleen een eindigheids-check (NaN/inf); 135.581/135.633 punten behouden (was 132.921).
- **`export_clusters_geojson.py`**: de lineaire graden-herschaling vervangen door een ECHTE EPSG:3857->WGS84-terugprojectie (`pyproj.Transformer`, relatieve positie in de grid-extent -> echte 3857-meters -> inverse projectie). Reden: de `.pmtiles`-puntenlaag ondergaat dit al impliciet via standaard tegeladressering (quadtree-onderverdeling is schaalinvariant, dus relatieve positie in het custom-grid komt via dezelfde tegel-index terecht als een punt op die relatieve positie in de ECHTE wereldwijde Mercator-piramide) -- expliciet dezelfde transformatie toepassen op de clusterlaag maakt de vervorming CONSISTENT tussen beide lagen i.p.v. een losse, incompatibele lineaire aanname. Bijkomend effect: breedtegraad verzadigt vanzelf bij ±85,05° (echte Web Mercator-grens), geen handmatige clamp nodig. Hull-contouren ook gladgestreken (periodieke kubische B-spline, `scipy.interpolate.splprep`) i.p.v. rechte convex-hull-randen.
- **Zenodo-archivering**: volledige verwerkingsketen gepubliceerd op **https://doi.org/10.5281/zenodo.22181705** (CC-BY-SA-4.0) -- ruwe VLOS-XML per crawl-zoekterm (13 zips, ~137 MiB gecomprimeerd), bge-m3-embeddings (`.npz`, 1,1 GiB, de kostbaarste stap: ~67 min lokale inferentie), en de 4 UMAP/cluster-JSON-exports. README/datadictionary legt uit dat bestandsnamen als `waterstof`/`migratie` crawl-zoektermen zijn (niet losse topics) die via `TOPIC_TITLE_KEYWORDS` (`pipeline/extract_arguments.py`) terug samenkomen tot de 4 echte topics. Geautomatiseerd via de Zenodo REST API (`ZENODO_TOKEN` in `.devcontainer/.env.local`) -- deposition als draft aangemaakt en befuld, publicatie zelf (onomkeerbaar, DOI) bewust door de gebruiker gedaan, niet automatisch.

**Gestart, nog niet afgerond: A0-printposter (issue #215)**. Eerste designer-feedbackcyclus lopend:
- Nieuw `scripts/a0_map/render_design_preview.py` (snelle matplotlib-preview, GEEN printkwaliteit-renderer) -- puntenwolk per onderwerp-kleur + alle 5 clusterniveaus als contourlijnen (lijndikte dikker=grover, per de gekozen hiërarchie-encodering).
- Designer-pakket `data/export/design-handoff/plenaire-kaart-print/` (lokaal, bewust niet ingecheckt -- `data/export/design-handoff/` is al langer volledig gitignored, geen van de bestaande designpakketten staat in git): README (vraag aan designer: kleur, dichtheid, hiërarchie-weergave, typografie/branding), `qgis-project-notes.md`, twee referentiescreenshots (eigen matplotlib-preview + een QGIS-schets met parent_id-categorized kleuring), plus het QGIS-projectbestand (`a0-umap.qgz`) + stijlbestanden (`clusters.qml`/`points.qml`) zelf -- verplaatst hierheen vanuit een eerdere, inconsistente locatie (`docs/design/a0-umap/`) om bij de bestaande designpakket-conventie te blijven (alles voor een designer onder `data/export/design-handoff/<pakket>/`).
- **Nog open, volgende stappen uit het plan** (zie plan-bestand van deze sessie, niet in git): een "platte"/niet-geprojecteerde GeoJSON-exportmodus voor de print-pijplijn (geen Mercator-heenenweer-reis nodig zonder vector-tile-viewer erbij), de daadwerkelijke `datashader`-puntenwolk-rasterrender op A0/300dpi, QGIS-compositie + eerste echte A0-PDF-export, en pas daarna de Illustrator-brandingslag. Wacht nu op de eerste designer-feedbackronde voordat dit verder uitgewerkt wordt.

## Stand bij einde sessie (2026-08-29, tile-pyramide plenaire kaart + bredere commissiedebatten-crawl, issue #215/#253) — begin hier bij een nieuwe sessie

**Uitgangspunt**: issue #215 (hoge-resolutie A0-export van de plenaire kaart) leidde
tot een bredere architectuur: een vector-tile-pyramide (MVT/PMTiles) over de UMAP-
coördinaten, i.p.v. de bestaande platte `plenair-map.json`. Dat lost meteen ook
issue #253 op (machine-leesbaar `cluster`-id per document, want dat is nu gewoon
een MVT-property).

**Deel 1 -- tile-pyramide, afgerond en geverifieerd:**
- Nieuwe subpackage `pipeline/tiling/` (`grid.py`: custom morecantile-grid over de
  UMAP-bounding-box met een "neppe" vlakke CRS; `encode.py`: MVT-encodering per
  tile via `mapbox_vector_tile`; `build_pyramid.py`: CLI, verdeelt tile-encodering
  over dask). Nieuwe `uv`-dependency-group `tiling` (dask[distributed], morecantile,
  mapbox-vector-tile, pmtiles, bokeh). Nieuw Makefile-target `tiles` (los van
  `export`-keten, experimenteel).
- **Persistente dask-cluster**: `dask scheduler`/`dask worker` (built-in dask-CLI)
  op `tcp://127.0.0.1:8786`/dashboard `:8787`, gestart via
  `.devcontainer/devcontainer.json` `postStartCommand` -- overleeft de hele sessie
  i.p.v. per run te verschijnen/verdwijnen. `pipeline/tiling/build_pyramid.py`'s
  `make_client()` verbindt hiermee als het bereikbaar is, anders eigen kortstondige
  cluster als fallback.
- Nieuwe frontend-component `frontend/src/components/TiledPlenairMap.vue` (naast,
  niet i.p.v. `PlenairMap.vue`, die ongewijzigd blijft) + `frontend/src/lib/
  tiledMapTransform.ts` + `plenairMapColors.ts` + testpagina `/tests/tiled-plenair-map`.
  Nieuwe npm-deps: `pmtiles`, `@mapbox/vector-tile`, `pbf` (let op: `pbf@5` exporteert
  geen default meer, gebruik `import { PbfReader } from "pbf"`, niet `import Pbf`).
- **QGIS-bug gevonden en gefixt**: QGIS toonde alle punten als "1 punt". Root cause:
  `mapbox_vector_tile.encode()` liet het MVT-feature-`id`-veld ongezet, decodeerde
  overal als `0` -- QGIS' vector-tile-provider dedupliceert kennelijk op dat id.
  Fix in `pipeline/tiling/encode.py`: `pid` (document-id) als feature-`id` meegeven.
  Geverifieerd (voorheen 2/2, nu 587/587 unieke ids in een steekproef-tile) en
  live bevestigd werkend in QGIS.
- `frontend/public/plenair-map-viewer.html` (nieuw, standalone HTML, CDN-MapLibre +
  pmtiles-protocol, geen npm/build-afhankelijkheid) als tweede, onafhankelijke
  viewer op hetzelfde .pmtiles-bestand -- handig om de tile-data zelf te
  controleren los van `TiledPlenairMap.vue`'s eigen canvas-renderer.

**Deel 2 -- bredere dekking (crawl + ingest), afgerond:**
- `crawlers/tweede_kamer/tweede_kamer/odata.py`'s `vergaderingen_url()` kreeg een
  `soort`-parameter (was hardcoded `'Plenair'`); `verslagen_periode.py`-spider kreeg
  `-a soort=Commissie`. **Let op datumgrens**: de huidige kamerperiode is
  2025-11-12..heden ("Tweede Kamer 2025-heden" in `data/politieke-periodes.toml`),
  niet 2024 zoals eerst aangenomen -- check die toml bij twijfel, niet uit het hoofd
  aannemen. Gecrawld: 265 Commissie-Vergaderingen gevonden, 250 succesvol naar
  `data/raw/tweede_kamer/_commissie_2025-heden/`.
- **Ingest kostte geen nieuwe code**: `pipeline/ingest/ingest_tk.py`'s
  `ingest_plenair()` bleek ondanks de naam al volledig soort-onafhankelijk (itereert
  gewoon alle `<activiteit>`-elementen, geen plenair-specifieke filter) -- gewoon
  `uv run python -m pipeline.ingest.ingest_tk --plenair-dir _commissie_2025-heden`
  gedraaid. 40.378 nieuwe spreekbeurten geïmporteerd (`topic_id NULL`, zelfde bucket
  als de bestaande brede plenaire crawl). DB nu: 232.333 documents totaal, 144.377
  UMAP-eligible (was 191.955/118.539 vóór deze crawl).
- **Expliciet besluit**: UMAP draait op alle data; extract/tag (LLM, kostbaar)
  blijft beperkt tot de 4 gecureerde "polarized topics" (stikstof/abortus/asiel/
  energietransitie) -- ter info, historisch was dat toch al maar 5.281/191.955
  documenten (2,75%), de "(geen topic/plenair)"-bucket had al 0 extractie. De
  commissiedebatten volgen dus dezelfde regel: nooit extract/tag, alleen
  UMAP-coördinaten.
- `scripts/experiment_umap_documents.py` kreeg een `--export-suffix`-optie (default
  `""`, bestaand gedrag ongewijzigd) zodat een volle-dataset-run naar
  `plenair-map-full.json`/`-clusters-full.json`/`-hierarchy-full.json` schrijft
  **zonder** het bestaande, op ~40k punten performance-getunede
  `data/export/plenair-map.json` (dat `PlenairMap.vue` rechtstreeks gebruikt) te
  overschrijven. Gebruik: `--export-suffix=-full` (met `=`, anders leest argparse
  `-full` als een losse vlag i.p.v. een waarde).

**Afgerond sinds hierboven**: volle-dataset UMAP-run geslaagd
(`--start 2000-01-01 --end 2026-08-30 --label full --full-range-topics
stikstof,abortus,asiel,energietransitie --export-frontend --export-suffix=-full`,
zie de exacte commando's/cache-paden verderop) -- 135.633 documenten embedden
kostte 4040.5s (sequentieel tegen de lokale LM Studio-backend, bewust niet
dask-parallel), UMAP zelf maar 105.8s (single-threaded door `random_state=42`
bleek dus geen echte bottleneck op deze schaal -- geen besluit meer nodig
over loslaten van `random_state`). Resultaat: `data/export/plenair-map-full.json`
(132.921 punten, 20,5 MiB, ruim onder de 25 MiB Cloudflare-grens) +
`plenair-map.json` (de ~40k-punten productie-export) volledig ongewijzigd.
Tile-pyramide herbouwd: `data/export/plenair-map-full.pmtiles` (45.225 tiles,
zoom 0-8, 237 MB -- nog steeds ongedecimeerd per zoomniveau, zie eerdere noot).

**N-laagse clustering toegevoegd** (gebruiker wilde "meerdere niveaus van
clusters, zoals de zoom-lagen"): `scripts/experiment_umap_documents.py` kreeg
`build_multilevel_clusters()`/`label_multilevel_clusters()` (nieuw, naast de
oude `build_hierarchical_clusters()`/`label_hierarchical_clusters()` die
**ongewijzigd** blijven -- zowel voor `notebooks/explore_plenary_umap_clusters.py`
dat ze rechtstreeks importeert, als omdat het standaardpad (geen
`--cluster-level-sizes`) in `main()` bewust naar de oude functies blijft
wijzen; alleen expliciet `--cluster-level-sizes` schakelt over naar het
nieuwe N-laagse pad. Kernidee: elk niveau is een ONAFHANKELIJKE snede van
dezelfde HDBSCAN condensed tree op een eigen drempel (i.p.v. de oude
recursieve coarse/fine-aanpak) -- sneden van dezelfde boom op verschillende
hoogtes zijn altijd automatisch consistent/genest, dus ouder/kind-relaties
tussen niveaus worden achteraf via meerderheidsoverlap bepaald (zelfde truc
als de oude `parent_of_fine`), niet expliciet per tak afgedwongen. Nieuwe CLI-
vlag `--cluster-level-sizes` (komma-gescheiden, dalend, bv.
`4000,1200,350,100,30`), genegeerd/optioneel, `--cluster-min-size-to-name`
blijft de default-2-niveaus-instelling. Live gedraaid op de volle dataset:
7 -> 15 -> 37 -> 91 -> 683 clusters, `plenair-map-clusters-full.json` heeft nu
naast de bestaande `"coarse"`/`"fine"`-sleutels (resp. niveau 0 en het diepste
niveau, voor backward compat met bestaande consumenten) ook een `"levels"`-
sleutel met alle N niveaus. Tile-pyramide opnieuw gebouwd met de bijgewerkte
(diepste-niveau) cluster-ids per punt.

**Nog open**: `label_clusters_with_llm()` (LLM-naamgeving) ondersteunt nog
alleen exact 2 niveaus -- bij `--cluster-level-sizes` met >2 niveaus is
`--skip-llm-naming` verplicht (harde `SystemExit` anders). De TF-IDF-namen
(zonder LLM) zijn bruikbaar maar soms rommelig (zie bv. "Schors" als
domeinnaam in de laatste run-log) -- LLM-naamgeving generaliseren naar N
niveaus is nog niet gedaan. Ook nog niet gedaan: `TiledPlenairMap.vue`/
`plenair-map-viewer.html` tonen nog alleen `clusters.coarse` (niveau 0) als
hull-overlay, geen keuze/zoom-afhankelijke wissel tussen de 5 niveaus.

**Volgende, nog niet uitgewerkte fase (verkenning gestart, geen goedgekeurd plan)**:
gebruiker wil daarna nog een **hiërarchische UMAP**: niet alleen clustering op
meerdere niveaus (hierboven, wél afgerond), maar per cluster ook opnieuw UMAP
draaien op alleen die punten (`vectors[member_idx]`, geen her-embedding nodig)
voor een gedetailleerdere "ingezoomde" lokale layout, met **Procrustes-
uitlijning** (`scipy.spatial.procrustes`/`scipy.linalg.orthogonal_procrustes`,
al beschikbaar) om elke lokale laag terug te registreren op zijn eigen
plek/oriëntatie/schaal in de globale kaart. Dit is ook waar dask-parallelisme
(per-cluster her-UMAP is embarrassingly parallel) écht meerwaarde heeft, meer
dan bij de tile-encodering alleen. Openstaande ontwerpvragen: op welk
clusterniveau (van de nu 5 beschikbare) triggert een lokale her-UMAP, hoe een
zoomniveau in de tile-pyramide bepaalt of globale of lokaal-uitgelijnde
coördinaten gebruikt worden. Zie ook de sessie-eigen planbestand-aantekeningen
(niet in git, `/home/vscode/.claude/plans/humming-tickling-seahorse.md` in de
devcontainer van die sessie) voor de volledige verkenningsbevindingen.

## Stand bij einde sessie (2026-08-16, videokalibratie via events-API, issue #130) — begin hier bij een nieuwe sessie

**Probleem**: sprekersbeurten in onze player liepen merkbaar slechter gelijk met de
video dan op debatdirect.tweedekamer.nl zelf. Oorzaak: `pipeline/match_argument_spans.py`
kalibreerde puur op de WebVTT-ondertitelklok met één mediane offset voor het hele debat
— aantoonbaar onbetrouwbaar (30+ min drift rond een schorsing, niet-monotone drift
binnen één beurt door tikvertraging van de live-stenograaf, zie #108).

**Oplossing**: Debat Direct's eigen `events`-API
(`https://api.debatdirect.tweedekamer.nl/debates/{id}`) geeft een exacte, drift-vrije
wandklok-tijd per beurtwissel, gekoppeld via de TK-Persoon-GUID (byte-identiek aan VLOS
`<spreker objectid>`). Volledige uitleg + pilotcijfers: `docs/tk-data-sources-overview.md`
sectie 5f.

- **Nieuwe kolommen** `documents.speaker_person_id`/`turn_type` (schema.sql + eenmalige
  `ALTER TABLE` op de live DB) — gevuld door `ingest_tk.py` bij nieuwe imports, met
  terugwerkende kracht via **`scripts/backfill_speaker_events_meta.py`** (nieuw). Bewust
  topic-onafhankelijk (géén `--topic`-filter via `find_matching_activiteiten`, i.t.t.
  `backfill_activiteit_tijden.py`): een eerste versie mét topic-matching miste 1427
  documenten (asiel/energietransitie) omdat die topics bij de oorspronkelijke ingest
  met `--also-keyword`/`--also-dir` verbreed zijn, nergens vastgelegd welke — de
  uiteindelijke versie matcht rechtstreeks op `external_id` (bestaat de rij al, ongeacht
  topic-logica) en dekte zo alsnog alle 42.920 documenten in één scan. Live gedraaid:
  0 documenten met `speaker_person_id IS NULL` over alle 4 topics.
- **[Issue #145](https://github.com/SiggyF/bipolariteit/issues/145) geopend**: de
  volledige `**/*.xml`-scan (305 bestanden, sommige tot ~4MB) bleek >1 uur te kosten
  voor deze backfill — sys-tijd domineerde ruim boven user-tijd, wijst op
  filesystem/syscall-overhead in de devcontainer, niet op een algoritmische blow-up.
  Niet opgelost, alleen vastgelegd (lxml/iterparse/index als mogelijke richtingen).
- **Nieuwe pipeline-stap** `pipeline/fetch_debate_events.py` (+ Makefile-target
  `fetch-debate-events`, tussen `enrich-video` en `fetch-subtitles`) cachet de
  `events`-array per debat naar `data/debate_events/<id>.json`. De gedeelde
  `fetch_debate_detail()`-call is uitgetrokken naar `pipeline/debatdirect_api.py`
  (hergebruikt door `fetch_subtitles.py`, gedrag ongewijzigd).
- **`pipeline/match_argument_spans.py` herzien**: twee tiers per sprekerbeurt. Tier 1
  (nieuw): exact events-anker via `find_turn_anchor` (persoon-GUID + verwacht
  eventType + dichtstbijzijnd tijdstip binnen 180s). Tier 2 (bestaand, nu per-beurt
  i.p.v. per-debat): VTT-quote-matching verfijnt de positie binnen een geankerde beurt
  (`match_turn_with_anchor`), gekalibreerd op dát beurt-anker. Debatten zonder
  events-cache vallen volledig terug op de oorspronkelijke aanpak (`match_debate`,
  ongewijzigd — geen regressie). Als bijvangst: de al langer gedocumenteerde maar nooit
  gebouwde `video_offset_seconds`-achtige fallback nu wél gebouwd — een geankerde beurt
  zonder VTT-match krijgt alsnog een spanne (anker + spreektempo-schatting van de duur),
  i.p.v. stilzwijgend te verdwijnen.
- **Coverage geverifieerd**: alle 666 al gekoppelde `debatdirect_id`'s (2013–2026,
  43.607 documenten) geven succesvol een `events`-array terug — volledige herkalibratie
  van de bestaande dataset is haalbaar zonder debatten te verliezen.
- Tests uitgebreid: `tests/test_match_argument_spans.py` (Tier-1-functies +
  regressiefixture die aantoont dat per-beurt-ankering een debat herstelt dat onder de
  oude debat-brede mediaan volledig ongekalibreerd zou blijven, + non-regressietest dat
  `events_json=None` exact het oude gedrag reproduceert), `tests/test_ingest_tk.py`.
  `uv run pytest tests/` groen (126 tests).
- **Na de eerste live-rollout gerapporteerd**: "argumenten komen steeds een paar
  seconden te vroeg". Oorzaak: de kalibratie pinde het eerste gématchte ARGUMENT vast
  op het beurt-anker, maar een beurt begint vaak met een inleidende reactie die zelf
  geen argument is (landbouwdebat turn 40: ~42s inleiding vóór het eerste argument).
  Fix: `turn_opening_needle()` matcht i.p.v. daarvan de beurt-tekst zélf (VLOS-content,
  met het niet-uitgesproken sprekerlabel gestript) tegen de VTT als kalibratiereferentie
  — zie `docs/tk-data-sources-overview.md` 5f. 5 nieuwe tests, `uv run pytest tests/`
  groen (131 tests). Live opnieuw gedraaid (`match-video-spans --force` + `make export`)
  vóór deze PR.

## Stand bij einde sessie (2026-08-12, validatie-experiment stijlmiddelen issue #67 + afsluiting #50) — begin hier bij een nieuwe sessie

**Issue #50** (stance/typology van Stage 1 naar Stage 1b verplaatsen) **gesloten**
met een tegenvoorstel-comment: bewijslast omgedraaid, want het bestaande
two-turn-experiment (sectie hieronder) suggereert dat classificatie-context
tijdens extractie juist kán helpen bij het herkennen van argumentgrenzen —
het omgekeerde van de aanname achter #50. Voorstel in de comment: eerst een
kleine, goedkope validatie via de bestaande ElecDeb60to20-evalharness
(`span_overlap_prf`, dezelfde 50/318-steekproef) die single-pass-extractie
vergelijkt met een variant zonder stance/typology, vóórdat dit weer wordt
opgepakt. Heropenen zodra die er is.

**Issue #67** (nieuw labelgroep "Stijlmiddelen", zie PR #68's onderzoeksrapport
`docs/research/Taxonomie Stijlmiddelen Politieke Debatten.md` met 10 kandidaat-tags):
kritisch doorgenomen en empirisch gevalideerd vóór opname in `data/tags.toml`.

- **Twee tags afgevallen** vóór validatie: "Dooddoener/Cliché" (te
  interpretatief, model waarschijnlijk niet sterk genoeg — zelfde soort twijfel
  als bij Slogan bleek terecht) en "Groepsidentiteit-appèl" (overlapt met de
  al bestaande `Moraliteit-Loyaliteit`-tag in Morele Fundamenten).
- **5 overgebleven kandidaten empirisch gevalideerd**: Slogan, Herhaling,
  Aangekondigde Opsomming (hernoemd van "Drieledige Opsomming" — gaat om
  vooraf een aantal aankondigen + gevolgd door precies dat aantal, niet per se
  drie), Antithese, Retorische Vraag. Nieuw, read-only experiment (geen
  DB-writes): `scripts/experiment_stijlmiddelen_validatie.py` +
  `scripts/stijlvalidatie.json` (20 fictieve testargumenten, 4 per
  stijlmiddel), branch `experiment/stijlmiddelen-validatie-issue-67`.
- **Onderweg ontdekt** (leerzamer dan de eindscore):
  1. Kale, geïsoleerde stijlmiddel-zinnen zonder onderbouwing worden door de
     extractiestap zelf al afgewezen ("geen onderbouwing = geen argument",
     `extract_argument.md`) — geen tagging-fout maar een architectuurbotsing:
     stijlmiddelen worden pas getagd ná een geslaagde extractie.
  2. Meerdere stijlmiddel-zinnen met "want..."-redenen in dezelfde paragraaf
     worden door de extractor samengevoegd tot minder/grotere argumenten
     (bedoeld gedrag: "één punt = één argument"). Fix: elk testitem in een
     eigen paragraaf.
  3. Definities zijn allesbepalend. De Slogan-definitie uit de issue-comments
     ("repeterende, herkenbare frase") is een **corpus-eigenschap**, niet op
     één los fragment te beoordelen — teruggegrepen op de brondefinitie
     (Da San Martino et al. 2019: "a brief and striking phrase ... tend to
     act as emotional appeals"). Retorische Vraag scherper gedefinieerd via
     Ad Herennium/Silva Rhetoricae: "een vraag waarvan het antwoord al
     besloten ligt in de formulering zelf" (i.p.v. "geen antwoord verwacht").
- **Eindresultaat na correcties: 20/20 correct herkend (4/4 per
  stijlmiddel)** — bevestigt dat de eerdere missers aan testopzet/definities
  lagen, niet aan het concept of het model.
- **Nog niet gedaan**: de daadwerkelijke opname in `data/tags.toml` (+
  `pipeline/taxonomy.py` `LABELGROEP_SELECTIE`, `seed_tags.py`,
  `export_tags_taxonomy.py`, iconen in `docs/design/tag-iconografie/`). Open
  vraag: onder welk perspectief — aanbeveling "Filosofisch &
  Argumentatietheoretisch" naast Dialectische Kwaliteit (retorica en
  dialectiek zijn klassiek verwante disciplines binnen argumentatietheorie),
  met een kleine herformulering van de perspectief-beschrijving.

## Stand bij einde sessie (2026-08-10, evalharnas ELECDEBATE60TO16 issue #62)

**PR #66 (branch `eval/elecdebate-harness-issue-62`) staat op WIP** — bewust
niet als "af" gemarkeerd. De onderliggende logica/databugs zijn deze sessie
echt gefixt (zie hieronder), maar de `/validatie-rapportage/<dataset>`-pagina
zelf ziet er niet uit en de resultaten zijn niet te doorgronden — dat is
zelf vastgesteld bij het bekijken van de live pagina, geen slag om de arm.
Eerste concrete vervolgstap voor een nieuwe sessie: een eigen UI/UX-ronde op
die pagina, los van de backend-logica.

Losse PR's die er ook nog liggen:
- **PR #65 (gemerged)**: bugfix `_GEEN_TAG`-sentinel in `tag_arguments.py` +
  correcte `pending_extraction`-telling in `scripts/pipeline_status.py`.
- **PR #68 (open)**: onderzoeksdocument `docs/Taxonomie Stijlmiddelen
  Politieke Debatten.md` voor issue #67 (nieuw labelgroep "Stijlmiddelen",
  ontdekt tijdens dit werk toen bleek dat "Slogan" noch drogreden noch frame
  is). Puur documentatie, geen implementatie, losstaand van #66.

### Wat er gebouwd is (PR #66, issue #62)

Evalharnas dat de extractie-/tagpipeline valideert tegen de externe
`ElecDeb60to20`-dataset (Amerikaanse presidentsverkiezingsdebatten), als
kwantitatieve aanvulling op de steekproefsgewijze experimenten op #50 (zie
de two-turn-sectie hieronder). Twee assen, onafhankelijk gescoord:
argumentherkenning (span-overlap tegen `final_relation_graph.csv`) en
2-van-de-6-drogredenen-tags (`Drogreden-Ad-Hominem`/`Drogreden-Bespelen-
Publiek` tegen `fallacy_second_version.csv` — de overige 4 vereisen een
inhoudelijk oordeel over of de redenering klopt, principieel buiten scope).
`make validate` (vars `DATASET`/`LIMIT`/`MODEL`/`BASE_URL`) maakt
cumulatieve, herhaalbare steekproeven; resultaten landen in
`data/export/eval/<dataset>.json` en op `/validatie-rapportage/<dataset>`.
Volledige methodologie en motivatie: `docs/eval-elecdebate.md`.

### Reële bugs gevonden tijdens het werk (niet alleen framing/tekst)

Ontdekt door zelf voorbeelden uit de gouden data te lezen, niet door de
scores te vertrouwen — dat bleek herhaaldelijk nodig:

1. **Claim+premisse werden niet samengevoegd.** `scripts/convert_elecdebate.py`
   voegde de twee helften van een Support-relatie als losse spans toe i.p.v.
   als één argument-eenheid, met kale stellingnames en losse onderbouwingen
   zonder claim als resultaat — precies wat onze eigen extractieprompt zou
   afwijzen. Gefixt: groeperen op (sprekersbeurt, Governor-tekst), min-start/
   max-end samenvoegen. 999 → 627 argument-spans.
2. **Geneste dubbele drogreden-annotaties** (dezelfde fallacie op twee
   granulariteiten in de brondata, bv. een volledige twee-zinsuiting én een
   losse rij voor alleen de tweede zin) werden niet gededupliceerd.
   `_drop_nested_fallacies()` toegevoegd. 336 → 324 drogreden-citaten.
3. **Tagprompt kreeg geen context bij korte citaten.** Een deel van de
   gouden drogreden-citaten is maar één woord ("Loaded Language"-stijl
   annotatie in de brondataset, bv. "disaster", "stolen"). Die kaal aan de
   tagprompt geven (`quote_context=None`) is geen eerlijke test. Gefixt
   (`_context_window`, ±200 tekens rond het citaat). Op een verse 10-record
   qwen-steekproef: drogreden-tag-recall 0.00 → 0.25, F1 0.00 → 0.40.
4. **Prompt-instructies waren zelf misleidend**: beweerde "Tweede Kamer-debat"
   (feitelijk onjuist voor deze dataset — `_build_prompt()` kreeg een
   `debate_context`-parameter, default blijft "Tweede Kamer-debat" voor
   productie), en vroeg het model om zelf een pro/contra-as per argument af
   te leiden voor een veld dat de eval niet eens scoort. Nu: stance staat
   altijd op `"unclear"`.
5. **"Span"-terminologie lekte in de tagging-taal** terwijl tagging geen
   eigen spandetectie doet (het classificeert een compleet citaat, net als
   `tag_arguments.py` in productie) — hernoemd naar "citaten" waar van
   toepassing.

### Volgende stap

UI/UX-ronde op `/validatie-rapportage/<dataset>` (leesbaarheid, layout,
hoe voorbeelden gepresenteerd worden) — de backend/databugs zijn opgelost,
de pagina zelf niet. Daarna: grotere `make validate`-steekproef (nu maar
10/318 records) voor een betrouwbaarder beeld, en uitzoeken waarom
`qwen/qwen3.6-27b` op een eerder moment deze sessie consistent lege
completions gaf (leek een lokale LM Studio-model-state-kwestie, niet
gereproduceerd na herladen).

## Stand bij einde sessie (2026-08-10, two-turn-tagging-experiment voor issue #50)

Voordat issue #50 ("stance/typology loskoppelen van Stage 1 naar Stage 1b")
daadwerkelijk gebouwd werd, eerst getest of extractie+tagging als twee turns
binnen één LM Studio-sessie (messages-array met turn-1-antwoord als
voorgeschiedenis) sneller is dan de huidige aanpak, in de hoop dat de
brontekst-context "warm" zou blijven en niet opnieuw geprocessed hoeft te
worden. Volledig uitgeschreven in nieuw `docs/two-turn-tagging-experiment.md`.
Kort: **verworpen** — op 10 testdocumenten (topic `stikstof`) was de
two-turn-aanpak gemiddeld ~2,5x langzamer dan de bestaande single-call
baseline (geen aanwijzing voor prefix-caching-winst; turn 2 was steevast de
traagste stap), én leverde het een kwaliteitsregressie op de argumentgrenzen
zelf op (andere opknipping/hallucinatie zodra stance/typology-framing uit
turn 1 werd weggelaten). Issue #50's oorspronkelijke doel (goedkope
hertagging zonder herextractie) blijft overeind, maar dan via de
oorspronkelijk voorgestelde route van twee écht onafhankelijke
stages/prompts, niet via sessie-chaining voor snelheidswinst. Experiment-
artefact `scripts/experiment_two_turn_tagging.py` blijft in de repo als
referentie, niet in productie gebruikt. Geen schema-, pipeline- of
prompt-wijzigingen; issue #50 zelf staat nog open.

## Stand bij einde sessie (2026-08-04, derde topic: asiel) — begin hier bij een nieuwe sessie

Branch `topic-asiel`, nog geen PR. Doel was een derde onderwerp opzetten met de resterende Gemini-credits. Het onderwerp staat er (crawl, ingest, omschrijving, export), maar de **extractie is bewust teruggedraaid en moet opnieuw** — zie "Wat er nog moet".

### Het onderwerp zelf

`asiel` ("Asiel en migratie"), topic-id 3. Gecrawld op twee trefwoorden (`asiel`, `migratie`) over vijf debatsoorten: Plenair debat (debat/wetgeving/tweeminutendebat), Commissiedebat, Wetgevingsoverleg. Plus 100 plenaire dagverslagen via `-a topic=Vragenuur -a soort=Vragenuur`, want vragenuur-activiteiten heten in de brondata letterlijk "Vragenuur" en matchen dus nooit op een inhoudelijk trefwoord.

Ingest: `--topic asiel --also-dir migratie --also-dir Vragenuur --also-keyword migratie`. Die laatste optie is nieuw (zie hieronder). Corpus na opschoning: **5.703 documenten binnen de cutoff**, na verwijdering van 1.238 arbeidsmigratie-documenten, 862 ICT-migratiedocumenten en het markeren van 5.154 voorzitter-beurten.

### Wat er is geleerd over de pro/contra-as (het echte werk van deze sessie)

Een eerste extractie van 267 argumenten legde drie structurele problemen bloot:

1. **De as stond verkeerd om.** PRO was "beperking van de instroom" gezet; besloten is PRO = *bescherming van de asielzoeker*. De tiebreak-regel is: bij een willekeurige keuze noemen we de pool die het dichtst bij het huidige kabinetsbeleid ligt PRO — maar **die regel hoort niet in `topics.description`**, want dan gaat de LLM "steunt dit het kabinet?" afwegen in plaats van de inhoud.
2. **Een mechanische omdraaiing (`pro` <-> `contra`) repareert dat niet.** De toenmalige prompt bevatte de regel "kritiek op het huidige/voorgestelde beleid is contra". Bij asiel wordt het kabinet van twee kanten bekritiseerd (te ver, of niet ver genoeg), dus een deel van de labels was via die vuistregel toegekend en niet via de as. Omdraaien maakt zulke labels zelfstandig fout in plaats van herkenbaar raar. Geverifieerd aan een steekproef: een PVV-uitspraak "is de wet wel streng genoeg?" stond na de omdraaiing als PRO.
3. **Het corpus was te smal**: 145 van de 267 argumenten kwamen uit één wetsbehandeling (dwangsommen bij niet tijdig beslissen), omdat batches op `documents.id` lopen en dat debat het laagste id-bereik had. Gevolg: gezinshereniging 1 argument, terugkeer 6, tweestatusstelsel 3.

De gebruiker heeft de 267 argumenten daarom zelf gewist (arguments + claims + tags, en `extraction_attempted_at` teruggezet).

### Wijzigingen in de pipeline

- **`--also-keyword`** in `ingest_tk.py`: verbreedt waaróp gematcht wordt, naast `--also-dir` dat verbreedt wélke mappen gescand worden. Zonder dit levert een puur migratiedebat uit de migratie-map nul sprekerbeurten op.
- **Voorzitter-detectie op tekst**: de `<activiteitdeel><titel>`-heuristiek mist voorzitter-beurten bij commissiedebatten; content die met "De voorzitter:" begint telt nu ook. Dat markeerde 5.154 documenten over alle topics heen (asiel 3.418, stikstof 1.475, abortus 261), zonder verlies van bestaande argumenten (nul argumenten kwamen uit zulke beurten).
- **Vierde standpunt `ander_onderwerp`** plus kolom `arguments.ander_onderwerp` (welk onderwerp het wél is). Migratie: `scripts/migrate_stance_ander_onderwerp.py` (tabelherbouw, want SQLite kan een CHECK niet wijzigen). Deze argumenten vallen uit de export; `status.json` toont aantal + top-10 onderwerpen. De frontend blijft dus op drie standpunten.
- **Promptwijzigingen** in `extract_argument.md`: standpunt volgt de pool die de onderbouwing steunt (niet regering-vs-oppositie), onderbouwing zonder pool is `unclear`, uitspraken over de behandeling van een voorstel (stemgedrag, moties-appreciatie, debatverzoeken) leveren geen argument op, en de `ander_onderwerp`-instructie. Terminologie volgt bewust de about-pagina: *standpunt* en *onderbouwing*.

### Vier bugs onderweg gevonden en gerepareerd

1. `scripts/agy_run_extraction_batch.py` gooide `UnboundLocalError` op het eerste document van elke run (tellers niet geïnitialiseerd sinds commit `6775fa5`) — `make extract-agy` was dus volledig stuk.
2. De crawler vroeg `$top = limit * 3`; boven 250 antwoordt de TK-API met HTTP 400 en laat Scrapy die respons stil vallen. Elke `-a limit=` boven 83 leverde dus geruisloos nul resultaten. Nu begrensd op `odata.MAX_TOP`.
3. `vergadering_soort_for_activiteit` gokte "Commissie" voor "Vragenuur", dat plenair is — vragenuur was daardoor onvindbaar.
4. `scripts/backfill_voorzitter_turns.py` pakte de tuple van `find_matching_activiteiten` niet uit (stuk sinds `title_match` erbij kwam).

### Quota-ervaring (agy/Gemini)

Bevestigt de eerdere kalibratie: **~0,1% dagquotum per document**, ~5-9s per call, ~6 documenten/minuut. `/usage` blijft alleen interactief uitleesbaar. Deze sessie verbruikt: ~37% (100% → 63%), waarvan een flink deel aan de teruggedraaide extractie.

### Wat er nog moet

1. **Extractie opnieuw draaien** met de nieuwe prompt en omschrijving, en **niet vanaf het laagste id**: de eerste 48 documenten van de nieuwe run leverden 39 argumenten op waarvan **32 `ander_onderwerp`** (arbeidsmigratie 14, faunabeheer/wolf 7, ruimtelijke ordening 3). Dat is de staart van losse beurten waarin "migratie" toevallig valt. Begin bij een echt asieldebat: `make extract-agy TOPIC=asiel LIMIT=300 MIN_ID=6542` (6542 = "Begroting Asiel en Migratie 2025"; 7860 = "Vreemdelingen- en asielbeleid"; 9213 = "Asielnoodmaatregelenwet en tweestatusstelsel"). `MIN_ID` is deze sessie aan het make-target toegevoegd. Een titelfilter is bewust *niet* toegevoegd.
2. **Taggen** (`make tag-agy TOPIC=asiel`) — maar pas als de labels definitief zijn; bij een herextractie verdwijnen argumenten en dus hun tags.
3. **Openstaand van vóór deze sessie**: 179 ongetagde abortus-argumenten, 206 ongetagde stikstof-argumenten.
4. **Issue [#50](https://github.com/SiggyF/bipolariteit/issues/50)**: stance en typologie verplaatsen van Stage 1 naar Stage 1b, zodat een as-correctie voortaan een hertagging is in plaats van een volledige herextractie. Dit is precies wat deze sessie duur maakte.
5. De teaser in `frontend/src/lib/topics.ts` staat er al; `data/export/topics/asiel.json` bestaat maar is momenteel leeg (0 argumenten).

## Stand bij einde sessie (2026-07-30, releasepad)

Losse sessie, eigen branch (`feature/preview-release`, PR [#15](https://github.com/SiggyF/bipolariteit/pull/15)). Ging alleen over publiceren; niets aan de pipeline of de kaart veranderd. Volledige documentatie staat in **`docs/release.md`** — hieronder alleen wat je daar niet uit afleidt.

Releasen is: `make export` → commit → `git tag v0.3.0` → `git push origin v0.3.0`. De Action doet de rest. `v0.3.0` wordt `https://v0-3-0-preview.bipolariteit.org`.

**Waarom Workers en niet Pages.** Eerst op Cloudflare Pages ingezet, maar Pages ondersteunt geen custom domain per preview-deployment — er is geen wildcard voor branch-aliassen. Workers static assets wel; `custom_domain: true` regelt DNS-record en certificaat vanzelf. Gevolg: `_headers` werkt niet (Pages-feature, wordt op Workers stil als statisch bestand geserveerd), vandaar de noindex-header in `deploy/worker.js`.

**Waarom `-preview` een streepje is en geen punt.** Universal SSL is gratis maar dekt één niveau: `*.bipolariteit.org`. Twee niveaus diep zou een betaald Advanced Certificate vereisen.

**De ontwikkelbalk is fail-open.** Verschijnt tenzij `PUBLIC_RELEASE_OFFICIEEL=true`. Belangrijk detail: `PUBLIC_RELEASE_TAG` moet mee met `npm run build`, niet met het deploy-script — Astro bakt de balk in de HTML. Daarom bouwen de `release`-targets zelf in plaats van `build` als prerequisite te gebruiken. Zet je de vlag op de verkeerde plek, dan is de balk leeg zonder dat er iets faalt.

**Al gedaan door de gebruiker:** Cloudflare API-token aangemaakt (sjabloon *Edit Cloudflare Workers* plus Zone→DNS→Edit en Zone→SSL and Certificates→Edit) en samen met het account-ID als GitHub-secret gezet. Het per ongeluk aangemaakte Pages-project `bipolariteit` is weer verwijderd.

**Nog niet gedaan:** er is nog nooit echt gedeployd. De eerste tag is de eerste live test; als hij stukloopt op een 403 gaat het vrijwel zeker om een ontbrekend token-recht — zie de hersteltip in `docs/release.md`, en maak géén nieuwe token aan.

**Losse constatering:** er stond een `astro dev`-server uit een vorige sessie op poort 4321, waardoor `make test-frontend` stil tegen de verkeerde server praatte en op een timeout viel. `make dev-stop` loste het op. De moeite waard om te onthouden bij een onverklaarbare smoke-test-fout.

## Stand bij einde sessie (2026-07-30, vervolg)

Vervolg op de sessie hieronder, zelfde dag, zelfde branch (`feature/correspondentie-3d`, PR [#8](https://github.com/SiggyF/bipolariteit/pull/8)). Deze sessie ging over ontwerpersfeedback op de kaart uit de vorige sessie, plus een reeks navigatiebugs die tijdens het verifiëren aan het licht kwamen. **Alles is gecommit** (twee commits: de feature, plus een opruimronde erna).

### Ontwerpersfeedback verwerkt

- **Tagpunten zijn nu effen, halftransparante cirkels, geen iconen meer.** Zowel de per-tag-iconen (vijftig) als later ook de per-perspectief-iconen (vier) bleken op kaartschaal niet als teken te lezen, vooral in dichte clusters van hetzelfde perspectief — zie de "brain"-blob die de sessie in gang zette (screenshot toonde een cauliflower-vormige klont in plaats van een herkenbaar brein-icoon; bleek 3-4 overlappende iconen van dezelfde vorm, geen renderbug). Kleur draagt de codering nu alleen; `tag-styles.json`'s `marker`-veld (circle/triangle/diamond/square) ligt klaar als extra onderscheid mocht kleur ooit weer te weinig zijn.
- **Iconen komen niet meer uit een gok naar het gelijknamige Lucide-icoon.** De gebruiker leverde de échte SVG's uit het ontwerpsysteem aan (eerst als `<script>`-blok met inline paden, uiteindelijk verwerkt tot `docs/design/tag-iconografie/icons/*.svg`, één bestand per icoonnaam). `build_tag_icons.mjs` leest daar nu uit i.p.v. uit `lucide-static` (dependency verwijderd) — geen `VERVANGERS`-tabel met handmatige gok meer nodig, want alle 54 namen uit `tag-styles.json` hebben nu hun eigen tekening.
- **Partijlogo's**: vereenvoudigde iconenset (`frontend/public/party-logos/simplified/*.svg`, vierkant 160×160, door de ontwerper geleverd) i.p.v. de officiële wordmarks met outline-effect. Vast op 20% verzadiging (geen toggle meer, "in kleur" verloor het altijd). Rijen zonder partij (of zonder logobestand) krijgen een initiaal-tegel i.p.v. een kale stip, dezelfde stijl als `PartyLogo.vue`'s bestaande placeholder — nu gedeelde `partyInitial()`-logica in `parties.ts`.
- **Plotcontrols herbouwd als pil-toolbar** (bordered, mono/uppercase labels) i.p.v. native `<select>`/checkbox, consistent met de rest van de paper-stijl. 2D/3D is nu ook een toggle i.p.v. checkbox.
- **Default rij-eenheid is nu "Personen"** i.p.v. "Partijen" — een partij is een optelsom van tientallen sprekers, en die nuance is precies waar de kaart voor bedoeld is.

**Nog een losse constatering, niet opgevolgd:** het `logos.ai`-bestand (Illustrator-bronbestand voor de partijlogo's) staat als los, ongetrackt/gewijzigd bestand in de repo; gebruiker vroeg expliciet om het mee te pushen, dus zit in de tweede commit.

### Drie echte navigatiebugs gevonden tijdens het verifiëren

1. **Scrollen op de 2D-kaart scrollde de pagina, niet de grafiek.** `wiel()` deed alleen `preventDefault()` in de 3D-tak; in 2D liet dat de pagina onder de muis vandaan scrollen, waardoor de rest van de scrollbeweging de kaart al niet meer raakte. `preventDefault()` staat nu onvoorwaardelijk vooraan in de functie.
2. **Zoom kon niet ver genoeg uit.** De 2D-assen hadden geen vaste `min`/`max` (auto-schaal), dus het genormaliseerde standaardvenster (90e-percentielvenster tegen de Ideologie-Links-Economisch-uitschieter) werd zelf de 0%-100%-referentie voor `dataZoom` — er was letterlijk nergens heen om uit te zoomen. Nieuwe `asVolledigeGrenzen` (het echte maximum, niet het percentiel) is nu de vaste asgrens; `asGrenzen` (90e percentiel) blijft alleen het *startvenster*.
3. **Dat startvenster zette zichzelf niet betrouwbaar terug.** `dispatchAction` op de ECharts-instantie bleek racy (chartRef wordt al waar vóórdat VChart's eigen `onMounted` de instantie initialiseert) — zelfs met een `requestAnimationFrame`-herkansing bleef het een stille no-op. Nu declaratief: `forceerNormalisatie` (ref) bepaalt of `chartOption` zelf `startValue`/`endValue` meegeeft in de `dataZoom`-config, in dezelfde `setOption`-aanroep die de kaart toch al ververst. Gaat na die ene toepassing weer uit (watcher op `chartOption`, `flush: "post"`) zodat latere her-renders (bv. een tagklik) de handmatige zoomstand van de gebruiker niet resetten.

Bijvangst: labels in 2D bleven bij inzoomen vast op de globale top-12-op-frequentie, ook als die twaalf allemaal buiten het gezoomde venster vielen. Nu bijgehouden via het `datazoom`-event (`opDataZoom`/`zicht2D`) — analoog aan de al bestaande dieptegebaseerde labelselectie in 3D tijdens slepen.

### Radiale compressie tegen de Ideologie-Links-Economisch-uitschieter

Op verzoek gecheckt: de Mahalanobis-afstand van deze tag (n=43, de zeldzaamste) in de eerste 3 CA-componenten is **~6× de mediaan** — geen renderbug maar standaard CA-gedrag bij een kolom met kleine massa. Na overleg (opties besproken: laten staan, radiale compressie, clip+flag, hogere ondergrenzen) gekozen voor radiale compressie: `r' = r^0.6` op de weergavecoördinaten, richting ongewijzigd, toegepast ná de echte CA en ná `alignSigns` (nieuwe `weergave`-computed, puur presentatie — `correspondence` zelf blijft ongemoeid, en klikken-om-te-filteren gaat toch op tagsleutel/rijlabel). Effect: de uitschieter zakt naar ~2,9× de mediaan, én — neveneffect van `r^p > r` zodra `r < 1` — de dichte kern van de wolk spreidt juist uit, waar het echte overlapprobleem zat.

**Open punt:** afstanden op de kaart zijn na deze compressie geen letterlijke chi-kwadraatafstanden meer, alleen richting en relatieve volgorde blijven behouden. Dat staat nu alleen in code-comments, nog niet in de gebruikersgerichte panel-copy of `/about`.

### Nog niet gedaan

- dim1/dim2/dim3 een naam (x/y/z) en eenheid geven in de UI — gevraagd, nog niet opgepakt.
- 3D-panning (naast roteren en zoomen) — gevraagd, nog niet opgepakt.
- Het palet-hervalidatie-punt uit de vorige sessie (zie hieronder) staat nog open.

## Stand bij einde sessie (2026-07-30) — verouderd, zie sectie hierboven

Deze sessie ging volledig over de correspondentiekaart (`frontend/src/components/TagCorrespondenceMap.vue`), issue #3. Branch: `feature/correspondentie-3d`. **Alles staat uncommitted** — `npm test` (23 tests) en `npx astro build` zijn groen, de kaart is met Playwright-screenshots geverifieerd, maar er is bewust nog niet gecommit.

### De drie gemelde 3D-bugs, en wat de oorzaak was

De 3D-modus is geen `echarts-gl`/`scatter3D`, maar een eigen orthografische-projectie-laag vóór een gewone 2D-scatter. Dat is een bewuste keuze (zie de comment bovenin de component: klikken-om-te-filteren, tooltip, dimmen en labelplaatsing hoeven niet dubbel gebouwd te worden), en het heeft één concreet voordeel dat onderweg belangrijk bleek: `labelLayout` is een 2D-cartesische feature die `scatter3D` niet kent, en die hebben we hier dus wél.

1. **Assen liepen niet synchroon met de punten.** Twee oorzaken. (a) x- en y-as spanden allebei `±grens` over een tekengebied van 3:1, dus op het scherm was de projectie een rotatie *plus* een uitrekking — de aslijnen bleven bijna horizontaal terwijl de wolk kantelde. Nu is het venster gelijk-aspect: een `ResizeObserver` op de wrapper meet de verhouding en `grensX` volgt daaruit. (b) Het venster werd elk frame opnieuw uit de *geprojecteerde* punten berekend, dus de kaart zoomde bij elke muisbeweging in en uit. Het venster hangt nu aan `straal`, een rotatie-invariante maat.
2. **Vertraging tussen slepen en punten.** ECharts koppelt zijn overgangsanimatie aan de index in de data-array, en de dieptesortering hersorteert die array elk frame — punten animeerden dus naar de plek van hun buurman. `animation: false`. (Dit is de 2D-scatter-knop `series.animation`, niet `scatter3D.animationDurationUpdate`.)
3. **Geen assenraster.** In 3D stond het cartesische raster van ECharts bewust uit (het zou een gedraaide mengeling van dimensies "dim 1"/"dim 2" noemen), maar er kwam niets voor in de plaats behalve twee vage lijntjes plus zwevende `axisTick`-streepjes op de nullijnen. Nu tekent de component een echt meegedraaid referentiekader: vloerraster in het dim1-dim3-vlak, ribben van de kubus, drie aslijnen vanuit de oorsprong en `dim n (x%)`-labels op de tippen — allemaal door dezelfde `projecteer()`, dus synchroon per constructie.

### Wat er verder in dezelfde ronde bij is gekomen

- **Perspectief in plaats van orthografisch.** `CAMERA_AFSTAND = 4` (in eenheden van `straal`); de isometrische look maakte de draairichting dubbelzinnig. Het venster houdt rekening met de maximale perspectiefvergroting, anders valt de voorste ribbe buiten beeld.
- **Luchtperspectief.** `mist()` mengt elke kleur naar de achtergrond naarmate een punt verder weg ligt — haalt in één bewerking verzadiging én contrast weg. Beeldsymbolen (logo's) kunnen geen kleur aannemen, die krijgen de mist via opacity.
- **Slepen zet geen filter meer om.** Het einde van een sleep was ook een `click`; nu geldt een marge van 4 px.
- **Zoom.** Scrollen in 3D zoomt (eigen `zoom`-ref), scrollen in 2D gebruikt ECharts' `dataZoom` type `inside` met `filterMode: "none"` — die laatste is belangrijk, want de standaard gooit punten uit de serie en dan springen de labels bij elke zoomstap. Knop "Aanzicht herstellen" reset beide.
- **Labels.** `labelLayout` staat op `{ hideOverlap: true, moveOverlap: "shiftY" }`, maar dat bleek een noodrem en geen ontwerp: welk label overleeft hangt af van de tekenvolgorde. Daarom houden alleen de 12 vaakst toegekende tags een vast label (`VASTE_TAGLABELS`), de rest komt bij hover. Rijen houden hun label, behalve als ze een logo hebben.
- **Partijlogo's als punt.** `lib/partyLogoSprite.ts` haalt de SVG op, leest de verhouding uit de `viewBox` (nodig, want ECharts perst een `image://`-symbool in het vak dat je opgeeft — zonder verhouding wordt PVV's 13:1 wordmerk een vierkant) en kan het logo herteken als contour in één inkt. CSS kan dat niet: het logo belandt op een canvas. Toggle "Logo's: in kleur / als contour", staat nu op contour. In personenweergave krijgt een spreker het logo van zijn partij.
- **Uitschieter-beleid.** `straal` is het **90e percentiel** van de puntafstanden, niet het maximum: één tag (`Ideologie-Links-Economisch`) ligt vier keer zo ver als de kern en perste met gelijk-aspect de rest tot een vlekje. In 2D viel dat niet op omdat elke as daar los schaalt. Gevolg: een handvol punten valt standaard buiten beeld, met een telling in de hint en een zoom-ondergrens (0,12) die ver genoeg uitzoomt om ze binnen te halen.
- **SGP-logo vervangen** door de 2016-versie van Wikimedia Commons (het oude bestand was verkeerd).

### Ontwerpsysteem voor de tagiconografie — geadopteerd, maar kijk er nog eens naar

`docs/design/tag-iconografie/` (verplaatst uit de repo-root, met een `docs/design/README.md` ernaast). `tag-styles.json` is het machineleesbare deel: per perspectief een kleur, marker en Lucide-icoon, en per tag een Lucide-icoon.

`frontend/scripts/build_tag_icons.mjs` genereert daaruit `src/lib/tagIcons.generated.ts`. Wat die stap doet: Lucide-iconen zijn een mix van `<path>`, `<circle>`, `<line>`, `<polyline>` en `<rect>`, en ECharts wil één padstring — dus alles wordt tot één `d` gesmolten, met twee lege `M`-sprongen ervoor die de bounding box op het volle 24×24-raster zetten (anders rekt ECharts elk icoon afzonderlijk uit tot het opgegeven vak). `lucide-static` is toegevoegd als **devDependency**; het gegenereerde bestand staat in de repo, dus Lucide belandt niet in de bundel.

**Zeven icoonnamen uit het ontwerpsysteem bestaan niet in Lucide** — `person-lectern`, `cheque`, `person-cap`, `resize-figure`, `round-table`, `voorzittershamer`, `paper`. Er staat nu een expliciete `VERVANGERS`-map in het generatiescript (bv. `voorzittershamer` → `gavel`, `cheque` → `hand-heart`). Die keuzes zijn van mij, niet van de ontwerper; laat ze nakijken.

**Openstaand punt, en het belangrijkste van deze sectie:** het geadopteerde palet is mono-accent — vier gedempte aardetinten (`#B68235`, `#4C7C7A`, `#B15E4A`, `#6B8558`). Het palet dat er stond was gevalideerd met de dataviz-validator tegen `--color-bg` in licht én donker met `--pairs all`; dit palet is dat niet, en het onderlinge kleurverschil is duidelijk kleiner. Het ontwerpsysteem vangt dat op met vorm ("perspectives are distinguished by tone + shape, not by clashing hues"), en de tagpunten dragen nu inderdaad hun eigen icoon. Maar: Lucide-iconen zijn lijntekeningen, dus de punten worden getekend met `itemStyle.borderColor` en een doorzichtige vulling — en op de screenshot van 2026-07-30 oogt de kaart daardoor **te licht en te vlak**, zeker in combinatie met de contourlogo's. Er is nog geen aparte donkere variant van het palet. Concreet nog te doen: contrast opnieuw meten, en overwegen de tagpunten wél te vullen (of de lijndikte op te voeren) zodat de wolk weer gewicht krijgt.

### Bestanden

Nieuw: `frontend/src/lib/partyLogoSprite.ts`, `frontend/src/lib/tagIcons.generated.ts`, `frontend/scripts/build_tag_icons.mjs`, `frontend/scripts/shoot_correspondence.mjs` (Playwright-hulpje: zet 3D aan, sleept, schiet screenshots naar `/tmp/correspondence-shots`), `docs/design/`.

Gewijzigd: `TagCorrespondenceMap.vue` (het leeuwendeel), `styles/main.css` (`.control-knop`, hogere grafiek in 3D), `package.json` (lucide-static), `public/party-logos/sgp.svg`.

**Let op:** er staan twee ongewenste bestanden in `frontend/public/party-logos/` — `logos.ai` en een `~ai-*.tmp`. Die horen daar niet; opruimen of in `.gitignore`.

### Nieuwe issue

**#7 — Taal in de codebase: vaste grens tussen Nederlands en Engels.** De repo mengt beide, soms binnen één functie (`correspondence.ts` heeft een Engelse API met Nederlandse helpers; `TagCorrespondenceMap.vue` Engelse props met Nederlandse locals). Voorstel in de issue: Engels voor alles wat met de techniek meepraat, Nederlands voor domeinbegrippen-als-waarde en voor commentaar/docs/commits, met een expliciete uitzondering voor domeinwoorden die niet vertaalbaar zijn.

## Stand bij einde sessie (2026-07-28)

Vervolg op de sessie van 2026-07-27 hieronder. Deze sessie ging over `agy` als tweede extractie-/taggingbackend naast de lokale qwen-pipeline — zowel een verworpen experiment (gebundelde prompts) als een geslaagde echte batch (single-call, zoals de bestaande aanpak).

- **Gebundelde (multi-document) extractieprompts getest en verworpen** — volledig uitgeschreven in nieuw `docs/batch-experiment.md`. Kort: 5 documenten per `agy`-call bespaart 66-80% prompt-tekens (geen scriptbare token-telling beschikbaar bij `agy`, dus tekens als proxy), en een automatische substring-check (elk `quote_text` moet letterlijk in de brontekst van het juiste document staan) vond geen grove cross-document citaat-verwisseling. **Maar** een inhoudelijke vergelijking tegen de bekende single-call-baseline (20 doc-ids, kalibratie van 2026-07-24) liet op 14 van de 20 documenten afwijkende resultaten zien, incl. een omgekeerde stance op doc 129 — en het is niet vastgesteld of dit door het bundelen zelf komt of door gewone modelvariatie (geen same-day controlemeting gedraaid). Besluit: single-document-per-call blijft de aanpak. Experiment-artefacten (`pipeline/prompts/extract_argument_batch.md`, `_build_batch_prompt()` in `pipeline/extract_arguments.py`, `scripts/agy_test_batch_extraction.py`) blijven in de repo als referentie, niet in productie gebruikt.
- **Nieuw `scripts/agy_run_extraction_batch.py`**: Stage 1-extractie via `agy` i.p.v. lokale qwen, zelfde contract als `pipeline/extract_arguments.py` (schrijft naar `arguments`/`claims`, zet `documents.extraction_attempted_at` + prompt/model-provenance). Draait single-doc-per-call. Analoog aan het bestaande `scripts/agy_run_tagging_batch.py`-patroon voor Stage 1b.
- **Twee echte batches gedraaid** (topic `stikstof`, model `gemini-3.6-flash-low`, dagquota ~100% → **14% resterend** aan einde sessie):
  - Extractie: 377 documenten, 2 fouten, 250 nieuwe arguments, 176 claims (`data/export/run-logs/agy_extraction_batch.log`). Empirisch tarief: **~0,10-0,11%/document**.
  - Tagging: alle 392 op dat moment ongetagde arguments (incl. de 250 nieuwe), 5 fouten, 784 derived tags, 2483 llm-tags (`data/export/run-logs/agy_tagging_batch_4.log`, vervolg op `agy_tagging_batch.log`/`_2.log`/`_3.log` (in data/export/run-logs/) van eerdere sessies). Empirisch tarief: **~0,10-0,15%/argument**.
  - **Belangrijk geleerd over quota-meting**: een eerdere same-day herhaling van dezelfde 20 documenten (het batch-experiment hierboven) gaf een quota-tarief dat een stuk gunstiger leek dan de kalibratie van 2026-07-24 — maar dat bleek vermoedelijk (deels) een cache-effect te zijn (letterlijk dezelfde documenttekst als 4 dagen eerder al eens naar Gemini gestuurd), niet een echt batching-voordeel. Bij het daadwerkelijke extractie-batch (verse, nooit eerder verwerkte documenten) kwam het tarief weer overeen met de oorspronkelijke kalibratie (~0,10%/doc). **Les: quota-vergelijkingen zijn alleen betrouwbaar op verse content**, hergebruikte testdocumenten geven een vertekend beeld.
  - Machine-power-gate (`feedback_llm_extraction_power_only`-memory) is bijgesteld: geldt alleen voor lokale LM Studio/qwen-inferentie op de M2 Max, **niet** voor `agy` (draait als losse API-call in Docker, geen zware lokale compute) — `agy`-batches mogen dus ook op accu draaien.
- **Stand na deze sessie**: `stikstof` staat op 2734/5213 documenten geprobeerd (2479 resterend), 1368 arguments totaal, slechts **5 ongetagd** (de foutgevallen uit de laatste batch). Dagquota `agy` op **14%** — waarschijnlijk niet genoeg voor nog een substantiële batch vandaag; volgende sessie moet zelf even `/usage` checken (nog steeds geen scriptbare check, zie sectie hieronder) voor een vers dagquotum.
- **Correctie op een eerdere aanname in deze sessie**: hieronder stond eerder dat de export niet opnieuw was gedraaid na de twee batches. Dat klopte niet — `make export TOPIC=stikstof` wás gedraaid (`status.json` was ~3 minuten stale t.o.v. de laatste taggingbatch, geen ongedraaide export). Alsnog opnieuw gedraaid ter controle; DB en export komen nu overeen (2734/5213 documenten, 1368 arguments, 1363 getagd, 5 ongetagd). **Les, in lijn met de waarschuwing verderop in dit document**: vertrouw bij twijfel de DB/`git diff`, niet blind de laatst geschreven sectie hier — ook niet binnen dezelfde sessie.
- **Nog niet gedaan**: de 5 taggingfouten uit de laatste batch zijn niet onderzocht/opnieuw geprobeerd. Alle wijzigingen van deze sessie én van 2026-07-27 (status-pagina, partij-klikfilter, minister-backfill, batch-experiment, agy-batches) zijn inmiddels wél gecommit (6 commits, main staat lokaal 12 commits voor op `origin/main`, nog niet gepusht).

## Stand bij einde sessie (2026-07-27) — verouderd, zie sectie hierboven

Vervolg op de sessie van 2026-07-26 hieronder (zelfde lopende gesprek, over de datumgrens heen). Alles hieronder staat nog **ongecommit** in de working tree (zie `git status`) — bewust, zodat er in één keer bekeken/gecommit kan worden.

- **Nieuwe `/status`-pagina**: publiek overzicht van pipeline-voortgang (documenten geëxtraheerd, arguments getagd, documenten redactie-gecheckt), per topic, met simpele voortgangsbalken. Databron: nieuwe `fetch_pipeline_status`/`status.json`-export in `pipeline/build_static_data.py` (draait automatisch mee met `build_static_data`, geen aparte stap). Frontend: `frontend/src/pages/status.astro` + CSS in `main.css` (`.status-*`-classes) + nav-link in `SiteNav.astro`. Bewust **geen** herhaling van de `/about`-pagina's "geen kwaliteitsoordeel/geen fact-checking"-framing op deze pagina — die hoort bij `/about`, andere pagina's blijven feitelijk/kort (zie ook memory `feedback_status_page_tone`).
- **Klik-op-partij-in-grafiek filtert argumenten** (was de aanleiding: "Onbekend"-balk in `StatsPanel.vue` deed niets bij klikken). Nieuw `frontend/src/lib/usePartyFilter.ts`, zelfde cross-island `CustomEvent`-patroon als het bestaande `useTagFilter.ts`. `StatsPanel.vue` zet de filter bij een klik op een bar-segment (nogmaals klikken = wissen, met dezelfde "alles tonen"-knop als de tag-filter). `ArgumentColumn.vue` combineert nu tag- én partij-filter (AND, beide onafhankelijk actief te zetten). "Onbekend" is een sentinel-partijnaam (zie hieronder), geen echte partijcode.
- **GitHub issue #2 (minister-partij) opgelost voor 3 van de 4 destijds onvindbare namen**, via twee nieuwe externe bronnen (geen AI, verifieerbaar) bovenop de al bestaande TK OData-route in `scripts/backfill_minister_info.py`:
  - **Jaimi van Essen → D66**: rijksoverheid.nl/regering/bewindspersonen/jaimi-van-essen. Let op: dit staat **niet** in de schema.org/JSON-LD op die pagina (die bevat alleen generieke WebPage/breadcrumb-metadata) maar als losse tekst ("Partij: D66") in de Next.js server-payload van de pagina — dus regex over de ruwe HTML, geen nette API.
  - **Jean Rummenie → BBB** en **Piet Adema → ChristenUnie**: via Wikidata (`P102`/lid-van-politieke-partij), opgevraagd via de publieke `Special:EntityData/<Q-id>.json`-API (niet de HTML-pagina scrapen — betrouwbaarder, machine-leesbaar). Rummenie zat niet meer op rijksoverheid.nl (uit functie), dus rijksoverheid was voor hem geen optie.
  - **Dick Schoof → `"Onafhankelijk"`** (i.p.v. NULL laten staan): Wikidata toont hem als PvdA-lid t/m 2021, en sindsdien (dus ook tijdens zijn premierschap) als onafhankelijk politicus. Bewuste waarde i.p.v. gok — hij hoort niet bij "Onbekend" (data-hiaat) maar ook niet bij een bestaande fractie. Dit is nu ook de reden dat "Onbekend" in de UI een echte restcategorie is geworden (alleen nog data-hiaten, geen "eigenlijk wel bekend maar nooit opgezocht"-gevallen meer).
  - **Onderzocht maar niet bruikbaar gebleken**: Nationaal Archief-dataset `nt00334` (rijk gestructureerde CSV's: `FUNCTIE`/`KABINET`/`PERSOON`, met een eigen `partij`-kolom) — goede kwaliteit maar dekt alleen tot en met het vierde kabinet-Balkenende (~2007-2010), te oud voor het huidige kabinet.
  - `MINISTER_PARTY`-dict in `backfill_minister_info.py` uitgebreid met deze 4 namen, dry-run + echte run gedraaid, gevolgd door een verse `build_static_data`-export. **Alleen Piet Adema had al arguments met NULL party in de stikstof-dataset vóór deze sessie zichtbaar** (samen met Van Essen/Rummenie/Schoof) — na deze backfill staat "Onbekend" op 0 voor stikstof (Adema had toevallig geen stikstof-arguments, dus geen zichtbaar effect voor hem specifiek, maar de dict is nu wel compleet voor een volgend topic).
- **Stage-1-batch twee keer hervat en weer gestopt binnen deze sessie** (stroom → accu → stroom → accu, netjes elke keer via `kill` + `lms unload --all`, geen corrupte state dankzij per-document commit). **Stand bij laatst stoppen: 2407/5213 documenten geprobeerd, model unloaded.** Zelfde hervat-commando als altijd (zie sectie "Setup om verder te werken" verderop).
- **Nog niet gedaan**: de wijzigingen van deze sessie (status-pagina, partij-klikfilter, minister-backfill) zijn nog niet gecommit, en de frontend is niet visueel in een browser getest na de partij-klikfilter-wijziging (wel geverifieerd dat de pagina zonder fouten rendert via curl/dev-server-logs). Bij twijfel: `/topics/stikstof/` openen, op de "Onafhankelijk"- of een andere partij-balk klikken, controleren dat de kolommen filteren.

## Stand bij begin sessie (2026-07-26) — verouderd, zie sectie hierboven

Bij het begin van deze sessie bleek de sectie hieronder ("Stand bij einde sessie 2026-07-25") **achterhaald**: een latere sessie diezelfde avond had al substantieel werk gedaan (bestandstijden 22:00–22:01, laatste DB-write 00:46) dat toen niet meer in dit document is bijgewerkt en ook nog ongecommit stond. Voor het vervolg dus: vertrouw bij twijfel de DB/`git status`/`git diff`, niet blind de laatst geschreven sectie hieronder.

- **Crawler uitgebreid naar Commissiedebatten** (`crawlers/tweede_kamer/tweede_kamer/odata.py`, `spiders/verslagen.py`): eerder ondersteunde `vergadering_url_for_activiteit`/`pick_closest_vergadering` alleen `Vergadering.Soort='Plenair'`. Nu ook `'Commissie'`, met een titel/onderwerp-woordoverlap-tiebreaker (`_title_words`/stopwoordenlijst) — nodig omdat op drukke commissiedagen tientallen commissies parallel lopen en datum-nabijheid alleen dan niet volstaat. Twee empirisch gevonden misser-gevallen (2025-06-18: 10 same-day kandidaten, verkeerde gekozen zonder titel-tiebreak; een "OMGEZET in schriftelijk overleg"-Activiteit die matchte met een compleet ongerelateerd commissiedebat) staan als comment in `odata.py`. Zonder woordoverlap geeft `pick_closest_vergadering` bewust `None` terug (gemiste match) in plaats van te gokken. Resultaat: het stikstof-corpus groeide van 3949 → **5213 documenten**.
- **`documents.is_voorzitter_turn`-kolom toegevoegd** (schema.sql + `pipeline/ingest/ingest_tk.py`) — lost de al langer bekende kwestie op dat de voorzitter (bv. Paulusma/D66, Krul/CDA) als gewone actor met partij-attributie werd opgeslagen wanneer die procedureel het woord voerde. Gedetecteerd via `build_parent_map`/`is_voorzitter_turn`: de dichtstbijzijnde omsluitende `<activiteitdeel><titel>` bevat "voorzitter" (bv. "Spreekbeurt - De voorzitter") — `<spreker><functie>` zelf draagt geen rolmarkering, blijft altijd "lid Tweede Kamer". Fractie in de brondata blijft ongewijzigd, dit is puur een rol-vlag.
- **`scripts/backfill_voorzitter_turns.py`** (nieuw): eenmalige backfill over de bestaande 3949 documenten (die al vóór deze kolom bestonden) + `--purge-arguments` om arguments die al ten onrechte uit voorzitter-beurten geëxtraheerd waren alsnog te verwijderen (incl. afhankelijke claims/argument_tags/argument_oppositions). **Geverifieerd**: 156 documenten geflagd als voorzitter-beurt, 0 documenten met `is_voorzitter_turn=1` hebben nu nog arguments in de DB — de purge is schoon doorgevoerd.
- `pipeline/extract_arguments.py` (`fetch_pending_documents`) en `scripts/pipeline_status.py` filteren/rapporteren nu op `is_voorzitter_turn = 0`.
- **Stage-1-batch was al verder gevorderd dan hierboven gemeld**: laatste `extraction_attempted_at` stond op 2026-07-25T22:46:58Z (document-id 2236), dus de batch is na de "1199/3949"-stand hieronder gewoon doorgelopen (waarschijnlijk in dezelfde late sessie die de crawler/voorzitter-wijzigingen deed) — maar dat verliep buiten `data/export/run-logs/extract_batch_full.log` (dat logbestand is stil sinds 10:01 die ochtend), dus de details van die run zijn alleen uit de DB af te leiden, niet uit logs. Bij hervatten (nu weer op stroom): **2951 documenten pending** (van de 5213, exclusief 156 voorzitter-beurten).
- Deze wijzigingen (crawler, schema, ingest, extract_arguments, pipeline_status, backfill-script) stonden aan het begin van deze sessie nog **ongecommit** in de working tree, samen met een losstaande, al-gestagede frontend-redesign (fonts, `useTheme.ts`, CSS, nav/stats/tags-componenten). Beide zijn in deze sessie als aparte commits vastgelegd (zie git-log voor de exacte commit-hashes).
- `data/bipolariteit.db.bak-20260725220207` was een ongetrackt lokaal backup-bestand van vóór de purge-stap — bewust niet in git, blijft lokaal liggen.

## Stand bij einde sessie (2026-07-26)

- Stage-1-batch hervat op stroom (`lms load qwen/qwen3.6-27b` + `extract_arguments.py --topic stikstof --limit 4000`), daarna bewust gestopt (`kill`, geen crash) omdat de gebruiker moest gaan unpluggen. Model expliciet unloaded (`lms unload --all`).
- **Stand bij stoppen: 2287/5213 documenten geprobeerd (max doc-id 2341), 1034 arguments.** Nog ~2870 documenten te gaan (van de 5213, exclusief 156 voorzitter-beurten).
- Hervatten zodra weer op stroom: zelfde commando als hierboven in de sectie "Stand bij begin sessie (2026-07-26)", pakt automatisch verder via het skip-mechanisme.
- Verse export gedraaid (`make export TOPIC=stikstof`) tegen de 1034-argument-stand — `data/export/topics/stikstof.json`/`topics-index.json` zijn nog **niet gecommit** (bewust, want de batch loopt nog door en deze export is dus alweer een tussenstand; opnieuw draaien vóór commit als er een "definitieve" snapshot nodig is).

### Extra `agy`-tagging-batch: bijgewerkte quota-kalibratie (derde meting)

Nog wat reservequota bij `agy` beschikbaar (gebruiker gaf ~20% budget vrij, `We're at 100%`) — ingezet als extra validatie-/doorvoerbatch bovenop de bestaande lokale tagging (niet i.p.v.), zelfde afweging als eerder (zie sectie "`agy` als tagging-validatiemiddel" hierboven): batch-tagging via `agy` blijft te duur voor de vólle batch, maar is bruikbaar voor gerichte extra doorvoer binnen een quota-budget.

```bash
open -a Docker   # als de daemon nog niet draaide
PYTHONPATH=. uv run python scripts/agy_run_tagging_batch.py --topic stikstof --limit 130
```

**Resultaat: 130 argumenten getagd, 0 fouten, 260 derived + 804 llm tags, gem. 6.3s/argument** (id 40 t/m 169). Tagged-totaal nu **168** (was 38). Quota 100% → 84.47% = **15.53% voor 130 argumenten, ~0.12%/argument** — iets gunstiger dan de eerdere meting (~0.154%/argument bij een kleinere taxonomie), dus binnen het opgegeven 20%-budget; geen noodstop nodig geweest ondanks dat een tussentijdse meting (92%→89% over documenten 40-78) op een schijnbaar hoger tempo (~0.205%/doc) wees — die tussenmeting bleek achteraf ruis, niet de trend. **Les voor een volgende keer**: één tussentijdse `/usage`-meting vroeg in een batch is te ruisgevoelig om een noodstop op te baseren; minstens twee metingen verspreid over de batch (zoals nu toevallig gebeurde) geven een betrouwbaarder beeld.

### Frontend: correspondentie-export, een echte compilerbug, en minister-weergave

Ná de agy-batch verder gewerkt aan de website (nog steeds 2026-07-26). Alle wijzigingen hieronder zijn gecommit (zie `git log`: `7d143ec`, `6e0b638`, `0db997c`).

- **Verse export + correspondentieanalyse**: `make export TOPIC=stikstof` gedraaid tegen de 1034-argument-stand. `build_correspondence_analysis` (in `build_static_data.py`) draait al automatisch mee in de export, geen aparte stap nodig.
- **Echte bug gevonden en gefixt: kolomkoppen toonden altijd hetzelfde (verkeerde) aantal.** `ArgumentColumn.vue` had een prop letterlijk genaamd `arguments`. Dat botst met het ingebouwde JS `arguments`-object dat elke niet-arrow functie heeft — Vue's templatecompiler laat zulke botsende globale namen (whitelist met o.a. `Math`, `Date`, `arguments`) in de template *ongemoeid* i.p.v. ze naar de prop te resolven. Dus `{{ arguments.length }}` in de template gaf stilzwijgend de lengte van dat native object terug (steevast hetzelfde getal, ongeacht de echte data) — vandaar dat Pro/Contra/Onduidelijk allemaal exact hetzelfde (onzinnige) aantal toonden. **Fix**: prop hernoemd naar `argumentList` (`ArgumentColumn.vue` + `[slug].astro`). Na de fix kloppen de aantallen weer (Pro 399, Contra 628, Onduidelijk 7). **Les voor de toekomst**: noem nooit een prop/variabele `arguments` in Vue-templates (of `eval`, `arguments`, en de andere entries in Vue's compiler-whitelist) — de fout is stil, geen crash, geen warning.
- **Bewindspersonen tonen nu een rol i.p.v. niets.** 9 actors hadden `party = NULL` omdat ze als Minister/Staatssecretaris spreken (VLOS `<spreker soort="Minister">` heeft geen `<fractie>`). Nieuwe kolom `documents.speaker_role_title` (schema.sql + `ingest_tk.py`) vangt de VLOS `<functie>`-tekst (bv. "minister van Landbouw, Visserij, Voedselzekerheid en Natuur") voor niet-Kamerlid-sprekers op, getoond op elke `ArgumentCard` ongeacht of de partij bekend is. **`scripts/backfill_minister_info.py`** (nieuw) vult dit met terugwerkende kracht (873 documenten) en backfilt daarnaast **de echte partij** voor 5 van de 9 actors via de TK OData Persoon/FractieZetelPersoon-API (geen AI, een verifieerbare bron): Wiersma→BBB, Erkens/Van der Wal(-Zeggelink)/Harbers→VVD.
  - **Voor Dick Schoof, Jean Rummenie, Piet Adema, Jaimi van Essen is géén partij vindbaar** — bevestigd via twee onafhankelijke OData-paden (`Persoon?$filter=contains(Achternaam,...)` geeft niets terug; `ActiviteitActor?$filter=contains(ActorNaam,...)` vindt wél een `Persoon_Id` voor Schoof, maar dat `Persoon`-record is volledig leeg/een stub, en heeft geen `FractieZetelPersoon`-geschiedenis). Voor Schoof klopt dit ook met de werkelijkheid (partijloos premier). **party blijft bewust NULL voor deze 4** — geen gok, een geverifieerde afwezigheid. Gedocumenteerd als **GitHub issue [#2](https://github.com/SiggyF/bipolariteit/issues/2)** voor wie dit verder wil uitzoeken (bv. `PersoonLoopbaan`/`PersoonNevenfunctie` nog niet geprobeerd).
- **Correspondentiekaart: compactere tooltip + klik-om-te-filteren.** Tooltip van de tag-scatter had geen breedtelimiet (lange `beschrijving`-teksten liepen over het scherm) — nu `max-width: 220px` + word-wrap. Klikken op een tag-punt filtert de Pro/Contra/Onduidelijk-kolommen naar alleen argumenten met die tag (nogmaals klikken = wissen). Cross-island state (elke Astro/Vue-eiland is een aparte Vue-app-instantie, een gewone module-scope `ref` wordt dus niet gedeeld) via een DOM `CustomEvent`, zelfde patroon als `useTheme.ts` al gebruikte voor de dark-mode-toggle — nieuw bestand `lib/useTagFilter.ts`.
- Dev-server tijdens dit werk een aantal keer herstart (`astro dev stop` + `astro dev --background`) om zeker te zijn van verse data/code, niet omdat Vite/Astro caching zelf het probleem was (zie de "echte bug" hierboven).

### Nog openstaand voor een volgende sessie
- Stage-1-batch verder afmaken (zie "Stand bij stoppen" hierboven, ~2870 documenten te gaan) en daarna Stage 2 volle batch.
- GitHub issue #2 (minister-partij) — geen actie vereist, puur gedocumenteerd voor later.
- `activiteit_soort` staat nog op NULL voor alle documenten (zie eerdere sessie) — nog niet opgepakt.
- Correspondentiekaart-klikfilter is geïmplementeerd maar **niet visueel getest in een browser** deze sessie (gebruiker had de Claude-in-Chrome-extensie niet geïnstalleerd) — wel geverifieerd dat de databinding (`argument.tags[].sleutel` ↔ filterlogica) klopt en de pagina zonder fouten rendert. Bij twijfel: handmatig een tag aanklikken op `/topics/stikstof/` en controleren dat de kolommen filteren.

## Stand bij einde sessie (2026-07-25) — verouderd, zie sectie hierboven

## Stand bij einde sessie (2026-07-25) — begin hier bij een nieuwe sessie

- **Stage-1-batch opnieuw op accu gepauzeerd, bewust gestopt (geen crash).** Bij het begin van deze sessie bleek het proces van de vorige sessie (PID 22133/22135) niet meer te leven (machine was kennelijk in slaap/herstart geweest zonder dat het proces netjes afsloot) en LM Studio had geen model meer geladen. Model opnieuw geladen (`lms load qwen/qwen3.6-27b`) en de batch herstart met exact hetzelfde commando; pakte automatisch verder via het skip-mechanisme bij document 977. Na ~1,5 uur (977→1199/3949 documenten geprobeerd, 520→610 arguments) gebruiker naar accu, proces netjes gekild (`kill`, per-document commit dus geen corrupte state) en het model in LM Studio expliciet unloaded.
- **Status bij einde sessie: 1199/3949 documenten geprobeerd, 610 arguments.** Onderweg 11 transiente fouten gezien (mix van `Read timed out` na 120s en `400 Bad Request`) — zelfde bekende patroon als eerdere sessies, die documenten blijven pending en worden automatisch opnieuw geprobeerd bij een volgende run; geen actie nodig.
- **Model is nu unloaded** (`lms unload --all` gedraaid) — bij hervatten dus eerst opnieuw `lms load qwen/qwen3.6-27b` vóór de batch te herstarten.
- **Check voortgang bij hervatten**: `tail -f data/export/run-logs/extract_batch_full.log`, of `uv run python -c "from pipeline.db import db; c=db.connect(db.DEFAULT_DB_PATH); print(c.execute('SELECT COUNT(*) FROM documents WHERE extraction_attempted_at IS NOT NULL').fetchone()[0])"`. Nog ~2750 documenten te gaan, geschat ~9-10 uur bij het eerder gemeten gemiddelde.
- Na afloop: `build_static_data.py` opnieuw draaien voor een verse export, en dan Stage 2 (`redactie_check.py`) op de volle batch overwegen (zelfde LM Studio-instance, dus wachten tot Stage 1 klaar is).
- **Hervatten zodra weer op stroom**: model laden, dan exact hetzelfde commando starten, pakt automatisch verder dankzij het skip-mechanisme (`extraction_attempted_at`, per-document commit):
  ```bash
  export PATH="$HOME/.lmstudio/bin:$PATH"
  lms load qwen/qwen3.6-27b
  nohup uv run python -m pipeline.extract_arguments --topic stikstof --limit 4000 >> data/export/run-logs/extract_batch_full.log 2>&1 &
  ```
- **Stage 2 (`redactie_check.py`) is deze sessie gebouwd en werkt**, maar de volle Stage-2-batch is nog niet gestart (zie sectie verderop) — bewust, om niet te concurreren met Stage 1 op dezelfde LM Studio-instance. Volgorde bij hervatten: eerst Stage 1 afmaken, dán pas een volle Stage-2-batch overwegen (of ze om en om in kleine porties laten lopen als dat sneller moet).
- Direct daarna nuttig, geen LLM nodig: `uv run python -m pipeline.build_static_data --topic stikstof` (verse export) — maar overweeg eerst of oppositions/redactie-data al meegenomen moet worden (nog niet geïmplementeerd, zie Stage 2-sectie).

## Setup om verder te werken

```bash
cd /Users/baart_f/src/bipolariteit
uv sync            # installeert dependencies (requests, pytest) in .venv
uv run pytest tests/ -v
```

Python-dependencies worden beheerd met `uv` (niet pip/venv handmatig, ook niet voor losse scratch-scriptjes: altijd `uv run python ...`). Nieuwe dependency toevoegen: `uv add <pkg>` (of `uv add --dev <pkg>` voor test-only).

`pyproject.toml` heeft nu `[tool.pytest.ini_options] pythonpath = ["."]` — nodig omdat `tests/` geen `__init__.py` heeft, waardoor pytest zonder deze regel de repo-root niet op `sys.path` zet en `import pipeline...` in testbestanden faalt.

## Voortgang (taken uit het plan)

1. ✅ Repo-scaffold + `.gitignore` (data/raw en *.db uitgesloten)
2. ✅ `pipeline/db/schema.sql` + `tests/test_schema_neutrality.py` (slaagt) — 8 tabellen aangemaakt en geverifieerd via `pipeline/db/db.py`
3. ✅ `crawlers/tweede_kamer/` — herschreven als Scrapy-project (`scrapy.cfg` + `tweede_kamer/` package: `settings.py`, `items.py`, `pipelines.py`, `odata.py`, `paths.py`, `spiders/verslagen.py`), consistent met het `scrapy_news/`-plan. Alle empirisch gevonden logica (datumheuristiek, `best_verslag`-voorkeur, `limit*3`-oversampling, dedup) 1-op-1 overgenomen uit de oude `tk_client.py`/`fetch_tk.py`. Geverifieerd: `uv run scrapy crawl verslagen -a topic=stikstof -a limit=5` (uitvoeren vanuit `crawlers/tweede_kamer/`) vindt exact dezelfde 5 verslag-IDs in dezelfde volgorde als de oude client, JSON-metadata byte-identiek. Oude `tk_client.py`/`fetch_tk.py` verwijderd (geen hybride).
   - Let op: Scrapy 2.17 heeft `start_requests()` volledig verwijderd uit de basisklasse (geen backwards-compat shim); de spider gebruikt `async def start(self)` in plaats daarvan.
4. ✅ `pipeline/ingest/ingest_tk.py` — segmenteert VLOS-XML per sprekerbeurt (woordvoerder + interrumpant, generiek gedetecteerd) naar `documents`/`actors`-rijen. Getest: `uv run pytest tests/test_ingest_tk.py` (naam-reconstructie + topic-filter + turn-detectie) en handmatig geverifieerd tegen alle 5 verslagen (3949 documenten, 50 actors).
   - **Naambug gevonden en gefixt**: de TK-bron plakt Nederlandse tussenvoegsels soms achteraan `achternaam` voor sorteerdoeleinden (bv. `achternaam="Plas van der"` i.p.v. "Van der Plas"), en soms een Arabisch "El"-voorvoegsel ook achteraan (bv. "Boujdaini El"). `_speaker_name`/`_reorder_achternaam` reconstrueert nu de juiste volgorde (incl. kleine letter bij tussenvoegsel na een voornaam: "Caroline van der Plas", maar "Van der Plas" zonder voornaam). Dit was cruciaal om nu te fixen, niet later: elk argument in latere stages erft de actor-naam, dus een verkeerde naam had zich overal doorheen verspreid.
   - **Bewuste, nog niet opgeloste kwestie**: de voorzitter (bv. Paulusma/D66, Krul/CDA) wordt als gewone actor met partij opgeslagen wanneer die procedureel het woord voert (bv. "Ik stel voor dat..."). Dit is procedurele tekst, geen politiek argument — maar wordt nu wél als `documents`-rij met partij-attributie bewaard. Dit is *bewust* doorgeschoven naar Stage 1 (LLM-extractie moet dit soort niet-argumentatieve voorzitter-chatter simpelweg geen argumenten opleveren), niet stilzwijgend genegeerd. Als dat niet vanzelf gebeurt, moet `extract_arguments.py` of `ingest_tk.py` alsnog voorzitter-turns filteren/markeren.
5. 🔶 Stage 1 LLM-extractie (`pipeline/extract_arguments.py` + `pipeline/prompts/extract_argument.md`) — werkt, promptversionering toegevoegd, volle batch onderweg maar **gepauzeerd op batterij bij 896/3949 documenten** (zie "Stand bij einde sessie" bovenaan). Zie sectie hieronder voor de kwaliteitsvergelijking tussen modellen.
6. ✅ Tag-taxonomie geïntegreerd (`data/tags.toml` → `pipeline/db/seed_tags.py` + `pipeline/tag_arguments.py`) — zie sectie hieronder. Lokale batch nog niet volledig doorgelopen (39/234+ getagd bij laatste meting), wacht op meer Stage-1-output.
7. ✅ Stage 2 redactie-check (`pipeline/redactie_check.py` + `prompts/redactie_bias_check.md`) — gebouwd en gevalideerd deze sessie, zie eigen sectie hieronder. Volle batch nog niet gedraaid (wacht op Stage 1).
8. 🔶 `build_static_data.py` JSON-export — bestaat en werkt (stats, tags-per-partij, correspondentieanalyse), exporteert nu ook Stage-2-data: `document.redactie_review` (pass_status/notes per document) en `oppositions` (symmetrische lijst tegenargumenten per argument, via nieuwe `fetch_redactie_reviews`/`fetch_oppositions`). Geverifieerd op de live DB: 478 argumenten geëxporteerd, 18 met oppositions, 11 met een redactie_review. **Nog niet gedaan**: dit visueel tonen in de frontend (ArgumentCard.vue kent deze velden nog niet) — puur de export-kant is deze sessie afgerond.
9. ✅ Astro+Vue frontend-scaffold — werkende v1 (`frontend/`), zie eigen sectie hieronder. Toont nog geen opposition-links (afhankelijk van punt 8).
10. ⬜ `run_walking_skeleton.sh` + volledige verificatie

## Belangrijke ontdekkingen tijdens de spike (Tweede Kamer OData API)

Deze zaten niet in de officiële documentatie en moesten empirisch getest worden — belangrijk om te weten voor wie hieraan verder bouwt:

1. **Geen directe FK tussen Activiteit en Vergadering.** De API documenteert geen `Vergadering_Id` op `Activiteit`. `tk_client.find_vergadering_for_activiteit()` gebruikt een datum-heuristiek (±1 dag, `Kamer='Tweede Kamer'`, `Soort='Plenair'`) om de juiste Vergadering te vinden, en kiest bij meerdere kandidaten de dichtstbijzijnde datum. Getest en werkend voor 10/10 stikstofdebatten sinds 2019.
2. **Tijdzone-valkuil**: `Vergadering.Datum` staat opgeslagen als lokale middernacht met `+01:00`/`+02:00`-offset. Een OData `$filter` met een `Z` (UTC) datumgrens op exact dezelfde kalenderdag mist die rij, omdat lokale middernacht in UTC vóór middernacht valt. Oplossing: query met een dag marge (−1/+1) in plaats van een exacte daggrens.
3. **VLOS XML-structuur** van een Verslag-resource (`GET /Verslag/{id}/resource`): namespace `http://www.tweedekamer.nl/ggm/vergaderverslag/v1.0`. Relevante nesting:
   `<vergadering><activiteit onderwerp="...">...<activiteitdeel soort="Spreekbeurt">...<activiteititem soort="Woordvoerder"><woordvoerder><spreker fractie=... weergavenaam=.../><tekst><alinea><alineaitem>...</alineaitem></alinea></tekst></woordvoerder>`.
   Segmentatie voor `ingest_tk.py`: filter top-level `<activiteit>` op `onderwerp` bevat het topic-keyword, zoek daarbinnen alle `<woordvoerder>`-elementen (spreker + tekst = één document/sprekerbeurt). Zie `/tmp/sample_verslag.xml` voor een volledig voorbeeld (niet gecommit, lokaal scratch-bestand — na een reboot moet dit opnieuw gedownload worden via `fetch_tk.py`).
4. **`tkapi`-package overwogen** (PyPI, Python ORM voor deze API): biedt geen ondersteuning voor de twee lastige stukken die wij nodig hebben (resource-XML downloaden, Activiteit↔Vergadering-koppeling), dus bewust niet toegevoegd als dependency — onze eigen `tk_client.py` doet dit al en is getest.
5. **Bronlink nog niet definitief**: `fetch_tk.py` slaat momenteel de OData resource-URL op als `source_resource_url` (verifieerbaar, technisch correct) maar NIET een publieke `tweedekamer.nl`-debatpagina-URL — dat patroon is nog niet uitgezocht en mag niet gegokt worden. Dit moet nog opgelost worden vóór `build_static_data.py` de `documents.url`-kolom vult (zie plan: elk argument moet een link naar de brontekst hebben).

## Stage 1 LLM-extractie: script staat er, klaar voor kwaliteitsvergelijking + volle run

`pipeline/extract_arguments.py` (CLI, gebruikt `pipeline/prompts/extract_argument.md`) leest per document (sprekerbeurt) de tekst, stuurt 'm naar een lokaal LLM via LM Studio's OpenAI-compatibele API, en schrijft `arguments`+`claims`-rijen weg. Gebruik:

```bash
uv run python -m pipeline.extract_arguments --topic stikstof --limit 15 [--min-id N] [--model ...] [--dry-run]
```

- `--dry-run`: extraheert en print, schrijft niets weg (gebruikt voor alle tests tot nu toe).
- `--min-id`: sla documenten met een lager id over — handig omdat de eerste ~40 documenten van het stikstofdebat grotendeels procedureel zijn (opening, welkomstwoord); pas vanaf document-id ~40 begint echte inhoudelijke wisseling (Van der Plas/Bromet/Heutink-discussie).
- Idempotent voor documenten die al minstens 1 argument opleverden (die worden overgeslagen bij een herhaalde run) — **maar niet voor documenten die 0 argumenten opleverden** (bv. procedurele tekst): die hebben geen rij om aan te herkennen en worden bij elke run opnieuw verstuurd. Voor de steekproeffase is dat geen probleem; vóór de volle batch-run moet dit nog een eigen skip-mechanisme krijgen (bv. een `processed_documents`-log of -tabel), anders wordt bij een onderbroken/herstarte volle run onnodig dubbel werk gedaan.
- Prompt verbiedt expliciet een waardeoordeel; voorzitter-/procedurele tekst levert per instructie 0 argumenten op (**punt 4 uit de eerdere sectie hierboven is hiermee opgelost**: getest en bevestigd — documenten 43, 44, 46-49, 52-54 (allemaal voorzitter/orde-tekst) leverden terecht 0 argumenten op in de laatste testrun).

**Testresultaat (`--topic stikstof --limit 15 --min-id 40 --dry-run`, model `qwen/qwen3.6-27b`, `reasoning_effort=none`):** 15 documenten, 0 fouten, 11 argumenten + 10 claims geëxtraheerd, kwalitatief correct (procedurele turns terecht overgeslagen, inhoudelijke turns van Van der Plas/Bromet/Heutink correct als pro/contra-argumenten met claims herkend). Latency: gem. 13.0s/doc (min 3.3s, max 43.9s — hangt sterk af van turnlengte). **Op dat gemiddelde: ~14.3 uur voor de volle 3949 documenten.** Dat is technisch haalbaar (overnight run) maar nog niet als zodanig gedraaid of geverifieerd op een langere steekproef.

### Nog open, volgende concrete stappen
1. ✅ **Kwaliteitsvergelijking tussen modellen gedaan.** Nieuw script `scripts/compare_models.py` (los van `extract_arguments.py` — negeert bewust de `extraction_attempted_at`-skipfilter zodat je hetzelfde vaste documentbereik `id 40-54` steeds opnieuw kan doorrekenen ongeacht wat er al écht verwerkt is; schrijft niets naar de DB, puur console-output). Gebruik: `PYTHONPATH=. uv run python scripts/compare_models.py <model>` (let op: móet vanuit de repo-root met `PYTHONPATH=.`, anders vindt Python de `pipeline`-package niet omdat het script-pad vóór de cwd in `sys.path` staat).

   Resultaat, alle drie op exact dezelfde 15 documenten (id 40-54, topic stikstof):

   | model | gem. latency | geschat volle batch (3949 docs) | argumenten | claims | belangrijkste probleem |
   |---|---|---|---|---|---|
   | `qwen/qwen3.6-27b` | 13.0s | ~14.3u | 11 | 10 | geen gevonden — correcte procedurele filtering, correcte stance/typology |
   | `google/gemma-4-e4b` | 3.3s | ~3.6u | 23 | 2 | over-extractie (knipt één punt op in meerdere "argumenten"), extraheert kale vragen als argument, veel `stance=unclear`/`typology=other` als vluchtheuvel, claims bijna afwezig |
   | `google/gemma-4-31b` | 10.8s | ~11.8u | 8 | 1 | mist een echte inhoudelijke beurt volledig (doc 51 — qwen vond daar 4 argumenten, gemma-31b 0), dezelfde "vergunningverlening"-quote die qwen correct `contra/economic` tagt wordt hier `unclear/other`, claims-extractie vrijwel afwezig |

   **Besluit: `qwen/qwen3.6-27b` blijft de keuze.** Beide gemma-modellen zijn sneller maar leveren merkbaar mindere kwaliteit in — gemma-e4b is te onnauwkeurig om bruikbaar te zijn, gemma-31b is maar ~17% sneller terwijl het echte argumenten en bijna alle claims mist. De ~14 uur voor de volle 3949 documenten (overnight run) is de juiste afweging.
2. Doorvoertijd (~14 uur) is nu bevestigd op basis van 15 documenten, waarvan de meeste inhoudelijk — dus nog steeds een overschatting van het gemiddelde over de hele dataset (die ook veel korte procedurele turns bevat, zoals 43/44/46-49/52-54 hierboven). Een langere steekproef (~50-100 docs) zou een stabieler gemiddelde geven, maar is niet blokkerend voor de volle run.
3. ✅ **Skip-mechanisme voor 0-argument-documenten gebouwd.** Nieuwe kolom `documents.extraction_attempted_at` (schema.sql + handmatige `ALTER TABLE` op de live DB, zelfde eenmalige aanpak als eerder bij `arguments.tagged_at`), gezet ná elke LLM-call (ook bij 0 resultaat), niet alleen bij een geslaagde extractie. `fetch_pending_documents` filtert nu op `extraction_attempted_at IS NULL` i.p.v. `NOT IN (SELECT document_id FROM arguments)`. Bestaande 12 documenten met al bekende arguments zijn met terugwerkende kracht gemarkeerd (`extracted_at` van hun eerste argument). Geverifieerd: 3 procedurele 0-argument-documenten (43, 44, 46) tweemaal achter elkaar gedraaid — tweede run sloeg ze terecht over en ging door naar 47-49, i.p.v. ze opnieuw te versturen. `uv run pytest tests/` blijft groen (16 tests, dit pad had nog geen eigen tests).
4. Nu modelkeuze en skip-mechanisme beide klaar zijn: de volledige batch draaien (`uv run python -m pipeline.extract_arguments --topic stikstof --limit 4000`, overnight), en daarna verder met Stage 2 (`redactie_check.py`).

### ✅ Recall-probleem metadiscours-argumenten gefixt

`qwen/qwen3.6-27b` gaf eerder `{"arguments": []}` terug op een Heutink-beurt (document-id 150) die inhoudelijk overduidelijk over de *legitimiteit van het debat zelf* ging ("Dit is geen dunne lijn", "Ik ga geen grens over" — verzet tegen een mogelijke inperking door de voorzitter). Dat was geen terecht 0-argument/procedureel geval, maar een gemist argument — een recall-probleem, iets anders dan het `extraction_attempted_at`-skipmechanisme (dat voorkomt alleen dat al-verwerkte documenten dubbel verstuurd worden).

**Fix toegepast** in `pipeline/prompts/extract_argument.md`: nieuwe regel die expliciet onderscheid maakt tussen procedurele voorzitters-chatter (geen argument) en metadiscours — uitingen over legitimiteit/reikwijdte/bevoegdheid/spelregels van het debat zelf (wél een argument, met `typology: "other"` en `stance: "unclear"` tenzij een pro/contra-richting duidelijk is).

**Geverifieerd**:
- Document 150 (de bekende Heutink-metadiscours-beurt) levert nu correct 1 argument op (`stance: unclear`, `typology: other`, quote_context correct herkent de zelfreferentiële aard van de uiting).
- Regressietest op de vaste steekproef id 40-54 (via `scripts/compare_models.py qwen/qwen3.6-27b`) blijft consistent: 14 argumenten/14 claims, procedurele documenten (43, 44, 47, 49, 52-54) leveren nog steeds terecht 0 argumenten op. Geen regressie.
- Nog niet opnieuw tegen de volle 200-doc steekproefbatch getest (die batch was met de oude prompt gedraaid, zie hieronder) — dat gebeurt impliciet zodra de review-doc-stap (volgende sectie) opnieuw gegenereerd wordt met de gefixte prompt op vers geëxtraheerde documenten, maar de al-geschreven 137 arguments in de DB zijn met de oude prompt geëxtraheerd en dus niet met terugwerkende kracht gecorrigeerd.

### Grotere steekproefbatch gestart (achtergrondproces, status bij einde sessie: nog lopend)

Om een ~50 pagina's review-document te bouwen voor externe (Gemini-)validatie van de Stage-1-extractiekwaliteit is een bredere batch gedraaid:
```bash
uv run python -m pipeline.extract_arguments --topic stikstof --limit 200
```
✅ **Compleet** (afgerond ná het schrijven van de vorige versie van deze sectie): 200 documenten verwerkt, 0 fouten, 118 nieuwe arguments + 98 claims deze batch. Totaal nu **137 arguments** in de DB (was 19 bij start van de sessie). Latency gem=12.5s/doc, geschat volle batch (3949 docs) ≈ 13.7 uur — consistent met eerdere schatting.

**Voortgang:**
1. ✅ Extractieprompt gefixt voor het metadiscours-recallprobleem hierboven (`pipeline/prompts/extract_argument.md`), + hertest (zie sectie hierboven).
2. ✅ `scripts/build_extraction_review_doc.py` gedraaid → `data/export/extractie_review_stikstof.md` (137 argumenten, 9112 woorden, ~18 pagina's).
3. ✅ Antwoord van Gemini verwerkt → `data/export/extractie_review_feedback.md` en de extractieprompt daarop herzien (zie volgende sectie).
```bash
PYTHONPATH=. uv run python scripts/build_extraction_review_doc.py --topic stikstof --output data/export/extractie_review_stikstof.md
```
Dat genereert een documentje per argument (quote/context/stance/typology/actor) met beoordelingsinstructies voor een externe reviewer (Gemini), analoog aan `data/export/tag_quality_review.md` maar dan voor Stage 1 i.p.v. de tag-laag. Plakken in Gemini en het antwoord verwerken is bewust menselijk werk, niet geautomatiseerd zoals `import_tag_batch.py`.

### Gemini-review van de 137 arguments verwerkt: prompt verder aangescherpt

`data/export/extractie_review_feedback.md` (Gemini's beoordeling per argument + samenvattende patronen) wees op vier systematische problemen, naast de al bekende metadiscours-recall:
1. **Kale standpunten/intenties zonder onderbouwing** werden toch als argument geëxtraheerd (bv. "Ik strijd hier tot de laatste dag voor de boeren", "Afzwakking steunen we niet").
2. **Versnippering**: opeenvolgende zinnen die één punt uitwerken werden opgeknipt in meerdere losse argumenten.
3. **Typologie-inconsistenties**: overmatig gebruik van `legal` voor bestuurlijke/beleidsmatige feiten die geen wet/regelgeving zijn.
4. **Pro/contra-verwarring**: `stance` was gedefinieerd t.o.v. het abstracte onderwerp "{topic}", niet t.o.v. het beleid dat concreet ter discussie staat — leidde tot foute labels bij bv. BBB-sprekers die het eigen verleden verdedigen tegen huidig beleid.
5. **Dubbele extracties** (zelfde punt 2-3x geëxtraheerd binnen één betoog) — cross-document duplicaten (zelfde punt herhaald over meerdere sprekerbeurten) zijn hiermee bewust NIET opgelost (kan niet per-document, elke LLM-call heeft geen zicht op andere documenten) en blijven een open punt voor een latere dedup-stap.

**Beslissing (met gebruiker afgestemd via AskUserQuestion)**: `stance` wordt voortaan gemeten t.o.v. het **zittende/voorgestelde kabinetsbeleid**, niet t.o.v. het abstracte onderwerp. Om dit concreet te maken kreeg `topics` een `description`-kolom (was ongebruikt/`NULL`): een door de gebruiker/onderzoeker geschreven pro/contra-narratief per topic, ingevuld voor `stikstof` via een handmatige `UPDATE topics SET description = ...`. `extract_arguments.py` faalt nu hard (`SystemExit`) als een topic geen `description` heeft — voorkomt een stille terugval naar de oude ambigue definitie voor toekomstige topics (asielbeleid, abortus, etc.).

**Prompt-wijzigingen** (`pipeline/prompts/extract_argument.md`): expliciete "geen onderbouwing = geen argument"-regel met negatieve voorbeelden, "één punt = één argument"-regel (samenvoegen i.p.v. opknippen binnen een sprekerbeurt), aangescherpte `legal`-definitie (alleen echte wet/regelgeving/juridische procedure), en `stance` nu gedefinieerd via de nieuwe `{topic_description}`-placeholder i.p.v. het kale onderwerp.

**Geverifieerd** via `scripts/compare_models.py qwen/qwen3.6-27b --doc-ids <lijst>` (uitgebreid met een `--doc-ids`-flag, was hardcoded op 40-54): getest tegen de specifiek door Gemini gevlagde documenten (37, 56, 101, 107, 116, 122, 129, 133, 150, 167, 169, 175, 192, 218) — geen regressie op procedurele/metadiscours-gevallen, en doc 150 blijft correct 1 argument opleveren. **Nog niet kwantitatief opnieuw beoordeeld** (geen nieuwe Gemini-review-ronde gedraaid op deze wijzigingen) — dat is een logische volgende stap vóór de volle batch.

**Nog niet gedaan**: de 137 bestaande arguments in de DB zijn geëxtraheerd met de oude prompt/stance-definitie en zijn niet met terugwerkende kracht gecorrigeerd. De ~218 documenten met `extraction_attempted_at IS NOT NULL` (incl. 0-argument-gevallen) worden door de huidige skip-logica niet opnieuw verwerkt. Of je dit moet leegmaken en opnieuw draaien vóór de volle batch is nog een open beslissing.

## Antigravity CLI (`agy`) in Docker: werkend als alternatieve LLM-backend

Naast de lokale LM Studio/qwen-pipeline is `agy` (Google's Antigravity CLI, geeft toegang tot Gemini-modellen) nu bruikbaar vanuit een geïsoleerde Docker-container — bedoeld om te testen of een sterker model de extractiekwaliteit verder verbetert. Zie ook het plan-document `~/.claude/plans/om-de-accuraatheid-wat-recursive-hoare.md` voor de volledige achtergrond/afwegingen.

- **`docker/agy/Dockerfile`**: `debian:bookworm-slim` + non-root user `agy`, installeert de CLI via `curl -fsSL https://antigravity.google/cli/install.sh | bash`. Gebouwd en getest (`docker build -t bipolariteit-agy docker/agy`).
- **Auth zonder de host-Keychain aan te raken**: `agy` gebruikt geen API-key-auth (nog niet ondersteund door Google, zie hun GitHub issue #78), alleen browser-OAuth. Credentials + volledige sessiestate blijken te leven onder **`~/.gemini`** (niet `~/.config` of `~/.antigravity`, ondanks wat de naam doet vermoeden — bevestigd door dit empirisch te testen met een probe-mount over meerdere kandidaat-paden). Bind mount: `-v "$HOME/.bipolariteit/agy_gemini_config:/home/agy/.gemini"`. Eenmalige interactieve login (`docker run -it --rm -v ...:/home/agy/.gemini bipolariteit-agy agy`, moet door de gebruiker zelf gedraaid worden i.v.m. de browser-URL/code-plak-stap) volstaat; latere `docker run`s met dezelfde bind mount hergebruiken de sessie zonder opnieuw in te loggen.
- **`~/.bipolariteit/agy_gemini_config/`** bevat dus een live OAuth-token (`antigravity-oauth-token`) plus volledige sessietranscripten — bewust **buiten de repo** gehouden (verplaatst uit het voorheen gebruikte `docker/agy/gemini_config/`, vlak vóór het eerste `git init`, zodat een live token nooit binnen een version-controlled directory kan belanden, ook niet gitignored). `scripts/agy_run_batch.py`/`agy_run_tagging_batch.py`/`agy_test_tag_reasons.py` verwijzen hier nu naartoe via `AGY_GEMINI_CONFIG_DIR = Path.home() / ".bipolariteit" / "agy_gemini_config"`.
- **Non-interactieve extractie werkt**: `agy --print "<prompt>" --model <naam> --sandbox` (geen `--dangerously-skip-permissions` nodig, we vragen alleen tekstgeneratie). Geverifieerd op doc 150 (dezelfde metadiscours-testcase) met zowel `gemini-3.1-pro-low` als `gemini-3.6-flash-low`: beide leveren identieke, correcte JSON-output (1 argument, `stance: unclear`, `typology: other`). **Besluit: `gemini-3.6-flash-low` als eerste keuze** (zelfde kwaliteit op deze test, vermoedelijk sneller/goedkoper dan pro-low — latency nog niet formeel vergeleken).
- **Beschikbare modellen** (`agy models`, na login): `gemini-3.6-flash-{high,medium,low}`, `gemini-3.5-flash-{high,medium,low}`, `gemini-3.1-pro-{high,low}`, `claude-sonnet-4-6`, `claude-opus-4-6-thinking`, `gpt-oss-120b-medium`.
- **⚠️ Geen scriptbare usage/quota-check gevonden.** `/usage`, `/credits`, `/quota` bestaan alleen als interactieve TUI-commando's (bubbletea, crasht met "could not open TTY" zonder een echte terminal) — geen los CLI-subcommando, niets bruikbaars in de logs (`~/.gemini/antigravity-cli/log/*.log`, alleen "starting reload" zonder cijfers) of cache-bestanden. Gebruiker noemde een daglimiet van ~10% — dit kan alleen handmatig gecontroleerd worden door zelf `agy` interactief te starten en `/usage` te typen; geen geautomatiseerde before/after-check mogelijk zolang Google dit niet blootlegt.
- **`scripts/compare_models.py`** kreeg een `--doc-ids`-flag (zie sectie hierboven) — nog niet uitgebreid om `agy` als backend aan te roepen (draait nu alleen tegen de LM Studio/`call_llm`-pad). Logische volgende stap als `agy` serieus als backend gebruikt gaat worden.

**Nog niet gedaan / buiten scope van deze sessie**: `agy` integreren als volwaardige, herbruikbare backend-optie in `pipeline/extract_arguments.py` (naast `call_llm`'s LM Studio-pad).

### Quota-kalibratie: volle batch via `agy` past niet in één dag

Om de "geen scriptbare usage-check"-beperking hierboven te omzeilen: 20 echte extractieprompts (dezelfde 20 documenten als de Gemini-review, via nieuwe scripts `scripts/agy_prepare_batch_prompts.py` + `scripts/agy_run_batch.py`, model `gemini-3.6-flash-low`) door `agy` gedraaid, met de gebruiker die `/usage` handmatig aflas vóór en ná de run (enige beschikbare methode, zie hierboven).

**Resultaat**: 99.50% → 97.38% quota over 20 documenten = **2.12% verbruikt, ~0.106%/document**. Alle 20 calls slaagden (~5s/doc, geen lege antwoorden). Geëxtrapoleerd naar de resterende volle batch (~3949 documenten): **~419% van een dagquota** — grofweg 4-5 dagen quota nodig als die dagelijks reset, dus **niet** in één overnight run te draaien zoals de lokale qwen-setup (die kostte alleen stroom/tijd, geen quota).

**Besluit**: `agy`/Gemini wordt niet gebruikt voor de volle batch — te duur qua dagquota (zie hierboven). De volle 3949-document batch blijft draaien via de lokale qwen/LM Studio-pipeline (`pipeline/extract_arguments.py`, gratis, alleen tijd/stroom). `agy` wordt ingezet als **validatiemiddel**: steekproeven/tweede-beoordeling van de qwen-extracties, analoog aan hoe Gemini via de browser al gebruikt is voor de review van de 137 arguments (`extractie_review_feedback.md`) — maar dan gescript via de Docker-container in plaats van handmatig kopiëren/plakken. `scripts/agy_prepare_batch_prompts.py` + `scripts/agy_run_batch.py` (al gebouwd, zie hierboven) zijn hiervoor het startpunt; een volgende stap zou zijn er een `--doc-ids`-achtige flag aan toe te voegen (zoals `compare_models.py` al heeft) zodat gerichte steekproeven uit de qwen-output makkelijk via `agy` te controleren zijn, i.p.v. de nu hardcoded `DOC_IDS`-lijst.

## Tag-taxonomie: `data/tags.toml` geïntegreerd als tweede-pass tagging

Een argumentatie-onderzoeker leverde `data/tags.toml`: 4 perspectieven → oorspronkelijk 10 labelgroepen → 46 tags (`sleutel`/`beschrijving`), inmiddels uitgebreid naar 11 labelgroepen → 51 tags (zie "Metadiscussie" verderop). Was volledig ongebruikt tot nu toe. Geïntegreerd als:

- **`pipeline/db/schema.sql`**: 3 nieuwe tabellen (`labelgroepen`, `tags`, `argument_tags`, allemaal `IF NOT EXISTS` zodat ze veilig tegen de al-bestaande lokale DB toegepast konden worden), plus `documents.activiteit_soort` en `arguments.tagged_at` kolommen (via `ALTER TABLE`, éénmalig handmatig toegepast — zie hieronder). Toegepast op de echte `data/bipolariteit.db` (3949 documenten, 0 arguments op dat moment) zonder dataverlies, geverifieerd via `.schema`-diff.
- **`pipeline/db/seed_tags.py`**: laadt `tags.toml` in de DB. **Belangrijk voor toekomstige tag-updates van de onderzoeker**: dit is een two-phase sync (eerst alles `active=0`, dan alles wat nog in het bestand staat upserten naar `active=1`), niet clear+reinsert. Dus een tag-update is voortaan gewoon: onderzoeker past `tags.toml` aan → `uv run python -m pipeline.db.seed_tags` → klaar. Verwijderde/hernoemde tags worden stil (`active=0`), nooit hard verwijderd (behoudt `argument_tags`-geschiedenis, geen FK-breuk).
- **`pipeline/taxonomy.py`**: onze eigen (niet uit `tags.toml` afgeleide) inschatting van single- vs. multi-select per labelgroep (`LABELGROEP_SELECTIE`), plus welke 3 labelgroepen deterministisch afgeleid worden i.p.v. door het LLM bepaald (`DERIVED_LABELGROEPEN`: Issue Arena, Actor Type, Parlementaire Context).
- **`pipeline/tag_arguments.py`** + **`pipeline/prompts/tag_argument.md`**: nieuwe, losse tweede pass (draait na `extract_arguments.py`, laat die zelf ongewijzigd) die per argument eerst de 3 deterministische tags toekent (`created_by='derived'`, gratis, geen LLM) en dan de overige 7 labelgroepen (~33 tags) via het lokale LLM laat kiezen (`created_by='llm'`). De tag-catalogus in de prompt wordt runtime uit de DB gegenereerd (nooit hardcoded), dus een tags.toml-update komt automatisch mee in de eerstvolgende run. Idempotent via `arguments.tagged_at IS NULL` (zelfde patroon als Stage 1's bekende 0-resultaat-probleem, nu met een expliciete completion-marker i.p.v. absence-based check).
- **Parlementaire Context — nog niet volledig geverifieerd**: `ingest_tk.py` legt nu `<activiteit soort="...">` vast in `documents.activiteit_soort`. Van de 5 lokale VLOS-bestanden is alleen `"Plenair debat"` → `Context-Plenair` bevestigd (32 hits); de mapping voor Vragenuur/Commissiedebat/Wetgevingsoverleg/Tweeminutendebat in `ACTIVITEIT_SOORT_TO_CONTEXT` (`pipeline/tag_arguments.py`) is een aanname op basis van de terminologie in `docs/plan.md`, nog niet tegen echte data getest. Onbekende `soort`-waarden blijven bewust ongetagd.
- **Getest**: `uv run pytest tests/` (16 tests, incl. nieuwe `test_tags_toml.py` en `test_seed_tags.py`) + een handmatige smoke-test met gefabriceerde data (derived-tags, cardinaliteit-validatie, onbekende-sleutel-validatie) — alle drie gedragingen correct bevestigd. **Nog niet getest tegen echte LLM-output** (Stage 1 heeft nog geen enkel argument in de DB geschreven, alleen `--dry-run`-runs tot nu toe).

Gebruik:
```bash
uv run python -m pipeline.db.seed_tags [--dry-run]
uv run python -m pipeline.tag_arguments --topic stikstof --limit 15 [--min-id N] [--model ...] [--dry-run]
```

## Batch-tag-workflow via Gemini (alternatief voor `tag_arguments.py`'s one-by-one lokale LLM-calls)

`pipeline/tag_arguments.py` tagt één argument per lokale LLM-call (~30s/argument via LM Studio) — voor een handjevol argumenten prima, maar te traag om als workflow te herhalen tijdens iteratie op de taxonomie/prompt. Daarom twee nieuwe losse scripts die hetzelfde databasecontract (`argument_tags`, `arguments.tagged_at`) vullen maar via één plak-actie in een externe chat-LLM (Gemini, gebruiker heeft alleen consumer-abonnementen, zie sectie hieronder):

- **`pipeline/prepare_tag_batch.py`**: haalt ongetagde arguments op (`fetch_untagged_arguments`, zelfde functie als `tag_arguments.py` gebruikt), kent meteen de 3 deterministische tags toe (Arena/Actor-Type/Parlementaire Context — gratis, geen LLM), en schrijft één groot promptdocument weg met de taxonomie-instructies + alle argumenten + een JSON-antwoordskelet. Output plak je in Gemini.
  ```bash
  uv run python -m pipeline.prepare_tag_batch --topic stikstof --limit 40 --output data/export/tag_batch_stikstof.md
  ```
- **`pipeline/import_tag_batch.py`**: leest het geplakte Gemini-antwoord (JSON, evt. in een ```json-codeblok — `_extract_json` strippt dat), valideert per argument tegen de actieve tags-tabel (`_validate_tags`/`load_valid_tags`, hergebruikt uit `tag_arguments.py`), en schrijft geaccepteerde tags weg als `created_by='llm'` + zet `tagged_at`.
  ```bash
  uv run python -m pipeline.import_tag_batch --topic stikstof --input data/export/tag_batch_stikstof_response.json [--dry-run]
  ```

**Geverifieerd**: volledige round-trip gedraaid op de 19 op dat moment beschikbare arguments (`data/export/tag_batch_stikstof.md` → geplakt in Gemini → antwoord opgeslagen als `data/export/tag_batch_stikstof_response.json` → geïmporteerd). Resultaat: 170 `argument_tags`-rijen (38 derived + 132 llm), alle 19 arguments `tagged_at` gezet, geen import-fouten. Nog niet beoordeeld op tag-*kwaliteit* (klopt de labeling inhoudelijk) — dat is nog open, zie volgende sectie.

Deze workflow vervangt `tag_arguments.py` niet (die blijft de "echte" geautomatiseerde pad voor de uiteindelijke volle run), maar is handig voor snelle iteratie/steekproeven zolang de taxonomie/prompt nog niet definitief is.

**Bekende beperking**: `prepare_tag_batch.py --output` gebruikt een vast bestandspad, dus een tweede batch-run (bv. resterende ongetagde argumenten) overschrijft het promptbestand én -- als je hetzelfde pad voor het antwoord gebruikt -- ook het vorige Gemini-antwoord. Bij de eerste keer draaien is dit ook gebeurd: de 19 arguments zijn in twee rondes getagd (11 + 8), maar alleen het antwoordbestand van de laatste ronde (argumenten 12-19) is nog aanwezig in `data/export/`. Geen dataverlies in de DB (beide rondes zijn al geïmporteerd), wel verlies van de ruwe Gemini-respons voor argumenten 1-11 als brondocument. Voor toekomstige batches: geef `--output` een uniek pad per ronde (bv. met argument-id-range of timestamp in de bestandsnaam).

### Tag-kwaliteitscontrole (steekproef, labelgroep "Dialectische Kwaliteit")

Handmatige tweede-beoordeling uitgevoerd op 4 van de 19 getagde arguments (id 8, 15, 16, 17), via `data/export/tag_quality_review.md` (promptbestand, geplakt in Gemini als onafhankelijke tweede beoordelaar met alleen de taxonomiedefinities + volledige argumenttekst, geen kennis van wie de tag oorspronkelijk toekende).

**Resultaat: 3 van 4 correct, 1 fout gevonden — en die fout leidde tot een nieuwe labelgroep, niet alleen een tag-correctie.**
- Arg 8, 15, 16: toegekende drogreden-tags (Stropop, Ad-Hominem, Bespelen-Publiek) bevestigd als terecht.
- **Arg 17: fout, en interessanter dan een gewone misser.** Had `Drogreden-Bespelen-Publiek`, maar de tekst ("wij de plicht hebben om partijen te verwijten wat hier is misgegaan...") is geen drogreden — het is een heel ander soort uiting: een uitspraak *over* de discussie zelf (mag je dit hier zeggen), niet een inhoudelijk argument *in* de discussie. Eerste correctie (`Kwaliteit-Zuiver`) bleek ook niet juist: de uitspraak beweert een blaam-claim ("verantwoordelijk voor het slopen van de boerenstand") als vaststaand feit en gebruikt de plicht-framing om die claim aan bewijslast te onttrekken — dat is geen "schoon" argument, het is gewoon een ander fenomeen dan wat de bestaande taxonomie ving.

**Nieuwe labelgroep "Metadiscussie" toegevoegd** (`data/tags.toml`, perspectief "Filosofisch & Argumentatietheoretisch", naast Redeneerschema en Dialectische Kwaliteit) na overleg met de argumentatie-onderzoeker — brief staat in `docs/research/onderzoeksvraag-discussieniveau.md`, gebaseerd op het pragma-dialectische onderscheid objectniveau vs. metaniveau. 5 tags, `selectie = "enkel"` (`pipeline/taxonomy.py`): `Meta-Bevoegdheid` (wie gaat hierover), `Meta-Agenda-Tijdigheid` (is dit nu aan de orde), `Meta-Reikwijdte` (mag dit hier besproken worden / is deze bewering toelaatbaar), `Meta-Vorm-Setting` (in welke setting/vergaderformat), `Meta-Deelnemers` (wie mag meedoen). Geen `Meta-Object`-tag — afwezigheid van een Metadiscussie-tag betekent gewoon objectniveau (zelfde patroon als "null als geen enkele optie past" elders in de taxonomie). `uv run python -m pipeline.db.seed_tags` gedraaid: nu 11 labelgroepen, 51 tags in de DB (was 10/46). Arg 17 opnieuw gecorrigeerd: `Kwaliteit-Zuiver` vervangen door `Meta-Reikwijdte`.

Conclusie: batch-tagging via Gemini is grotendeels betrouwbaar op deze kleine steekproef, maar niet foutloos — en de ene fout die we vonden wees niet op een verkeerde tag-keuze binnen de bestaande taxonomie, maar op een gat in de taxonomie zelf. Een tweede-beoordelingsstap (net als hier gedaan) blijft zinvol vóór een volle batch-run. De overige labelgroepen (Framing-Focus, Morele Fundamenten, Redeneerschema, etc.) zijn nog niet los gecontroleerd, en de nieuwe Metadiscussie-labelgroep is nog nergens anders dan bij arg 17 toegepast/getest.

## LLM-provider: lokaal via LM Studio, model-keuze nog niet definitief

Lokaal via LM Studio (niet Ollama — gebruiker gebruikt MacPorts + LM Studio, niet Homebrew/Ollama), OpenAI-compatibele server op `http://localhost:1234`. Machine: Apple M2 Max, 64GB RAM. Reden voor lokaal: gebruiker heeft alleen Claude Pro/Gemini Pro (consumer-abonnementen, geen API-toegang inbegrepen), en koos voor een lokale gratis optie boven Gemini's gratis API-tier.

4 modellen lokaal aanwezig (65GB totaal), getest op reasoning-overhead met een triviale prompt ("Zeg alleen het woord: hallo"):

| model | reasoning tokens (triviale test) | opmerking |
|---|---|---|
| `qwen/qwen3.6-35b-a3b` (MoE, 22GB) | 2600+ | oorspronkelijke keuze; reasoning niet uit te zetten gebleken tot de ontdekking hieronder |
| `qwen/qwen3.6-27b` (dense, 17GB) | ~200 zonder fix, **0 mét fix** | zie hieronder — huidige default in `extract_arguments.py` |
| `google/gemma-4-31b` (dense, 19GB) | ~65 | lichte reasoning, nog niet builtin te onderdrukken getest |
| `google/gemma-4-e4b` (dense, 6GB) | 0 | instant, geen reasoning-overhead, nog niet op extractiekwaliteit getest |

**Belangrijke ontdekking: `reasoning_effort` request-parameter.** `chat_template_kwargs.enable_thinking:false` en een `/no_think`-suffix in de prompt werken **niet** bij deze Qwen3.6-modellen via LM Studio. Wat wél werkt: de top-level request-parameter `"reasoning_effort": "none"` in de `/v1/chat/completions`-payload — dit is vermoedelijk wat ook de "Reasoning effort"-toggle in de LM Studio chat-sidebar instelt. Bevestigd via curl op zowel `qwen/qwen3.6-27b` als handmatig door de gebruiker in de UI. Met deze parameter zet `qwen/qwen3.6-27b` `reasoning_tokens` naar 0 en antwoordt direct. `extract_arguments.py` gebruikt dit al standaard (`--reasoning-effort none`, override mogelijk via CLI-flag).

Starten/laden (CLI `lms`, in `~/.lmstudio/bin`, niet standaard op PATH):
```bash
export PATH="$HOME/.lmstudio/bin:$PATH"
lms server start
lms load qwen/qwen3.6-27b   # of: lms unload --all && lms load <ander model> -- pas op met meerdere grote modellen tegelijk geladen (kan "insufficient system resources" geven)
```

## Frontend v1: Astro + Vue, gebouwd op de bestaande 234 arguments

Vooruitlopend op de volle batch (zie hieronder) is een eerste werkende website gebouwd (`frontend/`, Astro + Vue, losse CSS, geen React — conform `docs/plan.md`), zodat besloten kan worden wat er nog nodig is op basis van echte data i.p.v. blind door te bouwen.

- **`pipeline/build_static_data.py`** (nieuw): exporteert `arguments` (+ `claims`, `argument_tags`) naar `data/export/topics/<slug>.json` + `topics-index.json`. Nog geen Stage 2 (redactie/opposition-linking bestaat nog niet). `uv run python -m pipeline.build_static_data --topic stikstof` opnieuw draaien na elke DB-wijziging om de export te verversen.
- **Pagina's**: `/` (topiclijst), `/topics/[slug]/` (drie kolommen pro/contra/onduidelijk — `unclear` bewust een eigen kolom, niet weggelaten, want daar landen o.a. de metadiscours-argumenten uit deze sessie), `/about/` (uitgangspunten/"we listen and we don't judge", zodat het neutraliteits-voorbehoud niet op elke pagina/kaart herhaald hoeft te worden).
- **`StatsPanel.vue`**: percentage pro/contra/onduidelijk per partij, ECharts (`vue-echarts`) met een **custom `renderItem`-series** (niet standaard bar-series — een eerdere per-partij-multi-series-aanpak voor variabele bar-dikte brak de uitlijning tussen y-as-labels en bars; custom renderItem garandeert dat bars altijd gecentreerd blijven op hun category-tick, ongeacht dikte). Bar-dikte schaalt (sqrt) met het aantal argumenten per partij. Kleuren volgen de `dataviz`-skill: diverging paar blauw/rood (pro/contra) + neutraal grijs (onduidelijk), gevalideerd i.p.v. de aanvankelijk handgekozen teal/amber.
- **Partijlogo's**: echte SVG's van Wikimedia Commons (via de Wikimedia API, niet gescrapet) voor de 16 partijen die daadwerkelijk in de data voorkomen; `PartyLogo.vue` valt terug op een simpele zwart-wit initiaal-placeholder voor eenmansfracties zonder officieel logo (Groep Markuszower, Lid Keijzer) — bewust géén verzonnen logo. "PRO" krijgt een disambiguatie-suffix ("voorheen PvdA/GroenLinks") via `lib/parties.ts`.
- **Feedback-UI**: elke `ArgumentCard` heeft een "feedback geven"-knop (verkeerde stance/typologie/geen argument/citaat klopt niet/anders + toelichting), opgeslagen in `localStorage` (bewust geen backend — site blijft statisch) met een "Feedback exporteren"-knop die alles als JSON-bestand dumpt. Periodiek handmatig te legen/verwerken.
- **Tags in de UI**: geëxtraheerde taxonomie-tags (waar aanwezig) tonen als kleine badges met dotted-underline (hover = tooltip met labelgroep + beschrijving + `reden`, zie hieronder).
- Dev server: `cd frontend && npx astro dev --background` (CLAUDE.md van het frontend-scaffold beveelt dit expliciet aan i.p.v. voorgrond-dev-server), status/logs via `astro dev status`/`astro dev logs`, stoppen via `astro dev stop`.

## Tag-kwaliteit: "Kwaliteit-Zuiver" verwijderd + `reden` per tag toegevoegd

Twee taxonomie-verbeteringen na gebruikersfeedback tijdens het bekijken van de UI:

1. **`Kwaliteit-Zuiver` verwijderd** uit `data/tags.toml` (labelgroep "Dialectische Kwaliteit") — "geen herkenbare logische fouten" is een positief kwaliteitsoordeel ("dit argument is logisch zuiver"), in tegenstelling tot de overige tags in die groep die een specifiek retorisch PATROON beschrijven (bv. "dit is een ad-hominem-constructie") zonder te oordelen of dat patroon hier terecht/overtuigend is. Botst met het "we don't judge"-kernprincipe. `uv run python -m pipeline.db.seed_tags` gedraaid: tag is nu `active=0` (soft-delete, geen dataverlies — het ene bestaande argument met deze tag behoudt 'm in zijn geschiedenis).
2. **`argument_tags.reden` toegevoegd** (schema + live-DB via eenmalige `ALTER TABLE`, zelfde patroon als eerdere kolommen): een korte, argument-specifieke onderbouwing per toegekende tag, i.p.v. alleen de generieke tag-beschrijving. Doorgevoerd in:
   - `pipeline/prompts/tag_argument.md` + de inline instructietekst in `prepare_tag_batch.py`: expliciete instructie om per tag een `reden` te geven die het specifieke tekstfragment/patroon benoemt, geen herhaling van de taxonomie-beschrijving.
   - `tag_arguments.py`: JSON-skeleton per tag is nu `{"sleutel": ..., "reden": ...}` i.p.v. een kale string (`_validate_tags` accepteert ter achterwaartse compatibiliteit ook nog kale strings uit oudere geplakte Gemini-antwoorden, dan `reden=None`). `assign_derived_tags` genereert ook voor de 3 deterministische labelgroepen een automatische reden (bv. "Afgeleid van VLOS-activiteitsoort 'Plenair debat'.").
   - `import_tag_batch.py`, `build_static_data.py` (tags-export bevat nu `reden`), `ArgumentCard.vue` (tooltip toont beschrijving + reden).
   - **Geverifieerd tegen een echt model** (`agy`/`gemini-3.6-flash-low`, zie hieronder): reden-teksten zijn daadwerkelijk argument-specifiek (citeren het exacte tekstfragment), geen kale herhaling van de tag-beschrijving.

## `agy` als tagging-validatiemiddel: tweede quota-kalibratie

Naast de eerdere extractie-kalibratie (zie hierboven, 419% dagquota voor de volle batch) is nu ook Stage 2 (tagging) via `agy` gekalibreerd, met dezelfde Docker-opzet:

- **`scripts/agy_test_tag_reasons.py`** (dry-read, geen DB-writes): eerste test op 1 argument, bevestigde dat de reden-teksten goed zijn (zie hierboven).
- **`scripts/agy_run_tagging_batch.py`** (schrijft écht naar de DB, zelfde contract als `tag_arguments.py`): batch van 20 ongetagde argumenten (id 20-39), model `gemini-3.6-flash-low`. **Resultaat: 0 fouten, 40 derived + 174 llm tags, gem. 7.0s/argument.** Quota: 85.20% → 82.12% = **3.08% voor 20 argumenten, ~0.154%/argument** — duurder dan extractie (~0.106%/document), verklaarbaar door de langere taxonomie-catalogus in de prompt en de gemiddeld 8-10 tags + redens per antwoord.
- **Bevestigt het eerdere besluit**: `agy` blijft ongeschikt voor de volle batch (zou nog slechter uitpakken dan de 419%-schatting voor extractie, gezien de hogere kost per argument), en blijft dus **validatie-only** — nu voor zowel Stage 1 als Stage 2. De volle taggingrun blijft via `pipeline/tag_arguments.py` (lokale qwen/LM Studio, gratis) lopen zodra die weer aangezet wordt.
- Na deze batch: **39/234 arguments getagd** (was 19), 384 `argument_tags`-rijen, 214 met een `reden` gevuld (de rest is historisch, van vóór dit veld bestond).

## Extractiebatch gepauzeerd (stroom/batterij), hervatbaar

De volle Stage-1-batch (`pipeline/extract_arguments.py --topic stikstof --limit 4000`, lokale qwen/LM Studio) is halverwege gestopt omdat de laptop op accu liep en de batterij laag werd — **niet** vanwege een fout. Stand bij pauzeren: **414/3949 documenten geprobeerd, 234 arguments**. Herstarten met exact hetzelfde commando pakt automatisch verder waar het gebleven was (skip-mechanisme via `extraction_attempted_at`, per-document commit dus geen corrupte state). Nog te doen zodra weer op stroom: batch hervatten/afmaken, dan `build_static_data.py` opnieuw draaien voor een verse export.

## Stage 2 gebouwd: `redactie_check.py` (balans-check + opposition-linking)

Laatste ontbrekende pipeline-stage uit `docs/plan.md`. Twee losse dingen, geen van beide een fact-check:

1. **Balans-check, deterministisch, geen LLM** — expliciete gebruikerskeuze via een vraag: een `document` hier is één sprekersbeurt van één Kamerlid, dus "is dit document eenzijdig" is triviaal altijd waar en zegt niets. In plaats daarvan: `compute_balance()` berekent de **lopende** pro/contra-verhouding van het topic-corpus, begrensd tot documenten `<= document_id` (niet de hele, nog groeiende corpus tellen — dat zou bij elke run andere getallen opleveren voor dezelfde rij, precies het tegenovergestelde van "deterministisch"). `pass_status` (balanced/imbalanced/flag) volgt uit het minderheidsaandeel (drempels 35%/15%, zie code-comment). Eén `redactie_reviews`-rij per document.
2. **Opposition-linking, wel LLM** (lokale qwen/LM Studio, zelfde contract als de andere stages) — per document met nieuwe pro/contra-argumenten wordt een steekproef van bestaande argumenten met het *tegenovergestelde* standpunt aangeleverd (willekeurig gekozen, niet "meest recente N" — anders wordt een handvol recente argumenten kunstmatig een opposition-hub, sample-artefact i.p.v. signaal), en vraagt de prompt (`prompts/redactie_bias_check.md`) alleen naar `direct_rebuttal` vs. `thematic`-koppelingen, nooit wie gelijk heeft. Geretourneerde id's worden gevalideerd tegen de aangeleverde kandidatenset (zelfde patroon als tag-sleutel-validatie in `tag_arguments.py`) — hallucinaties worden overgeslagen, niet vertrouwd.
- Idempotent via het bestaan van een `redactie_reviews`-rij per document (niet een aparte timestamp-kolom); bij een LLM-fout blijft het document bewust pending (geen rij geschreven) zodat een volgende run het herprobeert — zelfde foutafhandelingspatroon als `extract_arguments.py`.
- Getest: kleine live run + herhaalde run bevestigt idempotency (verwerkt automatisch de volgende documenten, slaat al-gereviewde over) én retry-on-error (een timeout op één document werd bij de volgende run alsnog succesvol verwerkt). `uv run pytest tests/` blijft groen.
- **Nog niet gedaan** (bewust buiten scope van deze stap): oppositions exporteren in `build_static_data.py` + een visuele koppeling tussen tegenargumenten in de frontend (plan-stap 8). Ook de volle Stage-2-batch is nog niet gestart — draait op dezelfde LM Studio-instance als de nog lopende Stage-1-batch, dus wachten tot die klaar is voorkomt onnodige GPU-contentie.

## video_url: geïmplementeerd en gedraaid

Volledig overzicht van alle TK-databronnen/API's/libraries die zijn uitgezocht (OData, SyncFeed, `tkapi`, `tkconv`, Debat Direct, tweedekamer.nl-zoeken, echokamer, OpenDataPortaal-issues) staat in **`docs/tk-data-sources-overview.md`**.

**Blocker opgelost**: de eerdere aanname dat `documents.published_at` een crawl-/fetch-timestamp was, bleek bij verificatie **onjuist** — het is al `markeertijdbegin`, een echte sprekerbeurt-timestamp uit de brontekst (geverifieerd via een directe join tussen een DB-rij en zijn exacte XML-element, exacte match). Maar `published_at` is per-sprekerbeurt, niet debat-breed. De VLOS-bron bevat het debat-brede start-/eindtijdstip rechtstreeks op `<activiteit>`-niveau (`<aanvangstijd>`/`<eindtijd>`, niet eerder opgemerkt).

- **Nieuwe kolommen** `documents.activiteit_aanvangstijd`/`activiteit_eindtijd` (schema.sql + eenmalige `ALTER TABLE` op de live DB), gevuld door `ingest_tk.py` bij nieuwe imports en met terugwerkende kracht voor alle 3949 bestaande documenten via **`scripts/backfill_activiteit_tijden.py`** (eenmalig, `document_exists`-dedup in `ingest_tk.py` zorgt dat een her-run van de ingest bestaande rijen nooit bijwerkt).
- **`pipeline/enrich_video_url.py`** (nieuw, geen LLM): groepeert documenten per activiteit (op `(activiteit_aanvangstijd, activiteit_eindtijd)`), queryt Debat Direct's zoek-API (`cdn.debatdirect.tweedekamer.nl/search?van=&tot=<debatdatum>`, gepagineerd), en kiest de kandidaat met de dichtstbijzijnde starttijd (venster: 5 min) mét een duur-ratio-sanitycheck (max. factor 2 verschil, zelfde principe als `tkconv`) om een toevallige starttijd-match op het verkeerde debat uit te sluiten. Bouwt `video_url` als `https://debatdirect.tweedekamer.nl/{debateDate}/{categoryIds[0]}/{locationId}/{slug}/video`. Idempotent via `documents.video_url IS NULL`.
  ```bash
  uv run python -m pipeline.enrich_video_url --topic stikstof [--dry-run]
  ```
- **Gedraaid en geverifieerd**: alle 8 activiteiten in de stikstof-dataset gematcht (0 zonder match), 3949/3949 documenten kregen een `video_url`, alle 8 gematchte titels komen inhoudelijk overeen met het stikstofonderwerp (bv. "Samenhangende aanpak landbouw, natuur en stikstof", "NPLG en stikstofproblematiek"). `build_static_data.py` opnieuw gedraaid: alle 478 geëxporteerde argumenten hebben nu een werkende `video_url`.
- Tests toegevoegd (`tests/test_enrich_video_url.py`: match-op-tijdvenster, duur-ratio-afwijzing, URL-opbouw). `uv run pytest tests/` blijft groen (23 tests).
- **UX-gevolg, nu opgelost**: de "bron"-link op elke `ArgumentCard` wees eerder alleen naar de ruwe OData-Verslag-resource (XML); er is nu ook een werkende video-link naast beschikbaar (frontend gebruikte `document.video_url` al, was tot nu toe altijd `NULL`).
- **Nog niet gedaan**: `activiteit_soort` staat voor alle 3949 documenten op `NULL` in de live DB (ondanks dat `ingest_tk.py` het al langer vastlegt) — losstaand van deze fix (video_url-matching gebruikt het niet), maar wel relevant voor de eerder genoemde Parlementaire-Context-tag (zie tag-taxonomie-sectie). Vermoedelijk een kolom die pas ná de laatste volle ingest is toegevoegd; behoeft een eigen backfill zoals hierboven, niet gedaan in deze sessie.

### Deep link naar het exacte spreekmoment (`?event=speaker...`)

Gebruiker wees erop dat Debat Direct ook direct naar een specifieke spreker binnen een debat kan linken: `.../{slug}?event=speaker<ISO8601-tijdstip-met-offset, url-encoded>` (naast de generieke `.../video`-link naar het begin van het hele debat).

- **`build_static_data.py`**: nieuwe `_speaker_event_url(video_url, published_at)` — bouwt deze link per argument uit de al-aanwezige `documents.published_at` (VLOS `markeertijdbegin`, zie eerder in dit document) + het debat-brede `video_url`. `published_at` is naive lokale tijd zonder offset; `zoneinfo.ZoneInfo("Europe/Amsterdam")` levert automatisch de juiste `+01:00`/`+02:00`-offset (CET/CEST), geen hardgecodeerde DST-regel nodig. Nieuw exportveld: `document.speaker_video_url`.
- **Geverifieerd**: alle 478 argumenten krijgen een `speaker_video_url`; het format matcht exact het door de gebruiker aangeleverde voorbeeld (`...T17%3A12%3A59%2B0200`). Tests toegevoegd (`tests/test_build_static_data.py`, incl. een winter-datum om de CET-offset apart te bevestigen) — `uv run pytest tests/` blijft groen (27 tests).
- **Frontend** (`ArgumentCard.vue`): toont nu "video (dit moment)" die naar `speaker_video_url` linkt (springt naar de spreker), met "video (hele debat)" (`video_url`) als fallback wanneer er om wat voor reden geen `speaker_video_url` is. Geverifieerd tegen de lopende dev-server (`localhost:4321`) — de link met `?event=speaker...` staat daadwerkelijk in de gerenderde pagina.

## Issue-opruiming + design-pakket "debattenlijst-tijdlijn" (#112)

- Drie issues bleken al opgelost door gemergede PR's maar stonden nog open omdat het Nederlandse "Sluit #N"/"Fixt #N" in de PR-body niet door GitHub's (Engelstalige) auto-close-keywords wordt herkend: **#201** (PR #208, Debatzetten-terminologie), **#188** (PR #206, mini-player-trigger), **#173** (PR #174/#176/#193, video-links-consistentie). Alle drie handmatig gesloten met verwijzing naar de mergende PR. → nieuwe geheugen-regel: na elke merge controleren of de gekoppelde issue(s) daadwerkelijk gesloten zijn.
- Data-analyse (ad-hoc, matplotlib) bevestigde dat de Debatzetten-labelgroep te sparse is voor een tijdlijn-signaal: 626 toekenningen op slechts 29 dagen in een 3,5 jaar corpus, sterk geclusterd per debatdag.
- **Besluit (issue #112, comment)**: `ArgumentTimeline.vue` wordt uitgefaseerd. Vervanging: de bestaande debattenlijst (`frontend/src/pages/debatten/index.astro` + `DebateList.vue`) wordt een kaartenweergave (stance-verdeling/top-tag i.p.v. kale tekstregel), plus een nieuw "volgende debat"-blok bovenaan gevoed door een nog te bouwen lichte agenda-fetch op de bestaande TK OData `Activiteit`-bron (status "Gepland" i.p.v. "Afgerond" — geen nieuwe externe bron, wel nieuwe pipeline-scope). Doel: een gevoel van een actuele, levende site voor terugkerende bezoekers.
- **Design-pakket klaargezet**: `data/export/design-handoff/debattenlijst-tijdlijn/` (+ `.zip`), met README (doel, waarom de tijdlijn wegvalt, bestaande implementatie, openstaande agenda-vraag), `styling-tokens.md`, screenshots (homepage, debattenlijst, huidige tijdlijn, debatdetail, sparsity-analyse) en een `icons/`-subset (Context-Plenair/-Commissie/-Vragenuur/-Tweeminutendebat, uit `docs/design/tag-iconografie/`).
- **Screenshot-valkuil, geen echte bug**: een eerste `fullPage`-Playwright-screenshot van een lang debat (687 argumenten) toonde 13.500px lege ruimte. Bleek `content-visibility:auto` + `contain-intrinsic-size:0 220px` op argumentkaarten (`DebateVideoView.vue:647-648`, bewuste performance-optimalisatie) die niet promoot zonder echt scrollen — en terugscrollen vóór de capture reproduceerde het probleem opnieuw. Losse viewport-shots stitchen gaf op zijn beurt een vals "9x herhaalde video"-artefact door de bewuste `position:sticky` op de video. Opgelost door gewoon een normale (niet-fullPage) viewport-screenshot te gebruiken.

## Issue #145: backfillscript-traagheid bleek een ontbrekende index, niet XML-parsing

`scripts/backfill_speaker_events_meta.py` (de #130-rollout) kostte destijds >45
min over de volledige brondata (**/*.xml). Het issue vermoedde `xml.etree.ElementTree`
(geen streaming) als oorzaak. Bij het oppakken bleek dat maar een klein deel van het
verhaal -- en de "pure Python"-aanname zelf klopte niet: CPython gebruikt voor
`xml.etree.ElementTree` standaard de ingebouwde `_elementtree` C-extensie (net als
`lxml` op libxml2 leunt), dus het verschil tussen beide is geen C-vs.-Python maar
expat vs. libxml2 plus API-verschillen -- vandaar dat de winst van de lxml-overstap
hieronder ook maar ~15% bleek, niet de dramatische versnelling die de C-parser-framing
deed vermoeden:

- **Werkelijke bottleneck**: `documents.external_id` had geen index. Elke
  `SELECT ... WHERE external_id = ?` (dit backfillscript, de overige
  `scripts/backfill_*.py`, én `document_exists()` in `ingest_tk.py` — dus ook
  élke reguliere ingest-run) deed een full table scan over 191k+ rijen,
  gemeten ~55ms per lookup. Bij tienduizenden sprekerbeurten per volledige
  scan liep dat op tot uren. Fix: `CREATE INDEX idx_documents_external_id ON
  documents(external_id)` (schema.sql + eenmalig toegepast op de live DB,
  zelfde patroon als eerdere kolom-toevoegingen) — 25.000x sneller per lookup
  (0,002ms), volledige dry-run van 505 bestanden nu ~10s.
- **XML-parsing was al niet het probleem**: `ET.parse()` + `root.iter()` +
  `.find()` op de eerste 40 bestanden kostte ~0,9s, geen quadratische
  blow-up. Een lxml-overstap is uitgeprobeerd en weer teruggedraaid:
  `lxml.etree.iterparse` (streaming) bleek zelfs 3x trager (Python-overhead
  per generatorstap overheerst de C-parsewinst), en lxml's `.find(tag)`
  bleek zelf trager dan ElementTree's (`lxml.etree.parse()` + een
  handmatige kind-tag-scan i.p.v. `.find()` haalde nog ~15% t.o.v.
  ElementTree, functioneel identiek geverifieerd). Met de index-fix draait
  het script al in ~10s, dus die 15% + een nieuwe dependency + een
  workaround voor lxml's trage `.find()` wogen niet op tegen gewoon
  `xml.etree.ElementTree` laten staan.

Les: de sys-tijd-observatie in het issue (~16 min sys vs ~6 min user) wees
naar syscall/filesystem-overhead, maar dat bleek zelf een symptoom van de
64k+ SQLite full-table-scans, niet van XML-bestandslezen op zich.
