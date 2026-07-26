# Handoff — Bipolariteit MVP

Status per 2026-07-26. Zie `docs/plan.md` voor het volledige, goedgekeurde architectuurplan. Dit document is voor het vervolg: wat staat er al, wat is er onderweg ontdekt, en wat is de volgende concrete stap.

## Stand bij begin sessie (2026-07-26) — begin hier bij een nieuwe sessie

Bij het begin van deze sessie bleek de sectie hieronder ("Stand bij einde sessie 2026-07-25") **achterhaald**: een latere sessie diezelfde avond had al substantieel werk gedaan (bestandstijden 22:00–22:01, laatste DB-write 00:46) dat toen niet meer in dit document is bijgewerkt en ook nog ongecommit stond. Voor het vervolg dus: vertrouw bij twijfel de DB/`git status`/`git diff`, niet blind de laatst geschreven sectie hieronder.

- **Crawler uitgebreid naar Commissiedebatten** (`crawlers/tweede_kamer/tweede_kamer/odata.py`, `spiders/verslagen.py`): eerder ondersteunde `vergadering_url_for_activiteit`/`pick_closest_vergadering` alleen `Vergadering.Soort='Plenair'`. Nu ook `'Commissie'`, met een titel/onderwerp-woordoverlap-tiebreaker (`_title_words`/stopwoordenlijst) — nodig omdat op drukke commissiedagen tientallen commissies parallel lopen en datum-nabijheid alleen dan niet volstaat. Twee empirisch gevonden misser-gevallen (2025-06-18: 10 same-day kandidaten, verkeerde gekozen zonder titel-tiebreak; een "OMGEZET in schriftelijk overleg"-Activiteit die matchte met een compleet ongerelateerd commissiedebat) staan als comment in `odata.py`. Zonder woordoverlap geeft `pick_closest_vergadering` bewust `None` terug (gemiste match) in plaats van te gokken. Resultaat: het stikstof-corpus groeide van 3949 → **5213 documenten**.
- **`documents.is_voorzitter_turn`-kolom toegevoegd** (schema.sql + `pipeline/ingest/ingest_tk.py`) — lost de al langer bekende kwestie op dat de voorzitter (bv. Paulusma/D66, Krul/CDA) als gewone actor met partij-attributie werd opgeslagen wanneer die procedureel het woord voerde. Gedetecteerd via `build_parent_map`/`is_voorzitter_turn`: de dichtstbijzijnde omsluitende `<activiteitdeel><titel>` bevat "voorzitter" (bv. "Spreekbeurt - De voorzitter") — `<spreker><functie>` zelf draagt geen rolmarkering, blijft altijd "lid Tweede Kamer". Fractie in de brondata blijft ongewijzigd, dit is puur een rol-vlag.
- **`scripts/backfill_voorzitter_turns.py`** (nieuw): eenmalige backfill over de bestaande 3949 documenten (die al vóór deze kolom bestonden) + `--purge-arguments` om arguments die al ten onrechte uit voorzitter-beurten geëxtraheerd waren alsnog te verwijderen (incl. afhankelijke claims/argument_tags/argument_oppositions). **Geverifieerd**: 156 documenten geflagd als voorzitter-beurt, 0 documenten met `is_voorzitter_turn=1` hebben nu nog arguments in de DB — de purge is schoon doorgevoerd.
- `pipeline/extract_arguments.py` (`fetch_pending_documents`) en `scripts/pipeline_status.py` filteren/rapporteren nu op `is_voorzitter_turn = 0`.
- **Stage-1-batch was al verder gevorderd dan hierboven gemeld**: laatste `extraction_attempted_at` stond op 2026-07-25T22:46:58Z (document-id 2236), dus de batch is na de "1199/3949"-stand hieronder gewoon doorgelopen (waarschijnlijk in dezelfde late sessie die de crawler/voorzitter-wijzigingen deed) — maar dat verliep buiten `data/export/extract_batch_full.log` (dat logbestand is stil sinds 10:01 die ochtend), dus de details van die run zijn alleen uit de DB af te leiden, niet uit logs. Bij hervatten (nu weer op stroom): **2951 documenten pending** (van de 5213, exclusief 156 voorzitter-beurten).
- Deze wijzigingen (crawler, schema, ingest, extract_arguments, pipeline_status, backfill-script) stonden aan het begin van deze sessie nog **ongecommit** in de working tree, samen met een losstaande, al-gestagede frontend-redesign (fonts, `useTheme.ts`, CSS, nav/stats/tags-componenten). Beide zijn in deze sessie als aparte commits vastgelegd (zie git-log voor de exacte commit-hashes).
- `data/bipolariteit.db.bak-20260725220207` was een ongetrackt lokaal backup-bestand van vóór de purge-stap — bewust niet in git, blijft lokaal liggen.

## Stand bij einde sessie (2026-07-25) — verouderd, zie sectie hierboven

## Stand bij einde sessie (2026-07-25) — begin hier bij een nieuwe sessie

- **Stage-1-batch opnieuw op accu gepauzeerd, bewust gestopt (geen crash).** Bij het begin van deze sessie bleek het proces van de vorige sessie (PID 22133/22135) niet meer te leven (machine was kennelijk in slaap/herstart geweest zonder dat het proces netjes afsloot) en LM Studio had geen model meer geladen. Model opnieuw geladen (`lms load qwen/qwen3.6-27b`) en de batch herstart met exact hetzelfde commando; pakte automatisch verder via het skip-mechanisme bij document 977. Na ~1,5 uur (977→1199/3949 documenten geprobeerd, 520→610 arguments) gebruiker naar accu, proces netjes gekild (`kill`, per-document commit dus geen corrupte state) en het model in LM Studio expliciet unloaded.
- **Status bij einde sessie: 1199/3949 documenten geprobeerd, 610 arguments.** Onderweg 11 transiente fouten gezien (mix van `Read timed out` na 120s en `400 Bad Request`) — zelfde bekende patroon als eerdere sessies, die documenten blijven pending en worden automatisch opnieuw geprobeerd bij een volgende run; geen actie nodig.
- **Model is nu unloaded** (`lms unload --all` gedraaid) — bij hervatten dus eerst opnieuw `lms load qwen/qwen3.6-27b` vóór de batch te herstarten.
- **Check voortgang bij hervatten**: `tail -f data/export/extract_batch_full.log`, of `uv run python -c "from pipeline.db import db; c=db.connect(db.DEFAULT_DB_PATH); print(c.execute('SELECT COUNT(*) FROM documents WHERE extraction_attempted_at IS NOT NULL').fetchone()[0])"`. Nog ~2750 documenten te gaan, geschat ~9-10 uur bij het eerder gemeten gemiddelde.
- Na afloop: `build_static_data.py` opnieuw draaien voor een verse export, en dan Stage 2 (`redactie_check.py`) op de volle batch overwegen (zelfde LM Studio-instance, dus wachten tot Stage 1 klaar is).
- **Hervatten zodra weer op stroom**: model laden, dan exact hetzelfde commando starten, pakt automatisch verder dankzij het skip-mechanisme (`extraction_attempted_at`, per-document commit):
  ```bash
  export PATH="$HOME/.lmstudio/bin:$PATH"
  lms load qwen/qwen3.6-27b
  nohup uv run python -m pipeline.extract_arguments --topic stikstof --limit 4000 >> data/export/extract_batch_full.log 2>&1 &
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

**Nieuwe labelgroep "Metadiscussie" toegevoegd** (`data/tags.toml`, perspectief "Filosofisch & Argumentatietheoretisch", naast Redeneerschema en Dialectische Kwaliteit) na overleg met de argumentatie-onderzoeker — brief staat in `docs/onderzoeksvraag-discussieniveau.md`, gebaseerd op het pragma-dialectische onderscheid objectniveau vs. metaniveau. 5 tags, `selectie = "enkel"` (`pipeline/taxonomy.py`): `Meta-Bevoegdheid` (wie gaat hierover), `Meta-Agenda-Tijdigheid` (is dit nu aan de orde), `Meta-Reikwijdte` (mag dit hier besproken worden / is deze bewering toelaatbaar), `Meta-Vorm-Setting` (in welke setting/vergaderformat), `Meta-Deelnemers` (wie mag meedoen). Geen `Meta-Object`-tag — afwezigheid van een Metadiscussie-tag betekent gewoon objectniveau (zelfde patroon als "null als geen enkele optie past" elders in de taxonomie). `uv run python -m pipeline.db.seed_tags` gedraaid: nu 11 labelgroepen, 51 tags in de DB (was 10/46). Arg 17 opnieuw gecorrigeerd: `Kwaliteit-Zuiver` vervangen door `Meta-Reikwijdte`.

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
