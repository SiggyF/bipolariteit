# Prompt voor Gemini Deep Research — doelgroeponderzoek Bipolariteit

Doel van dit document: een kant-en-klare prompt om te plakken in Gemini's research-modus, om te bepalen wie de doelgroep van het platform is en wat die doelgroep nodig heeft. Nog geen doelgroep gedefinieerd — dit onderzoek moet daar richting aan geven vóórdat er verder gebouwd wordt aan features die op een specifiek publiek mikken.

---

## Prompt (plak dit in Gemini)

Je bent onderzoeksassistent voor een Nederlands non-profit/hobbyproject: een website die argumenten in kaart brengt van gepolariseerde Nederlandse maatschappelijke discussies (te beginnen met stikstofbeleid; later asielbeleid, abortus, en vergelijkbare onderwerpen). Ik heb nog geen duidelijk gedefinieerde doelgroep en wil dat jij via deskresearch (bestaande bronnen, geen eigen enquête — die mogelijkheid heb je niet) potentiële gebruikersgroepen identificeert, hun behoeften inschat, en concrete aanbevelingen doet voor productrichting.

### Context over het platform

- **Kernprincipe ("We listen and we don't judge")**: geen fact-checking. De site registreert welke argumenten/claims/getallen door wie genoemd worden, zonder een oordeel te vellen over of ze kloppen. Elk argument wordt altijd toegeschreven aan de spreker ("volgens X..."), nooit gepresenteerd als objectieve waarheid van de site zelf.
- **Werkwijze**: crawlers verzamelen bronnen (Tweede Kamer-debatverslagen als eerste bron; later nieuws-RSS en NPO-ondertiteling), een LLM destilleert daaruit gestructureerde argumenten (pro/contra/onduidelijk, met een typologie: feitelijk/moreel/economisch/juridisch/overig), en een tweede LLM-pass ("redactie-check") controleert of het tegenperspectief evenwichtig aan bod komt binnen de site — géén waarheidscontrole, puur een balans-check.
- **Weergave**: per onderwerp drie kolommen (pro/contra/onduidelijk) met individuele argumentkaarten: citaat, spreker, partij, onderbouwende claims, en (in ontwikkeling) een taxonomie van retorische/argumentatietheoretische tags (bv. drogredenen, framing, moreel fundament) en koppelingen tussen een argument en zijn directe weerlegging elders in het corpus.
- **Techniek/kosten**: volledig statische site (gratis hosting), geen backend, geen advertenties of verdienmodel gepland — dit is (vooralsnog) geen commercieel product.
- **Wat het nadrukkelijk niet is**: geen fact-checksite (zoals Nu.nl Factcheck of Trollrensics), geen nieuwsaggregator, geen opiniepeiling, geen politiek advies/stemhulp (zoals Kieskompas/StemWijzer).

### Wat ik van jou nodig heb

1. **Marktverkenning van vergelijkbare initiatieven** (Nederlands én internationaal): denk aan Ground News, AllSides, ProCon.org, Wikipedia-overlegpagina's-achtige initiatieven, Kieskompas/StemWijzer (ter afbakening, niet als concurrent), Nederlandse polarisatie-initiatieven (bv. van Bureau Beleidsonderzoek, Kieskompas, Universiteit Leiden-onderzoek naar polarisatie), en journalistieke "beide kanten"-formats. Wat doen zij goed/fout, en welk gat laten zij open dat dit platform zou kunnen vullen?
2. **Kandidaat-doelgroepsegmenten**, elk met een korte onderbouwing waaróm deze groep hier baat bij zou hebben en wat hen zou kunnen tegenhouden. Overweeg in elk geval (maar beperk je niet tot):
   - Journalisten/redacteuren die snel een overzicht van standpunten nodig hebben voor een artikel.
   - Docenten maatschappijleer/burgerschap en hun leerlingen (voortgezet onderwijs/mbo) — argumentatievaardigheden, mediawijsheid.
   - Politiek geïnteresseerde burgers die zich vóór een debat/stemming willen informeren over het brede spectrum van argumenten, niet alleen die van "hun eigen kant".
   - Beleidsmedewerkers/ambtenaren die snel willen zien welke argumenten in het parlementaire debat spelen.
   - Onderzoekers (politicologie, argumentatietheorie, discourse analysis) die het platform of de onderliggende data zouden willen gebruiken.
   - Mensen die zich zorgen maken over polarisatie/echokamers en actief op zoek zijn naar het "andere perspectief".
3. **Per segment**: welke concrete behoeften/taken zouden zij hebben (bv. "snel scannen", "citeerbare bron nodig", "wil weten wie het zegt", "wil argumenten kunnen delen op sociale media", "wil geschiedenis van een standpunt over tijd zien")? Welke bestaande alternatieven gebruiken zij nu, en waarom zouden of zouden zij niet overstappen?
4. **Risico's en zorgen** die deze doelgroepen waarschijnlijk hebben bij een LLM-gegenereerd (dus niet handmatig samengesteld) overzicht van politieke argumenten: vertrouwen in neutraliteit, angst voor onzichtbare bias in de LLM zelf, verificatie van citaten, transparantie over de methode. Hoe gaan vergelijkbare initiatieven hiermee om?
5. **Prioritering**: gegeven dat dit een solo/hobbyproject is met beperkte capaciteit (geen marketingbudget, geen bemande redactie, gratis statische hosting), welke 1-2 segmenten zou je adviseren als eerste focus, en waarom? Wat is voor dát segment de kleinste versie van het product die al waarde levert?
6. **Concrete productimplicaties**: voor het geadviseerde focus-segment, welke features zou je prioriteren (bv. deelbare links per argument, RSS/nieuwsbrief, exportfunctie, vergelijking tussen partijen, tijdlijn van een debat) en welke zou je bewust uitstellen?

### Gewenste output-vorm

- Een kort overzicht van 4-6 kandidaat-segmenten (max. 1 alinea per segment: wie, behoefte, huidig alternatief, twijfelpunt).
- Een tabel: segment × (kernbehoefte, grootste risico/zorg, geschatte omvang/bereikbaarheid in Nederland).
- Een expliciete aanbeveling voor het/de eerste focus-segment(en), met argumentatie.
- Een lijst concrete, prioriteerbare features voor dat focus-segment.
- Bronvermelding/links naar de vergelijkbare initiatieven en eventueel onderzoek naar polarisatie/nieuwsconsumptie in Nederland waarop je je conclusies baseert.

Schrijf het antwoord in het Nederlands.
