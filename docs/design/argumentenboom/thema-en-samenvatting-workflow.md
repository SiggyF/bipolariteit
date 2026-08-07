# Handleiding: thema-titel en samenvatting per confrontatie-band

Zie [issue #49](https://github.com/SiggyF/bipolariteit/issues/49) — dit
document beschrijft de workflow voor het laatste openstaande punt van die
issue: "Betere compacte samenvatting". Het bouwt voort op de bestaande
export-prompt-build-workflow uit PR #48 (zie ook de moduledocstring van
`pipeline/build_confrontatie_export.py`): dezelfde Gemini-sessie levert nu
ook twee extra outputvelden (`thema`, `samenvatting`), en de handmatige
plak-stap (document + prompt in Gemini) kan optioneel vervangen worden door
één niet-interactieve `agy`-call (`scripts/agy_run_confrontatie_tree.py`).

## Wat dit oplost

De confrontatie-as toonde per band tot nu toe alleen een mechanisch
samengestelde titel (de twee `gist`-samenvattingen van het weersproken paar
aan elkaar geplakt, bv. "reductie opent vergunningverlening weer —
vrijwilligheid en drempelwaarden verlenen vergunningen") en toonde
gebundelde argumenten (hoofdargument + onderbouwing, of een coördinatieve
groep) als losse kaarten zonder gezamenlijke leesbare samenvatting. Twee
nieuwe velden verhelpen dat:

- **`thema`** per confrontatie-band: een echte, korte titel die het
  daadwerkelijke geschilpunt benoemt.
- **`samenvatting`** per gebundelde node/groep: één leesbare, gebronde zin of
  twee die de onderliggende argumenten samenvat.

Beide velden zijn **optioneel** in de export: ontbreken ze (oudere
`*-gemini-tree.json`-bestanden, of een Gemini-run die deze stap nog niet
volgde), dan valt de export terug op het oude mechanische gedrag. Er is dus
geen harde afhankelijkheid — je kunt gewoon een nieuwe Gemini-iteratie
proberen zonder dat een oudere export kapot gaat.

## De iteratieworkflow

Stap 1-3 (document exporteren, in Gemini plakken, antwoord opslaan) kunnen
handmatig, of automatisch via `agy` (Docker, zie
`docs/handoff.md`, sectie "Antigravity CLI (agy) in Docker" — dezelfde
container/auth die ook bij de extractie-/tagging-pipeline gebruikt wordt).

### Optie A: automatisch via agy (aanbevolen als je agy al hebt ingericht)

```
make confrontatie-tree-agy TOPIC=stikstof
```
Bouwt het argumentdocument in-memory (geen tussenbestand nodig), stuurt het
samen met `pipeline/prompts/argument_tree_gemini.md` via `agy --print` naar
Gemini, en schrijft het antwoord direct naar
`data/export/argument-docs/stikstof-gemini-tree.json`. Default model:
`gemini-3.6-flash-high` (één call per topic, dus de zwaarste flash-tier is
het waard; `gemini-3.1-pro-*` bewust vermeden — bekend gevoelig voor
verzonnen inhoud). Ander model proberen: `make confrontatie-tree-agy
TOPIC=stikstof MODEL=gemini-3.6-flash-medium`. Ga daarna direct naar stap 4.

### Optie B: handmatig plakken in Gemini

1. **Exporteer de brondata**:
   ```
   make argument-doc TOPIC=stikstof
   ```
   Dit zet alle pro/contra-argumenten van het topic klaar als markdown in
   `data/export/argument-docs/<topic>.md` — geen LLM-call.

2. **Plak in Gemini**: het markdown-document + de volledige inhoud van
   `pipeline/prompts/argument_tree_gemini.md` (stap 3 van die prompt vraagt
   nu ook om `thema` en `samenvatting`, zie hieronder voor de precieze
   regels; vervang `{topic}` handmatig door de topic-naam).

3. **Sla Gemini's antwoord op** als
   `data/export/argument-docs/<topic>-gemini-tree.json` (ruwe JSON, geen
   markdown-codeblok eromheen).

### Verder (beide opties)

4. **Bouw de export**:
   ```
   make confrontatie-export TOPIC=stikstof
   ```
   Puur mechanisch — geen LLM-call, er wordt geen tekst verzonnen. Wil je
   eerst snel de ruwe JSON scannen zonder 'm weg te schrijven, gebruik
   `--dry-run`:
   ```
   uv run python -m pipeline.build_confrontatie_export --topic stikstof --dry-run
   ```

5. **Bekijk het resultaat meteen op de site** — geen los reviewscript nodig,
   de site zelf is de review-omgeving:
   ```
   make dev
   ```
   en dan naar `/topics/<topic>`. Beoordeel elke band op:
   - **Scherpte**: benoemt `thema` het daadwerkelijke geschilpunt, of is het
     vaag/een onderwerplabel?
   - **Leesbaarheid**: is de `samenvatting` kort en leest 'ie prettig naast
     de kaart, zonder dat je meteen de citaten hoeft open te klikken?
   - **Trouw aan de argumenten**: klopt de samenvatting met wat de
     onderliggende citaten (via "citaten tonen"/"onderbouwing tonen")
     daadwerkelijk zeggen — geen cijfers of claims die er niet staan?

6. **Niet goed genoeg?** Verscherp de promptregels in
   `pipeline/prompts/argument_tree_gemini.md` (bv. een striktere
   lengte-eis, of een explicietere "geen cijfers verzinnen"-regel) en herhaal
   vanaf stap 2. Dit is dezelfde iteratieve aanpak die al gebruikt is om de
   boomstructuur zelf scherp te krijgen (zie PR #48).

## Wat Gemini precies levert (stap 3 van de prompt)

- `thema` op elk element van `oppositions[]`: max. ~8 woorden, geformuleerd
  als vraag of spanning, geen cijfers/bronnen/oordeel.
- `samenvatting` op elke node met `children` en elke coördinatieve
  `label`-groep: max. ~30 woorden / 2 zinnen, uitsluitend gebaseerd op de
  geciteerde argumenten van die node/groep — dezelfde "verzin niets"-
  discipline als bij `gist`.

## Waar het in de code terechtkomt

- `pipeline/build_confrontatie_export.py`: geeft `thema`/`samenvatting`
  mechanisch door (`build_bands_and_losse`, `build_export`); valt terug op
  de mechanische gist-samenvoeging als `thema` ontbreekt.
- `frontend/src/components/ArgumentTree.vue`: `band.thema` in de
  as-kolomtitel; `samenvatting` van een coördinatieve groep onder het
  groepslabel in de "Buiten de confrontatie"-sectie.
- `frontend/src/components/ArgumentConfrontatieKaart.vue`: `samenvatting`
  van een hoofdkaart (argument met onderbouwing) direct onder de `gist`.
