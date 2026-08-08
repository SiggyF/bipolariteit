# Experiment: gebundelde (multi-document) extractieprompts via agy

**Datum**: 2026-07-28
**Resultaat**: verworpen. Stage 1-extractie blijft één document per `agy`-call
(`pipeline/extract_arguments.py`, `scripts/agy_run_extraction_batch.py`).

## Vraag

Kost het minder quota/tokens om meerdere sprekerbeurten in één `agy`-call te
bundelen (i.p.v. één document per call), en levert dat dezelfde extractiekwaliteit
op?

## Opzet

- Nieuw prompt-template `pipeline/prompts/extract_argument_batch.md` +
  `_build_batch_prompt()` in `pipeline/extract_arguments.py`: bundelt N
  documenten in één call, model antwoordt met `{"documents": [{"document_id": ..., "arguments": [...]}]}`.
- Testscript `scripts/agy_test_batch_extraction.py`: draait dezelfde 20
  doc-ids als de eerdere quota-kalibratie (`agy_prepare_batch_prompts.DEFAULT_DOC_IDS`,
  zie `docs/handoff.md`), in groepen van 5 (4 calls i.p.v. 20).
- Automatische veiligheidscheck: elk teruggegeven `quote_text` moet een
  letterlijke substring zijn van de brontekst van het document waaronder het
  gerapporteerd wordt -- vangt grove cross-document misattributie af (citaat
  van document A onder document B gerapporteerd).
- Output: `data/export/batch-experiment/agy_batch_test_multidoc_results.md` (nieuw, batched),
  vergeleken met `data/export/batch-experiment/agy_batch_test_results.md` (bestaand, single-call,
  van de eerdere kalibratie op 2026-07-24).

## Resultaten

### Tokens/kosten (proxy: prompt-tekens, agy heeft geen scriptbare token/usage-output)

| group size | calls (20 docs) | totaal prompt-tekens | chars/doc | vs. baseline |
|---|---|---|---|---|
| 1 (huidige aanpak) | 20 | 126.647 | 6.332 | -- |
| 5 | 4 | 42.955 | 2.148 | -66% |
| 10 | 2 | 31.127 | 1.556 | -75% |
| 20 (alles in 1 call) | 1 | 25.213 | 1.261 | -80% |

Content-only (kale brontekst zonder instructies): 895 tekens/doc gemiddeld --
bij group size 20 zit je al dicht bij die vloer, dus de instructie-overhead
(vast per call) wordt bijna volledig weggeamortiseerd.

Live `/usage`-check na de testrun (6 agy-calls: 2 single-doc smoke-test +
4 batched calls voor de 20 docs) gaf 99,01% resterend quota. **Dit cijfer is
niet schoon te interpreteren**: de 20 batched documenten waren dezelfde
documenten als de originele 2026-07-24-kalibratie, dus een eventuele
prompt/context-cache bij Gemini/agy op identieke content kan de gemeten
besparing (kunstmatig) hebben vergroot. Geen gecontroleerde same-day
single-vs-batch quotameting uitgevoerd.

### Kwaliteit: 20 documenten single-call (2026-07-24) vs. batched groepen-van-5 (2026-07-28)

Automatische substring-check: **0 mismatches, 0 ontbrekende document_ids** --
geen grove cross-document citaat-verwisseling gedetecteerd.

Inhoudelijke vergelijking (stance/typology/quote per document): **6/20
identiek, 14/20 verschillend**. Voorbeelden van het soort verschil:

- **doc 129**: single-call `pro`, batched `contra` -- tegengesteld standpunt,
  compleet ander citaat.
- **doc 50, 51, 218**: single-call vond 0 argumenten, batched vond er 1
  (echte tekst uit het juiste document, geen hallucinatie -- maar wel een
  andere redactionele beslissing).
- **doc 45**: zelfde aantal argumenten (2), maar volledig andere citaten
  gekozen.
- **doc 167, 175**: single-call vond 2 argumenten, batched samengevoegd/
  verminderd tot 1.

**Belangrijke onzekerheid**: het is niet vastgesteld of dit verschil komt
door het bundelen zelf (context-vervuiling/anchoring tussen de 5 documenten
in één call), of door gewone run-to-run modelvariatie (de single-call
baseline is 4 dagen eerder gedraaid, geen same-day herhaalbaarheids-controle
beschikbaar). Een vervolgtest (dezelfde 20 docs nogmaals single-call, dezelfde
dag, om baseline-variantie te meten) is niet uitgevoerd.

## Besluit

Gezien de omvang van de kwaliteitsverschillen (incl. een stance-omkering) en
het ontbreken van een schone controlemeting, is besloten de gebundelde aanpak
niet te gebruiken voor de echte extractiebatch. `pipeline/extract_arguments.py`
en `scripts/agy_run_extraction_batch.py` blijven bij één document per call.

De experiment-artefacten (`pipeline/prompts/extract_argument_batch.md`,
`_build_batch_prompt()` in `pipeline/extract_arguments.py`,
`scripts/agy_test_batch_extraction.py`,
`data/export/batch-experiment/agy_batch_test_multidoc_results.md`) blijven in de repo staan
als referentie, maar worden niet in de productiepipeline aangeroepen. Een
mogelijke vervolgstap, mocht dit ooit opnieuw overwogen worden: eerst een
schone same-day AB-test draaien (single vs. batched, beide vers, quota voor
en na elke fase apart gemeten) voordat dit weer serieus overwogen wordt.
