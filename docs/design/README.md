# Ontwerp-artefacten

Bronmateriaal voor de visuele kant van de site.

## `tag-iconografie/`

Iconografie- en kleurschema voor de 50 tags en hun vier perspectieven.
`tag-styles.json` is het machineleesbare deel:

```
perspectives[] : key, naam, color, marker, icon
  groepen[]    : naam
    tags[]     : sleutel, icon
```

`icon` is een naam die verwijst naar een bestand in `icons/<naam>.svg` — de
échte tekening uit het ontwerpsysteem, niet een gok naar een gelijknamig
Lucide-icoon. `frontend/scripts/build_tag_icons.mjs` leest beide bestanden en
genereert daaruit `frontend/src/lib/tagIcons.generated.ts` (ECharts-padstrings
+ de perspectief-/tagmetadata). Opnieuw genereren na een wijziging in
`tag-styles.json` of `icons/`:

```
cd frontend && node scripts/build_tag_icons.mjs
```

Op de correspondentiekaart (`TagCorrespondenceMap.vue`) wordt alleen de
perspectiefkleur nog gebruikt — de iconen (vijftig per tag, vier per
perspectief) bleken op kaartschaal niet als teken te lezen, zeker in een
dichte cluster van hetzelfde perspectief. `marker` (circle/triangle/diamond/
square) ligt klaar als extra coderingslaag mocht kleur alleen ooit
tekortschieten (zie [#12](https://github.com/SiggyF/bipolariteit/issues/12)).
De tagiconen zelf zijn nog wel bruikbaar in de tooltip, de legenda en de
tagoverzichtspagina's uit #5 — daar staat nog niets voor gebouwd.

`Tag Iconografie en Kleurenschema (standalone).html` is het visuele naslagwerk
waar dit schema uit gehaald is (open lokaal in een browser). `uploads/` is het
originele ontwerpbrief-materiaal (`tags.toml` + een screenshot).

Zie #3 (correspondentiekaart), #5 (tagoverzichtspagina's) en
[#12](https://github.com/SiggyF/bipolariteit/issues/12) (paletvalidatie, nog
open).
