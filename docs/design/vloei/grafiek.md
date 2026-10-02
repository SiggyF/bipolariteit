# Grafiek

Grafiekspecificatie voor Vloei: het ECharts-thema `vloei` / `vloei-donker`, de kleuren per soort reeks, typografie, de gespiegelde standpuntbalk, legenda en tooltip. Hierop verwijzen README.md ("zie Grafiek") en invoering.md, stap 6.

Code: `frontend/src/lib/vloeiChart.ts` (thema, paletten, `gespiegeldeStandpuntBalk()`), en de CSS voor legenda en tooltip in `vloei-grafiek.css`, op te nemen in `main.css`. Font: `frontend/public/fonts/archivo-smal.woff2`.

## Uitgangspunten

- **Kleur doet één taak per grafiek:** identiteit (categorisch), hoeveelheid (sequentieel), polariteit (divergerend) of standpunt (pro/contra/onduidelijk). Die taken worden nooit gemengd.
- **`pro` en `contra` zijn voorbehouden aan standpunten.** Geen categorische reeks gebruikt groen of rood. Daarom vervangt Vloei de perspectiefkleuren uit `tag-styles.json` in grafieken: `#4C7C7A` leek op pro en `#B15E4A` op contra.
- **Kleur is nooit de enige drager.** Er is altijd een woord, glyph, positie, label of arcering bij.
- **Grafieken staan op `blad`** (een `.vl-grafiek`-paneel), met transparante ECharts-achtergrond. De titel is HTML (`kop-2`), nooit een ECharts-`title`.
- **Eén waarde-as.** Geen dubbele y-as. Twee maten betekent twee grafieken.

Alle paletten hieronder zijn doorgerekend. Voor de categorische set: lichtheidsband, chroma, CVD-scheiding (protanopie/deuteranopie, OKLab ΔE×100) en contrast. Voor de ramps: monotone lichtheid, stapgrootte en één hue.

## Kleuren per reekstype

### Standpunt (pro / onduidelijk / contra)

| rol | licht | donker | gebruik |
| --- | --- | --- | --- |
| `pro` | `#1f6f66` | `#6fc2b4` | vlak, ongewijzigd token |
| `contra` | `#9c3b32` | `#ec9387` | vlak, ongewijzigd token |
| `onduidelijk-vlak` | `#aab0bd` + arcering | `#525869` + arcering | **nieuw, alleen in grafieken** |

Waarom een apart `onduidelijk-vlak`: het teksttoken `onduidelijk` (#5d6475) valt als vlak bij deuteranopie samen met pro (ΔE 2,1). Onder normaal zicht is het verschil ook te klein (ΔE 7,9). Het lichtere vlak met diagonale arcering scheidt ze op lichtheid én textuur. De arcering past ook bij het idee van verdunde inkt.

- Pro↔contra: CVD ΔE 8,4 in licht (voldoende). In donker 7,0, in de grensband, wat alleen mag met een tweede drager. Die is er altijd: in de gespiegelde balk zitten ze aan weerszijden van de as, en elders staan het woord en de glyph ernaast.
- `onduidelijk-vlak` haalt geen 3:1 op `blad` (2,1 / 2,3). De waarde staat daarom altijd in de tooltip en in de legenda met telling.
- Arcering: ECharts `itemStyle.decal` via `onduidelijkArcering(modus)`: lijnen in `blad`, 2px lijn / 3px tussenruimte, −45°. In de HTML-legenda: `.vl-swatch.is-arcering`.

### Categorisch (identiteit: perspectief, onderwerp, reeksen)

Vier slots in vaste volgorde. Kleur volgt de entiteit, niet de rangorde: een filter dat reeksen weghaalt, kleurt de overblijvers niet opnieuw.

| slot | naam | licht | donker | vast voor |
| --- | --- | --- | --- | --- |
| 1 | indigo | `#434baa` | `#5763c4` | Methodologisch & Contextueel · enkelvoudige reeks · stikstof |
| 2 | oker | `#b97515` | `#986116` | Filosofisch & Argumentatietheoretisch · abortus |
| 3 | pruim | `#ab437b` | `#b94f87` | Politicologisch & Sociaal-Psychologisch · asiel |
| 4 | hemel | `#2692ba` | `#379fc7` | Communicatiewetenschappelijk & Media · energietransitie |
| — | overig | `rand` `#737b8e` | `#727c96` | onbekend perspectief, "plenair", alles boven vier |

- Gevalideerd **all-pairs** in beide modi, dus ook geschikt voor scatter. Slechtste paar CVD ΔE 10,0 licht / 10,0 donker. Normaal zicht 19,3 / 16,3. Alle slots ≥3:1 op `blad`.
- Meer dan vier reeksen: vouw samen tot "Overig" (`rand`) of maak small multiples. Genereer nooit een vijfde kleur.
- Eén reeks (bijvoorbeeld TagsPerParty): alle balken in slot 1, zonder legenda. De titel zegt wat het is. Kleur nooit op waarde.

### Sequentieel (hoeveelheid)

Eén hue (indigo), zes stappen. In donker is de schaal omgekeerd verankerd: meer = lichter.

| | 1 | 2 | 3 | 4 | 5 | 6 |
| --- | --- | --- | --- | --- | --- | --- |
| licht | `#a2ade4` | `#8592dc` | `#6b78cd` | `#515bb5` | `#393f9d` | `#262a71` |
| donker | `#4a5498` | `#606cc0` | `#7786e3` | `#95a4f6` | `#b8c4fc` | `#d9e0ff` |

De lichtste stap haalt ≥2:1 op `blad` (2,11 / 2,36). Nul is een lege cel (`blad`), geen kleur. Gebruik de schaal voor aantallen in heatmaps en dichtheid.

### Divergerend (polariteit t.o.v. een middelpunt)

Contra ← neutraal → pro, drie stappen per arm met gelijke lichtheid per stap:

| | contra | | | midden | | | pro |
| --- | --- | --- | --- | --- | --- | --- | --- |
| licht | `#9c3b32` | `#c87a6f` | `#eabfb8` | `#e3e5ea` | `#afd4cd` | `#53a298` | `#1f6f66` |
| donker | `#ec9387` | `#9f5c53` | `#5a3833` | `#2a2f3b` | `#294944` | `#308175` | `#6fc2b4` |

- Alleen voor waarden die echt een pro/contra-richting hebben, zoals een netto-standpunt (−1…1). Voor over- of ondervertegenwoordiging zónder standpuntbetekenis: de sequentiële schaal, of een neutrale divergerende schaal (indigo ↔ oker, met hetzelfde middengrijs).
- Het midden is altijd grijs, nooit een kleur. De visualMap-uiteinden krijgen de woorden "contra" en "pro".

## Typografie in de grafiek

Canvas kan geen `font-variation-settings`, dus de smalle Archivo staat als vaste instantie (`wdth` 85, `wght` variabel) in `archivo-smal.woff2`, onder de familienaam **"Archivo Smal"**. Wacht met de eerste render op `lettertypenKlaar()`: een canvas tekent niet opnieuw als het font later binnenkomt.

| element | lettertype | grootte | gewicht | kleur |
| --- | --- | --- | --- | --- |
| grafiektitel | HTML `kop-2` (Archivo) | 24/30 | 700 | `galnoot` |
| categorie-as (partijen, tags) | Archivo Smal | 13px | 600 | `galnoot` |
| waarde-as | Archivo Smal | 12px | 500 | `galnoot-zacht` |
| waardelabel op balk | Archivo Smal | 12px | 500 | `galnoot-zacht` (nooit de reekskleur) |
| n= achter categorie | Archivo Smal (rich text `n`) | 12px | 500 | `galnoot-zacht` |
| punt-/taglabel (scatter) | Archivo Smal | 11–12px | 600 | `galnoot` |
| legenda | Archivo `wdth` 85 (HTML) | 13/16 | 600, telling 500 | `galnoot`, telling `galnoot-zacht` |
| tooltip | Archivo `wdth` 85 (HTML) | 13/18, kop 14 | 500, kop en waarde 700 | `galnoot`, extra `galnoot-zacht` |
| citaat in tooltip | Literata italic | 14/21 | 400 | `galnoot` |

Tekst krijgt nooit een reekskleur. De uitzondering is het woord naast de standpuntglyph (`.vl-standpunt`), dat al de tokenkleur heeft.

Assen: geen aslijn en geen ticks. Rasterlijnen alleen op de waarde-as, 1px `lijn`. Grid via het thema (`containLabel: true`).

## De gespiegelde standpuntbalk ("de vouw")

Horizontale balken, één rij per partij (of typologie, tag, …), met een middenas op nul.

```
Partij A  n=37   84% ████████████████████▌░▐██ 11%
                                        ↑
                          middenas, 1,5px galnoot
Partij C  n=17   29%       ██████░░░░░░░░░██████ 29%
                                  ↑ onduidelijk (gearceerd) ligt over de as
```

- **Middenas:** een verticale lijn op x = 0, 1,5px `galnoot` (markLine). Dit is de enige donkere lijn in de grafiek.
- **Pro** loopt vanaf de as **naar links**, contra **naar rechts**, zoals op de onderwerppagina.
- **Onduidelijk** ligt gecentreerd over de as: de helft links, de helft rechts, in `onduidelijk-vlak` met arcering. Pro en contra beginnen pas buiten dat blok. Zo zit onduidelijk letterlijk in de vouw, en staat er nooit een gekleurd vlak direct naast een ander gekleurd vlak.
- **Maat:** balkdikte 16px, en rond alleen de buitenste uiteinden af (4px): pro links, contra rechts. Tussen segmenten zit 2px `blad`-ruimte (borderWidth 1 in `blad`).
- **Schaal:** symmetrisch, `min = −max`. Bij aantallen een ronde bovengrens (1-2-2,5-5-10), bij procenten ±100%. As-labels tonen de absolute waarde ("30", "50%"), dus nooit een minteken.
- **Labels:** de waarde bij het buitenste uiteinde, pro links en contra rechts, in Archivo Smal 12 `galnoot-zacht`. Onduidelijk krijgt geen label op de balk, alleen in de tooltip.
- **Rijen:** `inverse: true` op de categorie-as, zodat de eerste rij bovenaan staat (het `.reverse()`-trucje vervalt). Bij `eenheid: "procent"` staat achter de naam `n=37`.
- **Legenda:** gespiegeld (`.vl-legenda.is-gespiegeld`): links "pro-glyph ← pro · 68", midden "arcering onduidelijk · 18", rechts "75 · contra → contra-glyph".
- **Interactie:** tooltip per rij (`trigger: "axis"`, schaduw in `was` áchter de balken). Klik op een segment of rij zet het partijfilter, zoals nu.

`gespiegeldeStandpuntBalk(rijen, { modus, eenheid })` levert `xAxis`, `yAxis`, `series` en `tooltip`. Merge je eigen `grid` en klikgedrag erbij.

## Legenda

HTML boven de grafiek (`<ul class="vl-legenda">`), niet in de canvas. Zo werken de lettertypes, de glyph en de toegankelijkheid gewoon.

- Standpunt: de `.vl-standpunt`-glyph met woord en telling.
- Categorisch: `.vl-swatch` (10×10, `hoek-s`), met `.is-rond` voor scatter en `.is-lijn` voor lijnen of een mediaan. Kleur via `style="--kleur: …"`.
- Onduidelijk: `.vl-swatch.is-arcering`.
- Bij twee of meer reeksen is er altijd een legenda. Bij één reeks niet, want de titel noemt hem.
- Klikbare items (reeks aan/uit) zijn `<button aria-pressed>`. Uitgezet betekent `galnoot-zacht` en doorgehaald, en de kleur van de rest verandert niet.
- ECharts-legenda (alleen waar echt nodig, bijvoorbeeld de scrollende legenda van TagCorrespondenceMap): het thema zet `roundRect` 10×10, Archivo Smal 13/600 en inactief `rand`.

## Tooltip

`tooltip.className = "vl-tooltip"` (in het thema). De stijl staat in CSS:

- Een `.vl-laag`-achtig vlak: `blad`, `hoek-m`, schaduw `uitloop`, zonder rand, 10px × 12px binnenruimte, 180–260px breed.
- **Kop:** de naam (partij, tag, spreker) in 14px/700 links, en het totaal ("17 argumenten") rechts in `galnoot-zacht`.
- **Rijen:** `.vl-tooltip-rij` is een grid van `label | waarde | extra`. Het label is de glyph of swatch met naam, de waarde staat rechts uitgelijnd in 700 met tabulaire cijfers, en de extra (ruw aantal naast een percentage) in `galnoot-zacht`.
- Een citaat in de tooltip komt in `.vl-tooltip-citaat` (Literata italic).
- Volgorde bij standpunten: altijd pro, onduidelijk, contra, dezelfde volgorde als de vouw.
- Namen uit data worden ge-escaped vóór ze in de HTML van de tooltip gaan.

## Per component

| component | nu | in Vloei |
| --- | --- | --- |
| `StatsPanel.vue` | 100%-gestapeld pro→contra→onduidelijk, dikte = volume, kleuren hard gecodeerd | `gespiegeldeStandpuntBalk(…, { eenheid: "procent" })`. Volume wordt `n=` achter de naam in plaats van balkdikte. De custom series vervalt; klikken via `dataIndex` blijft. |
| `TagsPerParty.vue` | één reeks in `#33456e` / `#7d97c4` | één reeks in slot 1 (indigo), waardelabel rechts, geen legenda, `inverse: true` |
| `ActorTagUsage.vue` | balken per perspectief (tag-styles-kleuren), mediaan in inkt | `perspectiefKleur(p, modus)`, mediaanmarkering 2px `galnoot`, legenda met `.vl-swatch` en `.vl-swatch.is-lijn` voor de mediaan. De tag-iconen in de ticks krijgen `galnoot`. |
| `TagCorrespondenceMap.vue` | scatter per perspectief (opacity 0,5), partijsprites | `perspectiefKleur`, opacity 0,85 met een 1px `blad`-ring. De vier slots zijn all-pairs gevalideerd en de tag-iconen blijven de tweede drager. Sprites: `blad`-vlak met `galnoot`-letter. Rasterlijnen `lijn`, assen `galnoot-zacht`. |
| `PlenairBenchmark.vue` | `TOPIC_COLOR` (4 onderwerpen + plenair), statuskleuren hard gecodeerd | onderwerpen op slots 1–4, "plenair" op `rand` met opacity 0,25. Het is een benchmarkpagina: laagste prioriteit. |

Alle vijf: vervang de hard-gecodeerde `isDark ? "#…" : "#…"`-paren door `:theme="themaNaam(isDark)"` en haal `textStyle.fontFamily: "inherit"` weg (het thema zet Archivo Smal).

## Wat nog niet vastligt

- De tag-heatmap (`.tag-heatmap`) is HTML, geen ECharts. Die gebruikt dezelfde sequentiële en divergerende stappen als CSS-variabelen. Dat hoort bij module 8 (zie `invoering.md`).
- Of `tag-styles.json` zelf ook de nieuwe perspectiefkleuren krijgt (iconen buiten grafieken), is een aparte keuze. Deze spec vervangt ze alleen in grafieken; module 8 behandelt de tags-pagina.
