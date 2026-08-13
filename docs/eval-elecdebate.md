# Evalharnas: ELECDEBATE60TO16 (issue #62)

**Status**: harnas + gouden-datareconstructie werken correct (span-merge- en
dedup-fixes verwerkt); eerdere resultaten waren gemeten op nog-foutieve
gouden data en zijn ongeldig verklaard (zie "Eerste resultaten" hieronder).
`make validate` maakt herhaalbare, cumulatieve steekproeven mogelijk;
resultaten landen op `/validatie-rapportage`.

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
de gouden drogreden-citaten van de dataset, niet op wat onze eigen extractie
toevallig vond** (`benchmark_elecdebate.evaluate_tagging`) -- anders werkt een
extractiefout door in de tag-score en meet die niet meer de tagkwaliteit op
zich.

**"Span" (tekstgrenzen) is alleen relevant voor de argumentherkenning-as.**
Daar vergelijken we letterlijk óf onze extractie dezelfde tekstgrenzen vindt
als de dataset -- dat is inherent een vraag over begin/eind. Tagging kent
geen eigen spandetectie: net als de productie-tagprompt (`tag_arguments.py`)
classificeert de tag-stap één compleet, al afgebakend citaat in één keer, met
een reden. De start/end-tekenposities die de brondataset bij een drogreden
opslaat, gebruiken we uitsluitend om dat citaat uit de brontekst te snijden
vóórdat we het aan de tagprompt geven -- ze spelen daarna geen rol meer in
de classificatie of de score.

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

## Bekende beperkingen van de referentiedataset

Niet elke score-afwijking is een fout van onze pipeline. Twee voorbeelden uit
`elecdebate60to16` (zie `/validatie-rapportage/elecdebate60to16`):

**Ontbrekende annotatie.** Trump: *"The NAFTA agreement is defective. Just
because of the tax and many other reasons, but just because of the fact…"*.
Onze extractie herkent dit terecht als standpunt + onderbouwing, maar de
dataset heeft hier geen Claim-Premise-paar met een Support-relatie
geannoteerd (zie "Definitieverschil" hierboven) -- dus telt dit als
fout-positief ("onterecht herkend als argument"), terwijl het argument
evident aanwezig is. Met andere woorden: de referentiedataset zelf mist hier
een annotatie, dit is geen extractiefout.

**Te korte/inconsistente spangrenzen.** Dezelfde stop-and-frisk-uitspraak
van Trump staat in de dataset met twee verschillende spangrenzen: eenmaal
mét de aanloop (*"we went from 2,200 to 500 ... had a tremendous impact on
the safety of New York City"*) en eenmaal alleen het sluitstuk (*"stop-and-
frisk had a tremendous impact ... Tremendous beyond belief"*), allebei
gelabeld als Appeal to Emotion (`Drogreden-Bespelen-Publiek`). Losstaand,
zonder de voorafgaande cijfers over gedaalde criminaliteit, leest die korte
versie niet overtuigend als emotionele bespeling -- eerder als een kale
bewering. Onze tag-prompt classificeert 'm dan ook niet als zodanig
(`voorspeld: []`), wat de precision op deze drogreden drukt zonder dat het
per se een tagfout is: een te kort afgesneden span is voor mens én model
moeilijk eenduidig te classificeren.

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
  als de datum niet uniek matcht. **Alle premisses die dezelfde claim
  steunen worden samengevoegd tot ÉÉN span** (min start, max end over
  Dependent + Governor van alle bijbehorende rijen), gegroepeerd op
  (sprekersbeurt, letterlijke Governor-tekst) -- niet losse claim- en
  premisse-fragmenten. Een eerdere versie voegde ze abusievelijk apart toe,
  wat kale stellingnames zonder onderbouwing en onderbouwingen zonder claim
  als afzonderlijke "argumenten" opleverde (bij handmatige review van
  `/validatie-rapportage` ontdekt).
- **Drogredenen** (`fallacy_second_version.csv`): zelfde matchstrategie,
  (spreker, datum) met terugval op (spreker, jaar). Genest-dubbele
  annotaties (dezelfde drogreden op twee granulariteiten, bv. een volledige
  twee-zinsuiting én een aparte rij voor alleen de tweede zin) worden
  verwijderd via `_drop_nested_fallacies()`: een kortere span die volledig
  binnen een langere met hetzelfde label valt, vervalt.
- Bij een niet-unieke match wordt de eerste kandidaat gebruikt; aantallen
  niet-gevonden/ambigue/sprekersoverschrijdende matches worden bij het
  draaien geprint (geen giswerk, wel zichtbaar wat niet oplosbaar was).

Standaard alleen de debatjaren **2016 en 2020** (de twee meest recente,
dichtst bij het huidige politieke discours qua onderwerpen/toon):

```
uv run python scripts/convert_elecdebate.py            # jaren 2016,2020 (default)
uv run python scripts/convert_elecdebate.py --years all # volledige dataset
```

Resultaat (2016+2020): 318 records, 627 argument-spans, 324 drogreden-citaten.

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
  tagprompt tegen de gouden drogreden-citaten) draaien onafhankelijk van
  elkaar, puur lezend, geen DB-writes -- zelfde patroon als
  `scripts/compare_models.py`. `--limit` (default 15, zelfde conventie als
  `extract_arguments.py`/`tag_arguments.py`) en `--dataset` (default
  `elecdebate60to16`, bepaalt de exportbestandsnaam). Schrijft naast het
  stdout-rapport ook `data/export/eval/<dataset>.json` weg (samenvatting +
  per-voorbeeld items voor `/validatie-rapportage`).

**Elke run bouwt voort op de vorige**, net als `extraction_attempted_at`/
`tagged_at` dat doen in de productiepipeline: de export bevat
`evaluated_indices` (welke regels van `<dataset>.jsonl` al gescoord zijn),
en `--limit` selecteert steeds de eerstvolgende, nog niet gescoorde records
i.p.v. telkens dezelfde eerste N. tp/fp/fn-tellingen en items worden
opgeteld bij de vorige run. Bij een ander model dan de vorige run begint de
telling voor dat model opnieuw (modellen door elkaar optellen zou een
misleidend gemiddelde geven); `--fresh` forceert dat ook expliciet, bv. na
een prompt-wijziging. Kanttekening: dit steunt op een stabiele
recordvolgorde in `<dataset>.jsonl` -- bij een andere `--years`-selectie of
bijgewerkte brondata kan record-index N iets anders zijn gaan betekenen dan
bij de vorige run.

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

Resultaten bekijken (samenvatting + per-voorbeeld items, gegroepeerd op
gevonden/gemist/hallucinatie resp. correct/gemist/onterecht):
`make dev`, dan `/validatie-rapportage/<dataset>` in de browser.

`TOPIC_NAME`/`TOPIC_DESCRIPTION`/`DEBATE_CONTEXT` in `benchmark_elecdebate.py`
geven de extractieprompt context. Twee dingen zijn hierin gecorrigeerd:

- **`extract_argument.md` beweerde altijd "Tweede Kamer-debat"** te zijn,
  feitelijk onjuist voor deze dataset (Amerikaanse verkiezingsdebatten) en
  dus verwarrend voor het model. `_build_prompt()` in `extract_arguments.py`
  heeft nu een `debate_context`-parameter (default `"Tweede Kamer-debat"`,
  dus alle productie-aanroepen blijven ongewijzigd); het evalharnas geeft
  hier `DEBATE_CONTEXT = "Amerikaans presidentsverkiezingsdebat"` mee. Dit is
  wél een wijziging aan de productieprompt zelf (`extract_argument.md`),
  bewust en beperkt tot het parametriseren van deze ene aanname.
- **`TOPIC_DESCRIPTION` is door twee versies heen gegaan.** Eerst deed die
  alsof er één vaste pro/contra-as voor het hele debat was ("Generieke
  pro/contra-as: steunt de spreker het beleid..."). Die is er niet: elk
  argument kan over een ander specifiek onderwerp gaan (NAFTA nu, Iran zo).
  De vervolgpoging ("leid de as per argument zelf af") was zelf ook fout:
  "bekritiseert het beleid" is geen pool op zich (een maatregel kan te ver
  gaan óf juist niet ver genoeg -- exact de valkuil waar
  `extract_argument.md` elders expliciet voor waarschuwt), en het is
  sowieso een zware secundaire taak per argument voor een veld dat deze
  eval niet scoort. Nu simpelweg: het model wordt geïnstrueerd altijd
  `"unclear"` te kiezen, zodat er geen reasoning-capaciteit verspild wordt
  aan een dimensie die toch niet meetelt.

## Eerste resultaten -- ACHTERHAALD (2026-08-10, vóór de span-fix)

**De cijfers hieronder zijn ongeldig en blijven alleen als geschiedenis
staan.** Ze zijn gemeten vóór twee fixes die de gouden data zelf
veranderden: (1) claim+premisse werden niet samengevoegd tot één
argument-span (zie "Conversie" hierboven) -- veel getoonde "argumenten"
waren kale stellingnames of losse onderbouwingen, precies wat onze eigen
extractie ook zou afwijzen; (2) geneste dubbele drogreden-annotaties waren
nog niet verwijderd. Beide ontdekt bij handmatige review van
`/validatie-rapportage` -- zie de git-historie van dit bestand voor de
motivatie per fix. Een nieuwe, geldige eerste meting volgt hieronder zodra
die gedraaid is.

| Model | Metriek | precision | recall | F1 | detail |
|---|---|---|---|---|---|
| `qwen/qwen3.6-27b` (n=20) | Argumentherkenning | 0.41 | 0.54 | 0.47 | tp=2566 fp=3692 fn=2169 (tekens) |
| `qwen/qwen3.6-27b` (n=20) | Drogreden-tags | 1.00 | 0.17 | 0.29 | tp=2 fp=0 fn=10 |
| `google/gemma-4-e4b` (n=5) | Argumentherkenning | 0.34 | 0.60 | 0.44 | tp=913 fp=1743 fn=611 (tekens) |
| `google/gemma-4-e4b` (n=5) | Drogreden-tags | 1.00 | 0.10 | 0.18 | tp=1 fp=0 fn=9 |

Kanttekening die wel blijft staan: tijdens verificatie gaf
`qwen/qwen3.6-27b` op een ander moment (zelfde prompts, zelfde LM
Studio-instance) consistent lege extracties (6 completion-tokens, geen
redenering) waar `google/gemma-4-e4b` normaal reageerde -- lijkt een lokale
model-state-kwestie in LM Studio, geen bug in het harnas. Bij vreemde
resultaten: eerst het model in LM Studio herladen voor verder te zoeken in
de code.

## Resultaten (2026-08-12, na span-fix + context-fix, 50/318 records)

Cumulatief opgebouwd via twee `make validate`-runs (10 records op 2026-08-10
na de claim+premisse- en context-fixes, plus 40 nieuwe records op
2026-08-12) tegen `qwen/qwen3.6-27b`, lokaal via LM Studio. 0 extractie- en
0 tagfouten over de volle 50 records -- de hieronder genoemde
qwen-flakiness trad deze keer niet op.

| Model | Metriek | precision | recall | F1 | detail |
|---|---|---|---|---|---|
| `qwen/qwen3.6-27b` (n=50) | Argumentherkenning | 0.36 | 0.61 | 0.45 | tp=11208 fp=20290 fn=7266 (tekens) |
| `qwen/qwen3.6-27b` (n=50) | Drogreden-tags | 0.79 | 0.48 | 0.60 | tp=15 fp=4 fn=16 |

Drogreden-tag-F1 steeg van 0.40 (n=10, direct na de context-fix) naar 0.60
(n=50) -- consistent met een kleine-steekproefartefact in de eerdere meting,
niet met een nieuwe wijziging. Argumentherkenning blijft rond F1 0.45,
stabiel t.o.v. de eerdere n=10-meting.

## Nog te doen

- Grotere steekproef (`make validate LIMIT=...` met hoger getal) voor een
  nog betrouwbaarder beeld -- nu 50/318, dus nog altijd een minderheid van
  de test-split.
- Eventueel `data/ann/*.ann` (brat-standoff, bevat discontinue spans) direct
  parsen voor nog nauwkeurigere spans -- vereist opnieuw tekstsearch tegen
  `full_speeches_new.csv` (de `.ann`-offsets zelf zijn niet herbruikbaar, zie
  hierboven), dus een incrementele verbetering, geen fundamentele oplossing.
- Issue #67 (labelgroep "Stijlmiddelen") is losstaand en blokkeert dit niet.
