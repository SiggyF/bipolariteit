# Pipeline-overzicht

Elke stap tussen "een debat vindt plaats" en "de argumenten staan op de site"
heeft een eigen Makefile-target. Dit document geeft de volgorde en waar elk
target in die volgorde hoort. Voor de deploy zelf (Cloudflare, DNS,
wrangler), zie [release.md](release.md). Voor een overzicht van wélke
databestanden waar horen en via welk kanaal ze gepubliceerd worden, zie
[data-layout.md](data-layout.md).

## De kernketen

```
crawl -> ingest -> extract -> tag -> export -> tags-taxonomy -> export-public-data -> publish-data
```

`make pipeline TOPIC=<slug>` draait de eerste vijf stappen (t/m `export`) op
rij voor één topic. De laatste drie (`tags-taxonomy`, `export-public-data`,
`publish-data`) zitten daar bewust niet in — zie [Publiceren](#publiceren-bewust-los).

| # | Target | Doet | Netstroom/LLM |
| --- | --- | --- | --- |
| 0 | `crawl` | Haalt TK-verslagen op via de OData-API, schrijft ruwe VLOS-XML naar `data/raw/tweede_kamer/`. Vars: `TOPIC`, `LIMIT`, `SOORT`. | netwerk, geen LLM |
| 0b | `ingest` | Segmenteert die XML per sprekerbeurt naar `documents`/`actors` in SQLite. Vars: `TOPIC`. | lokaal, geen netwerk |
| 1 | `extract` | Destilleert argumenten (stance/typologie/quote) per document via een lokale LLM. Vars: `TOPIC`, `LIMIT`, `BASE_URL`. | **alleen op netstroom** (LLM) |
| 1b | `tag` | Kent labels toe aan geëxtraheerde argumenten. Vars: `TOPIC`, `LIMIT`, `BASE_URL`. | **alleen op netstroom** (LLM) |
| 2 | `export` | SQLite -> `data/export/topics/<slug>.json`. Draait zelf ook `enrich_video_url`, `fetch_debate_events`, `fetch_subtitles` en `match_argument_spans` (video-koppeling, zie issue #209), daarna `build_static_data`. Geen vars nodig, draait voor alle topics. | lokaal + netwerk voor de video-koppeling, geen LLM |

`extract`/`tag` hebben Docker/Gemini-varianten (`extract-agy`, `tag-agy`,
Vars ook `AGY_MODEL`, `MIN_ID`) voor als er geen lokale LM Studio-instance
beschikbaar is; die zitten niet in `make pipeline`, met de hand draaien.

### redactie: bouwt de argumentenboom (issue #252)

`make redactie TOPIC=<slug>` bouwt de argumentenboom van een topic en is de
enige plek waar de redactionele balanscontrole daadwerkelijk gebeurt — niet
als losse, corpus-brede stap (dat was een eerdere, nooit-gebruikte opzet,
`pipeline/redactie_check.py`, inmiddels verwijderd), maar ingebed in het
bouwen van de boom zelf. Twee stappen, via Docker agy/Gemini:

1. **Structureren** (`pipeline/prompts/argument_tree_gemini.md`, 1 call):
   selecteert uit alle argumenten van een topic een subset die elkaar
   scherp tegenspreekt, en legt daartussen getypeerde relaties (`support` =
   onderbouwing, `conflict` = weerlegging, AIF-gebaseerd, zie issue #252).
2. **Redactiecheck, per relatie apart** (`pipeline/prompts/
   boomredactie_rebuttal_detection.md` voor `conflict`,
   `boomredactie_support_check.md` voor `support`): elke relatie krijgt een
   eigen, geïsoleerde LLM-call met een zuiver feitelijke ja/nee-vraag
   ("engageert dit argument aantoonbaar met de kern van het andere?"), nooit
   een geldigheidsoordeel. Een relatie die "nee" krijgt vervalt.

Elke afgeronde stap wordt direct weggeschreven naar
`data/export/argument-docs/checkpoints/<slug>/` (structureer-output +
één regel per relatiecheck). Faalt een call halverwege, dan hervat
`make redactie TOPIC=<slug> RESUME=1` vanaf daar zonder de dure
structureer-call of de al gedane checks opnieuw te betalen. Met
`CANONICAL=1` worden bijna-duplicaten eerst samengevoegd tot canonieke
stellingen (issue #254, lokale LM Studio-call, geen agy-credits).

`pipeline/confrontatie_tree.py` voegt de uitkomsten samen (geen LLM), en
`pipeline/build_confrontatie_export.py` exporteert het resultaat naar
`data/export/argument-trees/<slug>.json`. Zie de module-docstring van
`pipeline/confrontatie_tree.py` en issue #252 voor waarom de eerdere opzet
(twee rolgebonden redacteuren, "onenigheid = signaal") is losgelaten: die
bleek niet te discrimineren tussen relaties, ongeacht de inhoud.

Draait bewust niet mee in `make pipeline` (zie hieronder): vereist Docker
agy/Gemini i.p.v. de lokale LLM van de rest van de keten, en herstructureert
de hele boom bij elke run.

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
2. `fetch-debate-events` — cachet per-beurt-ankers naar `data/debate-events/`.
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
| `tags-taxonomy` | `config/tags.toml` -> `frontend/src/lib/tagsTaxonomy.generated.ts` |
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
| `redactie` | Bouwt de argumentenboom (structureren + per-relatie redactiecheck, zie hierboven). |
| `argument-doc` | Exporteert pro/contra-argumenten van één topic als markdown, voor inspectie zonder LLM-call. |
| `check-public-exposure` | Controleert dat er geen gevoelige bestanden publiek staan op een gegeven host. |
| `test` / `test-js` / `test-frontend` / `ca-fixture` | Testsuites. |
| `dev` / `dev-stop` | Lokale Astro dev-server. |

## Eén topic van nul tot live, samengevat

```
make probe KEYWORDS="..."          # optioneel, vooraf peilen
make pipeline TOPIC=<slug>         # crawl -> ingest -> extract -> tag -> export
make tags-taxonomy                 # als config/tags.toml gewijzigd is
make export-public-data
make publish-data                  # bewuste, losse publicatiestap
make build && make release TAG=... # of make release-www voor main
```
