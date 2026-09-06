.DEFAULT_GOAL := help

TOPIC ?= stikstof
LIMIT ?= 15
DATASET ?= elecdebate60to16
MODEL ?= qwen/qwen3.6-27b
# Los van MODEL: dat is de default voor de lokale qwen-pipeline (extract/tag/
# validate) en is geen geldig model voor agy (Docker/Gemini). Leeg = laat het
# script zijn eigen Gemini-default kiezen.
AGY_MODEL ?=
# Zonder expliciete BASE_URL=... op de command line wordt scripts/detect_llm_base_url.sh
# gebruikt: probeert localhost:1234 en host.docker.internal:1234 (devcontainer),
# en stopt met een foutmelding als geen van beide een LM Studio-instance heeft.
ifeq ($(origin BASE_URL),command line)
  RESOLVE_BASE_URL = echo $(BASE_URL)
else
  RESOLVE_BASE_URL = scripts/detect_llm_base_url.sh
endif

.PHONY: help probe crawl ingest pipeline test test-js test-frontend ca-fixture status build dev dev-stop extract extract-agy tag tag-agy redactie validate export enrich-video fetch-debate-events fetch-subtitles match-video-spans check-video-urls tags-taxonomy db-init pipeline-status backup-db release release-dry release-www release-www-dry check-public-exposure argument-doc export-public-data publish-data tiles

help: ## Toon deze lijst
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

test: ## Draai de volledige pytest-suite
	uv run pytest tests/ -v

test-js: ## Unittests van de rekencode in de frontend (vitest, geen browser nodig)
	cd frontend && npx vitest run

ca-fixture: ## Genereer de gouden prince-fixture voor de correspondentie-tests
	PYTHONPATH=. uv run python scripts/dump_ca_fixture.py

test-frontend: ## Rooktest van de filterbalk in een echte browser (bouwt + serveert zelf)
	cd frontend && npm run build
	@cd frontend && npx astro preview --port 4321 >/dev/null 2>&1 & \
		pid=$$!; sleep 4; \
		(cd frontend && node tests/smoke-filters.mjs); status=$$?; \
		kill $$pid 2>/dev/null; exit $$status

probe: ## Tel TK-activiteiten per kandidaat-trefwoord, vóór een crawl. Vars: KEYWORDS
	@test -n "$(KEYWORDS)" || { echo 'Gebruik: make probe KEYWORDS="asiel migratie"'; exit 1; }
	PYTHONPATH=.:crawlers/tweede_kamer uv run python scripts/probe_topic_keywords.py $(KEYWORDS)

crawl: ## Stage 0 -- TK-verslagen crawlen naar data/raw/tweede_kamer/, vóór ingest. Vars: TOPIC, LIMIT, SOORT (default "Plenair debat (debat)")
	cd crawlers/tweede_kamer && uv run scrapy crawl verslagen -a topic=$(TOPIC) -a limit=$(LIMIT) $(if $(SOORT),-a soort="$(SOORT)",)

ingest: ## Stage 0b -- gecrawlde VLOS-XML importeren naar SQLite (documents/actors), vóór extract. Vars: TOPIC
	@test -n "$(TOPIC)" || { echo 'Gebruik: make ingest TOPIC=stikstof'; exit 1; }
	uv run python -m pipeline.ingest.ingest_tk --topic $(TOPIC)

pipeline: ## Volledige analyse-pipeline voor één topic op rij: crawl -> ingest -> extract -> tag -> export (zie docs/pipeline.md). Vars: TOPIC, LIMIT, SOORT, BASE_URL. `redactie` draait hier bewust niet in mee -- vereist Docker agy/Gemini i.p.v. de lokale LLM van de rest van deze keten, en herstructureert de hele argumentenboom (zie #252), dus een bewuste losse stap. export regenereert ook data/export/gepubliceerd/ lokaal; publiceren naar bipolariteit-data (tags-taxonomy/publish-data) blijft een bewuste losse stap erna.
	$(MAKE) crawl TOPIC=$(TOPIC) LIMIT=$(LIMIT)
	$(MAKE) ingest TOPIC=$(TOPIC)
	$(MAKE) extract TOPIC=$(TOPIC) LIMIT=$(LIMIT)
	$(MAKE) tag TOPIC=$(TOPIC) LIMIT=$(LIMIT)
	$(MAKE) export

status: ## Doorlopend overzicht van openstaand pipeline-werk per topic (scripts/pipeline_status.py)
	PYTHONPATH=. uv run python scripts/pipeline_status.py

db-init: ## Initialiseer/migreer het lokale SQLite-schema (pipeline/db/schema.sql)
	uv run python -m pipeline.db.db

backup-db: ## Kopieer data/bipolariteit.db naar ~/data/bipolariteit/ (sync die map zelf, bv. met Google Drive)
	mkdir -p ~/data/bipolariteit
	cp data/bipolariteit.db ~/data/bipolariteit/bipolariteit-$$(date +%Y%m%d-%H%M%S).db

extract: ## Stage 1 -- argumenten extraheren (LLM, alleen op netstroom). Vars: TOPIC, LIMIT, BASE_URL
	@url=$$($(RESOLVE_BASE_URL)) || exit 1; \
	uv run python -m pipeline.extract_arguments --topic $(TOPIC) --limit $(LIMIT) --base-url $$url

extract-agy: ## Stage 1 -- argumenten extraheren via Docker agy (Gemini). Vars: TOPIC, LIMIT, AGY_MODEL, MIN_ID
	PYTHONPATH=. uv run python scripts/agy_run_extraction_batch.py --topic $(TOPIC) --limit $(LIMIT) $(if $(AGY_MODEL),--model $(AGY_MODEL),) $(if $(MIN_ID),--min-id $(MIN_ID),)

tag: ## Stage 1b -- tags toekennen (LLM, alleen op netstroom). Vars: TOPIC, LIMIT, BASE_URL, IDS, IDS_FILE (gerichte hertag-batch, negeert LIMIT)
	@url=$$($(RESOLVE_BASE_URL)) || exit 1; \
	uv run python -m pipeline.tag_arguments --topic $(TOPIC) --limit $(LIMIT) --base-url $$url $(if $(IDS),--ids $(IDS),) $(if $(IDS_FILE),--ids-file $(IDS_FILE),)

tag-agy: ## Stage 1b -- tags toekennen via Docker agy (Gemini). Vars: TOPIC, LIMIT, AGY_MODEL
	PYTHONPATH=. uv run python scripts/agy_run_tagging_batch.py --topic $(TOPIC) --limit $(LIMIT) $(if $(AGY_MODEL),--model $(AGY_MODEL),)

redactie: ## Stage 2 -- argumentenboom bouwen + tweezijdige redactie (structureren + pro/contra-beoordeling, via Docker agy/Gemini) en meteen exporteren (#252). Vars: TOPIC, AGY_MODEL (default gemini-3.8-flash-medium)
	PYTHONPATH=. uv run python scripts/agy_run_confrontatie_tree.py --topic $(TOPIC) $(if $(AGY_MODEL),--model $(AGY_MODEL),)
	uv run python -m pipeline.build_confrontatie_export --topic $(TOPIC)

validate: ## Evalharnas draaien tegen een gouden validatiedataset (issue #62), zie docs/eval-elecdebate.md. Vars: DATASET, LIMIT, MODEL, BASE_URL
	uv run python scripts/convert_elecdebate.py
	@url=$$($(RESOLVE_BASE_URL)) || exit 1; \
	uv run python -m pipeline.eval.benchmark_elecdebate data/raw/$(DATASET)/test.jsonl $(MODEL) --dataset $(DATASET) --base-url $$url --limit $(LIMIT)

export: ## SQLite -> data/export/topics/<slug>.json + topics-index.json + data/export/gepubliceerd/ (lean, zie #163), voor alle topics (incl. video_url-enrichment + video-matching, zie issue #209). Publiceren naar bipolariteit-data blijft een losse stap (make publish-data)
	uv run python -m pipeline.enrich_video_url
	uv run python -m pipeline.fetch_debate_events
	uv run python -m pipeline.fetch_subtitles
	uv run python -m pipeline.match_argument_spans
	uv run python -m pipeline.build_static_data
	$(MAKE) export-public-data

enrich-video: ## Vult documents.video_url/debatdirect_id via Debat Direct, voor alle topics (geen LLM, geen netstroom nodig, gebruik pipeline.enrich_video_url --topic direct voor één topic)
	uv run python -m pipeline.enrich_video_url

fetch-debate-events: ## Cachet de debatdirect events-array (exact per-beurt-anker) per debat naar data/debate_events/, voor alle topics (voorbereiding op arguments.start_seconds/end_seconds, geen LLM, gebruik pipeline.fetch_debate_events --topic direct voor één topic)
	uv run python -m pipeline.fetch_debate_events

fetch-subtitles: ## Cachet het NL-ondertitel-VTT per debat naar data/subtitles/, voor alle topics (voorbereiding op arguments.start_seconds/end_seconds, geen LLM, gebruik pipeline.fetch_subtitles --topic direct voor één topic)
	uv run python -m pipeline.fetch_subtitles

check-video-urls: ## Controleert of opgeslagen raw_video_url-manifesten nog afspeelbaar zijn (master + eerste video-rendition), voor alle topics (geen LLM, geen netstroom nodig, gebruik pipeline.check_video_urls --topic/--limit voor een subset)
	uv run python -m pipeline.check_video_urls

match-video-spans: ## Vult arguments.start_seconds/end_seconds door quote_text te matchen tegen de gecachete VTT-ondertitels, gekalibreerd op de debatdirect events-anker per beurt, voor alle topics (geen LLM, vereist fetch-debate-events+fetch-subtitles vooraf, gebruik pipeline.match_argument_spans --topic direct voor één topic)
	uv run python -m pipeline.match_argument_spans

argument-doc: ## Exporteert alle pro/contra-argumenten van TOPIC (met claims) als markdown -- invoer voor `make redactie`, geen LLM-call
	uv run python -m pipeline.export_argument_doc --topic $(TOPIC)

tags-taxonomy: ## data/tags.toml -> frontend/src/lib/tagsTaxonomy.generated.ts
	PYTHONPATH=. uv run python scripts/export_tags_taxonomy.py

export-public-data: ## data/export/topics/*.json -> data/export/gepubliceerd/ (lean, per perspectief/onderwerp/tag), voor publish-data (issue #163)
	cd frontend && npx tsx scripts/export_public_data.ts

tiles: ## data/export/plenair-map.json -> plenair-map.pmtiles (vector-tile-pyramide, morecantile-grid + dask, zie issue #215/#253) -- experimenteel alternatief renderpad, los van `export`
	uv run python -m pipeline.tiling.build_pyramid

publish-data: export-public-data ## Commit + push data/export/gepubliceerd/ (submodule) naar bipolariteit/bipolariteit-data, gefetcht via jsDelivr (zie docs/release.md). Los van een frontend-release, niet automatisch in CI
	uv run python scripts/publish_data.py

build: ## Frontend production build (frontend/dist/)
	cd frontend && npm run build

dev: ## Start de Astro dev-server op de achtergrond (0.0.0.0:4321, ook bereikbaar via localhost:4321). Data komt in dev standaard van data/export/gepubliceerd/ i.p.v. de jsDelivr-CDN (zie lib/dataBaseUrl.ts) -- overschrijf desgewenst met PUBLIC_DATA_BASE_URL=...
	cd frontend && npx astro dev --background --host 0.0.0.0

dev-stop: ## Stop de achtergrond dev-server, incl. weesprocessen die de lockfile kwijt is
	cd frontend && npx astro dev stop
	@pids="$$(pgrep -f 'frontend/node_modules/astro/bin/astro\.mjs dev' || true)"; \
	if [ -n "$$pids" ]; then \
		echo "Weesprocessen gevonden (niet in .astro/dev.json): $$pids -- worden ook gestopt."; \
		kill $$pids 2>/dev/null; sleep 1; \
		still="$$(pgrep -f 'frontend/node_modules/astro/bin/astro\.mjs dev' || true)"; \
		if [ -n "$$still" ]; then kill -9 $$still 2>/dev/null || true; fi; \
	fi

# De ontwikkelbalk wordt bij het bouwen ingebakken, dus PUBLIC_RELEASE_TAG moet
# mee met `npm run build` -- niet met het releasescript, dat draait pas als
# dist/ al af is. Daarom bouwen deze targets zelf in plaats van `build` als
# prerequisite te gebruiken.
release: ## Publiceer een preview-release naar Cloudflare (zie docs/release.md). Vars: TAG
	@test -n "$(TAG)" || { echo "Gebruik: make release TAG=v0.3.0"; exit 1; }
	cd frontend && PUBLIC_RELEASE_TAG="$(TAG)" npm run build
	uv run python scripts/release_preview.py "$(TAG)"

release-dry: ## Zelfde als release, maar toont alleen hostnaam + config. Vars: TAG
	@test -n "$(TAG)" || { echo "Gebruik: make release-dry TAG=v0.3.0"; exit 1; }
	cd frontend && PUBLIC_RELEASE_TAG="$(TAG)" npm run build
	uv run python scripts/release_preview.py "$(TAG)" --dry-run

release-www: ## Publiceer main naar www.bipolariteit.org (zie docs/release.md)
	cd frontend && PUBLIC_RELEASE_OFFICIEEL=true npm run build
	uv run python scripts/release_www.py

release-www-dry: ## Zelfde als release-www, maar toont alleen de config
	cd frontend && PUBLIC_RELEASE_OFFICIEEL=true npm run build
	uv run python scripts/release_www.py --dry-run

check-public-exposure: ## Controleer dat er geen gevoelige bestanden publiek staan. Vars: HOST
	@test -n "$(HOST)" || { echo "Gebruik: make check-public-exposure HOST=www.bipolariteit.org"; exit 1; }
	uv run python scripts/check_public_exposure.py "$(HOST)"
