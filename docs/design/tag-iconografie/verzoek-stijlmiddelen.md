# Aanvraag: iconen voor labelgroep "Stijlmiddelen"

Zie [issue #74](https://github.com/SiggyF/bipolariteit/issues/74) voor de tracking; dit bestand is het zelfstandige pakketje om mee te werken.

## Wat er nodig is

5 nieuwe SVG-tekeningen in `icons/` (dit mapje) + een nieuwe groep-entry in `tag-styles.json`, in dezelfde stijl als de bestaande iconen (lijntekeningen, `fill: none`, `stroke-width: 2` — zie de andere bestanden in `icons/` als referentie).

**Geen nieuwe kleur/perspectief nodig.** De labelgroep hoort bij het al bestaande perspectief "Filosofisch & Argumentatietheoretisch" (kleur `#B68235`, marker `circle`), naast de bestaande groepen Redeneerschema/Debatzetten/Metadiscussie.

## De 5 tags

Uit `data/tags.toml`:

| Sleutel | Beschrijving |
|---|---|
| `Stijl-Slogan` | Beknopte, pakkende frase. |
| `Stijl-Herhaling` | Herhaling van hetzelfde woord of dezelfde woordgroep binnen het fragment, ter nadruk. |
| `Stijl-Aangekondigde-Opsomming` | Vooraf het aantal elementen aankondigen (twee, drie, vijf, ...), gevolgd door een opsomming van precies dat aantal. |
| `Stijl-Antithese` | Het naast elkaar plaatsen van twee tegengestelde begrippen of ideeën. |
| `Stijl-Retorische-Vraag` | Een vraag waarvan het antwoord al besloten ligt in de formulering zelf. |

## Waar het bij komt in `tag-styles.json`

Ter referentie, zo ziet een bestaande groep binnen hetzelfde perspectief eruit (`icon` is een semantische naam, niet per se een echt Lucide-icoon — de daadwerkelijke tekening komt uit de SVG in `icons/` met diezelfde naam):

```json
{
  "naam": "Redeneerschema",
  "tags": [
    { "sleutel": "Walton-Causaal", "icon": "workflow" },
    { "sleutel": "Walton-Consequentie", "icon": "trending-up" },
    { "sleutel": "Walton-Expertise", "icon": "graduation-cap" },
    { "sleutel": "Walton-Analogie", "icon": "arrow-left-right" },
    { "sleutel": "Walton-Regel", "icon": "gavel" }
  ]
}
```

Nieuw toe te voegen, na de bestaande "Metadiscussie"-groep binnen hetzelfde perspectief:

```json
{
  "naam": "Stijlmiddelen",
  "tags": [
    { "sleutel": "Stijl-Slogan", "icon": "<te bepalen>" },
    { "sleutel": "Stijl-Herhaling", "icon": "<te bepalen>" },
    { "sleutel": "Stijl-Aangekondigde-Opsomming", "icon": "<te bepalen>" },
    { "sleutel": "Stijl-Antithese", "icon": "<te bepalen>" },
    { "sleutel": "Stijl-Retorische-Vraag", "icon": "<te bepalen>" }
  ]
}
```

Elke `<te bepalen>`-icoonnaam heeft een bijbehorende `icons/<naam>.svg` nodig.

## Na afronding

```bash
node frontend/scripts/build_tag_icons.mjs
```
genereert `frontend/src/lib/tagIcons.generated.ts` opnieuw uit dit mapje.
