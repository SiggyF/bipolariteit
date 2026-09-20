# Onderzoeksvraag: kan semantisch clusteren de confrontatie-boom vollediger maken?

Voor Gemini Research (of vergelijkbaar). Context: we bouwen een debatplatform
dat Tweede Kamer-argumenten over politieke topics (asiel, stikstof, abortus,
energietransitie) structureert. Eén van de features is een "confrontatie-
boom" die pro- en contra-argumenten tegenover elkaar zet. Deze sessie hebben
we een nieuwe, geheel andere aanpak (embedding-gebaseerd semantisch
clusteren) uitgeprobeerd op dezelfde data, en die lijkt een structureel gat
in de bestaande aanpak bloot te leggen. Dit document zet de twee aanpakken
naast elkaar en vraagt om een onderzoeksrichting om ze te combineren.

**Status:** dit is een idee dat plausibel lijkt op basis van een paar
handmatige steekproeven, geen geverifieerde aanpak. Het vereist grondig
testen voordat we het bouwen -- deze onderzoeksvraag is bedoeld om een
onderbouwde aanpak/architectuur te krijgen, niet een kant-en-klare
implementatie.

## 1. De bestaande aanpak: Gemini-gecureerde confrontatie-boom

Pipeline: `pipeline/export_argument_doc.py` exporteert alle argumenten van
een topic (letterlijke citaten, stance, typologie, tags, claims) naar één
document. Dat document gaat naar Gemini met de instructies in
`pipeline/prompts/argument_tree_gemini.md`. Gemini's taak, samengevat:

1. Kies uit de **volledige** pro/contra-lijst een "beperkte, behapbare
   subset (richtlijn: 15-30 argumenten per standpunt, niet honderden)" van
   argumenten die elkaar het scherpst weerspreken.
2. Structureer die subset pragma-dialectisch (coördinatief/subordinatief) in
   een boom, met een `gist` (max. 3-4 woorden) per argument, een `thema` per
   pro/contra-oppositie, en een `samenvatting` per gebundelde groep.

`pipeline/build_confrontatie_export.py` voegt dit resultaat (opgeslagen als
`data/export/argument-docs/<slug>-gemini-tree.json`) mechanisch samen met de
volledige argumentgegevens uit de database tot de JSON die `ArgumentTree.vue`
toont (pro links, contra rechts, "confrontatie-banden").

**Belangrijk:** dit is een bewuste, expliciete curatie-instructie (Gemini
ziet de volle lijst, maar mag er maar een handjevol uit kiezen), geen
technische contextlimiet-noodgreep. De praktijkgetallen zijn niettemin
duidelijk:

| topic | argumenten totaal | unieke `argument_id`'s in de boom | dekking |
|---|---|---|---|
| abortus | 439 | 32 | ~7,3% |
| asiel | 3555 | 34 | ~1,0% |
| stikstof | 2049 | 21 | ~1,0% |

Met andere woorden: 93-99% van alle geëxtraheerde argumenten komt nergens in
deze feature terecht. Dat is inherent aan wat de boom probeert te zijn (een
scherpe, leesbare selectie van dé kernconfrontaties, geen volledig
overzicht) -- maar het betekent ook dat er geen enkel mechanisme is om te
weten *wat* er precies buiten de boom valt, of dat om een goede reden is
(irrelevant, redundant met wat al in de boom staat) of een gemiste kans
(een heel deelonderwerp dat nooit is opgepikt omdat Gemini toevallig andere
paren koos).

## 2. De nieuwe aanpak: embedding-gebaseerd semantisch clusteren

Los onderzoek (issue #156, oorspronkelijk bedoeld als 2D-visualisatie van
argumenten) leverde twee scripts op, geen van beide in de pipeline
geïntegreerd:

- **`scripts/experiment_umap_arguments.py`**: embedt `quote_text` per
  argument met `BAAI/bge-m3` (multilingual embedding-model, gedraaid via
  LM Studio op de host-GPU -- CPU-only in de devcontainer bleek voor dit
  568M-parameter model te traag), projecteert naar 2D met UMAP, kleurt op
  vier dimensies (`stance`, `partij`, `stijl`-tag, `drogreden`-tag).
  **Bevinding**: geen van die vier dimensies laat clustering zien -- pro en
  contra, alle partijen, en alle stijl-/drogreden-tags liggen door elkaar.
  Logisch: embeddings vangen inhoudelijke semantiek, niet retorische vorm of
  sprekersidentiteit.
- Diezelfde coords, met DBSCAN erop losgelaten (los van de vier bovenstaande
  kleurdimensies), laten wél iets zien: **coherente sub-onderwerp-clusters**
  binnen één topic, dwars door partij en stance heen. Voor "asiel" bv.
  Syrië-veiligheid, dwangsommen bij trage procedures, kinderen in de opvang,
  Opvangrichtlijn-naleving, opvang van Oekraïense ontheemden, statushouders
  in hotels -- elk cluster bevat zowel voor- als tegenstanders die
  inhoudelijk over precies hetzelfde deelpunt spreken.
- **`scripts/argument_tree/experiment_find_similar_arguments.py`**: rechtstreekse
  cosine-similarity-zoekopdracht op dezelfde bge-m3-vectoren (geen UMAP
  nodig, dat is alleen voor 2D-plotten), met de vectoren lokaal gecached in
  `data/embeddings/*.npz` (gitignored, regenereerbaar) zodat een herhaalde
  zoekopdracht niet opnieuw naar LM Studio hoeft. Handmatig getest op het
  abortus-topic met drie argumenten uit hetzelfde gesprek:
  - `[1707]` (VVD, pro): "Ik denk dat het weer belangrijk is om twee zaken
    uit elkaar te houden, namelijk het aantal onbedoelde zwangerschappen en
    het aantal abortussen. [...]"
  - `[1630]` (VVD, pro): "De opmerking over de rol van mannen bij
    anticonceptie kan de VVD alleen maar steunen. [...]"
  - `[1638]` (SP, pro): "Het onderzoek van Rutgers geeft inderdaad aan dat
    bij 41% van de vrouwen die een abortus ondergaan, geen sprake was van
    anticonceptie van tevoren. [...]"

  Voor alle drie kwamen de top-8 meest gelijkende argumenten inhoudelijk
  scherp overeen (cosine similarity 0,68-0,86), over partij- én
  stancegrenzen heen (VVD, SGP, PVV, GroenLinks-PvdA, SP, ChristenUnie,
  NSC), en 1707 en 1638 bleken zelfs wederzijds elkaars naaste buur. Zie
  `docs/poc/umap-argumenten/bgem3_abortus_subtopic_clusters.png` voor een
  visuele weergave: deze drie argumenten (rood omcirkeld) liggen samen in
  dezelfde dichte deelcluster van de abortus-argumentruimte.

  Geen van deze drie argumenten staat overigens in de huidige
  `abortus-gemini-tree.json` (32 van de 439 argumenten dekt dit specifieke
  deelonderwerp niet) -- een concreet voorbeeld van een inhoudelijk
  samenhangend deelgesprek dat de huidige boom-feature niet laat zien.

## 3. Het samenvoeg-idee

Gebruik de embedding-clusters niet om zelf een boom te bouwen (dat vraagt
juist het pragma-dialectische, genuanceerde redeneren waar Gemini goed in
is), maar om te **signaleren waar de bestaande boom dun of afwezig is**, en
die deelverzamelingen gericht aan Gemini voor te leggen:

1. Clusterme alle argumenten van een topic (embedding + UMAP/DBSCAN of een
   andere clustermethode).
2. Vergelijk de clusters met de `argument_id`'s die al in de bestaande
   `<slug>-gemini-tree.json` zitten.
3. Voor clusters die **grotendeels ontbreken** in de boom: dit zijn
   kandidaat-nieuwe-takken (branches) -- geef zo'n cluster (of een
   representatieve steekproef eruit) apart aan Gemini met het verzoek er een
   nieuwe confrontatie-band uit te structureren, met dezelfde
   pragma-dialectische aanpak als nu.
4. Voor clusters die **deels** al in de boom zitten (een paar leden zijn
   opgenomen, de rest niet): dit zijn kandidaten om **bladeren** toe te
   voegen aan een bestaande band -- extra voorbeeldargumenten die hetzelfde
   punt maken als een node die er al staat, zonder de structuur zelf te
   wijzigen.

Het doel is dus tweeledig meer coverage: meer **takken** (nieuwe
deelonderwerpen die nu nergens in de boom staan) én meer **bladeren**
(rijkere onderbouwing van bestaande punten met meer voorbeeldsprekers).

## 4. Concrete open vragen voor het onderzoek

1. **Clustermethode en granulariteit.** We gebruikten UMAP (2D) + DBSCAN met
   een handmatig gekozen `eps` (0,15 voor asiel: bij 0,05 valt alles uiteen
   in ruis, bij 0,3 versmelt alles tot één bol). Is 2D-projectie + DBSCAN de
   juiste aanpak, of is clusteren direct in de hoog-dimensionale
   embeddingruimte (bv. HDBSCAN, agglomeratief, of een similarity-graph +
   community-detection) robuuster en minder gevoelig voor handmatige
   parameterkeuze? Hoe zou je `eps`/granulariteit automatisch of
   topic-onafhankelijk kiezen (topics variëren van 339 tot 3555
   argumenten)?
2. **Cluster vs. boom vergelijken.** Hoe bepaal je "grotendeels ontbreekt"
   vs. "deels aanwezig" vs. "voldoende gedekt" voor een cluster t.o.v. de
   bestaande boom -- een simpele dekkingsratio (% van clusterleden dat al
   een `argument_id` in de boom heeft), of iets subtielers (bv. of de
   *kern* van het cluster, de dichtste/centrale punten, al gedekt is, ook al
   is de dekkingsratio laag)?
3. **Nieuwe tak vs. extra blad.** Wanneer moet een onvoldoende gedekt
   cluster een héél nieuwe confrontatie-band worden (nieuw `thema`), en
   wanneer is het eigenlijk een uitbreiding van een bestaande band die het
   cluster inhoudelijk raakt maar niet exact dekt? Embeddings vangen
   onderwerp, niet per se "is dit hetzelfde geschilpunt als band X" -- hoe
   zou je dat onderscheid maken?
4. **Voorbeeldselectie binnen een cluster.** Als een cluster te groot is om
   in zijn geheel aan Gemini voor te leggen (sommige clusters waren >100
   argumenten), hoe selecteer je een representatieve, diverse steekproef
   (bv. spreiding over partijen/sprekers, spreiding binnen het cluster zelf
   i.p.v. willekeurig) zonder zelf al te veel te sturen op wat "belangrijk"
   is?
5. **Stance-verdeling binnen clusters als signaal.** Elk cluster dat we
   bekeken bevatte zowel voor- als tegenstanders -- dat is eigenlijk precies
   het ruwe materiaal voor een confrontatie-band (het "wie zegt wat over
   hetzelfde deelpunt"-signaal zit er al in, vóórdat Gemini er iets mee
   doet). Is er een manier om dat te benutten (bv. clusters met een gemixte
   stance-verdeling prioriteren als kandidaat-tak boven clusters die bijna
   uitsluitend één stance bevatten, wat eerder op een niet-controversieel
   deelonderwerp wijst)?
6. **Kwaliteitsborging / validatie.** De bestaande pipeline is expliciet
   terughoudend met ongecontroleerde LLM-output (zie
   `redactie_reviews`-tabel, `twijfelachtige_classificaties`-veld in de
   huidige Gemini-prompt, het principe "verzin of parafraseer geen
   argumenttekst"). Hoe zou een evaluatieronde voor een uitgebreide boom
   eruitzien -- een steekproefsgewijze menselijke review zoals nu al
   gebeurt voor tags, of iets automatisch (bv. een tweede LLM-call die
   controleert of een voorgestelde nieuwe tak/blad daadwerkelijk aansluit)?
7. **Kosten/schaal.** bge-m3 via LM Studio op de host-GPU embedde 3555
   argumenten (asiel) in enkele tientallen seconden -- goedkoop genoeg om
   per topic te herhalen. Is het de moeite waard dit als vast, gecached
   pipeline-onderdeel te bouwen (analoog aan hoe `llm_calls` nu al
   LLM-aanroepen logt), of blijft dit beter een los, on-demand
   onderzoeksscript?
8. **Ruis / singleton-argumenten.** DBSCAN liet in alle topics een
   substantiële groep "ruis" (geen cluster) zien -- argumenten die semantisch
   geen duidelijke buren hebben. Zijn dat genuinely idiosyncratische
   standpunten die geen tak/blad verdienen, of eerder kandidaten voor
   extractiefouten (verkeerd getypeerd argument, te kort quote_text, etc.)
   die apart gesignaleerd zouden moeten worden?

## 5. Wat we niet vragen

Geen kant-en-klare implementatie of een concrete promptwijziging voor
`pipeline/prompts/argument_tree_gemini.md` -- wel een onderbouwd advies over
de aanpak/architectuur (bij voorkeur met een voorgestelde evaluatiemethode),
zodat we daarna zelf een prototype kunnen bouwen en testen op één topic
voordat het ergens in de pipeline landt.

## 6. Waar dit terechtkomt

Bij een positieve uitkomst raakt dit vermoedelijk twee plekken: een nieuwe
pipeline-stap voor het clusteren/vergelijken (naast
`pipeline/export_argument_doc.py`), en een tweede, gerichte
Gemini-promptvariant naast `pipeline/prompts/argument_tree_gemini.md` voor
"vul deze specifieke deelverzameling argumenten aan de bestaande boom toe"
i.p.v. de huidige "bouw de hele boom vanaf nul"-opzet. Referentiemateriaal:
`docs/poc/umap-argumenten/` (script, plots, eerdere bevindingen),
`scripts/argument_tree/experiment_find_similar_arguments.py` (cosine-similarity-zoekfunctie
+ cache), `data/embeddings/` (gecachete bge-m3-vectoren per topic, lokaal,
niet gecommit).
