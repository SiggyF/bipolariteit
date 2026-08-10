# Evalharnas: ELECDEBATE60TO16 (issue #62)

**Status**: harnas + converter werken end-to-end tegen de echte dataset;
nog geen benchmarkrun tegen een LLM uitgevoerd (dat is de volgende stap).

## Waarom

Issue #62 stelt voor een externe, publieke dataset te gebruiken om onze
extractie-/tagpipeline kwantitatief te valideren, als aanvulling op de tot nu
toe steekproefsgewijze experimenten op issue #50 (zie het verworpen
two-turn-experiment, `docs/two-turn-tagging-experiment.md`).

## De dataset

**ELECDEBATE60TO16** (Goffredo et al. 2023, EMNLP;
https://aclanthology.org/2023.emnlp-main.684/), bron:
https://github.com/pierpaologoffredo/FallacyDetection. Amerikaanse
presidentsverkiezingsdebatten 1960-2020, geannoteerd op drogreden-type,
argumentcomponent (Claim/Premise) en argumentrelatie (Support/Attack/
Equivalent).

Ophalen via `data/raw/elecdebate60to16/Makefile`:

```
cd data/raw/elecdebate60to16 && make all
```

Dit haalt twee vormen van dezelfde annotaties op:
- `{train,dev,test}.conll` -- token-level BIO-tags, alleen het drogreden-label
  (kolom 3/4 zijn placeholders, overal `_`, geen component-/relatie-info).
- `pos_{train,test}_set.csv` -- rijker: per fallacieuze span de exacte
  tekst, het label, `arg_comp` (Claim/Premise), `arg_rel` (Support/Attack/
  Equivalent), en `Context` (de omringende paragraaf). Geen `pos_dev_set.csv`.

`scripts/convert_elecdebate.py` zet de `pos_*_set.csv`-bestanden om naar het
genormaliseerde JSONL-tussenformaat van `pipeline/eval/schema.py`
(`data/raw/elecdebate60to16/{train,test}.jsonl`), gegroepeerd per unieke
`Context`-paragraaf (meerdere fallacy-rijen kunnen dezelfde paragraaf delen).
Train: 1790 rijen -> 1321 records (1281 unieke spans, 1393 unieke fallacies
na het samenvoegen van letterlijk dubbele CSV-rijen). Test: 199 rijen -> 191
records.

Zowel de brondata als de geconverteerde JSONL blijven onder `data/raw/`
(gitignored) -- we distribueren de dataset zelf niet mee in de repo, alleen
het Makefile dat 'm ophaalt.

## Wat deze dataset invult

Elke rij in `pos_*_set.csv` is een span die zowel een drogreden (van 6
mogelijke typen) als een argumentcomponent (Claim of Premise) is. Dat maakt
'm bruikbaar voor:

- **Recall op bekende argumentatieve+fallacieuze spans**: haalt onze
  extractie-prompt (`pipeline/extract_arguments.py`) dezelfde tekstspannen
  eruit als hier als Claim/Premise gemarkeerd staan?
- **De 2 van de 6 drogreden-typen met een tegenhanger in `data/tags.toml`**
  (labelgroep "Dialectische Kwaliteit"): kent onze tag-prompt
  (`pipeline/tag_arguments.py`) daar `Drogreden-Ad-Hominem`/
  `Drogreden-Bespelen-Publiek` toe waar de dataset `AdHominem`/
  `AppealtoEmotion` heeft gelabeld? Zie `pipeline/eval/label_mapping.py`.

Wat het niet invult: de dataset bevat alleen fallacieuze spans, geen
neutrale/niet-fallacieuze argumentvoorbeelden, dus dit meet recall op dat
deelverzameling, geen precision op willekeurige tekst. En 4 van de 6
drogreden-typen (`AppealtoAuthority`, `FalseCause`, `Slipperyslope`,
`Slogans`) hebben geen tegenhanger in onze taxonomie en worden dus niet
gescoord -- geen omissie, zie `label_mapping.UNMAPPED_FALLACIES` voor de
motivatie per label. Stance en typology worden helemaal niet vergeleken:
ELECDEBATE kent geen pro/contra-as in onze zin (die is per Nederlands
Kamerdebat-onderwerp gedefinieerd), en typology (`factual/moral/economic/
legal/other`) is een andere as dan drogreden-classificatie. Mocht er behoefte
zijn aan bredere dekking (precision, stance, de overige drogreden-typen),
dan zoeken of maken we daar een andere dataset voor -- dit is één stuk van
de validatie, niet de hele validatie.

## Het evalharnas

`pipeline/eval/`:
- `schema.py` -- `EvalRecord`/`Span`/`FallacySpan`, het genormaliseerde
  JSONL-tussenformaat.
- `label_mapping.py` -- `FALLACY_TAG_MAP` (de 2 bevestigde overlaps) en
  `UNMAPPED_FALLACIES` (de overige 4, met motivatie).
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
- Eventueel `dev.conll`/`train.conll` (de kale BIO-bestanden) alsnog
  gebruiken als die ooit een `pos_dev_set.csv`-equivalent krijgen; nu bieden
  ze niets dat `pos_*_set.csv` niet ook heeft.
