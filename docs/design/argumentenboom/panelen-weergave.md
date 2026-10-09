# Argumentenboom in panelen (mobiel en desktop)

Issue [#251](https://github.com/SiggyF/bipolariteit/issues/251). Naast de
confrontatie-as ([ontwerpgids](ontwerpgids-argumentenboom.md)) is er een tweede
weergave van dezelfde export (`data/export/argument-trees/<slug>.json`). Ze
beantwoordt twee problemen van de as: een harde minimumbreedte (±1360px, dus
horizontaal scrollen op een telefoon) en veel verticaal scrollen over één lange
pagina.

## Idee

De hele boom in één keer tonen werkt niet op een smal scherm. In plaats daarvan
drie niveaus, elk met genoeg ruimte voor tekst:

| Niveau | Inhoud | Volgende stap |
|---|---|---|
| 1. Overzicht | aantal argumenten voor en tegen, per deelthema een kaart met "n voor / n tegen", en de argumenten zonder tegenhanger | tik op een kant van een deelthema |
| 2. Lijst | de argumenten van die kant, gegroepeerd per deelthema, onderbouwing ingesprongen aan een gestippelde tak (één niveau diep) | tik op een argument |
| 3. Detail | gist, samenvatting, letterlijk citaat, genoemde claims, onderbouwing, tegenhanger, tags en bronlinks | tik op onderbouwing of tegenhanger om daarheen te springen |

De referentie was Kialo (één claim in focus, ouder compact erboven) en de
mobiele navigatie van Obsidian (terugknop binnen duimbereik, structuur niet als
zichtbare boom). De ontwerpschetsen staan in het issue.

## Mobiel en desktop

Eén component, één toestand (`side`, `scope`, `selectedId`), twee presentaties:

- **Tot en met 900px** (zelfde breekpunt als `main.css`): één niveau tegelijk.
  De terugbalk plakt onderin. Bij een niveauwissel scrolt de pagina terug naar
  de bovenkant van de component.
- **Vanaf 901px**: de drie niveaus staan als panelen naast elkaar op de hoogte
  van één scherm (`min(80vh, 880px)`); alleen het paneel dat te lang is scrolt.
  De Voor/Tegen-wissel wordt een werkbalk boven de lijst. In het detailpaneel
  staat het citaat van de tegenhanger meteen onder het argument, zodat de
  confrontatie van de as zichtbaar blijft.

Het verschil zit alleen in CSS (`data-level` op de wortel); de DOM is gelijk.

## Code

| Bestand | Rol |
|---|---|
| `frontend/src/lib/argumentTree.ts` | exporttypes en pure afleidingen (bandtellingen, lijstgroepen, tegenhanger, ouder). Getest in `argumentTree.test.ts`. |
| `frontend/src/components/ArgumentPanes.vue` | de weergave zelf |
| `frontend/src/components/ArgumentViews.vue` | tijdelijke wissel Panelen / Confrontatie-as op de onderwerppagina |

`ArgumentTree.vue` gebruikt nu dezelfde types uit `argumentTree.ts`. De wissel in
`ArgumentViews.vue` vervalt zodra `ArgumentPanes.vue` de confrontatie-as
vervangt.

## Bewust nog niet

- **Weerleggingslijnen tussen banden** bestaan in een lijst niet. De tegenhanger
  staat in het detail, de lijnen blijven alleen in de confrontatie-as.
- **Twijfelachtige classificaties** en de toggles voor citaten en onderbouwing
  uit de as zijn niet overgenomen.
- **Terugknop van de browser** doet niets met de niveaus; de navigatie zit niet
  in de URL.
- **Onderbouwing dieper dan één niveau** in de lijst: de stikstofdata heeft die
  niet, dus het gedrag is daar niet getest. Doorklikken via het detail werkt wel.
- **Sterkte-balkjes** (de graduele sterkte-score uit #254) en een minimap zoals
  in Kialo zijn niet getekend.
- "Argumenten zonder tegenhanger" telt ook de leden van coördinatieve groepen
  mee, dus dat getal is groter dan het aantal `losse_argumenten`.
