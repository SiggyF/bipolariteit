# Invoering per module

`main.css` gebruikt maar elf kleurvariabelen. Stap 1 zet ze daarom om naar Vloei-tokens, zonder één component aan te raken. Daarna schuift elke module los over.

## Stap 1: aliassen (één PR, meteen overal zichtbaar) — gedaan

Zet in `:root` en in `:root[data-theme="dark"]` de oude namen op de nieuwe tokens:

| oud | nieuw | let op |
| --- | --- | --- |
| `--color-bg` | `var(--vloei)` | |
| `--color-card-bg` | `var(--blad)` | |
| `--color-text` | `var(--galnoot)` | |
| `--color-muted` | `var(--galnoot-zacht)` | |
| `--color-border` | `var(--lijn)` | gebruik `rand` voor invoervelden |
| `--color-pro` | `var(--pro)` | waarde ongewijzigd |
| `--color-contra` | `var(--contra)` | licht ongewijzigd, donker iets lichter (#ec9387) |
| `--color-unclear` | `var(--onduidelijk)` | haalt nu 4.5:1 als tekst |
| `--color-accent` | `var(--galnoot)` | links: onderstreping `rand` |
| `--color-accent-active` | `var(--galnoot-zacht)` | |
| `--color-onderbouwing` | `var(--onderbouwing)` | donkerder, voor contrast |
| `--font-display`, `--font-heading` | `var(--font-kop)` | |
| `--font-body` | `var(--font-tekst)` | `body { font-weight: 400 }` |
| `--font-mono` | `var(--font-kop)` | plus `font-variation-settings: "wdth" 85` (volgt in stap 2, per module) |

De drie woff2-bestanden (Archivo variabel, Literata variabel + italic) staan
in `frontend/public/fonts/`. De Caslon-, Work Sans- en Plex-bestanden blijven
staan tot stap 3.

## Stap 2: module voor module

1. **Standpunt** — gedaan: `.stance-dot`/`.stance-badge` zijn vervangen door `StandpuntGlyph.vue` (`.vl-standpunt` in `main.css`), gebruikt in `ArgumentCard.vue` en `ClaimsHighlights.vue`. Altijd zichtbaar, niet meer alleen <900px: op `DebateVideoView.vue`'s argumentenlijst naast de video (geen kolomkop-per-standpunt) was de randkleur van `.argument-card` anders de enige drager.
2. **ArgumentCard** — gedaan: `.argument-card` is vervangen door `.vl-kaart is-{pro|contra|onduidelijk}` (`../lib/standpunt.ts`), de linkerrand-per-stance door de inkttab (`::before`), en de toestanden hernoemd (`is-speelt`/`is-gemarkeerd`/`is-klikbaar`). Zijstap: `.quote` gebruikte `--font-heading` (Archivo) i.p.v. `--font-tekst` cursief (Literata) voor het citaat -- rechtgezet, want dat was een citaat-op-verkeerd-lettertype-regressie uit stap 1. De kolomvolgorde (nu pro/contra/onduidelijk i.p.v. pro/onduidelijk/contra) en dus de kant waar de inkttab naar wijst t.o.v. de vouw, komt in de volgende module (TopicView) goed te staan.
3. **TopicView** — gedaan: kolommen in `.vl-vouw` (pro | onduidelijk | contra i.p.v. de vorige pro/contra/onduidelijk-volgorde, alleen lokaal in `TopicView.vue`; `STANCES` in `lib/types.ts` blijft ongewijzigd voor filters/DB). `ArgumentColumn.vue` krijgt een `stance`-prop i.p.v. `label`+`stanceClass` en rendert de `.vl-vouw-kolom`-kop zelf (gespiegeld bij contra: telling links, woord rechts, via `flex-direction: row-reverse` -- leesvolgorde voor schermlezers blijft overal woord-dan-telling). `.topic-pro-contra-item` verloor zijn linkerrand voor een `*-was`-grond en de hoofdletterlabel voor zinsopbouw.
4. **FilterBar** — gedaan: de zoekrij (`.vl-filterbalk`: zoekveld `.vl-zoek`, telling `.vl-data`, "alles wissen" `.vl-knop-tekst`) en de actieve filters (`.vl-chips`/`.vl-chip`). De facetknoppen, het facetpaneel en de datumkiezers (`.facet-button`, `.facet-panel`, `.facet-options`, de mobiele `.facet-sheet`) zijn bewust nog niet meegenomen -- die staan niet in het ontwerp (`project/components/Filterbalk/`) en blijven op de oude `--color-*`-aliassen tot een latere module.
5. **SiteNav** — gedaan: `.site-nav` is hernoemd naar `.vl-kopbalk`, de `border-bottom` is weg. Stond al niet sticky (dat stond alleen in het oude-recept-verhaal, niet in de code); de balk scrolt gewoon mee, zoals het ontwerp voorschrijft.
6. **Grafieken** — gedaan: het ECharts-thema `vloei`/`vloei-donker` staat (`frontend/src/lib/vloeiChart.ts`, `frontend/src/lib/echartsSetup.ts`, CSS in `main.css`; volledige spec in `grafiek.md`). `StatsPanel.vue` gebruikt `gespiegeldeStandpuntBalk()`. `TagsPerParty.vue` is één reeks in slot 1 (indigo), `inverse: true`, geen legenda. `ActorTagUsage.vue` gebruikt `perspectiefKleur()` i.p.v. de tag-styles.json-kleuren (die te dicht op pro/contra lagen), de mediaan-streep staat in `galnoot`, en er is een `.vl-legenda` met de vier perspectiefswatches. `TagCorrespondenceMap.vue` idem (`perspectiefKleur`, opacity 0,85 met een `blad`-ring, partijsprites nu `blad`-vlak met `galnoot`-letter). `PlenairBenchmark.vue` (laagste prioriteit, zie `grafiek.md`) staat op de vier categorische slots plus `rand` voor "plenair".
7. **Plenaire kaart**: zetelvorm per standpunt.

## Stap 3: opruimen

Pas als geen enkele module de oude variabelen nog direct gebruikt: aliassen verwijderen, oude fonts verwijderen, en `text-transform: uppercase` op labels schrappen.
