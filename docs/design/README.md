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
[#12](https://github.com/SiggyF/bipolariteit/issues/12) (paletvalidatie).

## `argumentenboom/`

Ontwerpreferentie voor de confrontatie-as-argumentenboom
(`frontend/src/components/ArgumentTree.vue` +
`ArgumentConfrontatieKaart.vue`): `ontwerpgids-argumentenboom.md` is de
functionele specificatie (bandopbouw, weerleggingslijnen, datamodel).
`classical-tokens.css` + `classical-design-system-readme.md` zijn de
kleur-/typografietokens van het "Classical" design system waarmee dit
oorspronkelijk is opgeleverd -- de implementatie gebruikt die tokens
uiteindelijk NIET: `ArgumentTree.vue` hergebruikt de bestaande site-tokens
uit `frontend/src/styles/main.css` ("Ink & Rust"-kleuren, Libre Caslon/Work
Sans) via een lokale `--confrontatie-*`-indirectielaag, zodat de boom
visueel in lijn blijft met de rest van bipolariteit.nl (en donker thema
automatisch meekomt) i.p.v. een eigen kleur-/lettertypesysteem te
introduceren. Deze CSS-bestanden blijven als historische referentie staan.
Het interactieve `.dc.html`-prototype waarmee dit is opgeleverd is niet
overgenomen (eigen "dc-runtime", laadt React via een CDN — geen
productiecode); deze map is wat overblijft nu de echte implementatie het
heeft overgenomen.

## `deelknoppen-preview/`

Ontwerp voor de deelknop + og:image-preview (issue #172), geïmplementeerd in
`frontend/src/components/ShareMenu.astro` en `BaseHead.astro`:
één deelknop naast de themaschakelaar in `SiteNav.astro` (dropdown met X,
LinkedIn, Bluesky, WhatsApp, Facebook, e-mail, "link kopiëren"), plus twee
og:image-scenario's -- A (één vaste 1200×630-afbeelding, geïmplementeerd als
`frontend/public/og/default.png`) en B (per-pagina opgebouwd, met
paginatitel/stance-balk -- nog niet gebouwd, bewust een latere stap). Het
`.dc.html`-bestand is hier wél overgenomen (in tegenstelling tot
`argumentenboom/`/`videoplayer/` hieronder) omdat het geen eigen "dc-runtime"
laadt via een CDN, alleen inline SVG/CSS op de bestaande site-tokens.
Het bijbehorende briefingpakket (screenshots, sjabloonzinnen per paginatype)
staat in `data/export/design-handoff/deelknoppen-preview/` (niet ingecheckt).

## `a0-map/`

Ontwerpverkenning voor de A0-printposter van de plenaire/debattenkaart
(issue #215), gevoed door het briefingpakket in
`data/export/design-handoff/plenaire-kaart-print/` (niet ingecheckt): eigen
matplotlib-preview + een QGIS-schets, plus de vier openstaande stijlvragen
(kleur, dichtheid, hiërarchie-weergave, typografie/branding).

`A0 Kaartontwerp.dc.html` bevat twee ronden:
- **Ronde 1** (richtingsbord, antwoord op de vier vragen): onderwerpkleur in
  de punten (de vier gecureerde topics), clusterfamilie/hiërarchie alleen in
  de hull-lijnen (niet in de punten, om de twee encoderingen niet te laten
  concurreren); "overig plenair" als lage-alpha-textuur met de vier topics
  op een aparte, voller gedekte laag; van de 5 clusterniveaus alleen
  niveau 1-3 als zichtbare lijnen + labels, niveau 4-5 als hairlines zonder
  label; typografie/kleurgebruik volgt de bestaande "Ink & Rust"-site-tokens
  (Libre Caslon Display koppen, IBM Plex Mono colofon/kicker).
- **Ronde 2** (nieuw voorstel, nog niet gevraagd): één gedeelde basisplaat
  met persoonlijke edities per Kamerlid (eigen bijdragen uitgelicht +
  representatieve citaten) en een fractie-editie (voor de fractiekamer, per-
  lid-uitsplitsing zonder citaten om geen lid voor te trekken) -- sluit aan
  bij het "gepersonaliseerde posters per Kamerlid"-idee uit de #215-
  discussie, nog niet eerder uitgewerkt.

Concrete specs voor de renderfase (zie `scripts/render_design_preview.py`,
de nog te bouwen `datashader`-render en `export_clusters_geojson.py`'s
platte exportmodus): 300dpi (~9.900×14.000px A0), TWEE losse rasters
("overig" en de vier onderwerpen, zodat alpha per laag apart te regelen is)
i.p.v. één gecombineerde puntenlaag, hull-lijndiktes 3,2/2,2/1,4pt (niveau
1-3, zwart) + 0,8/0,4pt hairlines (niveau 4-5, warm grijs) i.p.v. 5 gelijk
opgebouwde diktes.

## `videoplayer/`

Ontwerp voor visuele argumenttype-annotaties op een video-embed (issue #94):
overlay-badges op de video (max. drie tags, gesorteerd op zeldzaamheid binnen
het debat) + een tijdlijn met per-quote-markers, gebaseerd op het technisch
onderzoek in `docs/tk-data-sources-overview.md` (secties 5a/5b) en de PoC in
`docs/poc/video-eigen-player/`. Bevat expliciete developer-notities
(datacontract, sync-aanpak, toegankelijkheid) — zie `videoplayer/README.md`.
Zelfde afweging als bij `argumentenboom/`: het `.dc.html`-prototype en het
"Classical" design system zijn niet overgenomen, wel het datacontract-voorbeeld
(`arguments-timed.json`).
