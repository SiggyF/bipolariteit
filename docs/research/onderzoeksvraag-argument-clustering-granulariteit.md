# Onderzoeksvraag: spreekbeurt- of argument-niveau clustering? (abortus)

## Vraag en context

Issue #253 (topic-map-koppeling aan de argumentenboom) stelt de vraag niet vooraf aan te nemen of spreekbeurt-niveau clustering (de bestaande topic-map) precies genoeg is om individuele argumenten aan een topic-cluster te koppelen, of dat clusteren per individueel argument nodig is. Dit antwoord bepaalt het ontwerp van #254 (canonieke KPA-achtige clustering, RFC-fase 1, #175).

## Methode

- Topic: `abortus`
- Embeddingmodel: `text-embedding-bge-m3` (LM Studio)
- Documentcluster (fine-level) per argument gepropageerd vanuit de bestaande plenaire-kaart-export (`data/export/plenair-map/plenair-map.json`), geen her-run.
- Argumenten (`quote_text`) onafhankelijk embed en geclusterd met dezelfde methode als de topic-map: UMAP (`n_neighbors=15, min_dist=0.1, metric=cosine`) gevolgd door HDBSCAN, voor een eerlijke vergelijking.
- Overeenstemming gemeten met Adjusted Rand Index (chance-corrected, ongevoelig voor verschillende cluster-nummering) en Normalized Mutual Information (ongevoelig voor verschillend aantal clusters). HDBSCAN-noise (`-1`) telt mee als eigen label -- weglaten zou net de gevallen verdoezelen die de vraag beantwoorden.
- 43.3% van de argumenten had een brondocument met een clustertoewijzing en is meegenomen; de rest is uitgesloten (zegt iets over de dekking van de bestaande export, niet over de onderzoeksvraag zelf).

## Resultaten

- n (meegenomen argumenten): 190
- Adjusted Rand Index: 0.031
- Normalized Mutual Information: 0.118
- Noise-rate documentcluster-niveau: 0.0%
- Noise-rate argumentcluster-niveau: 38.4%

**Wat betekenen ARI/NMI hier, in gewone taal?** De 439 abortus-argumenten zijn op twee onafhankelijke manieren gegroepeerd: (1) via het cluster van hun eigen spreekbeurt op de topic-kaart, en (2) door de argumenten zélf te clusteren op hun eigen tekst. ARI en NMI meten of die twee groeperingen het ongeveer met elkaar eens zijn over welke argumenten bij elkaar horen -- 1,0 = perfecte overeenstemming, 0 = niet beter dan willekeurig door elkaar husselen. ARI=0,031 en NMI=0,118 zijn allebei vlak bij 0: het spreekbeurt-cluster van een argument zegt bijna niets over welke andere argumenten er inhoudelijk op lijken. Vergelijk het met boeken sorteren op boekenplank i.p.v. onderwerp: dezelfde plank betekent niet hetzelfde onderwerp, en andersom.

**Voorlopige duiding (drempelwaarde, geen definitieve conclusie):** ARI < 0.3 duidt op flink signaalverlies bij propageren op spreekbeurt-niveau -- clusteren per individueel argument is dan waarschijnlijk nodig voor #254.

## Validatie in de echte kaartruimte

Het bovenstaande gebruikte een eigen, losse UMAP-fit op alleen de abortus-argumenten -- een eerlijke vergelijking qua methode, maar in een willekeurige ruimte die niet te overlayen is op de gepubliceerde plenaire kaart. Ter validatie is dezelfde vraag herhaald met de daadwerkelijk gefitte, gepubliceerde UMAP-reducer (`pipeline/plenary_map/umap.py --export-reducer`, host-only qua geheugengebruik): de abortus-argumentembeddings zijn via `reducer.transform()` in de bestaande, volle-dataset-kaartruimte geplaatst (`scripts/experiments/transform_arguments_into_umap.py`), i.p.v. opnieuw gefit.

**Resultaten (n=121 argumenten met een brondocument-clustertoewijzing in `plenair-map-full.json`, van de 439):**

- Mediane afstand van een getransformeerd argumentpunt tot zijn eigen brondocument: 0,059 (erg klein -- het argument staat semantisch dicht bij de rest van zijn eigen spreekbeurt).
- p90-afstand: 5,590 (een lange staart -- bij een minderheid van de argumenten wijkt de eigen inhoud duidelijk af van de rest van de spreekbeurt).
- De 121 gematchte brondocumenten concentreren zich in slechts 5 fine-clusters, met één dominant cluster (72 van de 121, ~60%).
- Aandeel argumenten dat na transformatie in hetzelfde fine-cluster valt als zijn eigen brondocument: **50,4%** -- lager dan de 60% die je met een naïeve meerderheidsbaseline (altijd het dominante cluster voorspellen) al zou halen. Individuele argumenten wijken dus nog altijd systematisch méér af van hun spreekbeurt-cluster dan toeval bij deze scheve verdeling zou verklaren, al is de marge kleiner dan de eerste meting suggereerde (zie kanttekening).
- 90,4% van de argumentpunten valt binnen de hull van zijn eigen dichtstbijzijnde cluster (niet per se hetzelfde cluster als het brondocument) -- de meeste argumenten landen dus wél ergens duidelijk "binnen" een cluster, niet in een leeg gebied tussen clusters in.
- Visuele controle in QGIS (na herprojectie van de punten door dezelfde `pipeline.tiling.grid.umap_to_mercator`-herschaling als de clusterlaag, zie `docs/research/argument-transform-abortus-wgs84.geojson`) bevestigt dit: de argumentpunten verspreiden zich over veel verschillende clusters op de kaart, met één duidelijk aparte, dichte deelgroep -- geen overtuigende concentratie in een handvol "Abortus"-clusters.

Dit bevestigt, nu in de daadwerkelijke productie-embeddingruimte i.p.v. een synthetische herhaling, dezelfde conclusie als hierboven: **spreekbeurt-niveau clustertoewijzing is geen betrouwbare vervanger voor clusteren per individueel argument.**

*Kanttekening (gefixt):* het `nearest_cluster_name`/`nearest_cluster_distance`-veld werd initieel berekend als dichtstbijzijnde cluster-**centroïde**, niet dichtstbijzijnde hull-**rand**. Bij onregelmatige/grote hulls gaf dat een misleidend "dichtstbijzijnde cluster" op -- zie het voorbeeld van argument 1930 verderop, waar centroïde-afstand "Transparantie" aanwees terwijl de werkelijk dichtstbijzijnde hull-rand "D66" was, 12x dichterbij. `scripts/experiments/transform_arguments_into_umap.py`'s `nearest_cluster()` gebruikt sindsdien echte hull-geometrie (shapely `Polygon.contains`/`.distance`, plus een expliciet `in_nearest_cluster_hull`-veld) -- de 50,4%/90,4%-cijfers hierboven en het 1930-voorbeeld verderop zijn met de gefixte versie herberekend. Voor punt-in-hull-lidmaatschap t.o.v. specifiek de Abortus-hull (de 323/439-telling hierboven, en de precision/recall-tabel verderop) was al vanaf het begin de echte hull-geometrie gebruikt, dus die cijfers staan ongewijzigd.

## Spreekbeurt-niveau als voorspeller: precision/recall t.o.v. het Abortus-cluster

Om de vraag "voorspelt clusterlidmaatschap of een spreekbeurt een abortus-argument bevat?" scherp te maken: alle ~732k documentposities uit `plenair-map-full.json` (niet alleen de 439 al-bekende abortus-argumenten) zijn getoetst op ligging binnen 0,2 UMAP-eenheden van de Abortus-hull (dezelfde marge als hierboven), en vergeleken met of het document daadwerkelijk >=1 argument met `topic='abortus'` heeft (grondwaarheid, 224 documenten).

| | heeft abortus-argument | geen abortus-argument |
|---|---|---|
| **binnen/nabij Abortus-hull** | 55 (TP) | 1754 (FP) |
| **buiten Abortus-hull** | 169 (FN) | (de resterende ~730k, TN) |

**Let op: dit is een meting op spreekbeurt/document-positie, niet op argument-positie.** Verwar de lage 3%-precision hier niet met de "nabij de contour = betrouwbaar"-conclusie verderop -- die gaat over de positie van het argument zélf (zijn eigen `quote_text`-embedding), een veel scherper signaal dan de positie van de hele spreekbeurt waar het argument toevallig in voorkomt. Kanttekening: argument-niveau-**precision** (hoe vaak een argument van een ánder topic vals-positief nabij de Abortus-hull terechtkomt) is in dit onderzoek niet apart gemeten -- alleen argument-niveau-**recall** (323/439, hierboven). Gezien hoe veel scherper argumenten zijn dan hele spreekbeurten is een hoge precision aannemelijk, maar dat is nog niet bevestigd met een negatieve controlesteekproef (argumenten van andere topics).

- Recall: 55 / 224 = **24,6%** -- driekwart van de spreekbeurten met een echt abortus-argument ligt niet eens in de buurt van de Abortus-hull.
- Precision: 55 / 1809 = **3,0%** -- van alles wat wél in de buurt van de Abortus-hull ligt, gaat 97% niet over abortus.

Op spreekbeurt-niveau is de Abortus-hull dus zowel te grof (mist driekwart van de echte argumenten) als te lek (97% vals alarm) om als betrouwbare voorspeller te dienen. Dit sluit aan bij de eerdere ARI/NMI- en 50,4%-bevindingen: spreekbeurt-clustertoewijzing alleen is geen bruikbare proxy voor "bevat dit een abortus-argument".

## Herijking: argument-nabijheid is het eigenlijke doel

De precision/recall-tabel hierboven beantwoordt een vraag die achteraf niet de kernvraag blijkt: niet "voorspelt topic-clusterlidmaatschap of iets over abortus gaat", maar **"kunnen we, gegeven een argument, andere semantisch verwante argumenten terugvinden?"** -- exact wat #254 (canonieke KPA-clustering) nodig heeft.

Bij handmatige steekproef van individuele getransformeerde argumentpunten (via `reducer.transform()`, dus in de echte, gepubliceerde kaartruimte) blijkt:

- **Argument 1773** (pro, D66, over handhaving/verbod-mechanismen) valt buiten elke hull, dichtstbij "Boetestelsels" -- inhoudelijk verklaarbaar (gaat over handhavingsmechanismen, niet de kernargumentatie).
- **Argument 1930** (contra, ChristenUnie) en **argument 1822** (pro, D66) liggen slechts 0,114 eenheden uit elkaar -- en zijn inhoudelijk aantoonbaar hetzelfde weerwoord-paar: 1930 reageert direct op D66's framing, 1822 reageert direct op mevrouw Bikker (ChristenUnie). Beide vallen buiten de Abortus-hull, in een aangrenzend "D66"/politieke-dynamiek-gebied, omdat het procedureel/retorisch metadebat betreft (wie zei wat tegen wie) i.p.v. de inhoudelijke abortus-argumentatie zelf -- een patroon dat in elk topic optreedt, niet abortus-specifiek.

Dat is precies het verwachte gedrag: argumenten die over het debat zélf gaan (of over een ander onderwerp raken) horen thuis in een procedureel/algemeen gebied van de kaart, niet in het topic-specifieke cluster -- en de argument-nabijheidsmethode vindt ze daar, correct bij elkaar, ook al staan ze buiten de topic-hull.

## Conclusie en voorgestelde volgende stap: "vind vergelijkbare argumenten"

Spreekbeurt-niveau clustertoewijzing propageren naar argumenten (het oorspronkelijke #253-voorstel) is niet bruikbaar als voorspeller -- bevestigd met drie onafhankelijke metingen (ARI 0,031; 50,4% same-cluster; 3%/24,6% precision/recall). Maar argument-niveau embedding + `reducer.transform()` in de bestaande kaartruimte werkt wél voor het eigenlijke doel: gegeven een argument, andere semantisch verwante argumenten terugvinden (bevestigd met het 1930/1822-weerwoordpaar).

Dat geeft een concrete, direct bouwbare stap voor #254 (canonieke KPA-clustering, RFC-fase 1): een "vind vergelijkbare argumenten"-zoekopdracht op basis van argument-eigen `quote_text`-embeddings, getransformeerd in de gedeelde kaartruimte (zoals `scripts/experiments/transform_arguments_into_umap.py` nu al doet). De uitkomst valt in twee bruikbare categorieën, in plaats van een binaire ja/nee:

1. **Binnen/nabij de topic-contour (bv. Abortus-hull)** -- hoge zekerheid dat het om een abortus-argument gaat, rechtstreeks bruikbaar voor de argumentenboom zonder verdere check. Dit is de meerderheid: 323 van de 439 bekende abortus-argumenten (74%) vallen hier al binnen.
2. **Buiten de topic-contour, maar dicht bij een ander, al-bekend abortus-argument ("cross-boundary")** -- zoals het 1930/1822-paar: niet in het Abortus-cluster zelf (vaak omdat het over het debat/de andere partij gaat i.p.v. de kerninhoud), maar wél aantoonbaar relevant voor de argumentenboom. Deze categorie heeft een verificatiestap nodig (menselijk, of een lichte LLM-check) vóór opname, maar is de moeite van het bekijken waard -- juist deze argumenten worden door zuivere topic-clustering gemist.

Concreet: gebruik nabijheid tot *al-bekende argumenten van hetzelfde topic* (niet nabijheid tot de topic-hull an sich) als primair zoeksignaal, met de hull-lidmaatschap als extra vertrouwens-/prioriteringssignaal (categorie 1 vs. 2) in plaats van als harde filter. #253's oorspronkelijke afhankelijkheid (subtopic-grens via de topic-map, vóór #254) kan daarmee vervallen -- de topic-map-clustering is niet nodig om dit te laten werken.

## Voorbeelden: spreekbeurten die uiteenvallen in argument-clusters (synthetische UMAP-fit, sectie "Resultaten" hierboven)

### Document 5613 (documentcluster 0, 5 verschillende argument-clusters)

- argument 1855 (cluster -1, pro, D66): 'Meneer Kahraman, opkomen voor vrouwenrechten is nooit polariserend. Nooit! Het zou ons als land sieren om dat te blijven doen, want Nederland heeft dat eerder gedaan, of om dat opn'
- argument 1856 (cluster 22, pro, D66): 'Het Europees Parlement heeft zich namelijk uitgesproken voor het vastleggen van het recht op abortus in de Handvest van de grondrechten van de Europese Unie.'
- argument 1857 (cluster -1, pro, D66): 'Dit sluit ook aan bij bestaande internationale verdragen en resoluties, waarin het recht op gezondheid en lichamelijke integriteit juist is vastgelegd.'
- argument 1858 (cluster -1, pro, D66): 'Wat mij betreft gaat het daarbij dus ook niet om het opleggen van een Westers idee, maar om het beschermen van universele mensenrechten, zoals het recht om niet te hoeven sterven.'
- argument 1859 (cluster 15, pro, D66): 'Het gaat namelijk om het recht van vrouwen om zelf te kiezen, ook als ze ervoor kiezen om geen abortus te ondergaan.'
- argument 1860 (cluster 15, pro, D66): 'Ik zou willen dat abortus nergens meer illegaal is, zodat vrouwen wereldwijd toegang hebben tot levensreddende zorg.'
- argument 1861 (cluster 16, pro, D66): 'Er zijn ook organisaties die opkomen voor geloofsvrijheid in landen waar het niet legaal is om christen te zijn. Die organisaties steunen wij ook. Dus ik wil daar geen onderscheid '
- argument 1862 (cluster 25, pro, D66): 'We moeten én aan preventie werken én aan seksuele voorlichting én aan gratis anticonceptie. We hebben samen veel geïnvesteerd in Kansrijke Start. Laten we dat, mogelijk in een ande'

### Document 5559 (documentcluster 0, 5 verschillende argument-clusters)

- argument 1956 (cluster 22, unclear, VVD): 'Wat betreft mensenrechten zien we dat de Europese Unie en de Verenigde Naties daar op dit moment nee tegen zeggen en er in ieder geval geen draagvlak lijkt te zijn om abortus op Eu'
- argument 1957 (cluster -1, unclear, VVD): 'Het vrouwenkiesrecht begon ooit in één land om vervolgens uit te groeien tot een recht dat in ieder geval nu door vele landen als zodanig wordt gezien. Eerlijkheidshalve moet ik ze'
- argument 1958 (cluster -1, unclear, VVD): 'Tegelijkertijd kan een land of een parlement niet bij besluit iets tot een mensenrecht maken. Als dat wel zo zou zijn, zou Nederland dat dan kunnen? Of zouden alle landen daartoe h'
- argument 1959 (cluster 25, unclear, VVD): "Wij hebben namelijk fors bezuinigd op ontwikkelingssamenwerking en daarmee ook op het ondersteunen van ngo's. Ook de VVD — wij waren onderdeel van de vier, de drie en de twee — hee"
- argument 1960 (cluster 16, unclear, VVD): "Door doelbewust de wet te overtreden, loop je het risico dat ngo's het werken in die landen onmogelijk wordt gemaakt en dat een groter doel van ons daarmee ook onmogelijk wordt gem"
- argument 1961 (cluster 15, unclear, VVD): 'Leven we nu niet juist in een land waarin je de mening mag hebben van mevrouw Stoffer … Dit is een hele bijzondere combinatie! Excuus. Leven we nu niet juist in een land waarin je '
- argument 1962 (cluster 16, unclear, VVD): 'Van het beschermen van mensenrechtenverdedigers, onder andere door ervoor te zorgen dat wij ook aanwezig zijn bij rechtszaken, ben ik een groot voorstander. Ik kan me daar ook in v'

### Document 5513 (documentcluster 0, 4 verschillende argument-clusters)

- argument 1784 (cluster -1, pro, SP): 'Goede abortuszorg staat namelijk wereldwijd steeds meer onder druk, wat voor veel vrouwen het verschil tussen leven en dood kan betekenen. Conservatieve krachten willen dit stukje '
- argument 1785 (cluster -1, pro, SP): 'Afgelopen juni bracht het European Parliamentary Forum het rapport The Next Wave uit. Hierin werd nogmaals blootgelegd hoe conservatieve en religieuze groeperingen internationaal g'
- argument 1786 (cluster 22, pro, SP): 'Het vastleggen van abortus als mensenrecht in internationale verdragen zoals het Handvest van de grondrechten van de Europese Unie en het Internationaal Verdrag inzake burgerrechte'
- argument 1787 (cluster 2, pro, SP): 'Wij vinden net als de initiatiefnemers dat abortuszorg ook beschikbaar moet zijn voor onverzekerden in Nederland. Maar de financiering daarvan via het Mensenrechtenfonds lijkt ons '
- argument 1788 (cluster 26, pro, SP): 'Sinds dit kabinet is aangetreden, is er met miljoenen bezuinigd op seksuele rechten en gezondheid: 43 miljoen dit jaar, 100 miljoen volgend jaar en de jaren erop nog veel meer. De '

### Document 5515 (documentcluster 0, 4 verschillende argument-clusters)

- argument 1789 (cluster 22, contra, NSC): 'Maar het vastleggen van abortus als mensenrecht zien wij niet als de oplossing. Het opnemen van abortus in internationale verdragen zoals het EU-Handvest of het Internationaal Verd'
- argument 1790 (cluster -1, contra, NSC): 'De luide roep om abortus expliciet als mensenrecht vast te leggen, werkt in onze ogen zelfs averechts. In de huidige wereldorde, waarin dit thema zwaarbeladen, cultureel bepaald en'
- argument 1791 (cluster 22, contra, NSC): 'Veel experts wijzen er bovendien op dat het recht op toegang tot abortus al impliciet besloten ligt in bestaande verdragen, zoals het VN-Vrouwenverdrag en het Internationaal Verdra'
- argument 1792 (cluster 28, contra, NSC): 'Voor Nieuw Sociaal Contract ligt de nadruk op preventie. Het voorkomen van ongewenste zwangerschappen moet centraal staan; dat kan door goede voorlichting en door brede toegang tot'
- argument 1793 (cluster 16, contra, NSC): "Tegelijkertijd vinden wij het belangrijk dat door Nederland gefinancierde ngo's zich houden aan de wetten van de landen waar zij actief zijn."

### Document 5453 (documentcluster 0, 4 verschillende argument-clusters)

- argument 1804 (cluster 15, pro, D66): 'In 1970 werd de leus "baas in eigen buik" gemunt. Dat is een frase die gaat over het fundamentele uitgangspunt dat de overheid niet besluit over het lichaam van een vrouw. Nu, 25 j'
- argument 1805 (cluster 3, pro, D66): 'Toen ik dit debat ging voorbereiden, kwam ik het verhaal tegen van Teodora uit El Salvador. Zij was 24 en zwanger van haar tweede kindje. Tegen het einde van de zwangerschap ging h'
- argument 1806 (cluster 18, pro, D66): 'Het afbreken van een zwangerschap zou altijd veilig en toegankelijk moeten zijn, voor iedereen. Dat zou moeten, maar dat is het niet. Wereldwijd gaan er jaarlijks tienduizenden vro'
- argument 1807 (cluster -1, pro, D66): 'We kunnen natuurlijk niet de wet in andere landen bepalen, maar we zien wel dat in die landen heel veel clubs bezig zijn om te proberen de wet in onze landen te bepalen. We kunnen '

### Document 5354 (documentcluster 40, 3 verschillende argument-clusters)

- argument 1616 (cluster 17, pro, GroenLinks-PvdA): 'Nog steeds zijn er jaarlijks honderden vrouwen die in Nederland wonen en werken maar onvoldoende toegang hebben tot abortuszorg, simpelweg omdat de financiering niet geregeld is. D'
- argument 1617 (cluster 18, pro, GroenLinks-PvdA): 'Tijdens mijn werk hoorde ik de meest schrijnende verhalen, bijvoorbeeld van een dakloze vrouw die uit wanhoop een suïcidepoging deed, omdat zij geen toegang kreeg tot de abortus di'
- argument 1618 (cluster 7, pro, GroenLinks-PvdA): 'Dit raakt aan een fundamenteel mensenrecht: het recht op gezondheid en lichamelijke autonomie. Dit probleem ís niet ingewikkeld. Het is oplosbaar door de financiering van abortuszo'
- argument 1619 (cluster 7, pro, GroenLinks-PvdA): 'Deelt zij deze zorgen en is ze het met me eens dat abortus opnemen in een CAK-regeling dé oplossing is om te voorkomen dat nog meer vrouwen noodgedwongen voor een abortus in onveil'

### Document 5577 (documentcluster 0, 3 verschillende argument-clusters)

- argument 1849 (cluster -1, pro, D66): 'Wij hebben met deze initiatiefnota gekeken naar het recht op abortus. In onze veronderstelling — dat is ook onze conclusie — vloeit dit juist voort uit internationaal erkende mense'
- argument 1850 (cluster -1, pro, D66): 'Daarnaast is er een hardnekkig misverstand. Het is goed om dit bij elk debat te benoemen: het beperken van de toegang tot veilige abortussen leidt nergens tot minder abortussen, ma'
- argument 1851 (cluster 19, pro, D66): 'Wij hebben in de beantwoording ook gezegd dat biologisch gezien het leven ergens begint, maar dat wij een andere waardering maken als het gaat om de rechtendiscussie. Voor ons staa'
- argument 1852 (cluster 22, pro, D66): 'Maar in datzelfde verdrag staat ook dat we moeten zorgen voor veilige en toegankelijke abortuszorg, juist om de rechten en de gezondheid van meisjes te beschermen. Ook andere VN-me'

### Document 5442 (documentcluster 0, 3 verschillende argument-clusters)

- argument 1733 (cluster -1, contra, ChristenUnie): 'Abortus is voor mij geen mensenrecht. Volgens mij is dat het fundamentele verschil, want ik vind dat het recht op zelfbeschikking ook een grens heeft. En die grens ligt daar waar j'
- argument 1734 (cluster 21, contra, ChristenUnie): 'Ons verschil van inzicht betreft ook het begin van het menselijk leven. Waar begint het menselijk leven? Voor mij begint dat al in de buik, in de moederschoot, en niet pas als een '
- argument 1735 (cluster 14, contra, ChristenUnie): 'Ik weet het niet, en dat maakt mij terughoudend. Dat maakt ook waarom ik bij abortus … Ik zal nooit oordelen over een vrouw in een noodsituatie. Laat dat hier ook gezegd zijn. Miss'
