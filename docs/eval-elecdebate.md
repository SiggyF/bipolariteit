# Evalharnas: ELECDEBATE60TO16 (issue #62)

**Status**: eerste echte resultaat binnen (20 sprekersbeurten, zie
"Eerste resultaat" hieronder). `make validate` maakt herhaalbare steekproeven
mogelijk; resultaten landen op `/validatie-rapportage`.

## Waarom

Issue #62 stelt voor een externe, publieke dataset te gebruiken om onze
extractie-/tagpipeline kwantitatief te valideren, als aanvulling op de tot nu
toe steekproefsgewijze experimenten op issue #50 (zie het verworpen
two-turn-experiment, `docs/two-turn-tagging-experiment.md`).

## Twee vormen van validatie, onafhankelijk van elkaar gescoord

1. **Is dit een argument?** Vindt onze extractie-prompt
   (`pipeline/extract_arguments.py`) dezelfde tekstspannen als de dataset als
   "claim met onderbouwing" markeert?
2. **Bevat dit argument 1 van de 2 drogredenen die overlappen?** Kent onze
   tag-prompt (`pipeline/tag_arguments.py`) `Drogreden-Ad-Hominem` of
   `Drogreden-Bespelen-Publiek` toe waar de dataset respectievelijk "Ad
   Hominem" of "Appeal to Emotion" heeft gelabeld?

Verder niets: geen stance, geen typology, geen van de overige 4 drogreden-
typen (zie "Scope drogredenen" hieronder). En expliciet: **tagging draait op
de gouden drogreden-spans van de dataset, niet op wat onze eigen extractie
toevallig vond** (`benchmark_elecdebate.evaluate_tagging`) -- anders werkt een
extractiefout door in de tag-score en meet die niet meer de tagkwaliteit op
zich.

## Definitieverschil "argument": waarom dit niet triviaal is

Onze extractieprompt (`pipeline/prompts/extract_argument.md`) eist één
aaneengesloten citaat met zowel een standpunt ALS de onderbouwing erin
("geen onderbouwing = geen argument"), en voegt herhaling/uitwerking van
hetzelfde punt samen tot één citaat.

De dataset (`guidelines/annotation_guidelines.pdf`, Haddadan et al. 2018)
annoteert Claim en Premise als **losse componenten**, vaak niet-aaneengesloten,
en staat expliciet kale claims zonder premisse toe ("there are cases such
that no clause is supporting a certain claim"). Herhaalde claims worden als
aparte componenten geannoteerd, niet samengevoegd.

Rechtstreeks Claim/Premise-zinnen als gouden "argument"-spans gebruiken (de
eerste aanpak, met `full_components.csv`) vergelijkt dus twee verschillende
eenheden en onderschat de score kunstmatig. Oplossing: `final_relation_graph.csv`
geeft Support/Attack/Equivalent-relaties tussen componenten (`Dependent` ->
`Governor`). Een Claim met een inkomende Support-relatie is precies een
"standpunt MET onderbouwing" -- dezelfde eenheid als onze eigen
argumentdefinitie. Kale claims zonder Support-relatie (die onze extractie ook
zou afwijzen) worden dus terecht niet meegenomen als gouden span.

## De dataset

**ElecDeb60to20** (https://github.com/pierpaologoffredo/ElecDeb60to20),
canonieke bron voor wat oorspronkelijk als "ELECDEBATE60TO16" gepubliceerd
werd (Goffredo et al. 2023, EMNLP: https://aclanthology.org/2023.emnlp-main.684/).
Amerikaanse presidentsverkiezingsdebatten 1960-2020. Drie bronbestanden:

- `data/debates/full_speeches_new.csv` -- 7097 sprekersbeurten (datum,
  spreker, tekst). Dit is onze documenteenheid.
- `data/final_relation_graph.csv` -- 26.230 Support/Attack/Equivalent-relaties
  tussen Claim/Premise-componenten (`Dependent`, `Governor`, beide met hun
  letterlijke tekst + type + spreker). Bron voor de gouden argument-spans
  (zie hierboven).
- `data/fallacy_second_version.csv` -- 2744 drogreden-annotaties, MET
  spreker+datum.

Onderliggend brat-standoff-formaat (`data/ann/*.ann`) bevat de brontekst-
annotaties waar bovenstaande CSV's uit afgeleid zijn -- inclusief discontinue
spans (twee losse tekenreeksen als één component). De `.ann`-offsets zijn
niet direct te hergebruiken tegen `full_speeches_new.csv` (geverifieerd:
zelfde tekst, andere offset, en bestandsnamen coderen niet betrouwbaar de
echte debatdatum), dus dat blijft voor nu buiten scope; zie "Nog te doen".

Ophalen via `data/raw/elecdebate60to16/Makefile`:

```
cd data/raw/elecdebate60to16 && make all
```

`make all` haalt `full_speeches_new.csv`/`final_relation_graph.csv`/
`fallacy_second_version.csv` op -- wat `scripts/convert_elecdebate.py`
daadwerkelijk gebruikt. `make components`/`make pos`/`make conll`/`make paper`
zijn losse, niet-gebruikte targets (eerder overwogen/verworpen bronnen) die
alleen nog als referentiemateriaal dienen.

## Conversie

`scripts/convert_elecdebate.py` bouwt per sprekersbeurt een `EvalRecord`
(`pipeline/eval/schema.py`):

- **Argument-spans** (`final_relation_graph.csv`): alleen Support-relaties
  waarvan de Governor een Claim is en `Speaker1 == Speaker2` (relaties die
  over sprekersbeurten heen lopen vallen buiten onze per-beurt eenheid).
  Eerst matchen op (spreker, exacte datum), met terugval op (spreker, jaar)
  als de datum niet uniek matcht.
- **Drogredenen** (`fallacy_second_version.csv`): zelfde matchstrategie,
  (spreker, datum) met terugval op (spreker, jaar).
- Bij een niet-unieke match wordt de eerste kandidaat gebruikt; aantallen
  niet-gevonden/ambigue/sprekersoverschrijdende matches worden bij het
  draaien geprint (geen giswerk, wel zichtbaar wat niet oplosbaar was).

Standaard alleen de debatjaren **2016 en 2020** (de twee meest recente,
dichtst bij het huidige politieke discours qua onderwerpen/toon):

```
uv run python scripts/convert_elecdebate.py            # jaren 2016,2020 (default)
uv run python scripts/convert_elecdebate.py --years all # volledige dataset
```

Resultaat (2016+2020): 318 records, 999 argument-spans, 336 drogreden-spans.

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
- `benchmark_elecdebate.py` -- CLI-runner: `evaluate_extraction` (onze
  extractieprompt tegen de gouden argument-spans) en `evaluate_tagging` (onze
  tagprompt tegen de gouden drogreden-spans) draaien onafhankelijk van
  elkaar, puur lezend, geen DB-writes -- zelfde patroon als
  `scripts/compare_models.py`. `--limit` (default 15, zelfde conventie als
  `extract_arguments.py`/`tag_arguments.py`) en `--dataset` (default
  `elecdebate60to16`, bepaalt de exportbestandsnaam). Schrijft naast het
  stdout-rapport ook `data/export/eval/<dataset>.json` weg (samenvatting +
  per-voorbeeld items voor `/validatie-rapportage`).

Draaien via `make validate` (root-`Makefile`, vars `DATASET`/`LIMIT`/`MODEL`/
`BASE_URL`, zelfde vorm als `make extract`/`make tag`):

```
cd data/raw/elecdebate60to16 && make all && cd ../../..
make validate LIMIT=20
```

Of los, zonder Makefile:

```
uv run python scripts/convert_elecdebate.py
uv run python -m pipeline.eval.benchmark_elecdebate \
    data/raw/elecdebate60to16/test.jsonl qwen/qwen3.6-27b \
    --base-url http://localhost:1234/v1 --limit 20
```

## Eerste resultaat (2026-08-10, 20 sprekersbeurten, `qwen/qwen3.6-27b`)

| Metriek | precision | recall | F1 | detail |
|---|---|---|---|---|
| Argumentherkenning | 0.41 | 0.54 | 0.47 | tp=2566 fp=3692 fn=2169 (tekens) |
| Drogreden-tags | 1.00 | 0.17 | 0.29 | tp=2 fp=0 fn=10 |

Interpretatie: de tagger is niet overijverig (0 valse positieven), maar mist
het merendeel van de daadwerkelijke Ad Hominem/Appeal to Emotion-instanties
zelfs met de exact juiste tekstspan gegeven -- dat is een recall-probleem in
de tagprompt zelf, niet (meer) een gevolg van gemiste extractie. Zeer kleine
steekproef (n=20); geen conclusie voor productiegebruik, wel een eerste
concreet signaal. Herhaalbaar via `make validate`.

## Nog te doen

- Grotere steekproef (`make validate LIMIT=...` met hoger getal) voor een
  betrouwbaarder beeld.
- Eventueel `data/ann/*.ann` (brat-standoff, bevat discontinue spans) direct
  parsen voor nog nauwkeurigere spans -- vereist opnieuw tekstsearch tegen
  `full_speeches_new.csv` (de `.ann`-offsets zelf zijn niet herbruikbaar, zie
  hierboven), dus een incrementele verbetering, geen fundamentele oplossing.
- Issue #67 (labelgroep "Stijlmiddelen") is losstaand en blokkeert dit niet.
