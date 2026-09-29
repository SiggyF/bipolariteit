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
3. **TopicView**: kolommen in `.vl-vouw` (pro | onduidelijk | contra). `.topic-pro-contra-item` verliest zijn linkerrand en krijgt een `*-was`-grond.
4. **FilterBar**: `.vl-filterbalk` en `.vl-chip`.
5. **SiteNav**: `.vl-kopbalk`, niet meer sticky, zonder onderlijn.
6. **Grafieken**: het ECharts-thema `vloei` registreren (zie Grafiek), daarna de grafieken één voor één erop zetten.
7. **Plenaire kaart**: zetelvorm per standpunt.

## Stap 3: opruimen

Pas als geen enkele module de oude variabelen nog direct gebruikt: aliassen verwijderen, oude fonts verwijderen, en `text-transform: uppercase` op labels schrappen.
