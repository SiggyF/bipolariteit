# Experiment: extractie + tagging als twee turns in één LLM-sessie

**Datum**: 2026-08-10
**Resultaat**: verworpen. Geen aanwijzing voor prefix-caching-winst, en de
two-turn-aanpak is gemiddeld ~2,5x langzamer dan de huidige aanpak, met een
kwaliteitsregressie op de argumentgrenzen zelf. `pipeline/extract_arguments.py`
en `pipeline/tag_arguments.py` blijven ongewijzigd.

## Vraag

Issue #50 stelt voor `stance`/`typology`/tags los te koppelen van de
citaat-extractie (Stage 1 -> Stage 1b), zodat een aanpassing aan de
pro/contra-as niet meer een volledige herextractie van alle documenten
vereist. Voordat die migratie (schema, twee prompts, validatie, batch-scripts,
export, frontend) gebouwd wordt: kan tagging als tweede turn in dezelfde
LM Studio-sessie (messages-array met het turn-1-antwoord als voorgeschiedenis)
sneller dan vandaag, omdat de brontekst-context al "warm" in de KV-cache zou
staan en niet opnieuw geprocessed hoeft te worden?

## Opzet

Nieuw, los testscript `scripts/experiment_two_turn_tagging.py` (read-only,
geen DB-writes, geen wijziging aan bestaande prompts/pipeline-code):

- **Baseline**: de huidige, ongewijzigde `extract_argument.md`-prompt in één
  call (quote + claims + stance + typology, zoals de pipeline vandaag werkt).
- **Two-turn**: turn 1 = ingekorte "is dit een argument"-prompt (alleen
  `quote_text`/`quote_context`/`claims`, géén stance/typology); bij een
  positief resultaat turn 2 = zelfde sessie (messages van turn 1 + het
  assistant-antwoord als prefix) + een vervolgvraag die alsnog stance,
  typology en taxonomie-tags toekent (dezelfde tag-taxonomie-tekst als
  `tag_argument.md`, via `build_tag_catalogue()`).
- Getest tegen `qwen/qwen3.6-27b` via de lokale LM Studio-server, 10
  documenten uit topic `stikstof` (doc-ids 40-49), sequentieel gedraaid (geen
  interleaving met andere calls, nodig om eventuele slot-cache-hergebruik een
  eerlijke kans te geven).

## Resultaten

10 documenten, 7 zonder argumenten, 3 met argumenten:

| | gem. latency | opmerking |
|---|---|---|
| Baseline (huidig, 1 call) | ~18s | quote+claims+stance+typology samen |
| Two-turn totaal | ~46s | turn 1 (~14s) + turn 2 (~120s zodra er argumenten zijn) |

- **Geen aanwijzing voor prefix-caching-winst.** Turn 2 (tagging, zelfde
  sessie) is juist steevast de traagste stap (60-150s+), terwijl bij
  daadwerkelijk hergebruikte KV-cache turn 2 sneller had moeten zijn dan een
  koude call van vergelijkbare omvang. Meest waarschijnlijke verklaring: turn
  2's prompt bevat de volledige tag-taxonomie (~5,7KB) en vraagt tags over
  ~7 labelgroepen per argument tegelijk — puur meer te genereren output, geen
  cache-probleem. Er is geen aanwijzing dat de LM Studio-API hier
  cross-request prefix-hergebruik doet, of als dat wel gebeurt weegt de extra
  output-kost ruim zwaarder dan de eventuele besparing.
- **Kwaliteitsregressie op argumentgrenzen.** Op doc 40 splitste het model
  zonder stance/typology-framing wat in de baseline 1 argument was op in 3.
  Op doc 42 hallucineerde de two-turn-aanpak een `ander_onderwerp`-argument
  dat de baseline niet vond. Het weglaten van stance/typology uit turn 1
  verandert dus niet alleen wanneer een label wordt toegekend, maar ook hoe
  het model de argumentgrenzen zelf trekt.

## Besluit

De two-turn/single-sessie-aanpak wordt niet verder nagestreefd — geen
gemeten snelheidswinst, wel een kwaliteitsverlies. Blijft issue #50's
oorspronkelijke doel (goedkope hertagging zonder herextractie) relevant, dan
is dat beter te bereiken via de oorspronkelijk voorgestelde route: twee
werkelijk onafhankelijke stages/prompts (zoals in het issue omschreven), niet
door ze in één sessie te ketenen voor snelheidswinst.

Het experiment-artefact (`scripts/experiment_two_turn_tagging.py`) blijft in
de repo staan als referentie, maar wordt niet in de productiepipeline
aangeroepen.
