# Topic-contour: handmatige controle (#270)

Aanvulling op [rapport.md](rapport.md), dat door
`scripts/experiment_topic_contour.py` wordt gegenereerd en bij elke run
wordt overschreven. Dit document legt vast wat met de hand is beoordeeld.

## Vraag

Kunnen we binnen een debat dat over alles gaat (de Algemene Politieke
Beschouwingen, 2018 t/m 2026, 11.428 beurten) de spreekbeurten vinden die
over één topic gaan, zonder het topic in de titel of een trefwoord te
gebruiken? De eenheid is de spreekbeurt, niet het debat.

## Methode

- Contour per topic ("contrast"): centroid van de beurten waaruit de
  extractie een argument haalde, min het gemiddelde van alle beurten.
- Zonder die correctie scoort dezelfde korte debatbeurt bij elk topic hoog
  (bv. "Dat is ook helemaal niet wat we vragen" in de top van asiel,
  energietransitie, oekraine en stikstof). De contour pikte dan debatstijl
  op in plaats van onderwerp.
- Drempel per topic: laagste score waarbij de precision op hold-out
  extractielabels 80% haalt (zie rapport.md).

## Abortus: beoordeeld door de projecteigenaar

70 beurten, blind gepresenteerd (40 uit de top, 20 uit rang 41 t/m 300,
10 uit de rest). 23 beoordeeld.

| Groep | Beoordeeld | Ja | Aangrenzend | Nee |
|---|---|---|---|---|
| Top 40 | 15 | 12 | 2 | 1 |
| Rang 41 t/m 300 | 6 | 1 | 0 | 5 |
| Rang 301 en lager | 2 | 0 | 0 | 2 |

- Binnen de top 40 gaat 12 van de 15 beoordeelde beurten over abortus, met
  aangrenzende (draagmoederschap) 14 van de 15.
- Een deel van de goede beurten bevat het woord abortus niet, bv. Bikker
  over "ongewenst of onbedoeld zwanger" en Jetten over Kansrijke Start. Een
  trefwoordfilter mist die.

## Stikstof: gelezen door Claude

Drempel 0,257 (contrast), 204 van 11.428 beurten erboven.

| Waar | Steekproef | Over stikstof of direct aanverwant |
|---|---|---|
| Willekeurig boven de drempel | 10 | ongeveer 8 (rest aangrenzend of onduidelijk) |
| Net boven de drempel (0,258 t/m 0,261) | 10 | ongeveer 6 ja, 2 onduidelijk, 1 nee |
| Net onder de drempel (0,254 t/m 0,257) | 10 | 9 |
| Score 0,22 t/m 0,25 | 8 | 2 tot 3 |
| Score 0,19 t/m 0,22 | 8 | 1 |
| Score onder 0,19 | 16 | 0 tot 1 (één over het Deltaplan Biodiversiteit) |

- Bij 0,25 valt de kwaliteit scherp af. De drempel uit de extractielabels
  (0,257) ligt vlak bij die grens.
- Onder de grens zit vooral klimaat, natuur en landbouw in het algemeen:
  hetzelfde semantische gebied, maar niet over stikstof.
- De extractielabel is strenger dan "gaat over het onderwerp": een korte
  tussenwerpsel over stikstof levert geen argument op en telt dan als
  negatief. De drempel is daardoor eerder te voorzichtig dan te ruim.

## Asiel, energietransitie en oekraine: gelezen door Claude

Zelfde procedure als bij stikstof: 8 willekeurige beurten boven de drempel,
de 6 beurten net eronder en twee banden verder naar beneden (6 beurten per
band). Beoordeeld op de eerste ~185 tekens.

| Topic | Drempel | Boven de drempel (8) | Net onder (6) | Band 0,03 onder | Band 0,08 onder |
|---|---|---|---|---|---|
| asiel | 0,254 | 3 ja, 3 aangrenzend of onduidelijk, 2 nee | 3 ja | 2 | 0 |
| energietransitie | 0,252 | 6 ja, 1 aangrenzend, 1 nee | 4 ja | 1 tot 2 | 1 |
| oekraine | 0,306 | 8 ja | 5 ja | 2 ja, 2 aangrenzend (defensie) | 0, 3 aangrenzend (NAVO) |

- Asiel is het zwakst. Bij de hoogste scores staat veel algemene retoriek
  over migratie, islam en "problemen van Nederland" (Wilders), waarvan het
  onderwerp uit 185 tekens niet te bepalen is. Opvang van Oekraïense
  vluchtelingen valt hier ook onder. De drempel haalt 80% precision op
  topic-debatten, maar in de Beschouwingen komt dat dichter bij 55%.
- Energietransitie werkt, ongeveer 70% boven de drempel. Prijzen,
  kernenergie, gas en CO2 worden goed gevonden; belastingen en algemene
  economie schuiven er net onder en erboven in.
- Oekraine heeft een hoge drempel: boven de drempel zijn alle beurten
  relevant, maar vlak eronder (0,303 t/m 0,305) zijn er nog 5 van 6. De
  drempel is voor dit topic waarschijnlijk te streng; defensie en NAVO
  liggen in dezelfde buurt en zijn aangrenzend.

## Conclusie over de drempel

- Eén drempel op 80% precision per topic geeft een veilige onderkant, maar
  de plek waar de relevantie echt afvalt verschilt per topic en ligt bij
  stikstof, energietransitie en asiel dicht bij de gekozen waarde, bij
  oekraine eronder.
- Voor een wekelijkse scan is een tweeledige grens logischer: boven de
  precision-drempel automatisch toekennen, in de band daaronder (ongeveer
  0,03) als kandidaat voor controle of aanvullend signaal.

## Beperkingen

- Abortus: 23 van 70 beoordeeld, dus de percentages zijn grof. De overige
  topics zijn door één lezer beoordeeld op de eerste ~185 tot ~230 tekens
  van elke beurt, in steekproeven van 6 tot 10.
- De extractielabels komen alleen uit topic-debatten. De hold-out meet
  relevantie binnen zulke debatten; de beoordelingen hierboven zijn de
  controle daarbuiten.
- Topics met weinig geëxtraheerde beurten (abortus: 5 testbeurten bij de
  gestratificeerde split) kunnen niet via de hold-out worden gedrempeld.
- Drempels en scores zijn per topic en niet onderling vergelijkbaar.

## Volgende stappen

- Toekenning opslaan hoort bij #299 (many-to-many) en #348. Deze proef
  levert alleen de score per beurt en een drempel.
- Combineren met trefwoord- en dossiersignaal voor de grensgevallen.
- Context meenemen: een beurt erft het onderwerp van de uitwisseling
  waarin ze staat (bv. interrupties).
