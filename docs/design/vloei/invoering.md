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
7. **Plenaire kaart** -- gedaan (#369): kleuren (`THEME_COLOR`), label-achtergrondopaciteit, kaartomlijsting (`blad`) en UI (legenda, colorBy-knoppen, info-paneel, canvas-clusterlabels) staan op Vloei, met een zelf-gehoste Archivo-glyphset voor de clusterlabels i.p.v. MapLibre's publieke Noto-Sans-demo-font. Zetelvorm per standpunt (zoals oorspronkelijk in README.md geschetst) is **bewust blijvend buiten scope**, niet "nog te doen": de kaart toont sprekersbeurten, geen individuele argumenten, dus een 1:1 standpunt per punt bestaat niet zonder een nieuwe koppeling aan de argumentenboom. Onderweg (issue #356-vervolg) kwam wel een stapel bugs/performance-werk aan de kaart naar boven, als voorwaarde om hier zinvol aan te beginnen: video-links gefixt (als MVT-property i.p.v. het oude, dekkingsgat-behept `plenair-map-videos.json`), laadtijd verbeterd (lazy video-fetch, een dask-tokenize-bottleneck en een OOM in `build_pyramid.py` opgelost, `tms.tile()`'s trage CRS-hash vervangen door `tms._tile()`), labelleesbaarheid (ondoorzichtige achtergrond + halo i.p.v. `icon-opacity: 0,55`), en dichtheidsbewuste tile-thinning (`point_count`/`density` per punt, plus een losse density-COG, zie #367). De "geitenhouderijen"-hiërarchiebug (topniveau-label is eigenlijk een niche-subcluster, ontbrekende `--cluster-level-sizes`) staat los getrackt in #356 en is nog niet gefixt -- vereist een pipeline-her-run met echte clustering-niveaus. #366 (oude `PlenairMap.vue` opruimen) en #368 (de nieuwe `point_count`/`density`-velden in de frontend tonen) zijn losse vervolgissues, geen onderdeel van module 7 zelf.
8. **Tags-pagina** -- gedaan: `/tags/` (overzicht, `tags/index.astro`) gebruikte `PERSPECTIEVEN`/`tagIcons.generated.ts` (dus `tag-styles.json`'s kleuren, incl. de twee die te dicht op pro/contra lagen, `#4C7C7A`/`#B15E4A`) voor de kaartaccenten en icoonkleuren; dat is nu `perspectiefKleurVar()` (`lib/tagIcon.ts`), die dezelfde vier Vloei-categorische slots teruggeeft als `perspectiefKleur()` in `vloeiChart.ts` (`PERSPECTIEF_SLOT`), maar als CSS custom property (`--vl-indigo`/`-oker`/`-pruim`/`-hemel`, nieuw in `main.css`) i.p.v. een canvas-hex, zodat de donkere modus automatisch meeloopt zonder JS-themadetectie op een server-gerenderde Astro-pagina. `/tags/[sleutel]/` (`TagDetail.vue`) toont zelf geen perspectiefkleur. Correctie op een eerdere, onjuiste aanname in deze doc: `PerspectiefTagHeatmap.vue` (en daarmee de sequentiële/divergerende CSS-stappen uit `grafiek.md`) zit niet op `/tags/`, maar op `/perspectieven/[naam]/` via `PerspectiefView.vue` -- dat blijft dus nog open, los van deze module. `tag-styles.json` zelf blijft ongewijzigd (die kleuren dienen nog steeds als icoonaccent op andere, nog niet overgezette pagina's zoals `/personen/`, `/partijen/` en `/perspectieven/`).

## Stap 3: opruimen

Pas als geen enkele module de oude variabelen nog direct gebruikt: aliassen verwijderen, oude fonts verwijderen, en `text-transform: uppercase` op labels schrappen.
