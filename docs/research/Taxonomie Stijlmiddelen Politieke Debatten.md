# **Taxonomie van Stijlmiddelen in Politiek Debat: Synthese van SemEval-2020 Task 11 en Bipolariteit-Pipelinedesign**

De geautomatiseerde analyse van maatschappelijke en politieke debatten op het Bipolariteit-platform vereist een doordachte en argumentatietheoretisch zuivere categorisatie van taaluitingen. Bij de verwerking van politieke debatten — zoals de parlementaire beraadslagingen over het Nederlandse stikstofbeleid — is gebleken dat de bestaande labelgroepen Dialectische Kwaliteit (drogredenen) en Generieke Nieuwsframes (thematische invalshoeken) onvoldoende dekking bieden voor puur vormelijke en retorische middelen.  
Dit onderzoeksrapport biedt een evaluatie van het voorstel om een nieuwe labelgroep Stijlmiddelen te introduceren in het Bipolariteit-systeem (data/tags.toml). Hierin wordt de internationale propaganda-taxonomie van SemEval-2020 Task 11 ontleed1, getoetst aan het architectonische uitgangspunt van Bipolariteit ("geen inhoudelijk oordeel nodig"), en aangevuld met klassieke retorische stijlfiguren uit de Nederlandse parlementaire praktijk3.

## **Argumentatietheoretische en Architectonische Afbakening**

Het platform Bipolariteit is gebouwd op de fundamentele pijlers van neutrale argumentbegrippen: er vindt geen feitenonderzoek of fact-checking plaats, beweringen worden consequent toegeschreven aan de zender, en de redactionele controle richt zich uitsluitend op evenwicht tussen perspectieven. Om deze uitgangspunten consistent door te voeren in de geautomatiseerde verwerkingsketen (extract, tag, redactie), moet de taxonomie van labels scherp afgebakend zijn.  
Momenteel kent het systeem twee hoofdcategorieën voor het classificeren van tekstfragmenten, waaraan nu een derde categorie wordt toegevoegd:

> 1. **Dialectische Kwaliteit (Drogredenen):** Deze categorie identificeert redeneerfouten en overtredingen van dialectische regels. Een tag binnen deze groep claimt expliciet dat de onderliggende logica of argumentatiestructuur mank gaat, zoals een *Stropopredenering* of een *Vals Dilemma*.  
> 2. **Generieke Nieuwsframes (Framing):** Deze categorie beschrijft het perspectief of de thematische invalshoek waarmee een onderwerp belicht wordt, zoals het *Economisch frame* of het *Menselijk belang frame*. Het gaat hierbij over de inhoudelijke nadruk in de verslaglegging of het betoog, niet over specifieke woordkeuze of zinsbouw.  
> 3. **Stijlmiddelen (Retorische Tropes):** Deze nieuwe categorie richt zich op de microstructuur, stijl en lexicale vormgeving van uitingen. Een stijlmiddel claimt geen redeneerfout en definieert geen macroframe; het beschrijft uitsluitend de retorische verpakking waarin een stelling wordt gepresenteerd.

### **Het Architectonische Toetscriterium**

Om te bepalen of een tag in het geautomatiseerde Bipolariteit-systeem kan worden opgenomen zonder de neutraliteitsregel te schenden, geldt het **Toetscriterium voor Vormelijke Evaluatie**:  
*Kan de tag worden toegekend uitsluitend op basis van de oppervlaktestructuur, stijl of lexicale kenmerken van een fragment, zonder dat een inhoudelijk oordeel nodig is over de feitelijke juistheid van claims of de logische geldigheid van de onderliggende argumentatie?*

#### **De Slogan als Aanleiding**

De uitwerking van dit criterium werd getriggerd door de tag *Slogans* uit de ElecDeb60to20-richtlijnen (afkomstig uit de fallacy guidelines en gebaseerd op SemEval-2020 Task 11\)1. Een slogan zoals *"Geen boer, geen voer"* of *"Bouwen, bouwen, bouwen"* voldoet aan het toetscriterium: een taalmodel of menselijke annotator kan het aanwezig zijn van een ritmische, herhaalde en pakkende frase vaststellen op basis van de tekstuele vorm allein.  
Een slogan is echter geen drogreden. Een spreker kan een inhoudelijk volstrekt valide en cijfermatig onderbouwd stikstofbetoog afsluiten met een pakkende slagzin. Het toekennen van het label "Drogreden" zou ten onrechte impliceren dat de redenering foutief is. Evenmin is een slogan een nieuwsframe, aangezien het een specifieke stijlfiguur betreft en geen overkoepelende thematische invalshoek. De oprichting van de labelgroep Stijlmiddelen lost dit theoretische en praktische vacuüm op.

## **Systematische Analyse van SemEval-2020 Task 11**

SemEval-2020 Task 11 (*Detection of Propaganda Techniques in News Articles*) formuleerde een taxonomie van 18 technieken voor overtuigingskracht en beïnvloeding1. In de uiteindelijke shared task werden zeldzame klassen samengevoegd tot 14 categorieën voor de Technique Classification (TC) subtaak5.  
Voor de architectuur van Bipolariteit is de volledige set van 18 technieken geanalyseerd op drie aspecten:

* **Toetsvaliditeit:** Voldoet de techniek aan het criterium dat er geen inhoudelijk oordeel over de correctheid nodig is?  
* **Classificatie:** Hoort de techniek thuis onder *Stijlmiddelen*, *Dialectische Kwaliteit*, of valt deze af?  
* **Overlap:** Welke overlap bestaat er met reeds gedefinieerde tags in het Bipolariteit-schema (zoals Walton-schemas of traditionele drogredenen)?

| SemEval-2020 Techniek | Omschrijving | Voldoet aan Toets? | Bipolariteit Classificatie | Overlap / Motivering |
| :---- | :---- | :---- | :---- | :---- |
| **Loaded Language** | Gebruik van worden met sterke emotionele gevoelswaarde1. | Ja | Stijlmiddelen | Lexicaal stijlmiddel. Claimt geen logische fout1. |
| **Name Calling / Labeling** | Etikettering van personen of groepen met geladen termen1. | Ja | Stijlmiddelen | Vormelijk aanwijsbaar in het tekstfragment5. |
| **Repetition** | Meermaals herhalen van dezelfde boodschap of frase1. | Ja | Stijlmiddelen | Puur structuurelement en stijlfiguur5. |
| **Exaggeration / Minimization** | Overdrijven of kleiner maken van situaties (Hyperbool/Eufemisme)1. | Ja | Stijlmiddelen | Stijlfiguur op basis van lexicale schaalvergroting5. |
| **Slogans** | Beknopte, pakkende frase bedoeld om te blijven hangen1. | Ja | Stijlmiddelen | Vormelijk herkenbare slagzin of motto5. |
| **Doubt** | In twijfel trekken van geloofwaardigheid zonder bewijs1. | Ja | Stijlmiddelen | Retorische twijfelzaaiing op zinsniveau5. |
| **Appeal to Fear / Prejudice** | Inspelen op angst, onzekerheid of vooroordelen1. | Ja | Stijlmiddelen | Emotioneel appèl en retorische kleuring1. |
| **Flag-Waving** | Beroep doen op groepsidentiteit, symbolen of patriotisme1. | Ja | Stijlmiddelen | Identiteitsgerichte retoriek5. |
| **Thought-terminating Cliché** | Dooddoener die verdere discussie blokkeert5. | Ja | Stijlmiddelen | Vaststaande frase ("Het is nu eenmaal zo")5. |
| **Obfuscation / Vagueness** | Bewust vaag, complex of ambigu taalgebruik6. | Ja | Stijlmiddelen | Stijlmiddel gericht op verhulling8. |
| **Causal Oversimplification** | Aannemen van één enkele oorzaak voor een complex probleem1. | Nee | Dialectische Kwaliteit | Vereist inhoudelijk oordeel over de complexiteit. Overlap met *Vals Dilemma / False Cause*5. |
| **Appeal to Authority** | Aanroepen van een autoriteit om een claim te staven5. | Nee | Dialectische Kwaliteit | Vereist oordeel over expertise. Overlap met *Walton Expertise*5. |
| **Black-and-white Fallacy** | Presenteren van slechts twee extreme keuzes5. | Nee | Dialectische Kwaliteit | Redeneerfout. Overlap met *Drogreden-Vals-Dilemma*5. |
| **Whataboutism** | Afleiden van beschuldiging door tegenbeschuldiging5. | Nee | Dialectische Kwaliteit | Vereist relevantie-oordeel. Overlap met *Drogreden-Tu-Quoque / Ad Hominem*5. |
| **Red Herring** | Introduceren van irrelevant onderwerp om af te leiden5. | Nee | Dialectische Kwaliteit | Vereist inhoudelijk relevantie-oordeel. Overlap met *Drogreden-Rode-Haring*5. |
| **Straw Man** | Verdraaien van het standpunt van de tegenstander5. | Nee | Dialectische Kwaliteit | Vereist vergelijking met bronstandpunt. Overlap met *Drogreden-Stropop*5. |
| **Bandwagon** | Argumenteren dat iets juist is omdat velen het geloven5. | Nee | Dialectische Kwaliteit | Redeneerfout. Overlap met *Drogreden-Ad-Populum / Bespelen-Publiek*5. |
| **Reductio ad Hitlerum** | Discrediteren door vergelijking met gehaat symbool5. | Nee | Dialectische Kwaliteit | Vorm van vergelijkingsfout / *Ad Hominem*5. |

### **Diepere Inzichten uit de SemEval-Deconstructie**

De deconstructie van SemEval-2020 Task 11 brengt een fundamentele waterscheiding aan het licht tussen retorische beïnvloedingstechnieken en argumentatieve fouten1:

> 1. **Inhoudsafhankelijke versus Inhoudsonafhankelijke Annotatie:** Categorieën zoals *Straw Man* of *Causal Oversimplification* kunnen niet worden vastgesteld door uitsluitend naar het geannoteerde tekstfragment te kijken1. Een analist moet het oorspronkelijke betoog van de tegenstander kennen om te bepalen of een standpunt is verdraaid (*Straw Man*), of moet inhoudelijke domeinkennis bezitten over stikstofemissies om vast te stellen dat een oorzakelijk verband is oversimplificeerd1. Deze categorieën horen om die reden thuis onder *Dialectische Kwaliteit*.  
> 2. **Oppervlaktekenmerken van Taalgebruik:** Categorieën zoals *Loaded Language*, *Slogans*, en *Thought-terminating Clichés* manifesteren zich direct in de lexicale of syntactische structuur van de tekst1. Ze vereisen geen feitenonderzoek. Een passage waarin de term "stikstofwaanzin" of "vrijheidsberoving" voorkomt, kan direct worden gelabeld als *Geladen Taalgebruik* of *Etikettering*, ongeacht de inhoudelijke argumentatie van de spreker5.

## **Uitbreiding met Klassieke Retorische Stijlmiddelen uit Politiek Debat**

Aangezien SemEval-2020 Task 11 primair is ontworpen voor geschreven nieuwsartikelen1, dekt de set niet alle retorische vormen af die optreden in mondelinge politieke debatten. Politieke redevoeringen in de Tweede Kamer en tijdens verkiezingsdebatten maken intensief gebruik van klassieke stijlfiguren om de overtuigingskracht en memorabiliteit te vergroten3.  
Om een representatief kader te bieden voor Nederlandse politieke debatten, wordt de gefilterde SemEval-set aangevuld met vijf klassieke stijlmiddelen die veelvuldig voorkomen in parlementaire teksten3:

### **1\. Drieledige Opsomming (Tricolon / Enumeratie)**

Politici gieten argumenten of voorbeelden instinctief in reeksen van drie ("voor onze landbouw, voor onze leefbaarheid, en voor onze toekomst")4. Het tricolon verhoogt de ritmiek en de overtuigingskracht van een passage zonder dat het extra inhoudelijke feiten toevoegt4.

### **2\. Retorische Vraag**

Een vraagstelling waarop de spreker geen antwoord verwacht, maar waarmee een stelling of conclusie in de mond van het publiek of de tegenstander wordt gelegd ("Wilt u dat onze gezinsbedrijven over de kop gaan?")4. Het is een vormelijk middel om een standpunt te poneren onder de dekmantel van een vraag4.

### **3\. Antithese (Scherpe Tegenstelling)**

Het direct tegenover elkaar plaatsen van twee tegengestelde begrippen om een contrast te vergroten ("niet het papier van de bureaucratie, maar de realiteit van de boer")3. Dit stijlmiddel versterkt de polarisatie op de as van het debat3.

### **4\. Alliteratie en Klankspel**

Het herhalen van beginletters van beklemtoonde lettergrepen ("pragmatisch plattelandsbeleid", "stikstofstrop")4. Dit verhoogt het herkenbaarheidsgehalte van een boodschap en zorgt dat frasen sneller worden overgenomen in media-artikelen4.

### **5\. Cirkeltechniek en Vaste Afsluiting**

Het herhaaldelijk terugkeren naar een vast motief in het slot van een betoog, of het systematisch afsluiten van elke bijdrage met een vaste frase10. Een bekend parlementair voorbeeld is de traditie waarbij een spreker elk debat afsluit met een vaste, herkenbare slotformule4.

## **Voorgestelde Taxonomie voor data/tags.toml**

Op basis van de gefilterde SemEval-taxonomie en de klassieke retorische stijlfiguren wordt de onderstaande compacte, operationaliseerbare set voorgesteld voor de nieuwe labelgroep Stijlmiddelen.  
Om te voldoen aan het uitgangspunt van redactionele neutraliteit zijn pejoratieve termen uit de propaganda-literatuur (zoals "Name Calling" of "Propaganda") omgezet naar objectieve taalkundige benamingen.

| Tag Key | Nederlandse Naam | Formele Definitie | Voorbeeld (Stikstof / Politiek) | LLM-Detectiecriterium (Formeel) |
| :---- | :---- | :---- | :---- | :---- |
| stijlmiddel-slogan | **Slogan / Slagzin** | Beknopte, ritmische en herhaalde frase die dient als motto of identificatie1. | *"Geen boer, geen voer\!"* of *"Gezond verstand terug in de polder."* | Frase is kort (\<10 woorden), heeft een slagzingkarakter en wordt als motto gepresenteerd5. |
| stijlmiddel-geladen-taal | **Geladen Taalgebruik** | Woordkeuze met een sterke emotionele of waarderende lading1. | *"De stikstofwaanzin vernietigt onze gezinsbedrijven."* | Aanwezigheid van emotioneel gekleurde adjectieven of substantieven5. |
| stijlmiddel-etikettering | **Etikettering / Labeling** | Het toeschrijven van een typerend, stereotiep of geladen etiket aan personen of groepen1. | *"De 'klimaatrampers' aan het Binnenhof..."* | Vormelijke toeschrijving van een etiket of categorie aan de tegenpartij5. |
| stijlmiddel-herhaling | **Herhaling / Repetitie** | Letterlijke herhaling van kernbegrippen binnen hetzelfde fragment1. | *"We moeten bouwen, bouwen, en nog eens bouwen."* | Meervoudig voorkomen van dezelfde stam of frase in een kort segment5. |
| stijlmiddel-drieledige-opsomming | **Drieledige Opsomming** | Een ritmische opsomming van exact drie elementen (tricolon)4. | *"Voor onze natuur, voor onze boeren, en voor onze toekomst."* | Aanwezigheid van een driedelige syntactische opsomming4. |
| stijlmiddel-retorische-vraag | **Retorische Vraag** | Vraagstelling waarop geen antwoord wordt verwacht, gebruikt als stelling4. | *"Moeten we wachten tot de laatste boer vertrokken is?"* | Zinsbouw eindigt met vraagteken maar functioneert als argumentatieve claim4. |
| stijlmiddel-antithese | **Antithese / Contrast** | Het direct tegenover elkaar plaatsen van twee tegengestelde begrippen3. | *"Niet het papier in Den Haag, maar de realiteit in de klei."* | Syntactische nevenschikking van twee tegengestelde concepten4. |
| stijlmiddel-dooddoener | **Dooddoener / Cliché** | Een vaststaande uitspraak die verdere inhoudelijke discussie blokkeert5. | *"Regels zijn nu eenmaal regels."* of *"Het moet van Brussel."* | Gebruik van een vaststaand cliché dat inhoudelijke argumentatie afsluit5. |
| stijlmiddel-groepsidentiteit | **Groepsidentiteit-appèl** | Beroep doen op gedeelde waarden, symbolen of groepsgevoel1. | *"Als trotse Nederlanders laten we ons land niet op slot zetten."* | Expliciete verwijzing naar een in-group ("ons volk", "onze boeren")5. |
| stijlmiddel-hyperbool-eufemisme | **Hyperbool / Eufemisme** | Vormelijke overdrijving of verhullende verzachting van feiten1. | Overdrijving: *"Een catastrofe van bijbelse proporties."* Verzachting: *"Een aanpassing van de veestapel."* | Aanwezigheid van extreme schaalvergroting of verhullende terminologie5. |

## **Pipeline-Implementatie en Frontend-Representatie**

Het toevoegen van de labelgroep Stijlmiddelen vereist aanpassingen in de datastructuur, de LLM-prompts en de statische JSON-export naar de frontend.

### **Configuration Structure in data/tags.toml**

In het configuratiebestand data/tags.toml wordt de nieuwe sectie gedefinieerd met een heldere scheiding ten opzichte van Dialectische Kwaliteit:

Ini, TOML  
\[labelgroups.stijlmiddelen\]  
name \= "Stijlmiddelen"  
description \= "Vormelijke en retorische middelen die gebruikt worden in het debat. Claimen geen redeneerfout en vereisen geen feitelijk oordeel."

\[tags.stijlmiddel-slogan\]  
group \= "stijlmiddelen"  
label \= "Slogan / Slagzin"  
description \= "Beknopte, pakkende frase die als motto of slagzin wordt gebruikt."

\[tags.stijlmiddel-geladen-taal\]  
group \= "stijlmiddelen"  
label \= "Geladen Taalgebruik"  
description \= "Gebruik van woorden met een sterke emotionele of waarderende lading."

\[tags.stijlmiddel-drieledige-opsomming\]  
group \= "stijlmiddelen"  
label \= "Drieledige Opsomming"  
description \= "Ritmische opsomming van drie elementen (tricolon)."

### **Promptingstrategie voor de tag-Stage**

De prompt voor de geautomatiseerde tagging-stage moet de instructie bevatten dat het toekennen van stijlmiddelen onafhankelijk van het inhoudelijke waarheidsgehalte gebeurt:  
*"Beoordeel het onderstaande tekstfragment op de aanwezigheid van Stijlmiddelen. Let uitsluitend op de taalvorm, zinsbouw en woordkeuze. Ken een tag toe zodra het patroon vormelijk herkenbaar is, ongeacht of de uitspraak feitelijk juist is of argumentatief sterk. Maak een strikt onderscheid tussen Stijlmiddelen (vorm) en Dialectische Kwaliteit (logische redeneerfouten)."*

### **Frontend Data Export en UI-Representatie**

De geëxporteerde JSON-bestanden in data/export/ voeden de statische Astro/Vue-frontend. Binnen het argumentmodel worden stijlmiddelen gescheiden opgeslagen van logische drogredenen en frames:

JSON  
{  
  "argument\_id": "arg\_tk\_2023\_stikstof\_042",  
  "speaker": "Caroline van der Plas",  
  "text": "De stikstofregels zorgen voor een totale stilstand van ons platteland. Geen boer, geen voer\!",  
  "tags": {  
    "dialectische\_kwaliteit": \[\],  
    "nieuwsframes": \["frame-economisch-en-leefbaarheid"\],  
    "stijlmiddelen": \[  
      "stijlmiddel-geladen-taal",  
      "stijlmiddel-slogan"  
    \]  
  }  
}

In de gebruikersinterface worden stijlmiddelen getoond onder de neutraal geformuleerde header **"Gebruikte Stijlmiddelen"**, vergezeld van uitlegtoelichtingen. Dit voorkomt dat de analyse door bezoekers wordt geïnterpreteerd als een negatief oordeel over de spreker.

## **Conclusie en Actiepunten**

De synthese van de SemEval-2020 Task 11-taxonomie en de Nederlandse retorische debattractie leidt tot de volgende concrete conclusies en vervolgstappen voor issue \#62, PR \#66 en het Bipolariteit-platform:

> 1. **Invoering Labelgroep Stijlmiddelen:** Het toevoegen van een derde labelgroep naast *Dialectische Kwaliteit* en *Generieke Nieuwsframes* is argumentatietheoretisch noodzakelijk. Dit voorkomt dat vormelijke kenmerken zoals slogans ten onrechte als logische redeneerfouten worden aangemerkt.  
> 2. **Neutralisering van Terminologie:** Woorden uit de propaganda-literatuur worden vervangen door neutrale taalkundige en retorische begrippen (zoals *Geladen Taalgebruik* en *Etikettering*).  
> 3. **Herplaatsing van Logische Categorieën:** SemEval-categorieën die een inhoudelijk of vergelijkend oordeel vereisen (zoals *Straw Man*, *Black-and-White Fallacy*, en *Causal Oversimplification*) horen niet thuis bij Stijlmiddelen1. Deze vallen, voor zover ze niet reeds aanwezig zijn, onder *Dialectische Kwaliteit*.  
> 4. **Verrijking met Debatfiguren:** De toevoeging van klassieke stijlfiguren zoals het *Tricolon (Drieledige Opsomming)*, de *Retorische Vraag*, en de *Antithese* zorgt voor een dekking van de specifieke retoriek in Nederlandse parlementaire debatten3.  
> 5. **Implementatie in Codebase:** De voorgestelde taxonomie kan direct worden opgenomen in data/tags.toml. Vervolgens kunnen de prompts in de pipeline-stages van PR \#66 worden aangepast om het onderscheid tussen redeneerfout en taalvorm formeel te borgen.

#### **Works cited**

> 1. SemEval-2020 Task 11: Detection of Propaganda Techniques in News Articles \- ACL Anthology, [https://aclanthology.org/2020.semeval-1.186.pdf](https://aclanthology.org/2020.semeval-1.186.pdf)  
> 2. SemEval-2020 Task 11: Detection of Propaganda Techniques in News Articles, [https://aclanthology.org/2020.semeval-1.186/](https://aclanthology.org/2020.semeval-1.186/)  
> 3. Een moeilijk te analyseren, onvervangbare sfeer, [https://repository.ubn.ru.nl/bitstream/2066/68462/1/68462.pdf](https://repository.ubn.ru.nl/bitstream/2066/68462/1/68462.pdf)  
> 4. Proef 3: Speeches \- LitLab, [https://litlab.nl/proef/speeches/](https://litlab.nl/proef/speeches/)  
> 5. (PDF) SemEval-2020 Task 11: Detection of Propaganda Techniques in News Articles, [https://www.researchgate.net/publication/355429869\_SemEval-2020\_Task\_11\_Detection\_of\_Propaganda\_Techniques\_in\_News\_Articles](https://www.researchgate.net/publication/355429869_SemEval-2020_Task_11_Detection_of_Propaganda_Techniques_in_News_Articles)  
> 6. Detecting Propaganda Techniques in Code-Switched Social Media Text \- arXiv, [https://arxiv.org/html/2305.14534v2](https://arxiv.org/html/2305.14534v2)  
> 7. PTC tasks on "Detection of Propaganda Techniques in News Articles", [https://propaganda.math.unipd.it/ptc/](https://propaganda.math.unipd.it/ptc/)  
> 8. (PDF) UAIC1860 at SemEval-2020 Task 11: Detection of Propaganda Techniques in News Articles \- ResearchGate, [https://www.researchgate.net/publication/355430014\_UAIC1860\_at\_SemEval-2020\_Task\_11\_Detection\_of\_Propaganda\_Techniques\_in\_News\_Articles](https://www.researchgate.net/publication/355430014_UAIC1860_at_SemEval-2020_Task_11_Detection_of_Propaganda_Techniques_in_News_Articles)  
> 9. REQUISITOIR \- Openbaar Ministerie, [https://www.om.nl/site/binaries/site-content/collections/documents/wilders/map/map/requisitoir-zaak-wilders-in-hoger-beroep-2-en-3-juli-2019/190703\_requisitoir\_wilders.pdf](https://www.om.nl/site/binaries/site-content/collections/documents/wilders/map/map/requisitoir-zaak-wilders-in-hoger-beroep-2-en-3-juli-2019/190703_requisitoir_wilders.pdf)  
> 10. Stijl en politiek. Een taalkundig-stilistische benadering van Nederlandse parlementaire toespraken \- Scholarly Publications Leiden University, [https://scholarlypublications.universiteitleiden.nl/access/item%3A2919786/view](https://scholarlypublications.universiteitleiden.nl/access/item%3A2919786/view)  
> 11. Stijl en politiek \- LOT Publications, [https://www.lotpublications.nl/Documents/386\_fulltext.pdf](https://www.lotpublications.nl/Documents/386_fulltext.pdf)