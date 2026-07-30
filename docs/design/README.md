# Ontwerp-artefacten

Bronmateriaal voor de visuele kant van de site. Geen code die meedraait — de
frontend leest hier (nog) niets uit; wat hier staat is de afspraak waar de code
naartoe werkt.

## `tag-iconografie/`

Iconografie- en kleurschema voor de 50 tags en hun vier perspectieven, als
Claude-design-artefact. `tag-styles.json` is het machineleesbare deel:

```
perspectives[] : key, naam, color, marker, icon
  groepen[]    : naam
    tags[]     : sleutel, icon
```

De iconen zijn **namen** van [Lucide](https://lucide.dev)-iconen, geen paddata.

### Wat er nog tussen dit schema en de kaart zit

Voordat `TagCorrespondenceMap.vue` hierop over kan:

- **Lucide is nog geen dependency.** MIT-licentie, dus dat mag, maar het is een
  bewuste toevoeging (`lucide-static` levert de losse SVG's).
- **Lucide-iconen zijn lijntekeningen** (`fill: none`, `stroke-width: 2`) en
  bestaan uit `<path>`, `<circle>`, `<line>` en `<polyline>` door elkaar.
  ECharts' `path://` wil één padstring en vult die standaard. Er is dus een
  conversiestap nodig, plus `itemStyle.borderColor`/`borderWidth` in plaats van
  `color`.
- **Vijftig tagiconen zijn op de scatter niet uit elkaar te houden.** Bij de
  ~14 px die een tagpunt daar krijgt, draagt alleen het perspectiefniveau (vier
  iconen) informatie. De tagiconen zijn wel bruikbaar in de tooltip, de legenda
  en de tagoverzichtspagina's uit #5.
- **De kleuren wijken af van het huidige palet.** Dit schema is mono-accent
  (`#B68235`, `#4C7C7A`, `#B15E4A`, `#6B8558`); de kleuren die nu in
  `TagCorrespondenceMap.vue` staan zijn gevalideerd met de dataviz-validator
  tegen `--color-bg` in licht én donker, met `--pairs all`. Overstappen vraagt
  dus om een nieuwe validatieronde, en in donkere modus is dat de lastige.

Zie #3 (correspondentiekaart) en #5 (tagoverzichtspagina's).
