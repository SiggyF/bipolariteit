# Pipeline-overzicht

Elke stap tussen "een debat vindt plaats" en "de argumenten staan op de site"
heeft een eigen Makefile-target. Dit document geeft de volgorde en waar elk
target in die volgorde hoort. Voor de deploy zelf (Cloudflare, DNS,
wrangler), zie [release.md](release.md).

## De kernketen

```
crawl -> ingest -> extract -> tag -> redactie -> export -> tags-taxonomy -> export-public-data -> publish-data
```

`make pipeline TOPIC=<slug>` draait de eerste zes stappen (t/m `export`) op
rij voor één topic. De laatste drie (`tags-taxonomy`, `export-public-data`,
`publish-data`) zitten daar bewust niet in — zie [Publiceren](#publiceren-bewust-los).

| # | Target | Doet | Netstroom/LLM |
| --- | --- | --- | --- |
| 0 | `crawl` | Haalt TK-verslagen op via de OData-API, schrijft ruwe VLOS-XML naar `data/raw/tweede_kamer/`. Vars: `TOPIC`, `LIMIT`, `SOORT`. | netwerk, geen LLM |
| 0b | `ingest` | Segmenteert die XML per sprekerbeurt naar `documents`/`actors` in SQLite. Vars: `TOPIC`. | lokaal, geen netwerk |
| 1 | `extract` | Destilleert argumenten (stance/typologie/quote) per document via een lokale LLM. Vars: `TOPIC`, `LIMIT`, `BASE_URL`. | **alleen op netstroom** (LLM) |
| 1b | `tag` | Kent labels toe aan geëxtraheerde argumenten. Vars: `TOPIC`, `LIMIT`, `BASE_URL`. | **alleen op netstroom** (LLM) |
| 2 | `redactie` | Bias-check + opposition-linking (het "redactielid" uit het motto, zie [plan.md](plan.md)). Vars: `TOPIC`, `LIMIT`, `BASE_URL`. | **alleen op netstroom** (LLM) |
| 3 | `export` | SQLite -> `data/export/topics/<slug>.json`. Draait zelf ook `enrich_video_url`, `fetch_debate_events`, `fetch_subtitles` en `match_argument_spans` (video-koppeling, zie issue #209), daarna `build_static_data`. Geen vars nodig, draait voor alle topics. | lokaal + netwerk voor de video-koppeling, geen LLM |

`extract`/`tag` hebben Docker/Gemini-varianten (`extract-agy`, `tag-agy`,
Vars ook `AGY_MODEL`, `MIN_ID`) voor als er geen lokale LM Studio-instance
beschikbaar is; die zitten niet in `make pipeline`, met de hand draaien.

### Vóór crawl: probe

`make probe KEYWORDS="asiel migratie"` telt hoeveel TK-activiteiten een
kandidaat-trefwoord oplevert, zodat je vooraf weet of een `crawl` zinvol is.
Los target, geen onderdeel van de keten.

### Video-koppeling in detail

`export` bundelt vier stappen die vroeger los gedraaid moesten worden (zie
issue #209 — zonder deze stap toont de site een debat met een lege
tijdlijn):

1. `enrich-video` — vult `documents.video_url`/`debatdirect_id` via Debat
   Direct.
2. `fetch-debate-events` — cachet per-beurt-ankers naar `data/debate_events/`.
3. `fetch-subtitles` — cachet NL-ondertitel-VTT naar `data/subtitles/`.
4. `match-video-spans` — matcht `quote_text` tegen de ondertitels, gekalibreerd
   op de events-ankers, en vult `arguments.start_seconds`/`end_seconds`.

Elk van deze vier bestaat ook als los target (`--topic direct` voor één
topic), voor als je alleen die stap opnieuw wil draaien, bv. na een
handmatige `--force`-hercalibratie.

## Publiceren: bewust los

De site is statisch: alleen wat in `data/export/gepubliceerd/` (submodule
`bipolariteit/bipolariteit-data`) staat, is live. Dat gaat in drie stappen,
en die worden **niet automatisch** aan `make pipeline` geknoopt:

| Target | Doet |
| --- | --- |
| `tags-taxonomy` | `data/tags.toml` -> `frontend/src/lib/tagsTaxonomy.generated.ts` |
| `export-public-data` | `data/export/topics/*.json` -> `data/export/gepubliceerd/` (lean, per perspectief/onderwerp/tag, issue #163) |
| `publish-data` | Commit + push van die submodule naar de publieke data-repo, via jsDelivr opgehaald door de live site |

Reden om dit een bewuste stap te houden: `publish-data` pusht naar een
publiek, extern repo. Dat hoort een expliciete keuze te zijn, geen
neveneffect van een analyse-run. Na elke sessie die `data/export/*.json`
verandert (via `export`, of via handmatige tagging/redactie) hoort een
voorstel om `make publish-data` te draaien.

De frontend zelf (`make build`, `make release TAG=...` /
`make release-www`) is weer een aparte, latere stap — zie
[release.md](release.md).

## Ondersteunend / niet in de keten

Deze targets horen bij de pipeline maar draaien op eigen moment, niet als
vaste schakel:

| Target | Waarvoor |
| --- | --- |
| `status` | Overzicht van openstaand werk per topic (`scripts/pipeline_status.py`). |
| `db-init` | Schema aanmaken/migreren (`pipeline/db/schema.sql`). Eenmalig / bij schema-wijzigingen. |
| `backup-db` | Kopie van `data/bipolariteit.db` wegschrijven. |
| `check-video-urls` | Controleert of opgeslagen `raw_video_url`-manifesten nog afspeelbaar zijn. |
| `validate` | Evalharnas tegen een gouden dataset, zie [eval-elecdebate.md](eval-elecdebate.md). |
| `argument-doc` | Exporteert pro/contra-argumenten van één topic als markdown, voor handmatig structureren. |
| `confrontatie-tree` | Genereert de argumentenboom-export via Docker agy (Gemini) + `build_confrontatie_export`. |
| `check-public-exposure` | Controleert dat er geen gevoelige bestanden publiek staan op een gegeven host. |
| `test` / `test-js` / `test-frontend` / `ca-fixture` | Testsuites. |
| `dev` / `dev-stop` | Lokale Astro dev-server. |

## Eén topic van nul tot live, samengevat

```
make probe KEYWORDS="..."          # optioneel, vooraf peilen
make pipeline TOPIC=<slug>         # crawl -> ingest -> extract -> tag -> redactie -> export
make tags-taxonomy                 # als data/tags.toml gewijzigd is
make export-public-data
make publish-data                  # bewuste, losse publicatiestap
make build && make release TAG=... # of make release-www voor main
```
