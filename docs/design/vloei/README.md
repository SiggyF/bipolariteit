Vloei is richting A voor de visuele identiteit van bipolariteit.org (issue #220). Het inktthema blijft, maar de krant verdwijnt. De inkt gaat niet op een drukpers maar in vloeipapier: hij trekt uit, en een dichtgevouwen vloeiblad drukt de vlek in spiegelbeeld af. Die spiegeling is het organiserende idee, want de site gaat over tweedeling. Pro en contra staan aan weerszijden van een **vouw**. Onduidelijk zit ín de vouw. Het standpunt krijgt een eigen glyph: de twee lobben van het bestaande beeldmerk, waarvan één kant volloopt met inkt.

## Toon

- De site blijft Nederlands, zakelijk en analytisch. Schrijf in zinsopbouw, ook in labels: "Typologie", niet "TYPOLOGIE". Gebruik geen emoji.
- Citaten krijgen Nederlandse aanhalingstekens „…” en staan altijd in `citaat`. Parafrase staat in `body`.
- Aantallen worden geteld, niet gekleurd: "42 van 318 argumenten" in `.vl-data`, met het getal in `galnoot` vet.

## Wat weg is uit het oude recept

- De warme papiergrond (#f2efe7) en bijna-zwarte bruine inkt. In de plaats komen koel vloeigrijs (`vloei`) en blauwzwarte galnoteninkt (`galnoot`).
- Schreefkop met uppercase mono-labels. Nu: Archivo voor koppen **en** labels, waarbij de breedte-as de rol draagt: breed (`.vl-breed`, wdth 125) voor titels, smal (`.vl-smal`, wdth 85) voor labels en data. Literata is de leesletter. Er is geen monolettertype meer.
- Dunne 1px-randen overal. Vlakken scheiden zich nu met een inktwassing (`was`) op `vloei`, en leesvlakken zijn `blad`. Randen alleen op invoervelden (`rand`).
- De 4px-linkerrand als standpuntmarkering op kaarten. Daarvoor in de plaats: een inkttab aan de kant van de vouw, plus glyph en woord.
- De sticky masthead met 2px onderlijn. De kopbalk (`.vl-kopbalk`) scrollt nu mee en heeft geen lijn. Alleen de filterbalk mag sticky zijn op pagina's met argumentkolommen.

## Kleur

- Kerntrio: `vloei` (grond), `galnoot` (tekst) en `blad` (leesvlak). Het standpuntpaar `pro` en `contra` is ongewijzigd overgenomen (#1f6f66 / #9c3b32). `onduidelijk` is verdunde inkt.
- Zet alle lopende tekst in `galnoot` op `vloei` of `blad`. Metadata gaat in `galnoot-zacht`.
- Links hebben geen eigen accentkleur: `galnoot`, met een onderstreping in `rand` die bij hover 2px `galnoot` wordt. Bezochte links worden `galnoot-zacht`. Zo leest geen enkele link als "pro".
- De focusring is overal 2px `galnoot` met 2px offset. Die haalt ≥12:1 op elke grond.
- De wassingen `pro-was`, `contra-was` en `onduidelijk-was` zijn alleen voor kolomkoppen, de vouwkolom en legenda's, nooit voor een hele pagina.
- `onderbouwing` is alleen voor het argumentschema.
- In het donkere thema (Inktpot) lichten `pro` en `contra` op. Tekst óp een vol inktvlak is daarom altijd `op-inkt`, nooit letterlijk wit.

### Kleurblindheid: eerlijk gezegd

Het behouden paar verschilt in lichtheid nauwelijks (contrast 1,14:1). Bij deuteranopie wordt `pro` blauwgrijs (#5e6067) en `contra` olijf (#6d632f). Die blijven van elkaar te onderscheiden, maar `pro` valt dan vrijwel samen met `onduidelijk` (#5d6375). Kleur mag daarom **nooit** de enige drager zijn:

1. Het woord ("pro", "contra", "onduidelijk") of een telling staat altijd bij de kleur -- in `StandpuntGlyph.vue` zit het woord zelf in de DOM (title-attribuut + een visueel verborgen span voor screenreaders), zichtbaar draagt de vormcodering (punt 2) het in plaats daarvan.
2. De standpuntglyph codeert met vorm: pro heeft de linkerlob gevuld, contra de rechter, onduidelijk heeft beide lobben open met een stip.
3. De positie codeert ook: pro links van de vouw, contra rechts, onduidelijk erin.
4. In de plenaire kaart is pro een rondje, contra een vierkantje en onduidelijk een ring.

## Typografie

- Archivo (variabel: wght 100–900, wdth 62–125) en Literata (variabel: opsz, wght, met italic). Beide zijn OFL en staan als woff2 in `frontend/public/fonts/`. Zelf hosten zoals nu, dus geen CDN.
- Paginatitel: `display` + `.vl-breed`. Sectie: `kop-1` + `.vl-breed`. Kolomkop en grafiektitel: `kop-2`. Spreker: `kop-3`.
- Labels, chips en badges: `label` (smal). Tellingen, tijdcodes en as-labels: `data` / `.vl-data` (smal, tabulaire cijfers).
- Lopende tekst in `body`, gewicht 400. Het oude Work Sans 300 was te licht voor lange stukken. Intro's in `lead`, bronnen in `klein`.

## Ruimte, vorm, diepte

- Ruimte loopt in stappen van 4px: `ruimte-1` t/m `ruimte-12`. Kaarten krijgen `ruimte-6` binnenruimte en `ruimte-4` onderlinge afstand.
- `hoek-m` voor kaarten en panelen, `hoek-rond` voor chips en de filterbalk, `hoek-s` voor badges.
- Kaarten hebben geen schaduw. `uitloop` is alleen voor zwevende lagen (deelmenu, facet-sheet, tooltip).

## De vouw (paginapatroon)

- Elke weergave van argumenten per standpunt gebruikt `.vl-vouw`, met de kolommen pro | onduidelijk | contra. De contra-kolomkop spiegelt: telling links, woord rechts.
- Onder 900px worden de kolommen één lijst. De glyph en het woord in `.vl-kaart-meta` dragen dan het standpunt.
- Gespiegeld werkt ook in grafieken: pro-balken lopen naar links vanaf een middenas, contra naar rechts (zie Grafiek).
- Pro staat links omdat het in de leesvolgorde eerst komt, niet vanwege politiek links. Leg dat op de over-pagina één keer uit.

## Beeldmerk en iconen

- Het bestaande beeldmerk (twee gekantelde ellipsen met twee polen) blijft ongewijzigd: `assets/Logos/bipolariteit-beeldmerk.svg`. Inline zetten met `currentColor` in `galnoot`.
- De standpuntglyph is afgeleid van dezelfde twee lobben. Gebruik hem inline, zoals in `.vl-standpunt` (dan volgt hij het thema). De losse SVG's in `assets/Standpunt/` zijn alleen voor plekken zonder CSS.
- Partijlogo's blijven de bestaande PartyLogo-afbeeldingen, in een `.vl-partij-logo`-vak.

## Herkomst

Uitgewerkt in een Claude-design-system-artifact (tokens, componentpreviews,
fonts), overgenomen in deze map als tekstuele referentie voor de implementatie.
Zie [`invoering.md`](invoering.md) voor het stappenplan en
[`richting-b-stempel.md`](richting-b-stempel.md) voor de vergeleken, niet
gekozen richting.
