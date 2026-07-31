# Bipolariteit

Een platform dat argumenten in kaart brengt uit gepolariseerde Nederlandse
maatschappelijke discussies — te beginnen met stikstof. De bedoeling is niet
om uit te maken wie gelijk heeft, maar om zichtbaar te maken welke argumenten
er, van welke kant, gebruikt worden.

> "We listen and we don't judge."

## Uitgangspunten

- **Geen fact-checking.** We registreren welke getallen en claims genoemd
  worden en door wie, zonder oordeel over of ze kloppen.
- **Geen eigen perspectief.** Elk argument wordt altijd toegeschreven aan de
  zender ("volgens X…"), nooit gepresenteerd als objectieve waarheid van de
  site zelf.
- **Redactionele balans, geen waarheidscheck.** Waar een redactie-pass
  bestaat, checkt die alleen of het tegenperspectief evenwichtig aan bod
  komt — niet of een standpunt feitelijk juist is.

Volledige toelichting: de `/about`-pagina van de site (bron:
[`frontend/src/pages/about.astro`](frontend/src/pages/about.astro)).

## Snel starten

### Pipeline (Python)

Dependencies worden beheerd met [`uv`](https://docs.astral.sh/uv/) (niet
handmatig pip/venv).

```sh
uv sync                # installeert dependencies in .venv
make db-init            # initialiseert/migreert het lokale SQLite-schema
make test                # draait de pytest-suite
```

De LLM-pipeline (extractie/tagging/redactie-check) draait lokaal tegen SQLite
en heeft een lokaal taalmodel nodig; zie `make help` voor de losse
stages (`extract`, `tag`, `redactie`, `export`).

### Frontend (Astro + Vue)

```sh
cd frontend && npm install
make dev                 # start de Astro dev-server op localhost:4321 (achtergrond)
make build                # productie-build (frontend/dist/)
```

De frontend is volledig statisch en bouwt puur op de gecommitte JSON in
`data/export/` — geen live backend, database of secrets nodig om de site te
draaien.

## Nuttige Makefile-targets

`make help` toont het volledige, actuele overzicht. Een greep:

| Target | Doel |
| --- | --- |
| `make test` | Volledige pytest-suite |
| `make test-js` | Vitest-unittests van de rekencode in de frontend |
| `make dev` / `make dev-stop` | Astro dev-server starten/stoppen |
| `make build` | Frontend production build |
| `make db-init` | Lokaal SQLite-schema initialiseren/migreren |
| `make status` | Overzicht van openstaand pipeline-werk per topic |

## Architectuur & datapipeline

Drie bronnen (Tweede Kamer-open-data, nieuws-RSS, NPO-ondertiteling — TK
eerst) worden gesegmenteerd tot documenten, waarna een LLM-pipeline in
stages argumenten extraheert, ze tagt met een argumentatietheoretische
taxonomie, en een redactionele balans-check uitvoert. Het resultaat wordt
geëxporteerd naar gecommitte JSON die de statische frontend voedt.

Voor het volledige architectuurplan (datamodel, repo-structuur,
pipeline-stages in detail): [`docs/plan.md`](docs/plan.md).
Voor de lopende status en sessiegeschiedenis (wat is er al gedaan, wat staat
nog open): [`docs/handoff.md`](docs/handoff.md).

## Releasen

Een release is een git-tag die naar een Cloudflare Workers preview-URL
publiceert. Zie [`docs/release.md`](docs/release.md) voor de volledige
procedure en eenmalige inrichting.

## Licentie

[GNU GPLv3](LICENSE).
