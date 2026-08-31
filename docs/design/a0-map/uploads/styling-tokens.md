# Bestaande stijl-tokens (bipolariteit.nl)

Bron: `frontend/src/styles/main.css`. Geen Tailwind/design-systeem-framework
— handgeschreven CSS met custom properties. Een nieuw ontwerp hoeft zich hier
niet strikt aan te houden, maar consistentie met de rest van de site is
wenselijk.

## Typografie

| Token | Waarde | Gebruik |
|---|---|---|
| `--font-display` | "Libre Caslon Display", "Libre Caslon Text", Georgia, serif | Grote titels ("krantenkop"-register) |
| `--font-heading` | "Libre Caslon Text", Georgia, serif | Kopjes |
| `--font-body` | "Work Sans", system-ui, sans-serif | Lopende tekst |
| `--font-mono` | "IBM Plex Mono", ui-monospace, monospace | Tags/data ("agate"-register — kranten-microtypografie voor metadata) |

Type-schaal (1.25 ratio op 1rem): `--step--1: 0.85rem`, `--step-0: 1rem`,
`--step-1: 1.25rem`, `--step-2: 1.563rem`, `--step-3: 1.953rem`,
`--step-4: 2.441rem`.

Fontbestanden zijn self-hosted: `frontend/public/fonts/*.woff2`.

## Spacing

8px-ritme: `--space-1: 0.5rem`, `--space-2: 1rem`, `--space-3: 1.5rem`,
`--space-4: 2rem`, `--space-5: 3rem`.

## Kleuren — licht thema (default)

| Token | Waarde | Gebruik |
|---|---|---|
| `--color-bg` | `#f2efe7` | Paginaondergrond ("newsprint") |
| `--color-text` | `#221f1b` | Hoofdtekst |
| `--color-muted` | `#6f6558` | Bijschriften, secundaire tekst |
| `--color-border` | `#ddd5c4` | Randen |
| `--color-card-bg` | `#fbf9f4` | Kaarten/panelen |
| `--color-pro` | `#1f6f66` | Pro-argumenten (groen-teal) |
| `--color-contra` | `#9c3b32` | Contra-argumenten (roestrood) |
| `--color-unclear` | `#948a79` | Onduidelijke argumenten (neutraal) |
| `--color-accent` | `#33456e` | Links/interactieve elementen — bewust NIET hetzelfde als `--color-pro`, zodat een link niet impliciet als "pro"-gekleurd leest |

Dit palet heet intern "Ink & Rust".

## Kleuren — donker thema

Opt-in via `[data-theme="dark"]` op de root (toggle + localStorage, geen
automatische `prefers-color-scheme`).

| Token | Waarde |
|---|---|
| `--color-bg` | `#1c1815` |
| `--color-text` | `#f2ede3` |
| `--color-muted` | `#a89e8c` |
| `--color-border` | `#453f36` |
| `--color-card-bg` | `#242019` |
| `--color-pro` | `#4fa89b` |
| `--color-contra` | `#cf6b5f` |
| `--color-unclear` | `#a89e8c` |
| `--color-accent` | `#7d97c4` |

## Waar dit al gebruikt wordt in de huidige argumentenboom

`ArgumentTree.vue` kopieert deze pro/contra/unclear-kleuren handmatig naar de
ECharts-configuratie (ECharts kan geen CSS custom properties lezen), met een
`useTheme()`-hook om tussen licht/donker te wisselen. Coördinatieve
groep-knopen krijgen een aparte, gedempte kleur (`#948a79` licht /
`#a89e8c` donker) om ze visueel te onderscheiden van individuele
argument-knopen.

## Overig visueel materiaal

- Tag-iconografie (perspectief-kleuren + iconen per tag):
  `docs/design/tag-iconografie/` — `tag-styles.json` (machine-leesbaar),
  `icons/*.svg` (~55 iconen), en een standalone HTML-referentiedocument.
  Losstaand van de argumentenboom, maar relevant als de boom ooit
  tag/perspectief-kleuren wil hergebruiken.
- Partijlogo's: `frontend/public/party-logos/` (officiële wordmarks +
  vereenvoudigde vierkante iconen, 160×160).
