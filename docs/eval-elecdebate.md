# Evalharnas: ELECDEBATE60TO16 (issue #62)

**Status**: harnas + converter werken end-to-end tegen de echte dataset;
nog geen benchmarkrun tegen een LLM uitgevoerd (dat is de volgende stap).

## Waarom

Issue #62 stelt voor een externe, publieke dataset te gebruiken om onze
extractie-/tagpipeline kwantitatief te valideren, als aanvulling op de tot nu
toe steekproefsgewijze experimenten op issue #50 (zie het verworpen
two-turn-experiment, `docs/two-turn-tagging-experiment.md`).

## Twee vormen van validatie, verder niets

1. **Is dit een argument?** Vindt onze extractie-prompt
   (`pipeline/extract_arguments.py`) dezelfde tekstspannen als de dataset als
   Claim/Premise markeert?
2. **Bevat dit argument 1 van de 2 drogredenen die overlappen?** Kent onze
   tag-prompt (`pipeline/tag_arguments.py`) `Drogreden-Ad-Hominem` of
   `Drogreden-Bespelen-Publiek` toe waar de dataset respectievelijk "Ad
   Hominem" of "Appeal to Emotion" heeft gelabeld?

Verder niets: geen stance, geen typology, geen precision (de dataset bevat
geen bevestigde niet-argumentatieve tegenvoorbeelden), geen van de overige 4
drogreden-typen. Zie "Scope drogredenen" hieronder voor waarom.

## De dataset

**ElecDeb60to20** (https://github.com/pierpaologoffredo/ElecDeb60to20),
canonieke bron voor wat oorspronkelijk als "ELECDEBATE60TO16" gepubliceerd
werd (Goffredo et al. 2023, EMNLP: https://aclanthology.org/2023.emnlp-main.684/).
Amerikaanse presidentsverkiezingsdebatten 1960-2020, drie annotatielagen:

- `data/debates/full_speeches_new.csv` -- 7097 sprekersbeurten (datum,
  spreker, tekst). Dit is onze documenteenheid.
- `data/component_data/full_components.csv` -- 44.657 zinnen gemarkeerd als
  Claim of Premise, **ongeacht** of ze ook een drogreden zijn.
- `data/fallacy_second_version.csv` -- 2744 drogreden-annotaties, MET
  spreker+datum (in tegenstelling tot de eerder gevonden, beperktere bron
  `pierpaologoffredo/FallacyDetection`, die alleen fallacieuze spans zonder
  sprekerskoppeling had).

Onderliggend brat-standoff-formaat (`data/ann/*.ann`) bevat de brontekst-
annotaties waar `full_components.csv`/`final_relation_graph.csv` uit
afgeleid zijn -- inclusief discontinue spans (twee losse tekenreeksen als één
component). De `.ann`-offsets zijn niet direct te hergebruiken tegen
`full_speeches_new.csv` (geverifieerd: zelfde tekst, andere offset, en
bestandsnamen coderen niet betrouwbaar de echte debatdatum), dus dat blijft
voor nu buiten scope; zie "Nog te doen".

Ophalen via `data/raw/elecdebate60to16/Makefile`:

```
cd data/raw/elecdebate60to16 && make all
```

`make all` haalt alleen `full_components.csv`/`full_speeches_new.csv`/
`fallacy_second_version.csv` op -- wat `scripts/convert_elecdebate.py`
daadwerkelijk gebruikt. `make pos`/`make conll`/`make paper` zijn losse,
niet-gebruikte legacy-targets (de eerder gevonden `FallacyDetection`-bron)
die alleen nog dienen als referentiemateriaal.

## Conversie

`scripts/convert_elecdebate.py` bouwt per sprekersbeurt een `EvalRecord`
(`pipeline/eval/schema.py`):

- **Componenten** (`full_components.csv`) hebben alleen een `Year`-kolom,
  geen spreker/datum -- een zin wordt gezocht binnen alle beurten van dat
  jaar (tekstsubstring, geen fuzzy matching).
- **Drogredenen** (`fallacy_second_version.csv`) hebben spreker+jaar, dus
  eerst filteren op (jaar, spreker), dan pas op tekst zoeken.
- Bij een niet-unieke match wordt de eerste kandidaat gebruikt; aantallen
  niet-gevonden/ambigue matches worden bij het draaien geprint (geen
  giswerk, wel zichtbaar wat niet oplosbaar was).

Standaard alleen de debatjaren **2016 en 2020** (de twee meest recente,
dichtst bij het huidige politieke discours qua onderwerpen/toon):

```
uv run python scripts/convert_elecdebate.py            # jaren 2016,2020 (default)
uv run python scripts/convert_elecdebate.py --years all # volledige dataset
```

Resultaat (2016+2020): 502 records, met een deel niet-gevonden/ambigue
matches (geprint bij het draaien) -- dat is geen fout die opgelost moet
worden, we gebruiken gewoon wat wél uniek te matchen is.

Output (`data/raw/elecdebate60to16/test.jsonl`) blijft, net als de brondata,
onder `data/raw/` (gitignored) -- we distribueren de dataset zelf niet mee.

## Scope drogredenen: waarom precies deze 2 van de 6

Toets: kan de tag toegekend worden zonder een inhoudelijk oordeel te vellen
over of de onderliggende redenering klopt?

- **Ad Hominem, Appeal to Emotion** -- structureel vast te stellen (is dit
  een persoonlijke aanval? wordt hier emotie ingezet?), geen oordeel nodig
  over de inhoud. Vandaar `Drogreden-Ad-Hominem`/`Drogreden-Bespelen-
  Publiek` in `data/tags.toml`.
- **Appeal to Authority, False Cause, Slippery Slope** -- vereisen wél een
  inhoudelijk oordeel (is de autoriteit terecht overtuigend? klopt de
  causale claim niet? is het voorspelde gevolg implausibel?). Dat
  tegenspreekt ons "we listen and we don't judge"-uitgangspunt
  (`pipeline/db/schema.sql`), dus principieel buiten scope -- niet toevallig
  dat we er geen tag voor hebben.
- **Slogans** -- voldoet wél aan de toets, maar is geen drogreden: een
  slogan claimt geen redeneerfout, het is een stijlmiddel. Zie issue #67
  voor een apart labelgroep "Stijlmiddelen" (niet nu uit te werken).

Zie `pipeline/eval/label_mapping.py` voor de mapping zelf.

## Het evalharnas

`pipeline/eval/`:
- `schema.py` -- `EvalRecord`/`Span`/`FallacySpan`, het genormaliseerde
  JSONL-tussenformaat.
- `label_mapping.py` -- `FALLACY_TAG_MAP` (de 2 bevestigde overlaps) en
  `UNMAPPED_FALLACIES` (de overige 4, met motivatie per label).
- `metrics.py` -- precision/recall/F1, tekenniveau voor spans, labelset voor
  fallacy-tags, micro-geaggregeerd over alle records.
- `load_elecdebate.py` -- laadt het JSONL-tussenformaat.
- `benchmark_elecdebate.py` -- CLI-runner: hergebruikt de bestaande
  productieprompts (`extract_arguments._build_prompt`/`call_llm`, gevolgd
  door `tag_arguments._build_prompt`/`call_llm` met het model se eigen
  stance/typology-output) ongewijzigd tegen elk record, puur lezend, geen
  DB-writes -- zelfde patroon als `scripts/compare_models.py`.

Draaien:

```
cd data/raw/elecdebate60to16 && make all
cd ../../..
uv run python scripts/convert_elecdebate.py
uv run python -m pipeline.eval.benchmark_elecdebate \
    data/raw/elecdebate60to16/test.jsonl <model> --base-url http://localhost:1234/v1
```

## Nog te doen

- Eerste echte benchmarkrun tegen een lokaal model, resultaten hier
  bijschrijven (zelfde stijl als `docs/two-turn-tagging-experiment.md`).
- Eventueel `data/ann/*.ann` (brat-standoff, bevat discontinue spans die
  `full_components.csv` als één ellips-samengevoegde tekst exporteert) direct
  parsen voor een hoger matchpercentage op componenten -- vereist opnieuw
  tekstsearch tegen `full_speeches_new.csv` (de `.ann`-offsets zelf zijn niet
  herbruikbaar, zie hierboven), dus een incrementele verbetering, geen
  fundamentele oplossing.
- Issue #67 (labelgroep "Stijlmiddelen") is losstaand en blokkeert dit niet.
