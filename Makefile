.DEFAULT_GOAL := help

TOPIC ?= stikstof
LIMIT ?= 15

.PHONY: help test test-js test-frontend ca-fixture status build dev dev-stop extract tag redactie export db-init pipeline-status backup-db release release-dry

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

status: ## Doorlopend overzicht van openstaand pipeline-werk per topic (scripts/pipeline_status.py)
	PYTHONPATH=. uv run python scripts/pipeline_status.py

db-init: ## Initialiseer/migreer het lokale SQLite-schema (pipeline/db/schema.sql)
	uv run python -m pipeline.db.db

backup-db: ## Kopieer data/bipolariteit.db naar ~/data/bipolariteit/ (sync die map zelf, bv. met Google Drive)
	mkdir -p ~/data/bipolariteit
	cp data/bipolariteit.db ~/data/bipolariteit/bipolariteit-$$(date +%Y%m%d-%H%M%S).db

extract: ## Stage 1 -- argumenten extraheren (LLM, alleen op netstroom). Vars: TOPIC, LIMIT
	uv run python -m pipeline.extract_arguments --topic $(TOPIC) --limit $(LIMIT)

tag: ## Stage 1b -- tags toekennen (LLM, alleen op netstroom). Vars: TOPIC, LIMIT
	uv run python -m pipeline.tag_arguments --topic $(TOPIC) --limit $(LIMIT)

redactie: ## Stage 2 -- redactie-check/opposition-linking (LLM, alleen op netstroom). Vars: TOPIC, LIMIT
	uv run python -m pipeline.redactie_check --topic $(TOPIC) --limit $(LIMIT)

export: ## SQLite -> data/export/topics/<slug>.json + topics-index.json. Vars: TOPIC
	uv run python -m pipeline.build_static_data --topic $(TOPIC)

build: ## Frontend production build (frontend/dist/)
	cd frontend && npm run build

dev: ## Start de Astro dev-server op de achtergrond (localhost:4321)
	cd frontend && npx astro dev --background

dev-stop: ## Stop de achtergrond dev-server
	cd frontend && npx astro dev stop

release: build ## Publiceer een preview-release naar Cloudflare (zie docs/release.md). Vars: TAG
	@test -n "$(TAG)" || { echo "Gebruik: make release TAG=v0.3.0"; exit 1; }
	uv run python scripts/release_preview.py $(TAG)

release-dry: build ## Zelfde als release, maar toont alleen hostnaam + config. Vars: TAG
	@test -n "$(TAG)" || { echo "Gebruik: make release-dry TAG=v0.3.0"; exit 1; }
	uv run python scripts/release_preview.py $(TAG) --dry-run
