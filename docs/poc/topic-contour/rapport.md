# Topic-contour: validatie per spreekbeurt (#270)

Embeddings `full`, 785826 beurten (voorzitterbeurten uitgesloten). Opzet en beperkingen: `scripts/experiment_topic_contour.py`.

## Hold-out op extractielabels

Test = beurten uit topic-debatten die al door de extractie zijn gehaald, uit activiteiten die niet voor seeds of training zijn gebruikt. Positief = de beurt leverde een argument op. Drempel = laagste score met precision >= 80% op de test.

| Topic | Methode | Test (pos / neg) | AUC | AP | Drempel | Recall bij drempel | Beurten APB boven drempel |
|---|---|---|---|---|---|---|---|
| abortus | (te weinig data: 220 seeds, 5 testbeurten) | | | | | | |
| asiel | contrast | 311 / 693 | 0.892 | 0.781 | 0.254 | 50% | 455 van 11428 |
| asiel | classifier | 311 / 693 | 0.875 | 0.754 | 0.945 | 50% | 322 van 11428 |
| energietransitie | contrast | 350 / 643 | 0.868 | 0.772 | 0.252 | 50% | 519 van 11428 |
| energietransitie | classifier | 350 / 643 | 0.877 | 0.789 | 0.938 | 53% | 406 van 11428 |
| oekraine | contrast | 435 / 695 | 0.857 | 0.778 | 0.306 | 40% | 99 van 11428 |
| oekraine | classifier | 435 / 695 | 0.878 | 0.801 | 0.992 | 48% | 86 van 11428 |
| stikstof | contrast | 161 / 329 | 0.849 | 0.729 | 0.257 | 45% | 204 van 11428 |
| stikstof | classifier | 161 / 329 | 0.815 | 0.664 | 0.996 | 19% | 51 van 11428 |

## Algemene Politieke Beschouwingen 2026: topbeurten per topic (contrast)

Score met de drempel van het topic ernaast. Boven de drempel is de beurt een kandidaat.

### asiel (drempel 0.254)

- 0.430 (boven) De heer Brekelmans (VVD): Ik ben dat met de heer Eerdmans eens. Die aantallen moeten uiteraard fors omlaag; daar trekken wij ook samen in op. Ik heb niet geprobeerd aan te geven dat wij het hierbij laten zitten. Soms wordt het beeld geschetst als
- 0.428 (boven) De heer Dekker (FVD): Over dat onderwerp heeft de heer Wilders een aantal behartenswaardige zaken gezegd. Ik zou zeggen: we stoppen met het verlenen van asiel in Nederland. Asielzoekers die hier zijn, sturen we terug naar het land van herkoms
- 0.423 (boven) De heer Eerdmans (JA21): Ik zou zo graag willen dat de heer Bontenbal zegt: "Wij moeten hier geen asielzoekers meer opvangen. Dat zouden wij eigenlijk buiten Europa moeten doen." Ik zou willen dat u dat nou eens een keer zou zeggen. Dat hoor ik 
- 0.418 (boven) De heer Brekelmans (VVD): Dit is een beetje een flauwe vraag, want met dit soort aantallen ga ik een nummer noemen en dan zegt meneer Eerdmans "het moet nul zijn" of dan zegt de volgende weer "ze moeten juist terug, dus het moet -200 zijn". Volge
- 0.400 (boven) De heer Eerdmans (JA21): Dat kunnen we zeker doen. Sterker nog, dat gaan we ook doen. Maar u deelt dus de analyse van hoe het nu doorgaat? We zien inderdaad een pact. Dat komt helemaal niet uit Nederland; dat is een Europees pact waar wij gewoon
- 0.376 (boven) De heer Bontenbal (CDA): Ik denk dat ons asielbeleid de barmhartigheid van de samenleving weerspiegelt in de regels die het stelt. Uiteindelijk zul je die regels wel met elkaar moeten handhaven. Als je eenmaal met elkaar spelregels afspreekt ove

### energietransitie (drempel 0.252)

- 0.452 (boven) Mevrouw Teunissen (PvdD): Kennelijk wil ook de VVD geen groene energie van eigen bodem. De energierekening van mensen is nu torenhoog. Dat komt doordat we nog steeds vastzitten aan fossiel. Het Planbureau voor de Leefomgeving heeft gezegd dat we,
- 0.435 (boven) De heer Paternotte (D66): België heeft een kustlijn van niks. Volgens mij is die 42 kilometer. Ik bedoel niet dat die kustlijn lelijk is, maar dat die klein is. Wij hebben een hele grote kustlijn en wij hebben de Noordzee. Dat is de beste plek vo
- 0.428 (boven) Mevrouw Teunissen (PvdD): Een kwart van de Nederlandse bedrijven valt nu bijna om, omdat fossiele energie zo ontzettend duur is. Maar ik hoor het al: het klimaat interesseert de VVD helemaal niks. Als de heer Brekelmans het dan niet doet voor het
- 0.400 (boven) De heer Paternotte (D66): Die uitgestoken hand is er. Volgens mij ziet u dat ook aan de dingen die het kabinet heeft gedaan. Ik noem de forse investering in windenergie, een vertienvoudiging van de windenergie die we tot 2040 van de Noordzee gaan
- 0.395 (boven) Minister Jetten: Een van de belangrijkste vragen die er leeft over onze economie, is waar onze energie vandaan komt. Wij werken hard aan het afbouwen van afhankelijkheden vanuit het buitenland, met name van regimes die onvoorspelbaar zij
- 0.388 (boven) De heer Brekelmans (VVD): Ik moet zeggen dat mevrouw Teunissen mij steeds niet helemaal goed samenvat als ik iets gezegd heb. Ik heb niet gezegd dat ik verduurzaming niet belangrijk vind. Ik vind ook dat Nederland daaraan moet bijdragen en daarin

### oekraine (drempel 0.306)

- 0.488 (boven) De heer Brekelmans (VVD): De heer Dekker doet nu alsof hij een soort tussenpositie inneemt, maar in feite zegt hij exact hetzelfde als Poetin. Rusland valt Oekraïne binnen in 2014. Vervolgens doet Rusland dat nog een keer, massaal, in 2022. In pl
- 0.478 (boven) Minister Jetten: Het zijn gezellige APB, voorzitter. Oekraïne krijgt onze steun en blijft ook onze onvoorwaardelijke steun houden. Dat is nodig gezien de voortdurende Russische aanvallen op militaire en civiele doelen. De druk op Rusland
- 0.473 (boven) Minister Jetten: Het is echt onze overtuiging dat ervoor zorgen dat Poetin gaat inzien dat hij deze oorlog aan het verliezen is, de enige manier is om hem naar de onderhandelingstafel te dwingen. Hij is hem aan het verliezen, omdat hij e
- 0.456 (boven) De heer Paternotte (D66): Het idee dat we vrede krijgen als we Oekraïne maar laten vallen en niet investeren in defensie, vind ik echt wáánzinnig naïef, tenzij u een soort afspraak heeft met Poetin dat hij zal ophouden met aanslagen in Europa als
- 0.436 (boven) De heer Jimmy Dijk (SP): U moet toch een beetje op uw woorden passen, meneer Paternotte. Ik heb altijd dáár gestaan, waar u ook stond, bij debatten over Oekraïne, over steun voor Oekraïne, als dat nodig was om zichzelf te kunnen verdedigen. Ik h
- 0.427 (boven) Minister Jetten: Vanaf de allereerste dag van de grootschalige Russische invasie staat de deur open, hebben Zelensky en Europa gezegd: de enige manier om deze oorlog te stoppen is via onderhandeling om tot duurzame vrede te komen. Geen e

### stikstof (drempel 0.257)

- 0.419 (boven) De heer Bontenbal (CDA): We proberen een aantal dingen te doen. We proberen inderdaad de natuur te herstellen, maar vooral ook boeren te helpen om uit deze crisis te komen en Nederland van het stikstofslot te halen. Dat zijn een aantal doelen te
- 0.414 (boven) Minister Jetten: Dat gaan we niet doen, inderdaad, want daarvan zeggen nu ook mensen die de plannen hebben beoordeeld dat dit echt nodig is om de staat van instandhouding in natuurgebieden in ieder geval naar een veel hoger plan te tille
- 0.412 (boven) Minister Jetten: Oké. Een belangrijk onderdeel van deze ambitie op het gebied van economische groei, woningbouw en infraprojecten is dat we het stikstofslot met elkaar doorbreken. We hebben maximaal tempo gemaakt om binnen vier maanden n
- 0.409 (boven) Mevrouw Keijzer (Lid Keijzer): Die bouwers zijn gewoon al klaar als u eindelijk eens die rekenkundige ondergrens verhoogt. Vertel mij daar dus niets over. Het PBL — daar houdt u zich aan vast — zegt dat met dit pakket in de helft van de gebieden de op
- 0.398 (boven) De heer Bontenbal (CDA): Nee, ik denk dat het kabinet weer met allerlei regelingen gaat komen om te extensiveren, te verplaatsen enzovoorts. Dat zit allemaal in dat pakket. En ja, er zit ook geld in voor natuur. Dat heeft ook te maken met dat de
- 0.388 (boven) Mevrouw Teunissen (PvdD): Ik heb een vraag over stikstof. Er zijn inderdaad een paar goede stappen gezet voor de landbouw. Tegelijk zien we dat de doelen te laag zijn om de natuur echt te beschermen. Aan de wettelijke doelen wordt niet voldaan. M
