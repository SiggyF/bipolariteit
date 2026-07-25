# Bipolariteit — MVP Argumentenplatform

## Context

We bouwen een website die argumenten in kaart brengt van gepolariseerde Nederlandse maatschappelijke discussies (stikstof, abortus, asielbeleid, e.d.). De site verzamelt bronnen via drie crawlers (nieuws-RSS, Tweede Kamer open data, NPO-ondertiteling), laat een LLM daaruit gestructureerde argumenten destilleren, en toont die argumenten pro-tegenover-contra per onderwerp.

Kernprincipe, motto: **"We listen and we don't judge."** Dit betekent concreet:
- Geen fact-checking: we registreren welke getallen/claims genoemd worden en door wie, zonder oordeel over juistheid.
- Geen eigen perspectief: elk argument wordt altijd toegeschreven aan de zender ("volgens X..."), nooit als objectieve waarheid van de site zelf.
- Een **redactie-pass** (LLM als redactielid dat op bias checkt) beoordeelt of het tegenperspectief evenwichtig aan bod komt — dit is een balans-check, geen waarheids-check. ("Red team" wordt hier bewust "redactie" genoemd: binnen de redactie zitten leden die specifiek op bias/eenzijdigheid controleren, niet op feitelijke juistheid.)

**Technische voorkeuren van de gebruiker:**
- Geen React. Frontend: Astro met Vue-componenten (geen JSX/React).
- CSS los van het framework: gewone `.css`-bestanden, geen CSS-in-JS/scoped-styling-afhankelijkheid van een component-framework.
- Python blijft beperkt tot de crawlers + LLM-pipeline (geen live Python-webserver) — de site zelf blijft statisch, gratis gehost op Cloudflare Pages.
- Elk argument/document moet ook een link kunnen bevatten naar de bron-video: het Tweede Kamer-debat en/of een YouTube/NPO-video.

De werkmap is momenteel volledig leeg — dit is een greenfield opzet. Doel van deze plan: een werkende "walking skeleton" voor één bron (Tweede Kamer) end-to-end, met een uitbreidbaar datamodel voor de andere twee bronnen.

Waarom Tweede Kamer eerst: het open data-portaal (opendata.tweedekamer.nl) levert gestructureerde entiteiten (`Verslag` voor debatverslagen, `Persoon`, `Fractie` voor politieke partij) — spreker- en partijattributie is dus al gestructureerd beschikbaar, geen scraping-fragiliteit, en geen auteursrechtelijke risico's zoals bij nieuws. Nieuws-RSS is de tweede stap (copyright-veilig via titels/samenvattingen), NPO-ondertiteling de derde en moeilijkste (geen ingebouwde sprekerlabels).

## Repo-structuur

```
bipolariteit/
  crawlers/
    tweede_kamer/             # Scrapy-project (scrapy.cfg + tweede_kamer/ package)
      scrapy.cfg
      tweede_kamer/
        settings.py
        items.py
        pipelines.py           # schrijft ruwe XML + metadata-JSON naar data/raw/tweede_kamer/
        odata.py                 # pure OData URL-building + selectieheuristieken (geen HTTP)
        paths.py                  # RAW_DIR (repo-root gevonden via pyproject.toml, geen hardcoded parents[N])
        spiders/
          verslagen.py             # Activiteit -> Vergadering -> Verslag -> resource, keten van Requests
    scrapy_news/             # Scrapy-project, later toe te voegen
    npo_subtitles/           # SRT-fetch/parse, later toe te voegen
  pipeline/
    db/
      schema.sql              # SQLite DDL, single source of truth
      db.py                   # sqlite3 connection helper
    ingest/
      ingest_tk.py             # ruwe TK data -> documents + actors rows
    extract_arguments.py       # Stage 1 LLM-pass
    redactie_check.py          # Stage 2 LLM-pass (bias-balans + opposition-linking)
    prompts/
      extract_argument.md
      redactie_bias_check.md
    build_static_data.py       # SQLite -> gecommit JSON voor frontend
  data/
    raw/tweede_kamer/          # gitignored
    bipolariteit.db             # gitignored, lokaal
    export/
      topics/<slug>.json        # GECOMMIT — dit voedt de frontend build
      topics-index.json         # GECOMMIT
  frontend/                      # Astro static site, Vue-componenten (geen React), losse .css
    src/pages/index.astro
    src/pages/topics/[slug].astro
    src/components/ArgumentCard.vue
    src/styles/
      main.css                  # losse stylesheet(s), niet framework-gebonden
  tests/
    test_schema_neutrality.py   # controleert dat er geen "correct/verified"-kolom bestaat
    test_pipeline_walking_skeleton.py
  scripts/
    run_walking_skeleton.sh
  .gitignore
```

Belangrijke keuze: de LLM-pipeline draait lokaal tegen SQLite (nooit gecommit); alleen de JSON-export in `data/export/` wordt gecommit. Cloudflare Pages bouwt de Astro-frontend puur op basis van die gecommitte JSON — geen backend, geen secrets, geen always-on server nodig. Dit past bij de eis van gratis, statische hosting.

## Datamodel (SQLite — `pipeline/db/schema.sql`)

- `topics(id, slug, name, description)`
- `sources(id, type ENUM[news_rss|tweede_kamer|npo_subtitle], name, url, retrieved_at)`
- `documents(id, source_id, topic_id NULL, actor_id NULL, external_id, title, content, published_at, raw_ref, url, video_url NULL, activiteit_soort NULL)` — één RSS-item / één sprekerbeurt / één SRT-segment. `content` = de gesegmenteerde tekst zelf (input voor Stage 1 LLM-extractie); `actor_id` = bekende spreker waar de bron dat al structureel levert (bv. TK-segmentatie), NULL voor bronnen zonder vooraf bekende actor. `url` = link naar de brontekst (bijv. het Tweede Kamer-debat/Handelingen-pagina); `video_url` = optionele link naar YouTube/NPO-video van hetzelfde debat/fragment; `activiteit_soort` = VLOS `<activiteit soort="...">`-waarde (bv. "Plenair debat"), gebruikt om de Parlementaire-Context-tag af te leiden.
- `actors(id, name, type ENUM[person|party|organization], party TEXT NULL)`
- `arguments(id, document_id, topic_id, actor_id, stance ENUM[pro|contra|unclear], typology ENUM[factual|moral|economic|legal|other], quote_text, quote_context, extracted_at, cluster_id NULL, redactie_status, tagged_at NULL)` — **bewust geen truth/correctness/verified-kolom**; dit is de schema-niveau-handhaving van "we don't judge". `cluster_id NULL` is de vooruitgeschoven cross-source clustering hook. `tagged_at` markeert of de tag-taxonomie-pass (zie hieronder) al gedraaid heeft voor dit argument.
- `claims(id, argument_id, claim_text, attributed_source_text)` — welk getal/claim genoemd is en welke bron eraan wordt toegeschreven; geen `is_correct`-veld.
- `argument_oppositions(id, argument_a_id, argument_b_id, relation_type ENUM[direct_rebuttal|thematic], created_by ENUM[llm|manual], confidence)` — wordt gevuld door de redactie-stage.
- `redactie_reviews(id, document_id, pass_status ENUM[balanced|imbalanced|flag], notes, reviewer_model, created_at)` — per document, niet per argument: de vraag is of dít document/deze bron eenzijdig selecteerde. Naamgeving verwijst naar het redactieteam waarvan sommige leden specifiek op bias controleren (het "red team"-concept, maar redactioneel benoemd).
- `labelgroepen(naam, perspectief, beschrijving, selectie ENUM[enkel|meervoud], active)` / `tags(sleutel, labelgroep, beschrijving, active)` — de argumentatie-onderzoeker-taxonomie uit `data/tags.toml`, geladen via `pipeline/db/seed_tags.py`. `active` is een soft-delete-vlag: een seed-run zet alles inactief en heractiveert wat nog in `tags.toml` staat, zodat een taxonomie-update nooit `argument_tags`-geschiedenis breekt.
- `argument_tags(id, argument_id, tag_sleutel, created_by ENUM[llm|derived|manual], confidence, assigned_at)` — many-to-many koppeling tussen `arguments` en `tags`. `created_by='derived'` voor de 3 labelgroepen die deterministisch uit al bekende data volgen (Issue Arena, Actor Type, Parlementaire Context), `'llm'` voor de overige 7 (via `pipeline/tag_arguments.py`).

## LLM-pipeline (nu drie stages)

1. **Stage 1 — `extract_arguments.py`** (`prompts/extract_argument.md`): input = één gesegmenteerd document (sprekerbeurt/RSS-item/SRT-chunk); output = JSON-lijst `{actor_name, stance, typology, quote, claims:[{claim_text, attributed_source_text}]}`. Prompt verbiedt expliciet een waardeoordeel of "winnende kant" te kiezen.
2. **Stage 1b — `tag_arguments.py`** (`prompts/tag_argument.md`): tweede, losse pass per reeds geëxtraheerd argument (draait ná Stage 1, laat die ongewijzigd). Kent taxonomie-tags toe uit `data/tags.toml`/de `tags`-tabel: 3 labelgroepen deterministisch afgeleid (geen LLM), 7 via het LLM met een runtime uit de DB gegenereerde tag-catalogus (nooit hardcoded, zodat een tags.toml-update automatisch meekomt). Zelfde "geen waardeoordeel"-principe: ook fallacy-labels (Dialectische Kwaliteit) beschrijven argumentatieve vorm, nooit geldigheid.
3. **Stage 2 — `redactie_check.py`** (`prompts/redactie_bias_check.md`): simuleert een redactielid dat specifiek op bias/eenzijdigheid checkt (niet op feitelijke juistheid). Input = nieuw-geëxtraheerde argumenten van een document + bestaande argumentenset van het topic (beide standpunten); output = `pass_status` (balanced/imbalanced/flag) plus, indien een tegenargument gevonden wordt, een `argument_oppositions`-rij. Expliciet een balans-check, nooit een fact-check.

Let op: een `Verslag` (TK-debatverslag) is een volledig plenair transcript, geen argument-grote eenheid. `ingest_tk.py` moet per sprekerbeurt segmenteren (via `DocumentActor`/`ActiviteitActor`-grenzen) vóórdat tekst naar Stage 1 gaat — anders verlies je attributie en overschrijd je contextbudget.

## Frontend (Astro + Vue → Cloudflare Pages)

- Geen React: Astro als bouwtool/routing, componenten in Vue (`.vue`), styling in losse `.css`-bestanden onder `src/styles/` (geen CSS-in-JS, geen Tailwind-afhankelijkheid van het framework).
- `index.astro` — topiclijst, leest `topics-index.json`.
- `topics/[slug].astro` — MVP-kernview: twee kolommen (pro/contra), elke `ArgumentCard.vue` toont quote, typology-badge, verplichte attributieregel ("Volgens `<actor.name>` (`<actor.party>`)..."), eventuele `claims` als "noemt: `<claim_text>` (bron: `<attributed_source_text>`)" — nooit als platform-feit — en waar aanwezig links naar de brontekst (`document.url`, bijv. Tweede Kamer-Handelingen) en de video (`document.video_url`, YouTube/NPO). Waar `argument_oppositions`-rijen bestaan: visuele link tussen kaarten.
- Actor-centrische "wie gebruikt welke argumenten"-view: expliciet fase 2, niet onderdeel van de walking skeleton.
- Build command: alleen statische Astro-build op gecommitte JSON — geen Workers/functions nodig voor MVP. Python blijft volledig beperkt tot crawlers/pipeline; er is geen live Python-webserver.

## Bouwvolgorde (walking skeleton)

1. Repo scaffolden: bovenstaande mappenstructuur, `.gitignore` (data/raw, data/*.db).
2. `pipeline/db/schema.sql` schrijven + `tests/test_schema_neutrality.py` (faalt als een kolom matcht op `truth|correct|verified|is_valid`).
3. `crawlers/tweede_kamer/tk_client.py` + `fetch_tk.py`: spike tegen de OData-API om te bepalen welke entiteit/veld een debat aan een topic als "stikstof" koppelt (via `Zaak.Onderwerp`/Kamerstukdossier-koppeling of full-text op `Verslag`) — dit is de eerste onbekende die uitgezocht moet worden, geen blokkerend risico voor de rest van de plan.
4. `pipeline/ingest/ingest_tk.py`: segmenteert een `Verslag` per sprekerbeurt naar `documents`+`actors`-rows.
5. `pipeline/extract_arguments.py` + prompt: Stage 1 op de gesegmenteerde documents.
6. `pipeline/redactie_check.py` + prompt: Stage 2 (redactionele bias-check), incl. opposition-linking.
7. `pipeline/build_static_data.py`: SQLite → `data/export/topics/<slug>.json` + index (incl. `url`/`video_url`).
8. `frontend/`: Astro-scaffold met Vue-componenten en losse CSS: `index.astro`, `topics/[slug].astro`, `ArgumentCard.vue`, `styles/main.css`.
9. `scripts/run_walking_skeleton.sh --topic stikstof --limit 10`: draait bovenstaande keten end-to-end.

## Verificatie

1. Draai `run_walking_skeleton.sh --topic stikstof --limit 10`.
2. Controleer `data/raw/tweede_kamer/` bevat 10 ruwe `Verslag`-fetches; `documents`-tabel heeft >10 rijen (gesegmenteerd, dus niet 1:1).
3. Controleer `arguments`-rijen hebben niet-null `actor_id`, `stance`, `typology` (schema `NOT NULL`).
4. Controleer minstens 1 `argument_oppositions`-rij na de redactie-pass (0 bij een echt debatonderwerp is een pipeline-bug, geen geldig resultaat).
5. `tests/test_schema_neutrality.py` slaagt.
6. `tests/test_pipeline_walking_skeleton.py` draait tegen een vaste fixture (opgenomen TK API-response, geen live netwerk) en checkt de JSON-exportvorm.
7. `cd frontend && npm run build && npm run preview` — handmatig controleren dat `topics/stikstof.astro` beide kolommen toont, elke kaart een attributiezin heeft, en minstens één kaartpaar een opposition-link toont.
8. Lint-check: verbied woorden als "fact-check", "correct", "juist"/"onjuist" in `frontend/src/components/*` — goedkope guard tegen neutraliteitsschendingen in UI-copy.
