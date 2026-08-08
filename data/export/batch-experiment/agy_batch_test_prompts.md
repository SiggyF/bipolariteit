=== document 37 (Caroline van der Plas) ===
Je analyseert één sprekerbeurt uit een Tweede Kamer-debat over het onderwerp "stikstof". Spreker: Caroline van der Plas (BBB).

Context over de pro/contra-dimensie van dit onderwerp:
Dit debat gaat over het Nederlandse stikstofbeleid: het kabinetsbeleid gericht op het verlagen van stikstofuitstoot (via normen zoals de kritische depositiewaarde/KDW, gebiedsgerichte aanpak, en verplichtende maatregelen voor onder meer de landbouw), bedoeld om aan natuurdoelen en vergunningverlening te voldoen.

PRO = steunt dit beleid (het huidige of voorgestelde kabinetsbeleid), of pleit voor verdergaande/snellere stikstofreductie.
CONTRA = verzet zich tegen dit beleid, pleit voor afzwakking, uitstel, een ander instrument, vrijwilligheid in plaats van verplichting, of een wezenlijk alternatieve aanpak.

Let op: dit is puur een classificatie-hulpmiddel om het debat te ordenen, geen waardeoordeel over welke kant gelijk heeft.

Jouw taak: identificeer elk afzonderlijk politiek argument dat deze spreker inbrengt over "stikstof". Een argument heeft altijd twee delen: een standpunt (pro/contra/onduidelijk t.o.v. de pro/contra-dimensie hierboven) ÉN een reden/onderbouwing die dat standpunt ondersteunt. Beide delen moeten in het citaat zelf aanwezig zijn.

Regels (belangrijk, volg strikt):
- Jij bent geen scheidsrechter. Beoordeel nooit of een argument klopt, terecht is, of overtuigend is. Geef nooit het ene standpunt gelijk boven het andere.
- Citeer letterlijk uit de brontekst (quote_text) — verzin of parafraseer geen tekst.
- **Geen onderbouwing = geen argument.** Een kale stellingname, intentieverklaring, wens, of statement zonder reden is GEEN argument, ook niet als het stellig of politiek geladen klinkt. Voorbeelden van wat je NIET moet extraheren: "Ik strijd hier tot de laatste dag voor de boeren" (intentie, geen reden), "Afzwakking steunen we niet" (kaal standpunt, geen reden), "Dat vinden wij een goed idee" (instemming zonder reden), "Wij vinden het natuurbelang heel erg zwaar wegen" (waardestelling zonder reden). Extraheer dit soort zinnen alleen als de reden er letterlijk bij staat.
- **Eén punt = één argument.** Als de spreker hetzelfde punt in opeenvolgende zinnen verder uitwerkt, aanvult, of herhaalt (bv. een stelling gevolgd door de reden erachter, of twee keer dezelfde kernboodschap in andere woorden binnen dezelfde beurt), voeg dit samen tot één `quote_text` (met de tussenliggende tekst inbegrepen) in plaats van het op te knippen in meerdere argumenten. Knip alleen op naar een nieuw argument als er echt een ander punt, andere reden, of ander standpunt begint.
- Procedurele tekst levert GEEN argumenten op: orde van de vergadering, spreektijd-afspraken, "ik geef het woord aan...", "ik stel voor dat...", dank-/welkomstwoorden, en vergelijkbare voorzitters-chatter. Als de hele sprekerbeurt procedureel is, geef een lege lijst terug.
- Let op het verschil tussen procedurele chatter (hierboven, GEEN argument) en metadiscours (WEL een argument, mits onderbouwd): een uiting over de legitimiteit, reikwijdte, bevoegdheid, of spelregels van het debat zelf — bv. "dit is geen dunne lijn... ik benoem hier de feiten" — is een inhoudelijk standpunt over hoe het debat gevoerd mag worden, en telt mee als argument, ook als het niet direct over "stikstof" zelf gaat. Gebruik dan `typology: "other"` en `stance: "unclear"` tenzij een pro/contra-richting t.o.v. het beleid duidelijk is. Een kale roode-lijn-verklaring zonder reden ("afzwakking steunen we niet") blijft ook hier geen argument — de "geen onderbouwing = geen argument"-regel geldt onverkort.
- Eén sprekerbeurt kan 0, 1, of meerdere argumenten bevatten (bv. bij meerdere onderwerpen of tegenargumenten binnen dezelfde beurt).
- Elk genoemd getal, percentage, onderzoek, of feitelijke bewering met een bron ("uit onderzoek van X blijkt...", "volgens het RIVM...") noteer je als een claim, met alleen wat letterlijk gezegd is over de bron — beoordeel nooit of het getal of de bron klopt.
- `typology`: "factual" (feiten, cijfers, beleidsinhoudelijke of bestuurlijke constateringen — bv. een norm, een fractiestandpunt, wie iets wel/niet steunt), "moral" (ethisch/waarden), "economic" (kosten/baten), "legal" (verwijst naar een specifieke wet, regelgeving, of juridische toetsing/procedure), of "other". Gebruik "legal" alleen als het echt om wetgeving/regelgeving/juridische procedure gaat — een bestuurlijke keuze, beleidsnorm (bv. een GVE-norm of bufferzone-afstand), of politieke uitspraak van een bestuurder is meestal "factual" of "other", niet "legal".
- `stance`: "pro" of "contra" volgens de pro/contra-dimensie hierboven (niet t.o.v. het onderwerp "stikstof" in abstracte zin), of "unclear" als het standpunt niet eenduidig is. Kritiek op het huidige/voorgestelde beleid is `contra`, ook als de spreker dat doet door te verwijzen naar een eigen alternatief of eerder gevoerd beleid.

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok eromheen. Formaat:

```
{"arguments": [
  {
    "stance": "pro" | "contra" | "unclear",
    "typology": "factual" | "moral" | "economic" | "legal" | "other",
    "quote_text": "letterlijk citaat uit de brontekst",
    "quote_context": "korte context (optioneel, of null)",
    "claims": [
      {"claim_text": "wat genoemd is", "attributed_source_text": "aangehaalde bron, of null"}
    ]
  }
]}
```

Als er geen argumenten zijn: `{"arguments": []}`.

Brontekst (sprekerbeurt):
"""
Mevrouw Van der Plas (BBB): Dank u wel, voorzitter. Een groot welkom aan alle boeren, burgers en aanverwanten die dit debat bijwonen.
Voorzitter. De minister van LVVN en de minister-president stonden vrijdag breed lachend het einde van duizenden boeren aan te kondigen. Duizenden boeren die hun toekomst vernietigd zien worden, moesten op tv en op sociale media toekijken hoe dit kabinet met een vrolijke lach een mes in hun rug stak. Nog erger, de afgelopen maanden gingen hier ontbijtjes, een cafébezoek, hardloopsessies en een wijnparty met de voorzitter van LTO op het ministerie aan vooraf.
Voorzitter. Als er een Tjeerd de Groot-award zou bestaan, had deze minister die glansrijk gewonnen. Met maatregelen als zonering van 500 meter en 1 kilometer rondom natuurgebieden, grondgebondenheid, oftewel een grens van 2,6 koeien per hectare, afroming, dreigen met gedwongen uitkoop, gedwongen krimp van de veestapel en emissierecht per fosfaatnorm werd het volk voorgehouden dat boeren weer perspectief hebben, dat ze vergunningen kunnen krijgen. Feitelijk betekent het gewoon halvering van de veestapel, de natte droom van D66.
De stikstofobsessie gaat de natuur niet eens helpen. Er is geen stikstofprobleem. Er is een stikstofwetprobleem. Iedereen weet dat duizenden boeren met alle maatregelen vrijdag gewoon een doodsvonnis hebben gekregen. Maar deze minister deed alsof hij boeren een plezier deed. Hij doet alsof hij doet wat boeren hem hebben gevraagd. Ik citeer de minister. "Boeren zeggen ook: trek die pleister er maar eens af." Er is geen boer die dat zegt. Dit is wat bestuurders het volk willen doen geloven. Er is geen boer die zegt: duw me maar het ravijn in, want dan heb ik tenminste duidelijkheid. Dat zegt niemand. Boeren willen boeren en een toekomst, geen vernietiging.
Voorzitter. Alles wat BBB in de steigers heeft gezet in het kabinet-Schoof, beleid dat was gericht op écht perspectief voor onze boeren met veel minder ingrijpende maatregelen en een échte toekomst, wordt met de sloophamer vernietigd.
"""


=== document 40 (Caroline van der Plas) ===
Je analyseert één sprekerbeurt uit een Tweede Kamer-debat over het onderwerp "stikstof". Spreker: Caroline van der Plas (BBB).

Context over de pro/contra-dimensie van dit onderwerp:
Dit debat gaat over het Nederlandse stikstofbeleid: het kabinetsbeleid gericht op het verlagen van stikstofuitstoot (via normen zoals de kritische depositiewaarde/KDW, gebiedsgerichte aanpak, en verplichtende maatregelen voor onder meer de landbouw), bedoeld om aan natuurdoelen en vergunningverlening te voldoen.

PRO = steunt dit beleid (het huidige of voorgestelde kabinetsbeleid), of pleit voor verdergaande/snellere stikstofreductie.
CONTRA = verzet zich tegen dit beleid, pleit voor afzwakking, uitstel, een ander instrument, vrijwilligheid in plaats van verplichting, of een wezenlijk alternatieve aanpak.

Let op: dit is puur een classificatie-hulpmiddel om het debat te ordenen, geen waardeoordeel over welke kant gelijk heeft.

Jouw taak: identificeer elk afzonderlijk politiek argument dat deze spreker inbrengt over "stikstof". Een argument heeft altijd twee delen: een standpunt (pro/contra/onduidelijk t.o.v. de pro/contra-dimensie hierboven) ÉN een reden/onderbouwing die dat standpunt ondersteunt. Beide delen moeten in het citaat zelf aanwezig zijn.

Regels (belangrijk, volg strikt):
- Jij bent geen scheidsrechter. Beoordeel nooit of een argument klopt, terecht is, of overtuigend is. Geef nooit het ene standpunt gelijk boven het andere.
- Citeer letterlijk uit de brontekst (quote_text) — verzin of parafraseer geen tekst.
- **Geen onderbouwing = geen argument.** Een kale stellingname, intentieverklaring, wens, of statement zonder reden is GEEN argument, ook niet als het stellig of politiek geladen klinkt. Voorbeelden van wat je NIET moet extraheren: "Ik strijd hier tot de laatste dag voor de boeren" (intentie, geen reden), "Afzwakking steunen we niet" (kaal standpunt, geen reden), "Dat vinden wij een goed idee" (instemming zonder reden), "Wij vinden het natuurbelang heel erg zwaar wegen" (waardestelling zonder reden). Extraheer dit soort zinnen alleen als de reden er letterlijk bij staat.
- **Eén punt = één argument.** Als de spreker hetzelfde punt in opeenvolgende zinnen verder uitwerkt, aanvult, of herhaalt (bv. een stelling gevolgd door de reden erachter, of twee keer dezelfde kernboodschap in andere woorden binnen dezelfde beurt), voeg dit samen tot één `quote_text` (met de tussenliggende tekst inbegrepen) in plaats van het op te knippen in meerdere argumenten. Knip alleen op naar een nieuw argument als er echt een ander punt, andere reden, of ander standpunt begint.
- Procedurele tekst levert GEEN argumenten op: orde van de vergadering, spreektijd-afspraken, "ik geef het woord aan...", "ik stel voor dat...", dank-/welkomstwoorden, en vergelijkbare voorzitters-chatter. Als de hele sprekerbeurt procedureel is, geef een lege lijst terug.
- Let op het verschil tussen procedurele chatter (hierboven, GEEN argument) en metadiscours (WEL een argument, mits onderbouwd): een uiting over de legitimiteit, reikwijdte, bevoegdheid, of spelregels van het debat zelf — bv. "dit is geen dunne lijn... ik benoem hier de feiten" — is een inhoudelijk standpunt over hoe het debat gevoerd mag worden, en telt mee als argument, ook als het niet direct over "stikstof" zelf gaat. Gebruik dan `typology: "other"` en `stance: "unclear"` tenzij een pro/contra-richting t.o.v. het beleid duidelijk is. Een kale roode-lijn-verklaring zonder reden ("afzwakking steunen we niet") blijft ook hier geen argument — de "geen onderbouwing = geen argument"-regel geldt onverkort.
- Eén sprekerbeurt kan 0, 1, of meerdere argumenten bevatten (bv. bij meerdere onderwerpen of tegenargumenten binnen dezelfde beurt).
- Elk genoemd getal, percentage, onderzoek, of feitelijke bewering met een bron ("uit onderzoek van X blijkt...", "volgens het RIVM...") noteer je als een claim, met alleen wat letterlijk gezegd is over de bron — beoordeel nooit of het getal of de bron klopt.
- `typology`: "factual" (feiten, cijfers, beleidsinhoudelijke of bestuurlijke constateringen — bv. een norm, een fractiestandpunt, wie iets wel/niet steunt), "moral" (ethisch/waarden), "economic" (kosten/baten), "legal" (verwijst naar een specifieke wet, regelgeving, of juridische toetsing/procedure), of "other". Gebruik "legal" alleen als het echt om wetgeving/regelgeving/juridische procedure gaat — een bestuurlijke keuze, beleidsnorm (bv. een GVE-norm of bufferzone-afstand), of politieke uitspraak van een bestuurder is meestal "factual" of "other", niet "legal".
- `stance`: "pro" of "contra" volgens de pro/contra-dimensie hierboven (niet t.o.v. het onderwerp "stikstof" in abstracte zin), of "unclear" als het standpunt niet eenduidig is. Kritiek op het huidige/voorgestelde beleid is `contra`, ook als de spreker dat doet door te verwijzen naar een eigen alternatief of eerder gevoerd beleid.

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok eromheen. Formaat:

```
{"arguments": [
  {
    "stance": "pro" | "contra" | "unclear",
    "typology": "factual" | "moral" | "economic" | "legal" | "other",
    "quote_text": "letterlijk citaat uit de brontekst",
    "quote_context": "korte context (optioneel, of null)",
    "claims": [
      {"claim_text": "wat genoemd is", "attributed_source_text": "aangehaalde bron, of null"}
    ]
  }
]}
```

Als er geen argumenten zijn: `{"arguments": []}`.

Brontekst (sprekerbeurt):
"""
Mevrouw Van der Plas (BBB): Dit zijn weer grote woorden van mevrouw Bromet. We weten allemaal dat toen wij hier een coalitie hadden en in een kabinet zaten, de linkerkant van de Kamer, waar ik voor dat moment ook de VVD achter schaar, met heel veel moties en traineren heel veel dingen heeft vertraagd. BBB zit elf maanden in een kabinet. Dan is er een partij die daar de stekker uit trekt; daar hebben we nu het D66-kabinet aan te danken. Vervolgens wordt er van ons verwacht dat we binnen elf maanden alles zouden hebben opgelost. Hadden we er vier jaar gezeten, dan had de tribune hier niet zo vol gezeten met boeren. Ja, misschien met een feestmuts op, omdat we met beleid waren gekomen dat wél perspectief zou bieden. We hebben net buiten gezien dat boeren naar de Kamer zijn gekomen. Er is een manifest voorgelezen door de voorzitter van Agractie. In de tijd dat BBB in het kabinet zat, heeft hier niet één boer gestaan. Toen hingen de vlaggen niet op de kop en stonden de trekkers niet in Den Haag. Ga mij dus geen dingen voorhouden. Wij hebben onze uiterste best gedaan in het kabinet. Als wij er vier jaar hadden gezeten, weet ik zeker dat hier een beleid was uitgerold waardoor boeren hun bestaansrecht behielden en niet een mes in de rug gestoken werden.
"""


=== document 41 (Laura Bromet) ===
Je analyseert één sprekerbeurt uit een Tweede Kamer-debat over het onderwerp "stikstof". Spreker: Laura Bromet (PRO).

Context over de pro/contra-dimensie van dit onderwerp:
Dit debat gaat over het Nederlandse stikstofbeleid: het kabinetsbeleid gericht op het verlagen van stikstofuitstoot (via normen zoals de kritische depositiewaarde/KDW, gebiedsgerichte aanpak, en verplichtende maatregelen voor onder meer de landbouw), bedoeld om aan natuurdoelen en vergunningverlening te voldoen.

PRO = steunt dit beleid (het huidige of voorgestelde kabinetsbeleid), of pleit voor verdergaande/snellere stikstofreductie.
CONTRA = verzet zich tegen dit beleid, pleit voor afzwakking, uitstel, een ander instrument, vrijwilligheid in plaats van verplichting, of een wezenlijk alternatieve aanpak.

Let op: dit is puur een classificatie-hulpmiddel om het debat te ordenen, geen waardeoordeel over welke kant gelijk heeft.

Jouw taak: identificeer elk afzonderlijk politiek argument dat deze spreker inbrengt over "stikstof". Een argument heeft altijd twee delen: een standpunt (pro/contra/onduidelijk t.o.v. de pro/contra-dimensie hierboven) ÉN een reden/onderbouwing die dat standpunt ondersteunt. Beide delen moeten in het citaat zelf aanwezig zijn.

Regels (belangrijk, volg strikt):
- Jij bent geen scheidsrechter. Beoordeel nooit of een argument klopt, terecht is, of overtuigend is. Geef nooit het ene standpunt gelijk boven het andere.
- Citeer letterlijk uit de brontekst (quote_text) — verzin of parafraseer geen tekst.
- **Geen onderbouwing = geen argument.** Een kale stellingname, intentieverklaring, wens, of statement zonder reden is GEEN argument, ook niet als het stellig of politiek geladen klinkt. Voorbeelden van wat je NIET moet extraheren: "Ik strijd hier tot de laatste dag voor de boeren" (intentie, geen reden), "Afzwakking steunen we niet" (kaal standpunt, geen reden), "Dat vinden wij een goed idee" (instemming zonder reden), "Wij vinden het natuurbelang heel erg zwaar wegen" (waardestelling zonder reden). Extraheer dit soort zinnen alleen als de reden er letterlijk bij staat.
- **Eén punt = één argument.** Als de spreker hetzelfde punt in opeenvolgende zinnen verder uitwerkt, aanvult, of herhaalt (bv. een stelling gevolgd door de reden erachter, of twee keer dezelfde kernboodschap in andere woorden binnen dezelfde beurt), voeg dit samen tot één `quote_text` (met de tussenliggende tekst inbegrepen) in plaats van het op te knippen in meerdere argumenten. Knip alleen op naar een nieuw argument als er echt een ander punt, andere reden, of ander standpunt begint.
- Procedurele tekst levert GEEN argumenten op: orde van de vergadering, spreektijd-afspraken, "ik geef het woord aan...", "ik stel voor dat...", dank-/welkomstwoorden, en vergelijkbare voorzitters-chatter. Als de hele sprekerbeurt procedureel is, geef een lege lijst terug.
- Let op het verschil tussen procedurele chatter (hierboven, GEEN argument) en metadiscours (WEL een argument, mits onderbouwd): een uiting over de legitimiteit, reikwijdte, bevoegdheid, of spelregels van het debat zelf — bv. "dit is geen dunne lijn... ik benoem hier de feiten" — is een inhoudelijk standpunt over hoe het debat gevoerd mag worden, en telt mee als argument, ook als het niet direct over "stikstof" zelf gaat. Gebruik dan `typology: "other"` en `stance: "unclear"` tenzij een pro/contra-richting t.o.v. het beleid duidelijk is. Een kale roode-lijn-verklaring zonder reden ("afzwakking steunen we niet") blijft ook hier geen argument — de "geen onderbouwing = geen argument"-regel geldt onverkort.
- Eén sprekerbeurt kan 0, 1, of meerdere argumenten bevatten (bv. bij meerdere onderwerpen of tegenargumenten binnen dezelfde beurt).
- Elk genoemd getal, percentage, onderzoek, of feitelijke bewering met een bron ("uit onderzoek van X blijkt...", "volgens het RIVM...") noteer je als een claim, met alleen wat letterlijk gezegd is over de bron — beoordeel nooit of het getal of de bron klopt.
- `typology`: "factual" (feiten, cijfers, beleidsinhoudelijke of bestuurlijke constateringen — bv. een norm, een fractiestandpunt, wie iets wel/niet steunt), "moral" (ethisch/waarden), "economic" (kosten/baten), "legal" (verwijst naar een specifieke wet, regelgeving, of juridische toetsing/procedure), of "other". Gebruik "legal" alleen als het echt om wetgeving/regelgeving/juridische procedure gaat — een bestuurlijke keuze, beleidsnorm (bv. een GVE-norm of bufferzone-afstand), of politieke uitspraak van een bestuurder is meestal "factual" of "other", niet "legal".
- `stance`: "pro" of "contra" volgens de pro/contra-dimensie hierboven (niet t.o.v. het onderwerp "stikstof" in abstracte zin), of "unclear" als het standpunt niet eenduidig is. Kritiek op het huidige/voorgestelde beleid is `contra`, ook als de spreker dat doet door te verwijzen naar een eigen alternatief of eerder gevoerd beleid.

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok eromheen. Formaat:

```
{"arguments": [
  {
    "stance": "pro" | "contra" | "unclear",
    "typology": "factual" | "moral" | "economic" | "legal" | "other",
    "quote_text": "letterlijk citaat uit de brontekst",
    "quote_context": "korte context (optioneel, of null)",
    "claims": [
      {"claim_text": "wat genoemd is", "attributed_source_text": "aangehaalde bron, of null"}
    ]
  }
]}
```

Als er geen argumenten zijn: `{"arguments": []}`.

Brontekst (sprekerbeurt):
"""
Mevrouw Bromet (PRO): De vergunningverlening voor de bouw van huizen is compleet vastgelopen. De BBB had nota bene een minister voor Volkshuisvesting en de bouw van huizen. Daar is niks van terechtgekomen. Ik snap dat het soms niet lukt om dat wat je vanuit de oppositie roept te verwezenlijken in een kabinet. Maar moet er dan ook niet een beetje de hand in eigen boezem worden gestoken, in plaats van terug te schakelen naar het verhaal van zeven jaar geleden en weer helemaal opnieuw te beginnen?
"""


=== document 42 (Caroline van der Plas) ===
Je analyseert één sprekerbeurt uit een Tweede Kamer-debat over het onderwerp "stikstof". Spreker: Caroline van der Plas (BBB).

Context over de pro/contra-dimensie van dit onderwerp:
Dit debat gaat over het Nederlandse stikstofbeleid: het kabinetsbeleid gericht op het verlagen van stikstofuitstoot (via normen zoals de kritische depositiewaarde/KDW, gebiedsgerichte aanpak, en verplichtende maatregelen voor onder meer de landbouw), bedoeld om aan natuurdoelen en vergunningverlening te voldoen.

PRO = steunt dit beleid (het huidige of voorgestelde kabinetsbeleid), of pleit voor verdergaande/snellere stikstofreductie.
CONTRA = verzet zich tegen dit beleid, pleit voor afzwakking, uitstel, een ander instrument, vrijwilligheid in plaats van verplichting, of een wezenlijk alternatieve aanpak.

Let op: dit is puur een classificatie-hulpmiddel om het debat te ordenen, geen waardeoordeel over welke kant gelijk heeft.

Jouw taak: identificeer elk afzonderlijk politiek argument dat deze spreker inbrengt over "stikstof". Een argument heeft altijd twee delen: een standpunt (pro/contra/onduidelijk t.o.v. de pro/contra-dimensie hierboven) ÉN een reden/onderbouwing die dat standpunt ondersteunt. Beide delen moeten in het citaat zelf aanwezig zijn.

Regels (belangrijk, volg strikt):
- Jij bent geen scheidsrechter. Beoordeel nooit of een argument klopt, terecht is, of overtuigend is. Geef nooit het ene standpunt gelijk boven het andere.
- Citeer letterlijk uit de brontekst (quote_text) — verzin of parafraseer geen tekst.
- **Geen onderbouwing = geen argument.** Een kale stellingname, intentieverklaring, wens, of statement zonder reden is GEEN argument, ook niet als het stellig of politiek geladen klinkt. Voorbeelden van wat je NIET moet extraheren: "Ik strijd hier tot de laatste dag voor de boeren" (intentie, geen reden), "Afzwakking steunen we niet" (kaal standpunt, geen reden), "Dat vinden wij een goed idee" (instemming zonder reden), "Wij vinden het natuurbelang heel erg zwaar wegen" (waardestelling zonder reden). Extraheer dit soort zinnen alleen als de reden er letterlijk bij staat.
- **Eén punt = één argument.** Als de spreker hetzelfde punt in opeenvolgende zinnen verder uitwerkt, aanvult, of herhaalt (bv. een stelling gevolgd door de reden erachter, of twee keer dezelfde kernboodschap in andere woorden binnen dezelfde beurt), voeg dit samen tot één `quote_text` (met de tussenliggende tekst inbegrepen) in plaats van het op te knippen in meerdere argumenten. Knip alleen op naar een nieuw argument als er echt een ander punt, andere reden, of ander standpunt begint.
- Procedurele tekst levert GEEN argumenten op: orde van de vergadering, spreektijd-afspraken, "ik geef het woord aan...", "ik stel voor dat...", dank-/welkomstwoorden, en vergelijkbare voorzitters-chatter. Als de hele sprekerbeurt procedureel is, geef een lege lijst terug.
- Let op het verschil tussen procedurele chatter (hierboven, GEEN argument) en metadiscours (WEL een argument, mits onderbouwd): een uiting over de legitimiteit, reikwijdte, bevoegdheid, of spelregels van het debat zelf — bv. "dit is geen dunne lijn... ik benoem hier de feiten" — is een inhoudelijk standpunt over hoe het debat gevoerd mag worden, en telt mee als argument, ook als het niet direct over "stikstof" zelf gaat. Gebruik dan `typology: "other"` en `stance: "unclear"` tenzij een pro/contra-richting t.o.v. het beleid duidelijk is. Een kale roode-lijn-verklaring zonder reden ("afzwakking steunen we niet") blijft ook hier geen argument — de "geen onderbouwing = geen argument"-regel geldt onverkort.
- Eén sprekerbeurt kan 0, 1, of meerdere argumenten bevatten (bv. bij meerdere onderwerpen of tegenargumenten binnen dezelfde beurt).
- Elk genoemd getal, percentage, onderzoek, of feitelijke bewering met een bron ("uit onderzoek van X blijkt...", "volgens het RIVM...") noteer je als een claim, met alleen wat letterlijk gezegd is over de bron — beoordeel nooit of het getal of de bron klopt.
- `typology`: "factual" (feiten, cijfers, beleidsinhoudelijke of bestuurlijke constateringen — bv. een norm, een fractiestandpunt, wie iets wel/niet steunt), "moral" (ethisch/waarden), "economic" (kosten/baten), "legal" (verwijst naar een specifieke wet, regelgeving, of juridische toetsing/procedure), of "other". Gebruik "legal" alleen als het echt om wetgeving/regelgeving/juridische procedure gaat — een bestuurlijke keuze, beleidsnorm (bv. een GVE-norm of bufferzone-afstand), of politieke uitspraak van een bestuurder is meestal "factual" of "other", niet "legal".
- `stance`: "pro" of "contra" volgens de pro/contra-dimensie hierboven (niet t.o.v. het onderwerp "stikstof" in abstracte zin), of "unclear" als het standpunt niet eenduidig is. Kritiek op het huidige/voorgestelde beleid is `contra`, ook als de spreker dat doet door te verwijzen naar een eigen alternatief of eerder gevoerd beleid.

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok eromheen. Formaat:

```
{"arguments": [
  {
    "stance": "pro" | "contra" | "unclear",
    "typology": "factual" | "moral" | "economic" | "legal" | "other",
    "quote_text": "letterlijk citaat uit de brontekst",
    "quote_context": "korte context (optioneel, of null)",
    "claims": [
      {"claim_text": "wat genoemd is", "attributed_source_text": "aangehaalde bron, of null"}
    ]
  }
]}
```

Als er geen argumenten zijn: `{"arguments": []}`.

Brontekst (sprekerbeurt):
"""
Mevrouw Van der Plas (BBB): Hier wordt altijd gezegd: je mag geen desinformatie verspreiden. Wat mevrouw Bromet hier doet, is puur desinformatie verspreiden. Onze minister van Volkshuisvesting en Ruimtelijke Ordening stond elke week op een bouwplaats om de start van woningen in te luiden. Onze minister van Volkshuisvesting en Ruimtelijke Ordening heeft talloze plannen en wetsvoorstellen naar de Kamer gestuurd om de bouw los te trekken. Ik vind het heel kwalijk dat hier gewoon letterlijk wordt gezegd dat er niets is gebeurd. Dat is totaal niet het geval. De volgende keer dat mevrouw Bromet begint met "u mag geen desinformatie verspreiden", dan ga ik haar hier ook op aanspreken.
"""


=== document 45 (Caroline van der Plas) ===
Je analyseert één sprekerbeurt uit een Tweede Kamer-debat over het onderwerp "stikstof". Spreker: Caroline van der Plas (BBB).

Context over de pro/contra-dimensie van dit onderwerp:
Dit debat gaat over het Nederlandse stikstofbeleid: het kabinetsbeleid gericht op het verlagen van stikstofuitstoot (via normen zoals de kritische depositiewaarde/KDW, gebiedsgerichte aanpak, en verplichtende maatregelen voor onder meer de landbouw), bedoeld om aan natuurdoelen en vergunningverlening te voldoen.

PRO = steunt dit beleid (het huidige of voorgestelde kabinetsbeleid), of pleit voor verdergaande/snellere stikstofreductie.
CONTRA = verzet zich tegen dit beleid, pleit voor afzwakking, uitstel, een ander instrument, vrijwilligheid in plaats van verplichting, of een wezenlijk alternatieve aanpak.

Let op: dit is puur een classificatie-hulpmiddel om het debat te ordenen, geen waardeoordeel over welke kant gelijk heeft.

Jouw taak: identificeer elk afzonderlijk politiek argument dat deze spreker inbrengt over "stikstof". Een argument heeft altijd twee delen: een standpunt (pro/contra/onduidelijk t.o.v. de pro/contra-dimensie hierboven) ÉN een reden/onderbouwing die dat standpunt ondersteunt. Beide delen moeten in het citaat zelf aanwezig zijn.

Regels (belangrijk, volg strikt):
- Jij bent geen scheidsrechter. Beoordeel nooit of een argument klopt, terecht is, of overtuigend is. Geef nooit het ene standpunt gelijk boven het andere.
- Citeer letterlijk uit de brontekst (quote_text) — verzin of parafraseer geen tekst.
- **Geen onderbouwing = geen argument.** Een kale stellingname, intentieverklaring, wens, of statement zonder reden is GEEN argument, ook niet als het stellig of politiek geladen klinkt. Voorbeelden van wat je NIET moet extraheren: "Ik strijd hier tot de laatste dag voor de boeren" (intentie, geen reden), "Afzwakking steunen we niet" (kaal standpunt, geen reden), "Dat vinden wij een goed idee" (instemming zonder reden), "Wij vinden het natuurbelang heel erg zwaar wegen" (waardestelling zonder reden). Extraheer dit soort zinnen alleen als de reden er letterlijk bij staat.
- **Eén punt = één argument.** Als de spreker hetzelfde punt in opeenvolgende zinnen verder uitwerkt, aanvult, of herhaalt (bv. een stelling gevolgd door de reden erachter, of twee keer dezelfde kernboodschap in andere woorden binnen dezelfde beurt), voeg dit samen tot één `quote_text` (met de tussenliggende tekst inbegrepen) in plaats van het op te knippen in meerdere argumenten. Knip alleen op naar een nieuw argument als er echt een ander punt, andere reden, of ander standpunt begint.
- Procedurele tekst levert GEEN argumenten op: orde van de vergadering, spreektijd-afspraken, "ik geef het woord aan...", "ik stel voor dat...", dank-/welkomstwoorden, en vergelijkbare voorzitters-chatter. Als de hele sprekerbeurt procedureel is, geef een lege lijst terug.
- Let op het verschil tussen procedurele chatter (hierboven, GEEN argument) en metadiscours (WEL een argument, mits onderbouwd): een uiting over de legitimiteit, reikwijdte, bevoegdheid, of spelregels van het debat zelf — bv. "dit is geen dunne lijn... ik benoem hier de feiten" — is een inhoudelijk standpunt over hoe het debat gevoerd mag worden, en telt mee als argument, ook als het niet direct over "stikstof" zelf gaat. Gebruik dan `typology: "other"` en `stance: "unclear"` tenzij een pro/contra-richting t.o.v. het beleid duidelijk is. Een kale roode-lijn-verklaring zonder reden ("afzwakking steunen we niet") blijft ook hier geen argument — de "geen onderbouwing = geen argument"-regel geldt onverkort.
- Eén sprekerbeurt kan 0, 1, of meerdere argumenten bevatten (bv. bij meerdere onderwerpen of tegenargumenten binnen dezelfde beurt).
- Elk genoemd getal, percentage, onderzoek, of feitelijke bewering met een bron ("uit onderzoek van X blijkt...", "volgens het RIVM...") noteer je als een claim, met alleen wat letterlijk gezegd is over de bron — beoordeel nooit of het getal of de bron klopt.
- `typology`: "factual" (feiten, cijfers, beleidsinhoudelijke of bestuurlijke constateringen — bv. een norm, een fractiestandpunt, wie iets wel/niet steunt), "moral" (ethisch/waarden), "economic" (kosten/baten), "legal" (verwijst naar een specifieke wet, regelgeving, of juridische toetsing/procedure), of "other". Gebruik "legal" alleen als het echt om wetgeving/regelgeving/juridische procedure gaat — een bestuurlijke keuze, beleidsnorm (bv. een GVE-norm of bufferzone-afstand), of politieke uitspraak van een bestuurder is meestal "factual" of "other", niet "legal".
- `stance`: "pro" of "contra" volgens de pro/contra-dimensie hierboven (niet t.o.v. het onderwerp "stikstof" in abstracte zin), of "unclear" als het standpunt niet eenduidig is. Kritiek op het huidige/voorgestelde beleid is `contra`, ook als de spreker dat doet door te verwijzen naar een eigen alternatief of eerder gevoerd beleid.

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok eromheen. Formaat:

```
{"arguments": [
  {
    "stance": "pro" | "contra" | "unclear",
    "typology": "factual" | "moral" | "economic" | "legal" | "other",
    "quote_text": "letterlijk citaat uit de brontekst",
    "quote_context": "korte context (optioneel, of null)",
    "claims": [
      {"claim_text": "wat genoemd is", "attributed_source_text": "aangehaalde bron, of null"}
    ]
  }
]}
```

Als er geen argumenten zijn: `{"arguments": []}`.

Brontekst (sprekerbeurt):
"""
Mevrouw Van der Plas (BBB): De minister zegt hier: de vergunningverlening komt los. Nou, het is nog maar de vraag of dat gebeurt. Weet je wat er gebeurt hier zo meteen naar aanleiding van deze plannen? Voor duizenden boeren zullen deze plannen gewoon einde bedrijf betekenen. Duizenden boeren zullen gewoon moeten stoppen met hun bedrijf. En dan wordt er gezegd: ja, maar je kunt extensiveren. Ik hoorde de minister bij Sven Kockelmann zeggen: ja, maar je kunt ook biologisch worden. Er zijn talloze biologische boeren die ermee stoppen omdat het niet rendabel is! Dat is een worst voorhouden. Dat is gewoon een worst voorhouden. En dan hebben we 20 miljard. Weet je wat je met 20 miljard kan doen? Daar kun je de eigen bijdrage in de zorg mee verlagen. Daar zou PRO voorstander van moeten zijn. Er is 20 miljard nodig tot 2038 om onze wegen en bruggen te herstellen, te repareren of aan te leggen. Maar de minister zegt: geen geld, geen geld. Nee, maar we gaan wel 20 miljard stoppen in het uitkopen van boeren omdat we dat ene salamandertje en dat ene plantje willen herstellen. We zijn hier in Nederland echt helemaal compleet koekoek!
"""


=== document 50 (Hidde Heutink) ===
Je analyseert één sprekerbeurt uit een Tweede Kamer-debat over het onderwerp "stikstof". Spreker: Hidde Heutink (Groep Markuszower).

Context over de pro/contra-dimensie van dit onderwerp:
Dit debat gaat over het Nederlandse stikstofbeleid: het kabinetsbeleid gericht op het verlagen van stikstofuitstoot (via normen zoals de kritische depositiewaarde/KDW, gebiedsgerichte aanpak, en verplichtende maatregelen voor onder meer de landbouw), bedoeld om aan natuurdoelen en vergunningverlening te voldoen.

PRO = steunt dit beleid (het huidige of voorgestelde kabinetsbeleid), of pleit voor verdergaande/snellere stikstofreductie.
CONTRA = verzet zich tegen dit beleid, pleit voor afzwakking, uitstel, een ander instrument, vrijwilligheid in plaats van verplichting, of een wezenlijk alternatieve aanpak.

Let op: dit is puur een classificatie-hulpmiddel om het debat te ordenen, geen waardeoordeel over welke kant gelijk heeft.

Jouw taak: identificeer elk afzonderlijk politiek argument dat deze spreker inbrengt over "stikstof". Een argument heeft altijd twee delen: een standpunt (pro/contra/onduidelijk t.o.v. de pro/contra-dimensie hierboven) ÉN een reden/onderbouwing die dat standpunt ondersteunt. Beide delen moeten in het citaat zelf aanwezig zijn.

Regels (belangrijk, volg strikt):
- Jij bent geen scheidsrechter. Beoordeel nooit of een argument klopt, terecht is, of overtuigend is. Geef nooit het ene standpunt gelijk boven het andere.
- Citeer letterlijk uit de brontekst (quote_text) — verzin of parafraseer geen tekst.
- **Geen onderbouwing = geen argument.** Een kale stellingname, intentieverklaring, wens, of statement zonder reden is GEEN argument, ook niet als het stellig of politiek geladen klinkt. Voorbeelden van wat je NIET moet extraheren: "Ik strijd hier tot de laatste dag voor de boeren" (intentie, geen reden), "Afzwakking steunen we niet" (kaal standpunt, geen reden), "Dat vinden wij een goed idee" (instemming zonder reden), "Wij vinden het natuurbelang heel erg zwaar wegen" (waardestelling zonder reden). Extraheer dit soort zinnen alleen als de reden er letterlijk bij staat.
- **Eén punt = één argument.** Als de spreker hetzelfde punt in opeenvolgende zinnen verder uitwerkt, aanvult, of herhaalt (bv. een stelling gevolgd door de reden erachter, of twee keer dezelfde kernboodschap in andere woorden binnen dezelfde beurt), voeg dit samen tot één `quote_text` (met de tussenliggende tekst inbegrepen) in plaats van het op te knippen in meerdere argumenten. Knip alleen op naar een nieuw argument als er echt een ander punt, andere reden, of ander standpunt begint.
- Procedurele tekst levert GEEN argumenten op: orde van de vergadering, spreektijd-afspraken, "ik geef het woord aan...", "ik stel voor dat...", dank-/welkomstwoorden, en vergelijkbare voorzitters-chatter. Als de hele sprekerbeurt procedureel is, geef een lege lijst terug.
- Let op het verschil tussen procedurele chatter (hierboven, GEEN argument) en metadiscours (WEL een argument, mits onderbouwd): een uiting over de legitimiteit, reikwijdte, bevoegdheid, of spelregels van het debat zelf — bv. "dit is geen dunne lijn... ik benoem hier de feiten" — is een inhoudelijk standpunt over hoe het debat gevoerd mag worden, en telt mee als argument, ook als het niet direct over "stikstof" zelf gaat. Gebruik dan `typology: "other"` en `stance: "unclear"` tenzij een pro/contra-richting t.o.v. het beleid duidelijk is. Een kale roode-lijn-verklaring zonder reden ("afzwakking steunen we niet") blijft ook hier geen argument — de "geen onderbouwing = geen argument"-regel geldt onverkort.
- Eén sprekerbeurt kan 0, 1, of meerdere argumenten bevatten (bv. bij meerdere onderwerpen of tegenargumenten binnen dezelfde beurt).
- Elk genoemd getal, percentage, onderzoek, of feitelijke bewering met een bron ("uit onderzoek van X blijkt...", "volgens het RIVM...") noteer je als een claim, met alleen wat letterlijk gezegd is over de bron — beoordeel nooit of het getal of de bron klopt.
- `typology`: "factual" (feiten, cijfers, beleidsinhoudelijke of bestuurlijke constateringen — bv. een norm, een fractiestandpunt, wie iets wel/niet steunt), "moral" (ethisch/waarden), "economic" (kosten/baten), "legal" (verwijst naar een specifieke wet, regelgeving, of juridische toetsing/procedure), of "other". Gebruik "legal" alleen als het echt om wetgeving/regelgeving/juridische procedure gaat — een bestuurlijke keuze, beleidsnorm (bv. een GVE-norm of bufferzone-afstand), of politieke uitspraak van een bestuurder is meestal "factual" of "other", niet "legal".
- `stance`: "pro" of "contra" volgens de pro/contra-dimensie hierboven (niet t.o.v. het onderwerp "stikstof" in abstracte zin), of "unclear" als het standpunt niet eenduidig is. Kritiek op het huidige/voorgestelde beleid is `contra`, ook als de spreker dat doet door te verwijzen naar een eigen alternatief of eerder gevoerd beleid.

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok eromheen. Formaat:

```
{"arguments": [
  {
    "stance": "pro" | "contra" | "unclear",
    "typology": "factual" | "moral" | "economic" | "legal" | "other",
    "quote_text": "letterlijk citaat uit de brontekst",
    "quote_context": "korte context (optioneel, of null)",
    "claims": [
      {"claim_text": "wat genoemd is", "attributed_source_text": "aangehaalde bron, of null"}
    ]
  }
]}
```

Als er geen argumenten zijn: `{"arguments": []}`.

Brontekst (sprekerbeurt):
"""
De heer Heutink (Groep Markuszower): Daar kom ik op. Ik moet 'm heel kort inleiden, en dan zie ik af van de derde. PRO zegt nu niks aan dat stikstofplan te willen afzwakken. Het zijn diezelfde provincies die dit vernietigende stikstofplan zo meteen moeten gaan uitvoeren. Mijn vraag aan BBB is: gaat BBB nou, met al haar gedeputeerden in Nederland, samen met de PRO-gedeputeerden, met wie ze dus nauw samenwerken, dit vernietigende stikstofbeleid uitvoeren of gaan ze al die BBB-gedeputeerden terugtrekken?
"""


=== document 51 (Caroline van der Plas) ===
Je analyseert één sprekerbeurt uit een Tweede Kamer-debat over het onderwerp "stikstof". Spreker: Caroline van der Plas (BBB).

Context over de pro/contra-dimensie van dit onderwerp:
Dit debat gaat over het Nederlandse stikstofbeleid: het kabinetsbeleid gericht op het verlagen van stikstofuitstoot (via normen zoals de kritische depositiewaarde/KDW, gebiedsgerichte aanpak, en verplichtende maatregelen voor onder meer de landbouw), bedoeld om aan natuurdoelen en vergunningverlening te voldoen.

PRO = steunt dit beleid (het huidige of voorgestelde kabinetsbeleid), of pleit voor verdergaande/snellere stikstofreductie.
CONTRA = verzet zich tegen dit beleid, pleit voor afzwakking, uitstel, een ander instrument, vrijwilligheid in plaats van verplichting, of een wezenlijk alternatieve aanpak.

Let op: dit is puur een classificatie-hulpmiddel om het debat te ordenen, geen waardeoordeel over welke kant gelijk heeft.

Jouw taak: identificeer elk afzonderlijk politiek argument dat deze spreker inbrengt over "stikstof". Een argument heeft altijd twee delen: een standpunt (pro/contra/onduidelijk t.o.v. de pro/contra-dimensie hierboven) ÉN een reden/onderbouwing die dat standpunt ondersteunt. Beide delen moeten in het citaat zelf aanwezig zijn.

Regels (belangrijk, volg strikt):
- Jij bent geen scheidsrechter. Beoordeel nooit of een argument klopt, terecht is, of overtuigend is. Geef nooit het ene standpunt gelijk boven het andere.
- Citeer letterlijk uit de brontekst (quote_text) — verzin of parafraseer geen tekst.
- **Geen onderbouwing = geen argument.** Een kale stellingname, intentieverklaring, wens, of statement zonder reden is GEEN argument, ook niet als het stellig of politiek geladen klinkt. Voorbeelden van wat je NIET moet extraheren: "Ik strijd hier tot de laatste dag voor de boeren" (intentie, geen reden), "Afzwakking steunen we niet" (kaal standpunt, geen reden), "Dat vinden wij een goed idee" (instemming zonder reden), "Wij vinden het natuurbelang heel erg zwaar wegen" (waardestelling zonder reden). Extraheer dit soort zinnen alleen als de reden er letterlijk bij staat.
- **Eén punt = één argument.** Als de spreker hetzelfde punt in opeenvolgende zinnen verder uitwerkt, aanvult, of herhaalt (bv. een stelling gevolgd door de reden erachter, of twee keer dezelfde kernboodschap in andere woorden binnen dezelfde beurt), voeg dit samen tot één `quote_text` (met de tussenliggende tekst inbegrepen) in plaats van het op te knippen in meerdere argumenten. Knip alleen op naar een nieuw argument als er echt een ander punt, andere reden, of ander standpunt begint.
- Procedurele tekst levert GEEN argumenten op: orde van de vergadering, spreektijd-afspraken, "ik geef het woord aan...", "ik stel voor dat...", dank-/welkomstwoorden, en vergelijkbare voorzitters-chatter. Als de hele sprekerbeurt procedureel is, geef een lege lijst terug.
- Let op het verschil tussen procedurele chatter (hierboven, GEEN argument) en metadiscours (WEL een argument, mits onderbouwd): een uiting over de legitimiteit, reikwijdte, bevoegdheid, of spelregels van het debat zelf — bv. "dit is geen dunne lijn... ik benoem hier de feiten" — is een inhoudelijk standpunt over hoe het debat gevoerd mag worden, en telt mee als argument, ook als het niet direct over "stikstof" zelf gaat. Gebruik dan `typology: "other"` en `stance: "unclear"` tenzij een pro/contra-richting t.o.v. het beleid duidelijk is. Een kale roode-lijn-verklaring zonder reden ("afzwakking steunen we niet") blijft ook hier geen argument — de "geen onderbouwing = geen argument"-regel geldt onverkort.
- Eén sprekerbeurt kan 0, 1, of meerdere argumenten bevatten (bv. bij meerdere onderwerpen of tegenargumenten binnen dezelfde beurt).
- Elk genoemd getal, percentage, onderzoek, of feitelijke bewering met een bron ("uit onderzoek van X blijkt...", "volgens het RIVM...") noteer je als een claim, met alleen wat letterlijk gezegd is over de bron — beoordeel nooit of het getal of de bron klopt.
- `typology`: "factual" (feiten, cijfers, beleidsinhoudelijke of bestuurlijke constateringen — bv. een norm, een fractiestandpunt, wie iets wel/niet steunt), "moral" (ethisch/waarden), "economic" (kosten/baten), "legal" (verwijst naar een specifieke wet, regelgeving, of juridische toetsing/procedure), of "other". Gebruik "legal" alleen als het echt om wetgeving/regelgeving/juridische procedure gaat — een bestuurlijke keuze, beleidsnorm (bv. een GVE-norm of bufferzone-afstand), of politieke uitspraak van een bestuurder is meestal "factual" of "other", niet "legal".
- `stance`: "pro" of "contra" volgens de pro/contra-dimensie hierboven (niet t.o.v. het onderwerp "stikstof" in abstracte zin), of "unclear" als het standpunt niet eenduidig is. Kritiek op het huidige/voorgestelde beleid is `contra`, ook als de spreker dat doet door te verwijzen naar een eigen alternatief of eerder gevoerd beleid.

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok eromheen. Formaat:

```
{"arguments": [
  {
    "stance": "pro" | "contra" | "unclear",
    "typology": "factual" | "moral" | "economic" | "legal" | "other",
    "quote_text": "letterlijk citaat uit de brontekst",
    "quote_context": "korte context (optioneel, of null)",
    "claims": [
      {"claim_text": "wat genoemd is", "attributed_source_text": "aangehaalde bron, of null"}
    ]
  }
]}
```

Als er geen argumenten zijn: `{"arguments": []}`.

Brontekst (sprekerbeurt):
"""
Mevrouw Van der Plas (BBB): Eén ding: ik ben natuurlijk niet betrokken bij collegeonderhandelingen in de provincie. Punt twee. Misschien kan de heer Heutink zich ook de vraag stellen: wat was er gebeurd als BBB niet in een college had gezeten en het een volledig links college van Gedeputeerde Staten was geweest? Nou, dan waren de rapen nog gaarder geweest dan ze nu zijn met de kabinetsbrief van deze minister. Wij hebben ook in de provincies gewoon heel erg veel weten tegen te houden. Dat is niet altijd zichtbaar. Dat staat niet altijd als headline in de krant, want het is natuurlijk niet zo heel welgevallig om te zeggen: dit gaat goed. Kranten zien meestal alles wat fout gaat en heel veel mensen geloven ook nog alles wat er staat. Wij hebben dus ook heel veel tegengehouden. Kijk bijvoorbeeld naar de windturbines in Overijssel. Het kan zijn dat er plannen zijn, maar sinds BBB in het college zit, is er in Overijssel geen windturbine bij gekomen. Dat moeten wij als BBB veel beter uitdragen. Nogmaals, ga je afvragen wat de toekomst is voor boeren in Nederland als er geen BBB meer is.
"""


=== document 56 (Caroline van der Plas) ===
Je analyseert één sprekerbeurt uit een Tweede Kamer-debat over het onderwerp "stikstof". Spreker: Caroline van der Plas (BBB).

Context over de pro/contra-dimensie van dit onderwerp:
Dit debat gaat over het Nederlandse stikstofbeleid: het kabinetsbeleid gericht op het verlagen van stikstofuitstoot (via normen zoals de kritische depositiewaarde/KDW, gebiedsgerichte aanpak, en verplichtende maatregelen voor onder meer de landbouw), bedoeld om aan natuurdoelen en vergunningverlening te voldoen.

PRO = steunt dit beleid (het huidige of voorgestelde kabinetsbeleid), of pleit voor verdergaande/snellere stikstofreductie.
CONTRA = verzet zich tegen dit beleid, pleit voor afzwakking, uitstel, een ander instrument, vrijwilligheid in plaats van verplichting, of een wezenlijk alternatieve aanpak.

Let op: dit is puur een classificatie-hulpmiddel om het debat te ordenen, geen waardeoordeel over welke kant gelijk heeft.

Jouw taak: identificeer elk afzonderlijk politiek argument dat deze spreker inbrengt over "stikstof". Een argument heeft altijd twee delen: een standpunt (pro/contra/onduidelijk t.o.v. de pro/contra-dimensie hierboven) ÉN een reden/onderbouwing die dat standpunt ondersteunt. Beide delen moeten in het citaat zelf aanwezig zijn.

Regels (belangrijk, volg strikt):
- Jij bent geen scheidsrechter. Beoordeel nooit of een argument klopt, terecht is, of overtuigend is. Geef nooit het ene standpunt gelijk boven het andere.
- Citeer letterlijk uit de brontekst (quote_text) — verzin of parafraseer geen tekst.
- **Geen onderbouwing = geen argument.** Een kale stellingname, intentieverklaring, wens, of statement zonder reden is GEEN argument, ook niet als het stellig of politiek geladen klinkt. Voorbeelden van wat je NIET moet extraheren: "Ik strijd hier tot de laatste dag voor de boeren" (intentie, geen reden), "Afzwakking steunen we niet" (kaal standpunt, geen reden), "Dat vinden wij een goed idee" (instemming zonder reden), "Wij vinden het natuurbelang heel erg zwaar wegen" (waardestelling zonder reden). Extraheer dit soort zinnen alleen als de reden er letterlijk bij staat.
- **Eén punt = één argument.** Als de spreker hetzelfde punt in opeenvolgende zinnen verder uitwerkt, aanvult, of herhaalt (bv. een stelling gevolgd door de reden erachter, of twee keer dezelfde kernboodschap in andere woorden binnen dezelfde beurt), voeg dit samen tot één `quote_text` (met de tussenliggende tekst inbegrepen) in plaats van het op te knippen in meerdere argumenten. Knip alleen op naar een nieuw argument als er echt een ander punt, andere reden, of ander standpunt begint.
- Procedurele tekst levert GEEN argumenten op: orde van de vergadering, spreektijd-afspraken, "ik geef het woord aan...", "ik stel voor dat...", dank-/welkomstwoorden, en vergelijkbare voorzitters-chatter. Als de hele sprekerbeurt procedureel is, geef een lege lijst terug.
- Let op het verschil tussen procedurele chatter (hierboven, GEEN argument) en metadiscours (WEL een argument, mits onderbouwd): een uiting over de legitimiteit, reikwijdte, bevoegdheid, of spelregels van het debat zelf — bv. "dit is geen dunne lijn... ik benoem hier de feiten" — is een inhoudelijk standpunt over hoe het debat gevoerd mag worden, en telt mee als argument, ook als het niet direct over "stikstof" zelf gaat. Gebruik dan `typology: "other"` en `stance: "unclear"` tenzij een pro/contra-richting t.o.v. het beleid duidelijk is. Een kale roode-lijn-verklaring zonder reden ("afzwakking steunen we niet") blijft ook hier geen argument — de "geen onderbouwing = geen argument"-regel geldt onverkort.
- Eén sprekerbeurt kan 0, 1, of meerdere argumenten bevatten (bv. bij meerdere onderwerpen of tegenargumenten binnen dezelfde beurt).
- Elk genoemd getal, percentage, onderzoek, of feitelijke bewering met een bron ("uit onderzoek van X blijkt...", "volgens het RIVM...") noteer je als een claim, met alleen wat letterlijk gezegd is over de bron — beoordeel nooit of het getal of de bron klopt.
- `typology`: "factual" (feiten, cijfers, beleidsinhoudelijke of bestuurlijke constateringen — bv. een norm, een fractiestandpunt, wie iets wel/niet steunt), "moral" (ethisch/waarden), "economic" (kosten/baten), "legal" (verwijst naar een specifieke wet, regelgeving, of juridische toetsing/procedure), of "other". Gebruik "legal" alleen als het echt om wetgeving/regelgeving/juridische procedure gaat — een bestuurlijke keuze, beleidsnorm (bv. een GVE-norm of bufferzone-afstand), of politieke uitspraak van een bestuurder is meestal "factual" of "other", niet "legal".
- `stance`: "pro" of "contra" volgens de pro/contra-dimensie hierboven (niet t.o.v. het onderwerp "stikstof" in abstracte zin), of "unclear" als het standpunt niet eenduidig is. Kritiek op het huidige/voorgestelde beleid is `contra`, ook als de spreker dat doet door te verwijzen naar een eigen alternatief of eerder gevoerd beleid.

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok eromheen. Formaat:

```
{"arguments": [
  {
    "stance": "pro" | "contra" | "unclear",
    "typology": "factual" | "moral" | "economic" | "legal" | "other",
    "quote_text": "letterlijk citaat uit de brontekst",
    "quote_context": "korte context (optioneel, of null)",
    "claims": [
      {"claim_text": "wat genoemd is", "attributed_source_text": "aangehaalde bron, of null"}
    ]
  }
]}
```

Als er geen argumenten zijn: `{"arguments": []}`.

Brontekst (sprekerbeurt):
"""
Mevrouw Van der Plas (BBB): Dat is natuurlijk onzin; dat weet de heer Heutink heel goed. Er zijn inmiddels al een aantal provincies waar de BBB-gedeputeerden ronduit hebben gezegd dat ze dit beleid van deze minister niet steunen. Als de heer Heutink even wat kranten had gelezen van gisteren en vandaag, dan zou hij dat hebben geweten. Hier zomaar even zeggen: ik constateer dat de BBB gedeputeerden niet gaat terugtrekken … Nogmaals, lees even de kranten. Daarin staat gewoon duidelijk dat er provincies zijn — ik noem Friesland, Gelderland, Zuid-Holland — die zeggen: dit gaan we gewoon niet doen.
"""


=== document 101 (Caroline van der Plas) ===
Je analyseert één sprekerbeurt uit een Tweede Kamer-debat over het onderwerp "stikstof". Spreker: Caroline van der Plas (BBB).

Context over de pro/contra-dimensie van dit onderwerp:
Dit debat gaat over het Nederlandse stikstofbeleid: het kabinetsbeleid gericht op het verlagen van stikstofuitstoot (via normen zoals de kritische depositiewaarde/KDW, gebiedsgerichte aanpak, en verplichtende maatregelen voor onder meer de landbouw), bedoeld om aan natuurdoelen en vergunningverlening te voldoen.

PRO = steunt dit beleid (het huidige of voorgestelde kabinetsbeleid), of pleit voor verdergaande/snellere stikstofreductie.
CONTRA = verzet zich tegen dit beleid, pleit voor afzwakking, uitstel, een ander instrument, vrijwilligheid in plaats van verplichting, of een wezenlijk alternatieve aanpak.

Let op: dit is puur een classificatie-hulpmiddel om het debat te ordenen, geen waardeoordeel over welke kant gelijk heeft.

Jouw taak: identificeer elk afzonderlijk politiek argument dat deze spreker inbrengt over "stikstof". Een argument heeft altijd twee delen: een standpunt (pro/contra/onduidelijk t.o.v. de pro/contra-dimensie hierboven) ÉN een reden/onderbouwing die dat standpunt ondersteunt. Beide delen moeten in het citaat zelf aanwezig zijn.

Regels (belangrijk, volg strikt):
- Jij bent geen scheidsrechter. Beoordeel nooit of een argument klopt, terecht is, of overtuigend is. Geef nooit het ene standpunt gelijk boven het andere.
- Citeer letterlijk uit de brontekst (quote_text) — verzin of parafraseer geen tekst.
- **Geen onderbouwing = geen argument.** Een kale stellingname, intentieverklaring, wens, of statement zonder reden is GEEN argument, ook niet als het stellig of politiek geladen klinkt. Voorbeelden van wat je NIET moet extraheren: "Ik strijd hier tot de laatste dag voor de boeren" (intentie, geen reden), "Afzwakking steunen we niet" (kaal standpunt, geen reden), "Dat vinden wij een goed idee" (instemming zonder reden), "Wij vinden het natuurbelang heel erg zwaar wegen" (waardestelling zonder reden). Extraheer dit soort zinnen alleen als de reden er letterlijk bij staat.
- **Eén punt = één argument.** Als de spreker hetzelfde punt in opeenvolgende zinnen verder uitwerkt, aanvult, of herhaalt (bv. een stelling gevolgd door de reden erachter, of twee keer dezelfde kernboodschap in andere woorden binnen dezelfde beurt), voeg dit samen tot één `quote_text` (met de tussenliggende tekst inbegrepen) in plaats van het op te knippen in meerdere argumenten. Knip alleen op naar een nieuw argument als er echt een ander punt, andere reden, of ander standpunt begint.
- Procedurele tekst levert GEEN argumenten op: orde van de vergadering, spreektijd-afspraken, "ik geef het woord aan...", "ik stel voor dat...", dank-/welkomstwoorden, en vergelijkbare voorzitters-chatter. Als de hele sprekerbeurt procedureel is, geef een lege lijst terug.
- Let op het verschil tussen procedurele chatter (hierboven, GEEN argument) en metadiscours (WEL een argument, mits onderbouwd): een uiting over de legitimiteit, reikwijdte, bevoegdheid, of spelregels van het debat zelf — bv. "dit is geen dunne lijn... ik benoem hier de feiten" — is een inhoudelijk standpunt over hoe het debat gevoerd mag worden, en telt mee als argument, ook als het niet direct over "stikstof" zelf gaat. Gebruik dan `typology: "other"` en `stance: "unclear"` tenzij een pro/contra-richting t.o.v. het beleid duidelijk is. Een kale roode-lijn-verklaring zonder reden ("afzwakking steunen we niet") blijft ook hier geen argument — de "geen onderbouwing = geen argument"-regel geldt onverkort.
- Eén sprekerbeurt kan 0, 1, of meerdere argumenten bevatten (bv. bij meerdere onderwerpen of tegenargumenten binnen dezelfde beurt).
- Elk genoemd getal, percentage, onderzoek, of feitelijke bewering met een bron ("uit onderzoek van X blijkt...", "volgens het RIVM...") noteer je als een claim, met alleen wat letterlijk gezegd is over de bron — beoordeel nooit of het getal of de bron klopt.
- `typology`: "factual" (feiten, cijfers, beleidsinhoudelijke of bestuurlijke constateringen — bv. een norm, een fractiestandpunt, wie iets wel/niet steunt), "moral" (ethisch/waarden), "economic" (kosten/baten), "legal" (verwijst naar een specifieke wet, regelgeving, of juridische toetsing/procedure), of "other". Gebruik "legal" alleen als het echt om wetgeving/regelgeving/juridische procedure gaat — een bestuurlijke keuze, beleidsnorm (bv. een GVE-norm of bufferzone-afstand), of politieke uitspraak van een bestuurder is meestal "factual" of "other", niet "legal".
- `stance`: "pro" of "contra" volgens de pro/contra-dimensie hierboven (niet t.o.v. het onderwerp "stikstof" in abstracte zin), of "unclear" als het standpunt niet eenduidig is. Kritiek op het huidige/voorgestelde beleid is `contra`, ook als de spreker dat doet door te verwijzen naar een eigen alternatief of eerder gevoerd beleid.

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok eromheen. Formaat:

```
{"arguments": [
  {
    "stance": "pro" | "contra" | "unclear",
    "typology": "factual" | "moral" | "economic" | "legal" | "other",
    "quote_text": "letterlijk citaat uit de brontekst",
    "quote_context": "korte context (optioneel, of null)",
    "claims": [
      {"claim_text": "wat genoemd is", "attributed_source_text": "aangehaalde bron, of null"}
    ]
  }
]}
```

Als er geen argumenten zijn: `{"arguments": []}`.

Brontekst (sprekerbeurt):
"""
Mevrouw Van der Plas (BBB): Ik strijd hier tot de laatste dag om desastreus beleid voor onze boeren en het platteland tegen te houden. Dat zal ik tot mijn laatste snik doen.
"""


=== document 107 (Caroline van der Plas) ===
Je analyseert één sprekerbeurt uit een Tweede Kamer-debat over het onderwerp "stikstof". Spreker: Caroline van der Plas (BBB).

Context over de pro/contra-dimensie van dit onderwerp:
Dit debat gaat over het Nederlandse stikstofbeleid: het kabinetsbeleid gericht op het verlagen van stikstofuitstoot (via normen zoals de kritische depositiewaarde/KDW, gebiedsgerichte aanpak, en verplichtende maatregelen voor onder meer de landbouw), bedoeld om aan natuurdoelen en vergunningverlening te voldoen.

PRO = steunt dit beleid (het huidige of voorgestelde kabinetsbeleid), of pleit voor verdergaande/snellere stikstofreductie.
CONTRA = verzet zich tegen dit beleid, pleit voor afzwakking, uitstel, een ander instrument, vrijwilligheid in plaats van verplichting, of een wezenlijk alternatieve aanpak.

Let op: dit is puur een classificatie-hulpmiddel om het debat te ordenen, geen waardeoordeel over welke kant gelijk heeft.

Jouw taak: identificeer elk afzonderlijk politiek argument dat deze spreker inbrengt over "stikstof". Een argument heeft altijd twee delen: een standpunt (pro/contra/onduidelijk t.o.v. de pro/contra-dimensie hierboven) ÉN een reden/onderbouwing die dat standpunt ondersteunt. Beide delen moeten in het citaat zelf aanwezig zijn.

Regels (belangrijk, volg strikt):
- Jij bent geen scheidsrechter. Beoordeel nooit of een argument klopt, terecht is, of overtuigend is. Geef nooit het ene standpunt gelijk boven het andere.
- Citeer letterlijk uit de brontekst (quote_text) — verzin of parafraseer geen tekst.
- **Geen onderbouwing = geen argument.** Een kale stellingname, intentieverklaring, wens, of statement zonder reden is GEEN argument, ook niet als het stellig of politiek geladen klinkt. Voorbeelden van wat je NIET moet extraheren: "Ik strijd hier tot de laatste dag voor de boeren" (intentie, geen reden), "Afzwakking steunen we niet" (kaal standpunt, geen reden), "Dat vinden wij een goed idee" (instemming zonder reden), "Wij vinden het natuurbelang heel erg zwaar wegen" (waardestelling zonder reden). Extraheer dit soort zinnen alleen als de reden er letterlijk bij staat.
- **Eén punt = één argument.** Als de spreker hetzelfde punt in opeenvolgende zinnen verder uitwerkt, aanvult, of herhaalt (bv. een stelling gevolgd door de reden erachter, of twee keer dezelfde kernboodschap in andere woorden binnen dezelfde beurt), voeg dit samen tot één `quote_text` (met de tussenliggende tekst inbegrepen) in plaats van het op te knippen in meerdere argumenten. Knip alleen op naar een nieuw argument als er echt een ander punt, andere reden, of ander standpunt begint.
- Procedurele tekst levert GEEN argumenten op: orde van de vergadering, spreektijd-afspraken, "ik geef het woord aan...", "ik stel voor dat...", dank-/welkomstwoorden, en vergelijkbare voorzitters-chatter. Als de hele sprekerbeurt procedureel is, geef een lege lijst terug.
- Let op het verschil tussen procedurele chatter (hierboven, GEEN argument) en metadiscours (WEL een argument, mits onderbouwd): een uiting over de legitimiteit, reikwijdte, bevoegdheid, of spelregels van het debat zelf — bv. "dit is geen dunne lijn... ik benoem hier de feiten" — is een inhoudelijk standpunt over hoe het debat gevoerd mag worden, en telt mee als argument, ook als het niet direct over "stikstof" zelf gaat. Gebruik dan `typology: "other"` en `stance: "unclear"` tenzij een pro/contra-richting t.o.v. het beleid duidelijk is. Een kale roode-lijn-verklaring zonder reden ("afzwakking steunen we niet") blijft ook hier geen argument — de "geen onderbouwing = geen argument"-regel geldt onverkort.
- Eén sprekerbeurt kan 0, 1, of meerdere argumenten bevatten (bv. bij meerdere onderwerpen of tegenargumenten binnen dezelfde beurt).
- Elk genoemd getal, percentage, onderzoek, of feitelijke bewering met een bron ("uit onderzoek van X blijkt...", "volgens het RIVM...") noteer je als een claim, met alleen wat letterlijk gezegd is over de bron — beoordeel nooit of het getal of de bron klopt.
- `typology`: "factual" (feiten, cijfers, beleidsinhoudelijke of bestuurlijke constateringen — bv. een norm, een fractiestandpunt, wie iets wel/niet steunt), "moral" (ethisch/waarden), "economic" (kosten/baten), "legal" (verwijst naar een specifieke wet, regelgeving, of juridische toetsing/procedure), of "other". Gebruik "legal" alleen als het echt om wetgeving/regelgeving/juridische procedure gaat — een bestuurlijke keuze, beleidsnorm (bv. een GVE-norm of bufferzone-afstand), of politieke uitspraak van een bestuurder is meestal "factual" of "other", niet "legal".
- `stance`: "pro" of "contra" volgens de pro/contra-dimensie hierboven (niet t.o.v. het onderwerp "stikstof" in abstracte zin), of "unclear" als het standpunt niet eenduidig is. Kritiek op het huidige/voorgestelde beleid is `contra`, ook als de spreker dat doet door te verwijzen naar een eigen alternatief of eerder gevoerd beleid.

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok eromheen. Formaat:

```
{"arguments": [
  {
    "stance": "pro" | "contra" | "unclear",
    "typology": "factual" | "moral" | "economic" | "legal" | "other",
    "quote_text": "letterlijk citaat uit de brontekst",
    "quote_context": "korte context (optioneel, of null)",
    "claims": [
      {"claim_text": "wat genoemd is", "attributed_source_text": "aangehaalde bron, of null"}
    ]
  }
]}
```

Als er geen argumenten zijn: `{"arguments": []}`.

Brontekst (sprekerbeurt):
"""
Mevrouw Van der Plas (BBB): Dat heeft ook te maken met het feit dat de heer Ergin niet veel landbouwdebatten heeft bijgewoond. Wat er nu op tafel ligt, is wezenlijk anders dan wat wij hebben voorgesteld. De grondgebondenheid, de koeien per hectare, dat zat er bij ons helemaal niet in. Een bufferzone van een kilometer zat er bij ons niet in. Die komt rondom een heel natuurgebied. Nederland heeft 162 natuurgebieden en is een postzegeltje als land. Dat betekent dat straks vrijwel heel Nederland op slot komt te staan. Dat doen wij niet, hè. Dat doet deze minister. De afroming van dierrechten — ik ga nu misschien een beetje de techniek in — hebben wij er afgehaald. Die komt gewoon weer terug. De gedwongen onteigening was er bij ons uit. Die komt gewoon weer terug. De gedwongen uitkoop was er bij ons uit. Die komt gewoon weer terug. Waarom denkt de heer Ergin dat in de tijd dat BBB in het kabinet heeft gezeten er nul boeren stonden te protesteren voor het Tweede Kamergebouw, er nul trekkers in Den Haag stonden en de vlag niet op de kop hing? Dat kwam omdat boeren natuurlijk kritisch waren op ons beleid — dat mag — maar ze nu ook wel zien dat het helemaal nog niet zo gek was. Als we die vier jaar vol hadden kunnen maken, hadden we nog veel meer kunnen doen. Er stond nog veel meer in de steigers, op het gebied van vergunningverlening en over een hele stelselwijziging. Maar die tijd hebben we niet gehad, want op 29 oktober waren er verkiezingen en toen koos half Nederland voor breed lachende mensen met fatsoen en Nederlandse vlaggen op de achtergrond. Die zagen er allemaal zo leuk uit. Daar hebben we nu dit kabinet aan te danken.
"""


=== document 116 (Caroline van der Plas) ===
Je analyseert één sprekerbeurt uit een Tweede Kamer-debat over het onderwerp "stikstof". Spreker: Caroline van der Plas (BBB).

Context over de pro/contra-dimensie van dit onderwerp:
Dit debat gaat over het Nederlandse stikstofbeleid: het kabinetsbeleid gericht op het verlagen van stikstofuitstoot (via normen zoals de kritische depositiewaarde/KDW, gebiedsgerichte aanpak, en verplichtende maatregelen voor onder meer de landbouw), bedoeld om aan natuurdoelen en vergunningverlening te voldoen.

PRO = steunt dit beleid (het huidige of voorgestelde kabinetsbeleid), of pleit voor verdergaande/snellere stikstofreductie.
CONTRA = verzet zich tegen dit beleid, pleit voor afzwakking, uitstel, een ander instrument, vrijwilligheid in plaats van verplichting, of een wezenlijk alternatieve aanpak.

Let op: dit is puur een classificatie-hulpmiddel om het debat te ordenen, geen waardeoordeel over welke kant gelijk heeft.

Jouw taak: identificeer elk afzonderlijk politiek argument dat deze spreker inbrengt over "stikstof". Een argument heeft altijd twee delen: een standpunt (pro/contra/onduidelijk t.o.v. de pro/contra-dimensie hierboven) ÉN een reden/onderbouwing die dat standpunt ondersteunt. Beide delen moeten in het citaat zelf aanwezig zijn.

Regels (belangrijk, volg strikt):
- Jij bent geen scheidsrechter. Beoordeel nooit of een argument klopt, terecht is, of overtuigend is. Geef nooit het ene standpunt gelijk boven het andere.
- Citeer letterlijk uit de brontekst (quote_text) — verzin of parafraseer geen tekst.
- **Geen onderbouwing = geen argument.** Een kale stellingname, intentieverklaring, wens, of statement zonder reden is GEEN argument, ook niet als het stellig of politiek geladen klinkt. Voorbeelden van wat je NIET moet extraheren: "Ik strijd hier tot de laatste dag voor de boeren" (intentie, geen reden), "Afzwakking steunen we niet" (kaal standpunt, geen reden), "Dat vinden wij een goed idee" (instemming zonder reden), "Wij vinden het natuurbelang heel erg zwaar wegen" (waardestelling zonder reden). Extraheer dit soort zinnen alleen als de reden er letterlijk bij staat.
- **Eén punt = één argument.** Als de spreker hetzelfde punt in opeenvolgende zinnen verder uitwerkt, aanvult, of herhaalt (bv. een stelling gevolgd door de reden erachter, of twee keer dezelfde kernboodschap in andere woorden binnen dezelfde beurt), voeg dit samen tot één `quote_text` (met de tussenliggende tekst inbegrepen) in plaats van het op te knippen in meerdere argumenten. Knip alleen op naar een nieuw argument als er echt een ander punt, andere reden, of ander standpunt begint.
- Procedurele tekst levert GEEN argumenten op: orde van de vergadering, spreektijd-afspraken, "ik geef het woord aan...", "ik stel voor dat...", dank-/welkomstwoorden, en vergelijkbare voorzitters-chatter. Als de hele sprekerbeurt procedureel is, geef een lege lijst terug.
- Let op het verschil tussen procedurele chatter (hierboven, GEEN argument) en metadiscours (WEL een argument, mits onderbouwd): een uiting over de legitimiteit, reikwijdte, bevoegdheid, of spelregels van het debat zelf — bv. "dit is geen dunne lijn... ik benoem hier de feiten" — is een inhoudelijk standpunt over hoe het debat gevoerd mag worden, en telt mee als argument, ook als het niet direct over "stikstof" zelf gaat. Gebruik dan `typology: "other"` en `stance: "unclear"` tenzij een pro/contra-richting t.o.v. het beleid duidelijk is. Een kale roode-lijn-verklaring zonder reden ("afzwakking steunen we niet") blijft ook hier geen argument — de "geen onderbouwing = geen argument"-regel geldt onverkort.
- Eén sprekerbeurt kan 0, 1, of meerdere argumenten bevatten (bv. bij meerdere onderwerpen of tegenargumenten binnen dezelfde beurt).
- Elk genoemd getal, percentage, onderzoek, of feitelijke bewering met een bron ("uit onderzoek van X blijkt...", "volgens het RIVM...") noteer je als een claim, met alleen wat letterlijk gezegd is over de bron — beoordeel nooit of het getal of de bron klopt.
- `typology`: "factual" (feiten, cijfers, beleidsinhoudelijke of bestuurlijke constateringen — bv. een norm, een fractiestandpunt, wie iets wel/niet steunt), "moral" (ethisch/waarden), "economic" (kosten/baten), "legal" (verwijst naar een specifieke wet, regelgeving, of juridische toetsing/procedure), of "other". Gebruik "legal" alleen als het echt om wetgeving/regelgeving/juridische procedure gaat — een bestuurlijke keuze, beleidsnorm (bv. een GVE-norm of bufferzone-afstand), of politieke uitspraak van een bestuurder is meestal "factual" of "other", niet "legal".
- `stance`: "pro" of "contra" volgens de pro/contra-dimensie hierboven (niet t.o.v. het onderwerp "stikstof" in abstracte zin), of "unclear" als het standpunt niet eenduidig is. Kritiek op het huidige/voorgestelde beleid is `contra`, ook als de spreker dat doet door te verwijzen naar een eigen alternatief of eerder gevoerd beleid.

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok eromheen. Formaat:

```
{"arguments": [
  {
    "stance": "pro" | "contra" | "unclear",
    "typology": "factual" | "moral" | "economic" | "legal" | "other",
    "quote_text": "letterlijk citaat uit de brontekst",
    "quote_context": "korte context (optioneel, of null)",
    "claims": [
      {"claim_text": "wat genoemd is", "attributed_source_text": "aangehaalde bron, of null"}
    ]
  }
]}
```

Als er geen argumenten zijn: `{"arguments": []}`.

Brontekst (sprekerbeurt):
"""
Mevrouw Van der Plas (BBB): Ik weet niet hoeveel duidelijker ik nog moet zijn. Volgens mij ben ik in mijn inbreng hartstikke duidelijk geweest. Maar ik zit hier niet voor de minister en de staatssecretaris. Ik zit hier voor deze mensen. Ik zit hier voor mensen in het land. Ik ben een volksvertegenwoordiger. Dat is waarom ik hier zit. Ik laat mensen niet kapotmaken op basis van slecht beleid, op basis van wetgeving waarvan al lang is gewaarschuwd dat het een wurgende wetgeving is. Dat ga ik gewoon niet doen. Ik ga hier geen technische discussies voeren over wat wel of niet. Ik ga deze mensen niet laten zakken.
"""


=== document 122 (Laura Bromet) ===
Je analyseert één sprekerbeurt uit een Tweede Kamer-debat over het onderwerp "stikstof". Spreker: Laura Bromet (PRO).

Context over de pro/contra-dimensie van dit onderwerp:
Dit debat gaat over het Nederlandse stikstofbeleid: het kabinetsbeleid gericht op het verlagen van stikstofuitstoot (via normen zoals de kritische depositiewaarde/KDW, gebiedsgerichte aanpak, en verplichtende maatregelen voor onder meer de landbouw), bedoeld om aan natuurdoelen en vergunningverlening te voldoen.

PRO = steunt dit beleid (het huidige of voorgestelde kabinetsbeleid), of pleit voor verdergaande/snellere stikstofreductie.
CONTRA = verzet zich tegen dit beleid, pleit voor afzwakking, uitstel, een ander instrument, vrijwilligheid in plaats van verplichting, of een wezenlijk alternatieve aanpak.

Let op: dit is puur een classificatie-hulpmiddel om het debat te ordenen, geen waardeoordeel over welke kant gelijk heeft.

Jouw taak: identificeer elk afzonderlijk politiek argument dat deze spreker inbrengt over "stikstof". Een argument heeft altijd twee delen: een standpunt (pro/contra/onduidelijk t.o.v. de pro/contra-dimensie hierboven) ÉN een reden/onderbouwing die dat standpunt ondersteunt. Beide delen moeten in het citaat zelf aanwezig zijn.

Regels (belangrijk, volg strikt):
- Jij bent geen scheidsrechter. Beoordeel nooit of een argument klopt, terecht is, of overtuigend is. Geef nooit het ene standpunt gelijk boven het andere.
- Citeer letterlijk uit de brontekst (quote_text) — verzin of parafraseer geen tekst.
- **Geen onderbouwing = geen argument.** Een kale stellingname, intentieverklaring, wens, of statement zonder reden is GEEN argument, ook niet als het stellig of politiek geladen klinkt. Voorbeelden van wat je NIET moet extraheren: "Ik strijd hier tot de laatste dag voor de boeren" (intentie, geen reden), "Afzwakking steunen we niet" (kaal standpunt, geen reden), "Dat vinden wij een goed idee" (instemming zonder reden), "Wij vinden het natuurbelang heel erg zwaar wegen" (waardestelling zonder reden). Extraheer dit soort zinnen alleen als de reden er letterlijk bij staat.
- **Eén punt = één argument.** Als de spreker hetzelfde punt in opeenvolgende zinnen verder uitwerkt, aanvult, of herhaalt (bv. een stelling gevolgd door de reden erachter, of twee keer dezelfde kernboodschap in andere woorden binnen dezelfde beurt), voeg dit samen tot één `quote_text` (met de tussenliggende tekst inbegrepen) in plaats van het op te knippen in meerdere argumenten. Knip alleen op naar een nieuw argument als er echt een ander punt, andere reden, of ander standpunt begint.
- Procedurele tekst levert GEEN argumenten op: orde van de vergadering, spreektijd-afspraken, "ik geef het woord aan...", "ik stel voor dat...", dank-/welkomstwoorden, en vergelijkbare voorzitters-chatter. Als de hele sprekerbeurt procedureel is, geef een lege lijst terug.
- Let op het verschil tussen procedurele chatter (hierboven, GEEN argument) en metadiscours (WEL een argument, mits onderbouwd): een uiting over de legitimiteit, reikwijdte, bevoegdheid, of spelregels van het debat zelf — bv. "dit is geen dunne lijn... ik benoem hier de feiten" — is een inhoudelijk standpunt over hoe het debat gevoerd mag worden, en telt mee als argument, ook als het niet direct over "stikstof" zelf gaat. Gebruik dan `typology: "other"` en `stance: "unclear"` tenzij een pro/contra-richting t.o.v. het beleid duidelijk is. Een kale roode-lijn-verklaring zonder reden ("afzwakking steunen we niet") blijft ook hier geen argument — de "geen onderbouwing = geen argument"-regel geldt onverkort.
- Eén sprekerbeurt kan 0, 1, of meerdere argumenten bevatten (bv. bij meerdere onderwerpen of tegenargumenten binnen dezelfde beurt).
- Elk genoemd getal, percentage, onderzoek, of feitelijke bewering met een bron ("uit onderzoek van X blijkt...", "volgens het RIVM...") noteer je als een claim, met alleen wat letterlijk gezegd is over de bron — beoordeel nooit of het getal of de bron klopt.
- `typology`: "factual" (feiten, cijfers, beleidsinhoudelijke of bestuurlijke constateringen — bv. een norm, een fractiestandpunt, wie iets wel/niet steunt), "moral" (ethisch/waarden), "economic" (kosten/baten), "legal" (verwijst naar een specifieke wet, regelgeving, of juridische toetsing/procedure), of "other". Gebruik "legal" alleen als het echt om wetgeving/regelgeving/juridische procedure gaat — een bestuurlijke keuze, beleidsnorm (bv. een GVE-norm of bufferzone-afstand), of politieke uitspraak van een bestuurder is meestal "factual" of "other", niet "legal".
- `stance`: "pro" of "contra" volgens de pro/contra-dimensie hierboven (niet t.o.v. het onderwerp "stikstof" in abstracte zin), of "unclear" als het standpunt niet eenduidig is. Kritiek op het huidige/voorgestelde beleid is `contra`, ook als de spreker dat doet door te verwijzen naar een eigen alternatief of eerder gevoerd beleid.

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok eromheen. Formaat:

```
{"arguments": [
  {
    "stance": "pro" | "contra" | "unclear",
    "typology": "factual" | "moral" | "economic" | "legal" | "other",
    "quote_text": "letterlijk citaat uit de brontekst",
    "quote_context": "korte context (optioneel, of null)",
    "claims": [
      {"claim_text": "wat genoemd is", "attributed_source_text": "aangehaalde bron, of null"}
    ]
  }
]}
```

Als er geen argumenten zijn: `{"arguments": []}`.

Brontekst (sprekerbeurt):
"""
Mevrouw Bromet (PRO): Voorzitter. Goed verhaal van de SP. Van de ruim acht jaar dat ik in de Tweede Kamer zit, ben ik inmiddels meer dan zeven jaar woordvoerder stikstof. Ik heb alle plannen om de natuur te verbeteren en de vergunningverlening weer op gang te brengen, voorbij zien komen. Soms waren ze simpel, maar meestal ongelofelijk ingewikkeld. In een eerder stikstofdebat legde ik het probleem eenvoudig uit: wat je erin stopt, komt er ook weer uit.
Vandaag bespreken we het nieuwste plan in een lange rij oplossingen voor de natuur, die overbelast wordt door ammoniak. Daardoor verslechtert de natuur en moeten woningzoekenden langer op een huis wachten, omdat de vergunningverlening stilvalt. Zoals bij alle eerdere plannen zitten er onderdelen in het plan van het kabinet die PRO goed vindt. Maar er zijn ook zaken waarvan wij denken: moet het niet sneller, simpeler of beter?
Laat ik beginnen met de zones rondom Natura 2000-gebieden. Dat vinden wij een goed idee. Met de minister bezocht ik een biologische boer in zo'n zone. Veel weiland, hoge waterpeilen, een boerderijwinkel aan de weg en volop aandacht voor natuur. Het was een boer die trots is op zijn bedrijf en op ieder gruttokuiken dat er groot wordt. Het was een boer die onderneemt met de natuur. Dat is precies het soort boeren dat wat PRO betreft de toekomst heeft. Dat is precies het soort boeren dat wat PRO betreft toekomst heeft.
"""


=== document 129 (Pieter Grinwis) ===
Je analyseert één sprekerbeurt uit een Tweede Kamer-debat over het onderwerp "stikstof". Spreker: Pieter Grinwis (ChristenUnie).

Context over de pro/contra-dimensie van dit onderwerp:
Dit debat gaat over het Nederlandse stikstofbeleid: het kabinetsbeleid gericht op het verlagen van stikstofuitstoot (via normen zoals de kritische depositiewaarde/KDW, gebiedsgerichte aanpak, en verplichtende maatregelen voor onder meer de landbouw), bedoeld om aan natuurdoelen en vergunningverlening te voldoen.

PRO = steunt dit beleid (het huidige of voorgestelde kabinetsbeleid), of pleit voor verdergaande/snellere stikstofreductie.
CONTRA = verzet zich tegen dit beleid, pleit voor afzwakking, uitstel, een ander instrument, vrijwilligheid in plaats van verplichting, of een wezenlijk alternatieve aanpak.

Let op: dit is puur een classificatie-hulpmiddel om het debat te ordenen, geen waardeoordeel over welke kant gelijk heeft.

Jouw taak: identificeer elk afzonderlijk politiek argument dat deze spreker inbrengt over "stikstof". Een argument heeft altijd twee delen: een standpunt (pro/contra/onduidelijk t.o.v. de pro/contra-dimensie hierboven) ÉN een reden/onderbouwing die dat standpunt ondersteunt. Beide delen moeten in het citaat zelf aanwezig zijn.

Regels (belangrijk, volg strikt):
- Jij bent geen scheidsrechter. Beoordeel nooit of een argument klopt, terecht is, of overtuigend is. Geef nooit het ene standpunt gelijk boven het andere.
- Citeer letterlijk uit de brontekst (quote_text) — verzin of parafraseer geen tekst.
- **Geen onderbouwing = geen argument.** Een kale stellingname, intentieverklaring, wens, of statement zonder reden is GEEN argument, ook niet als het stellig of politiek geladen klinkt. Voorbeelden van wat je NIET moet extraheren: "Ik strijd hier tot de laatste dag voor de boeren" (intentie, geen reden), "Afzwakking steunen we niet" (kaal standpunt, geen reden), "Dat vinden wij een goed idee" (instemming zonder reden), "Wij vinden het natuurbelang heel erg zwaar wegen" (waardestelling zonder reden). Extraheer dit soort zinnen alleen als de reden er letterlijk bij staat.
- **Eén punt = één argument.** Als de spreker hetzelfde punt in opeenvolgende zinnen verder uitwerkt, aanvult, of herhaalt (bv. een stelling gevolgd door de reden erachter, of twee keer dezelfde kernboodschap in andere woorden binnen dezelfde beurt), voeg dit samen tot één `quote_text` (met de tussenliggende tekst inbegrepen) in plaats van het op te knippen in meerdere argumenten. Knip alleen op naar een nieuw argument als er echt een ander punt, andere reden, of ander standpunt begint.
- Procedurele tekst levert GEEN argumenten op: orde van de vergadering, spreektijd-afspraken, "ik geef het woord aan...", "ik stel voor dat...", dank-/welkomstwoorden, en vergelijkbare voorzitters-chatter. Als de hele sprekerbeurt procedureel is, geef een lege lijst terug.
- Let op het verschil tussen procedurele chatter (hierboven, GEEN argument) en metadiscours (WEL een argument, mits onderbouwd): een uiting over de legitimiteit, reikwijdte, bevoegdheid, of spelregels van het debat zelf — bv. "dit is geen dunne lijn... ik benoem hier de feiten" — is een inhoudelijk standpunt over hoe het debat gevoerd mag worden, en telt mee als argument, ook als het niet direct over "stikstof" zelf gaat. Gebruik dan `typology: "other"` en `stance: "unclear"` tenzij een pro/contra-richting t.o.v. het beleid duidelijk is. Een kale roode-lijn-verklaring zonder reden ("afzwakking steunen we niet") blijft ook hier geen argument — de "geen onderbouwing = geen argument"-regel geldt onverkort.
- Eén sprekerbeurt kan 0, 1, of meerdere argumenten bevatten (bv. bij meerdere onderwerpen of tegenargumenten binnen dezelfde beurt).
- Elk genoemd getal, percentage, onderzoek, of feitelijke bewering met een bron ("uit onderzoek van X blijkt...", "volgens het RIVM...") noteer je als een claim, met alleen wat letterlijk gezegd is over de bron — beoordeel nooit of het getal of de bron klopt.
- `typology`: "factual" (feiten, cijfers, beleidsinhoudelijke of bestuurlijke constateringen — bv. een norm, een fractiestandpunt, wie iets wel/niet steunt), "moral" (ethisch/waarden), "economic" (kosten/baten), "legal" (verwijst naar een specifieke wet, regelgeving, of juridische toetsing/procedure), of "other". Gebruik "legal" alleen als het echt om wetgeving/regelgeving/juridische procedure gaat — een bestuurlijke keuze, beleidsnorm (bv. een GVE-norm of bufferzone-afstand), of politieke uitspraak van een bestuurder is meestal "factual" of "other", niet "legal".
- `stance`: "pro" of "contra" volgens de pro/contra-dimensie hierboven (niet t.o.v. het onderwerp "stikstof" in abstracte zin), of "unclear" als het standpunt niet eenduidig is. Kritiek op het huidige/voorgestelde beleid is `contra`, ook als de spreker dat doet door te verwijzen naar een eigen alternatief of eerder gevoerd beleid.

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok eromheen. Formaat:

```
{"arguments": [
  {
    "stance": "pro" | "contra" | "unclear",
    "typology": "factual" | "moral" | "economic" | "legal" | "other",
    "quote_text": "letterlijk citaat uit de brontekst",
    "quote_context": "korte context (optioneel, of null)",
    "claims": [
      {"claim_text": "wat genoemd is", "attributed_source_text": "aangehaalde bron, of null"}
    ]
  }
]}
```

Als er geen argumenten zijn: `{"arguments": []}`.

Brontekst (sprekerbeurt):
"""
De heer Grinwis (ChristenUnie): Dit kabinet heeft gezegd dat ze streven naar een draagvlak van minimaal 100 zetels. Mevrouw Bromet weet dat dit kabinet slechts tot 66 kan tellen. Met de 20 zetels van PRO ben je er nog steeds niet, want dan zit je op 86 zetels hier in de Tweede Kamer maar heb je nog geen meerderheid in de Eerste Kamer. Je zult ook andere zetels, meer uit het politieke midden en van rechts, nodig hebben om een gedragen pakket te krijgen. Dat heb je nodig om Nederland weer een toekomst te geven, om Nederland van het slot te halen, om weer huizen te kunnen bouwen voor jonge mensen en om boeren weer een toekomst te geven op het platteland. Dan begrijp ik niet dat er zo'n ... Ik las gisteren ergens een uitspraak waarbij de vraag werd opgeworpen of de heer Klaver een dictator zou zijn.
"""


=== document 133 (Pieter Grinwis) ===
Je analyseert één sprekerbeurt uit een Tweede Kamer-debat over het onderwerp "stikstof". Spreker: Pieter Grinwis (ChristenUnie).

Context over de pro/contra-dimensie van dit onderwerp:
Dit debat gaat over het Nederlandse stikstofbeleid: het kabinetsbeleid gericht op het verlagen van stikstofuitstoot (via normen zoals de kritische depositiewaarde/KDW, gebiedsgerichte aanpak, en verplichtende maatregelen voor onder meer de landbouw), bedoeld om aan natuurdoelen en vergunningverlening te voldoen.

PRO = steunt dit beleid (het huidige of voorgestelde kabinetsbeleid), of pleit voor verdergaande/snellere stikstofreductie.
CONTRA = verzet zich tegen dit beleid, pleit voor afzwakking, uitstel, een ander instrument, vrijwilligheid in plaats van verplichting, of een wezenlijk alternatieve aanpak.

Let op: dit is puur een classificatie-hulpmiddel om het debat te ordenen, geen waardeoordeel over welke kant gelijk heeft.

Jouw taak: identificeer elk afzonderlijk politiek argument dat deze spreker inbrengt over "stikstof". Een argument heeft altijd twee delen: een standpunt (pro/contra/onduidelijk t.o.v. de pro/contra-dimensie hierboven) ÉN een reden/onderbouwing die dat standpunt ondersteunt. Beide delen moeten in het citaat zelf aanwezig zijn.

Regels (belangrijk, volg strikt):
- Jij bent geen scheidsrechter. Beoordeel nooit of een argument klopt, terecht is, of overtuigend is. Geef nooit het ene standpunt gelijk boven het andere.
- Citeer letterlijk uit de brontekst (quote_text) — verzin of parafraseer geen tekst.
- **Geen onderbouwing = geen argument.** Een kale stellingname, intentieverklaring, wens, of statement zonder reden is GEEN argument, ook niet als het stellig of politiek geladen klinkt. Voorbeelden van wat je NIET moet extraheren: "Ik strijd hier tot de laatste dag voor de boeren" (intentie, geen reden), "Afzwakking steunen we niet" (kaal standpunt, geen reden), "Dat vinden wij een goed idee" (instemming zonder reden), "Wij vinden het natuurbelang heel erg zwaar wegen" (waardestelling zonder reden). Extraheer dit soort zinnen alleen als de reden er letterlijk bij staat.
- **Eén punt = één argument.** Als de spreker hetzelfde punt in opeenvolgende zinnen verder uitwerkt, aanvult, of herhaalt (bv. een stelling gevolgd door de reden erachter, of twee keer dezelfde kernboodschap in andere woorden binnen dezelfde beurt), voeg dit samen tot één `quote_text` (met de tussenliggende tekst inbegrepen) in plaats van het op te knippen in meerdere argumenten. Knip alleen op naar een nieuw argument als er echt een ander punt, andere reden, of ander standpunt begint.
- Procedurele tekst levert GEEN argumenten op: orde van de vergadering, spreektijd-afspraken, "ik geef het woord aan...", "ik stel voor dat...", dank-/welkomstwoorden, en vergelijkbare voorzitters-chatter. Als de hele sprekerbeurt procedureel is, geef een lege lijst terug.
- Let op het verschil tussen procedurele chatter (hierboven, GEEN argument) en metadiscours (WEL een argument, mits onderbouwd): een uiting over de legitimiteit, reikwijdte, bevoegdheid, of spelregels van het debat zelf — bv. "dit is geen dunne lijn... ik benoem hier de feiten" — is een inhoudelijk standpunt over hoe het debat gevoerd mag worden, en telt mee als argument, ook als het niet direct over "stikstof" zelf gaat. Gebruik dan `typology: "other"` en `stance: "unclear"` tenzij een pro/contra-richting t.o.v. het beleid duidelijk is. Een kale roode-lijn-verklaring zonder reden ("afzwakking steunen we niet") blijft ook hier geen argument — de "geen onderbouwing = geen argument"-regel geldt onverkort.
- Eén sprekerbeurt kan 0, 1, of meerdere argumenten bevatten (bv. bij meerdere onderwerpen of tegenargumenten binnen dezelfde beurt).
- Elk genoemd getal, percentage, onderzoek, of feitelijke bewering met een bron ("uit onderzoek van X blijkt...", "volgens het RIVM...") noteer je als een claim, met alleen wat letterlijk gezegd is over de bron — beoordeel nooit of het getal of de bron klopt.
- `typology`: "factual" (feiten, cijfers, beleidsinhoudelijke of bestuurlijke constateringen — bv. een norm, een fractiestandpunt, wie iets wel/niet steunt), "moral" (ethisch/waarden), "economic" (kosten/baten), "legal" (verwijst naar een specifieke wet, regelgeving, of juridische toetsing/procedure), of "other". Gebruik "legal" alleen als het echt om wetgeving/regelgeving/juridische procedure gaat — een bestuurlijke keuze, beleidsnorm (bv. een GVE-norm of bufferzone-afstand), of politieke uitspraak van een bestuurder is meestal "factual" of "other", niet "legal".
- `stance`: "pro" of "contra" volgens de pro/contra-dimensie hierboven (niet t.o.v. het onderwerp "stikstof" in abstracte zin), of "unclear" als het standpunt niet eenduidig is. Kritiek op het huidige/voorgestelde beleid is `contra`, ook als de spreker dat doet door te verwijzen naar een eigen alternatief of eerder gevoerd beleid.

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok eromheen. Formaat:

```
{"arguments": [
  {
    "stance": "pro" | "contra" | "unclear",
    "typology": "factual" | "moral" | "economic" | "legal" | "other",
    "quote_text": "letterlijk citaat uit de brontekst",
    "quote_context": "korte context (optioneel, of null)",
    "claims": [
      {"claim_text": "wat genoemd is", "attributed_source_text": "aangehaalde bron, of null"}
    ]
  }
]}
```

Als er geen argumenten zijn: `{"arguments": []}`.

Brontekst (sprekerbeurt):
"""
De heer Grinwis (ChristenUnie): Nee hoor, ik maakte een grapje. Maar zo heb ik het wel beleefd, want het is me nogal wat als je op die manier een hypotheek legt op deze discussie.
Ik neem mevrouw Bromet even mee naar Schiermonnikoog. Daar is in 2021 door de zeven melkveehouders vrijwillig 38% aan vee ingeleverd. En wat gebeurt er nu? Dit kabinet legt op Schiermonnikoog een zone van 500 meter neer. Waarom? Waarom op dit Waddeneiland een zone van 500 meter, en op Ameland, en op Terschelling, en op Texel en langs de hele Hollandse en Zeeuwse kust, terwijl dat daar geen effect heeft? Kan ik samen met mevrouw Bromet werken aan de verbetering van dit pakket en deze zones daar weg krijgen?
"""


=== document 150 (Hidde Heutink) ===
Je analyseert één sprekerbeurt uit een Tweede Kamer-debat over het onderwerp "stikstof". Spreker: Hidde Heutink (Groep Markuszower).

Context over de pro/contra-dimensie van dit onderwerp:
Dit debat gaat over het Nederlandse stikstofbeleid: het kabinetsbeleid gericht op het verlagen van stikstofuitstoot (via normen zoals de kritische depositiewaarde/KDW, gebiedsgerichte aanpak, en verplichtende maatregelen voor onder meer de landbouw), bedoeld om aan natuurdoelen en vergunningverlening te voldoen.

PRO = steunt dit beleid (het huidige of voorgestelde kabinetsbeleid), of pleit voor verdergaande/snellere stikstofreductie.
CONTRA = verzet zich tegen dit beleid, pleit voor afzwakking, uitstel, een ander instrument, vrijwilligheid in plaats van verplichting, of een wezenlijk alternatieve aanpak.

Let op: dit is puur een classificatie-hulpmiddel om het debat te ordenen, geen waardeoordeel over welke kant gelijk heeft.

Jouw taak: identificeer elk afzonderlijk politiek argument dat deze spreker inbrengt over "stikstof". Een argument heeft altijd twee delen: een standpunt (pro/contra/onduidelijk t.o.v. de pro/contra-dimensie hierboven) ÉN een reden/onderbouwing die dat standpunt ondersteunt. Beide delen moeten in het citaat zelf aanwezig zijn.

Regels (belangrijk, volg strikt):
- Jij bent geen scheidsrechter. Beoordeel nooit of een argument klopt, terecht is, of overtuigend is. Geef nooit het ene standpunt gelijk boven het andere.
- Citeer letterlijk uit de brontekst (quote_text) — verzin of parafraseer geen tekst.
- **Geen onderbouwing = geen argument.** Een kale stellingname, intentieverklaring, wens, of statement zonder reden is GEEN argument, ook niet als het stellig of politiek geladen klinkt. Voorbeelden van wat je NIET moet extraheren: "Ik strijd hier tot de laatste dag voor de boeren" (intentie, geen reden), "Afzwakking steunen we niet" (kaal standpunt, geen reden), "Dat vinden wij een goed idee" (instemming zonder reden), "Wij vinden het natuurbelang heel erg zwaar wegen" (waardestelling zonder reden). Extraheer dit soort zinnen alleen als de reden er letterlijk bij staat.
- **Eén punt = één argument.** Als de spreker hetzelfde punt in opeenvolgende zinnen verder uitwerkt, aanvult, of herhaalt (bv. een stelling gevolgd door de reden erachter, of twee keer dezelfde kernboodschap in andere woorden binnen dezelfde beurt), voeg dit samen tot één `quote_text` (met de tussenliggende tekst inbegrepen) in plaats van het op te knippen in meerdere argumenten. Knip alleen op naar een nieuw argument als er echt een ander punt, andere reden, of ander standpunt begint.
- Procedurele tekst levert GEEN argumenten op: orde van de vergadering, spreektijd-afspraken, "ik geef het woord aan...", "ik stel voor dat...", dank-/welkomstwoorden, en vergelijkbare voorzitters-chatter. Als de hele sprekerbeurt procedureel is, geef een lege lijst terug.
- Let op het verschil tussen procedurele chatter (hierboven, GEEN argument) en metadiscours (WEL een argument, mits onderbouwd): een uiting over de legitimiteit, reikwijdte, bevoegdheid, of spelregels van het debat zelf — bv. "dit is geen dunne lijn... ik benoem hier de feiten" — is een inhoudelijk standpunt over hoe het debat gevoerd mag worden, en telt mee als argument, ook als het niet direct over "stikstof" zelf gaat. Gebruik dan `typology: "other"` en `stance: "unclear"` tenzij een pro/contra-richting t.o.v. het beleid duidelijk is. Een kale roode-lijn-verklaring zonder reden ("afzwakking steunen we niet") blijft ook hier geen argument — de "geen onderbouwing = geen argument"-regel geldt onverkort.
- Eén sprekerbeurt kan 0, 1, of meerdere argumenten bevatten (bv. bij meerdere onderwerpen of tegenargumenten binnen dezelfde beurt).
- Elk genoemd getal, percentage, onderzoek, of feitelijke bewering met een bron ("uit onderzoek van X blijkt...", "volgens het RIVM...") noteer je als een claim, met alleen wat letterlijk gezegd is over de bron — beoordeel nooit of het getal of de bron klopt.
- `typology`: "factual" (feiten, cijfers, beleidsinhoudelijke of bestuurlijke constateringen — bv. een norm, een fractiestandpunt, wie iets wel/niet steunt), "moral" (ethisch/waarden), "economic" (kosten/baten), "legal" (verwijst naar een specifieke wet, regelgeving, of juridische toetsing/procedure), of "other". Gebruik "legal" alleen als het echt om wetgeving/regelgeving/juridische procedure gaat — een bestuurlijke keuze, beleidsnorm (bv. een GVE-norm of bufferzone-afstand), of politieke uitspraak van een bestuurder is meestal "factual" of "other", niet "legal".
- `stance`: "pro" of "contra" volgens de pro/contra-dimensie hierboven (niet t.o.v. het onderwerp "stikstof" in abstracte zin), of "unclear" als het standpunt niet eenduidig is. Kritiek op het huidige/voorgestelde beleid is `contra`, ook als de spreker dat doet door te verwijzen naar een eigen alternatief of eerder gevoerd beleid.

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok eromheen. Formaat:

```
{"arguments": [
  {
    "stance": "pro" | "contra" | "unclear",
    "typology": "factual" | "moral" | "economic" | "legal" | "other",
    "quote_text": "letterlijk citaat uit de brontekst",
    "quote_context": "korte context (optioneel, of null)",
    "claims": [
      {"claim_text": "wat genoemd is", "attributed_source_text": "aangehaalde bron, of null"}
    ]
  }
]}
```

Als er geen argumenten zijn: `{"arguments": []}`.

Brontekst (sprekerbeurt):
"""
De heer Heutink (Groep Markuszower): Dit is geen dunne lijn. Dit is geen dunne lijn! Ik benoem hier de feiten. Ik benoem hier als volksvertegenwoordiger precies wat hier gebeurt, namelijk dat er partijen in dit huis zijn die het de mensen op de tribune en de mensen thuis heel erg moeilijk gaan maken. Dat is de realiteit. Hoe ik dat verwoord hier in deze zaal is mijn goed recht. Ik ga geen grens over. Ik scheld niemand uit. Ik maak geen enkel persoonlijk feit. Ik accepteer ook niet van u, voorzitter, dat u mij dan de mond snoert.
"""


=== document 167 (Laura Bromet) ===
Je analyseert één sprekerbeurt uit een Tweede Kamer-debat over het onderwerp "stikstof". Spreker: Laura Bromet (PRO).

Context over de pro/contra-dimensie van dit onderwerp:
Dit debat gaat over het Nederlandse stikstofbeleid: het kabinetsbeleid gericht op het verlagen van stikstofuitstoot (via normen zoals de kritische depositiewaarde/KDW, gebiedsgerichte aanpak, en verplichtende maatregelen voor onder meer de landbouw), bedoeld om aan natuurdoelen en vergunningverlening te voldoen.

PRO = steunt dit beleid (het huidige of voorgestelde kabinetsbeleid), of pleit voor verdergaande/snellere stikstofreductie.
CONTRA = verzet zich tegen dit beleid, pleit voor afzwakking, uitstel, een ander instrument, vrijwilligheid in plaats van verplichting, of een wezenlijk alternatieve aanpak.

Let op: dit is puur een classificatie-hulpmiddel om het debat te ordenen, geen waardeoordeel over welke kant gelijk heeft.

Jouw taak: identificeer elk afzonderlijk politiek argument dat deze spreker inbrengt over "stikstof". Een argument heeft altijd twee delen: een standpunt (pro/contra/onduidelijk t.o.v. de pro/contra-dimensie hierboven) ÉN een reden/onderbouwing die dat standpunt ondersteunt. Beide delen moeten in het citaat zelf aanwezig zijn.

Regels (belangrijk, volg strikt):
- Jij bent geen scheidsrechter. Beoordeel nooit of een argument klopt, terecht is, of overtuigend is. Geef nooit het ene standpunt gelijk boven het andere.
- Citeer letterlijk uit de brontekst (quote_text) — verzin of parafraseer geen tekst.
- **Geen onderbouwing = geen argument.** Een kale stellingname, intentieverklaring, wens, of statement zonder reden is GEEN argument, ook niet als het stellig of politiek geladen klinkt. Voorbeelden van wat je NIET moet extraheren: "Ik strijd hier tot de laatste dag voor de boeren" (intentie, geen reden), "Afzwakking steunen we niet" (kaal standpunt, geen reden), "Dat vinden wij een goed idee" (instemming zonder reden), "Wij vinden het natuurbelang heel erg zwaar wegen" (waardestelling zonder reden). Extraheer dit soort zinnen alleen als de reden er letterlijk bij staat.
- **Eén punt = één argument.** Als de spreker hetzelfde punt in opeenvolgende zinnen verder uitwerkt, aanvult, of herhaalt (bv. een stelling gevolgd door de reden erachter, of twee keer dezelfde kernboodschap in andere woorden binnen dezelfde beurt), voeg dit samen tot één `quote_text` (met de tussenliggende tekst inbegrepen) in plaats van het op te knippen in meerdere argumenten. Knip alleen op naar een nieuw argument als er echt een ander punt, andere reden, of ander standpunt begint.
- Procedurele tekst levert GEEN argumenten op: orde van de vergadering, spreektijd-afspraken, "ik geef het woord aan...", "ik stel voor dat...", dank-/welkomstwoorden, en vergelijkbare voorzitters-chatter. Als de hele sprekerbeurt procedureel is, geef een lege lijst terug.
- Let op het verschil tussen procedurele chatter (hierboven, GEEN argument) en metadiscours (WEL een argument, mits onderbouwd): een uiting over de legitimiteit, reikwijdte, bevoegdheid, of spelregels van het debat zelf — bv. "dit is geen dunne lijn... ik benoem hier de feiten" — is een inhoudelijk standpunt over hoe het debat gevoerd mag worden, en telt mee als argument, ook als het niet direct over "stikstof" zelf gaat. Gebruik dan `typology: "other"` en `stance: "unclear"` tenzij een pro/contra-richting t.o.v. het beleid duidelijk is. Een kale roode-lijn-verklaring zonder reden ("afzwakking steunen we niet") blijft ook hier geen argument — de "geen onderbouwing = geen argument"-regel geldt onverkort.
- Eén sprekerbeurt kan 0, 1, of meerdere argumenten bevatten (bv. bij meerdere onderwerpen of tegenargumenten binnen dezelfde beurt).
- Elk genoemd getal, percentage, onderzoek, of feitelijke bewering met een bron ("uit onderzoek van X blijkt...", "volgens het RIVM...") noteer je als een claim, met alleen wat letterlijk gezegd is over de bron — beoordeel nooit of het getal of de bron klopt.
- `typology`: "factual" (feiten, cijfers, beleidsinhoudelijke of bestuurlijke constateringen — bv. een norm, een fractiestandpunt, wie iets wel/niet steunt), "moral" (ethisch/waarden), "economic" (kosten/baten), "legal" (verwijst naar een specifieke wet, regelgeving, of juridische toetsing/procedure), of "other". Gebruik "legal" alleen als het echt om wetgeving/regelgeving/juridische procedure gaat — een bestuurlijke keuze, beleidsnorm (bv. een GVE-norm of bufferzone-afstand), of politieke uitspraak van een bestuurder is meestal "factual" of "other", niet "legal".
- `stance`: "pro" of "contra" volgens de pro/contra-dimensie hierboven (niet t.o.v. het onderwerp "stikstof" in abstracte zin), of "unclear" als het standpunt niet eenduidig is. Kritiek op het huidige/voorgestelde beleid is `contra`, ook als de spreker dat doet door te verwijzen naar een eigen alternatief of eerder gevoerd beleid.

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok eromheen. Formaat:

```
{"arguments": [
  {
    "stance": "pro" | "contra" | "unclear",
    "typology": "factual" | "moral" | "economic" | "legal" | "other",
    "quote_text": "letterlijk citaat uit de brontekst",
    "quote_context": "korte context (optioneel, of null)",
    "claims": [
      {"claim_text": "wat genoemd is", "attributed_source_text": "aangehaalde bron, of null"}
    ]
  }
]}
```

Als er geen argumenten zijn: `{"arguments": []}`.

Brontekst (sprekerbeurt):
"""
Mevrouw Bromet (PRO): Dank voor de vraag. Die 2,6 gve vinden wij eigenlijk ook te hoog. Wij hebben hier een paar weken geleden een petitie aangenomen van de boeren van Netwerk GRONDig, die zeiden: "Hou nou vast aan de norm van 2,2 voor grondgebondenheid, want dan kan daar ook niet elke keer discussie over ontstaan. Als wij zelf een plan hadden gemaakt, hadden wij 2,2 erin gezet." Aan de andere kant is het zo dat 2,6 voor een heel groot gedeelte van de boeren in Nederland helemaal geen probleem is. Daar voldoen ze al aan. Het is wel een probleem in juist die gebieden waar de veehouderij ontzettend intensief is en waar de natuur ontzettend lijdt onder het overschot aan ammoniak, zoals de Peel in Brabant. Daar wordt het echt een hele grote opgave en een heel groot probleem. Maar ja, dat is precies waar wij het probleem zien, dus daar moet iets gebeuren.
"""


=== document 169 (Laura Bromet) ===
Je analyseert één sprekerbeurt uit een Tweede Kamer-debat over het onderwerp "stikstof". Spreker: Laura Bromet (PRO).

Context over de pro/contra-dimensie van dit onderwerp:
Dit debat gaat over het Nederlandse stikstofbeleid: het kabinetsbeleid gericht op het verlagen van stikstofuitstoot (via normen zoals de kritische depositiewaarde/KDW, gebiedsgerichte aanpak, en verplichtende maatregelen voor onder meer de landbouw), bedoeld om aan natuurdoelen en vergunningverlening te voldoen.

PRO = steunt dit beleid (het huidige of voorgestelde kabinetsbeleid), of pleit voor verdergaande/snellere stikstofreductie.
CONTRA = verzet zich tegen dit beleid, pleit voor afzwakking, uitstel, een ander instrument, vrijwilligheid in plaats van verplichting, of een wezenlijk alternatieve aanpak.

Let op: dit is puur een classificatie-hulpmiddel om het debat te ordenen, geen waardeoordeel over welke kant gelijk heeft.

Jouw taak: identificeer elk afzonderlijk politiek argument dat deze spreker inbrengt over "stikstof". Een argument heeft altijd twee delen: een standpunt (pro/contra/onduidelijk t.o.v. de pro/contra-dimensie hierboven) ÉN een reden/onderbouwing die dat standpunt ondersteunt. Beide delen moeten in het citaat zelf aanwezig zijn.

Regels (belangrijk, volg strikt):
- Jij bent geen scheidsrechter. Beoordeel nooit of een argument klopt, terecht is, of overtuigend is. Geef nooit het ene standpunt gelijk boven het andere.
- Citeer letterlijk uit de brontekst (quote_text) — verzin of parafraseer geen tekst.
- **Geen onderbouwing = geen argument.** Een kale stellingname, intentieverklaring, wens, of statement zonder reden is GEEN argument, ook niet als het stellig of politiek geladen klinkt. Voorbeelden van wat je NIET moet extraheren: "Ik strijd hier tot de laatste dag voor de boeren" (intentie, geen reden), "Afzwakking steunen we niet" (kaal standpunt, geen reden), "Dat vinden wij een goed idee" (instemming zonder reden), "Wij vinden het natuurbelang heel erg zwaar wegen" (waardestelling zonder reden). Extraheer dit soort zinnen alleen als de reden er letterlijk bij staat.
- **Eén punt = één argument.** Als de spreker hetzelfde punt in opeenvolgende zinnen verder uitwerkt, aanvult, of herhaalt (bv. een stelling gevolgd door de reden erachter, of twee keer dezelfde kernboodschap in andere woorden binnen dezelfde beurt), voeg dit samen tot één `quote_text` (met de tussenliggende tekst inbegrepen) in plaats van het op te knippen in meerdere argumenten. Knip alleen op naar een nieuw argument als er echt een ander punt, andere reden, of ander standpunt begint.
- Procedurele tekst levert GEEN argumenten op: orde van de vergadering, spreektijd-afspraken, "ik geef het woord aan...", "ik stel voor dat...", dank-/welkomstwoorden, en vergelijkbare voorzitters-chatter. Als de hele sprekerbeurt procedureel is, geef een lege lijst terug.
- Let op het verschil tussen procedurele chatter (hierboven, GEEN argument) en metadiscours (WEL een argument, mits onderbouwd): een uiting over de legitimiteit, reikwijdte, bevoegdheid, of spelregels van het debat zelf — bv. "dit is geen dunne lijn... ik benoem hier de feiten" — is een inhoudelijk standpunt over hoe het debat gevoerd mag worden, en telt mee als argument, ook als het niet direct over "stikstof" zelf gaat. Gebruik dan `typology: "other"` en `stance: "unclear"` tenzij een pro/contra-richting t.o.v. het beleid duidelijk is. Een kale roode-lijn-verklaring zonder reden ("afzwakking steunen we niet") blijft ook hier geen argument — de "geen onderbouwing = geen argument"-regel geldt onverkort.
- Eén sprekerbeurt kan 0, 1, of meerdere argumenten bevatten (bv. bij meerdere onderwerpen of tegenargumenten binnen dezelfde beurt).
- Elk genoemd getal, percentage, onderzoek, of feitelijke bewering met een bron ("uit onderzoek van X blijkt...", "volgens het RIVM...") noteer je als een claim, met alleen wat letterlijk gezegd is over de bron — beoordeel nooit of het getal of de bron klopt.
- `typology`: "factual" (feiten, cijfers, beleidsinhoudelijke of bestuurlijke constateringen — bv. een norm, een fractiestandpunt, wie iets wel/niet steunt), "moral" (ethisch/waarden), "economic" (kosten/baten), "legal" (verwijst naar een specifieke wet, regelgeving, of juridische toetsing/procedure), of "other". Gebruik "legal" alleen als het echt om wetgeving/regelgeving/juridische procedure gaat — een bestuurlijke keuze, beleidsnorm (bv. een GVE-norm of bufferzone-afstand), of politieke uitspraak van een bestuurder is meestal "factual" of "other", niet "legal".
- `stance`: "pro" of "contra" volgens de pro/contra-dimensie hierboven (niet t.o.v. het onderwerp "stikstof" in abstracte zin), of "unclear" als het standpunt niet eenduidig is. Kritiek op het huidige/voorgestelde beleid is `contra`, ook als de spreker dat doet door te verwijzen naar een eigen alternatief of eerder gevoerd beleid.

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok eromheen. Formaat:

```
{"arguments": [
  {
    "stance": "pro" | "contra" | "unclear",
    "typology": "factual" | "moral" | "economic" | "legal" | "other",
    "quote_text": "letterlijk citaat uit de brontekst",
    "quote_context": "korte context (optioneel, of null)",
    "claims": [
      {"claim_text": "wat genoemd is", "attributed_source_text": "aangehaalde bron, of null"}
    ]
  }
]}
```

Als er geen argumenten zijn: `{"arguments": []}`.

Brontekst (sprekerbeurt):
"""
Mevrouw Bromet (PRO): Ja, dit is ook een fijne vraag, want dan kan ik meteen even weerleggen dat ik de boeren haat. Ik vind het verschrikkelijk dat mensen die denken ergens in een bepaald gebied een toekomst op te bouwen op een bepaalde manier en met een bepaalde bedrijfsvoering, dat straks niet meer kunnen doen en afscheid moeten nemen van de manier waarop ze dachten dat ze hun bedrijf konden voortzetten. Ik hoop echt dat ze een bedrijf kunnen houden en over kunnen schakelen op een bedrijf dat veel meer met respect voor de natuur produceert en waar je ook nog een goede boterham mee verdient. Dat wens ik elke boer in zo'n gebied toe. Ik wens de boeren ook toe dat ze, als ze dat niet kunnen of willen, een andere plek in Nederland of ergens op de wereld vinden waar ze door kunnen gaan met wat ze al deden. De realiteit is dat dat in de zones rondom die natuurgebieden niet zal kunnen. Als het goed is, weten ze dat diep in hun hart ook al heel lang, want deze discussie is niet van vandaag of gisteren. Deze discussie speelt al bijna 30 jaar.
"""


=== document 175 (Laura Bromet) ===
Je analyseert één sprekerbeurt uit een Tweede Kamer-debat over het onderwerp "stikstof". Spreker: Laura Bromet (PRO).

Context over de pro/contra-dimensie van dit onderwerp:
Dit debat gaat over het Nederlandse stikstofbeleid: het kabinetsbeleid gericht op het verlagen van stikstofuitstoot (via normen zoals de kritische depositiewaarde/KDW, gebiedsgerichte aanpak, en verplichtende maatregelen voor onder meer de landbouw), bedoeld om aan natuurdoelen en vergunningverlening te voldoen.

PRO = steunt dit beleid (het huidige of voorgestelde kabinetsbeleid), of pleit voor verdergaande/snellere stikstofreductie.
CONTRA = verzet zich tegen dit beleid, pleit voor afzwakking, uitstel, een ander instrument, vrijwilligheid in plaats van verplichting, of een wezenlijk alternatieve aanpak.

Let op: dit is puur een classificatie-hulpmiddel om het debat te ordenen, geen waardeoordeel over welke kant gelijk heeft.

Jouw taak: identificeer elk afzonderlijk politiek argument dat deze spreker inbrengt over "stikstof". Een argument heeft altijd twee delen: een standpunt (pro/contra/onduidelijk t.o.v. de pro/contra-dimensie hierboven) ÉN een reden/onderbouwing die dat standpunt ondersteunt. Beide delen moeten in het citaat zelf aanwezig zijn.

Regels (belangrijk, volg strikt):
- Jij bent geen scheidsrechter. Beoordeel nooit of een argument klopt, terecht is, of overtuigend is. Geef nooit het ene standpunt gelijk boven het andere.
- Citeer letterlijk uit de brontekst (quote_text) — verzin of parafraseer geen tekst.
- **Geen onderbouwing = geen argument.** Een kale stellingname, intentieverklaring, wens, of statement zonder reden is GEEN argument, ook niet als het stellig of politiek geladen klinkt. Voorbeelden van wat je NIET moet extraheren: "Ik strijd hier tot de laatste dag voor de boeren" (intentie, geen reden), "Afzwakking steunen we niet" (kaal standpunt, geen reden), "Dat vinden wij een goed idee" (instemming zonder reden), "Wij vinden het natuurbelang heel erg zwaar wegen" (waardestelling zonder reden). Extraheer dit soort zinnen alleen als de reden er letterlijk bij staat.
- **Eén punt = één argument.** Als de spreker hetzelfde punt in opeenvolgende zinnen verder uitwerkt, aanvult, of herhaalt (bv. een stelling gevolgd door de reden erachter, of twee keer dezelfde kernboodschap in andere woorden binnen dezelfde beurt), voeg dit samen tot één `quote_text` (met de tussenliggende tekst inbegrepen) in plaats van het op te knippen in meerdere argumenten. Knip alleen op naar een nieuw argument als er echt een ander punt, andere reden, of ander standpunt begint.
- Procedurele tekst levert GEEN argumenten op: orde van de vergadering, spreektijd-afspraken, "ik geef het woord aan...", "ik stel voor dat...", dank-/welkomstwoorden, en vergelijkbare voorzitters-chatter. Als de hele sprekerbeurt procedureel is, geef een lege lijst terug.
- Let op het verschil tussen procedurele chatter (hierboven, GEEN argument) en metadiscours (WEL een argument, mits onderbouwd): een uiting over de legitimiteit, reikwijdte, bevoegdheid, of spelregels van het debat zelf — bv. "dit is geen dunne lijn... ik benoem hier de feiten" — is een inhoudelijk standpunt over hoe het debat gevoerd mag worden, en telt mee als argument, ook als het niet direct over "stikstof" zelf gaat. Gebruik dan `typology: "other"` en `stance: "unclear"` tenzij een pro/contra-richting t.o.v. het beleid duidelijk is. Een kale roode-lijn-verklaring zonder reden ("afzwakking steunen we niet") blijft ook hier geen argument — de "geen onderbouwing = geen argument"-regel geldt onverkort.
- Eén sprekerbeurt kan 0, 1, of meerdere argumenten bevatten (bv. bij meerdere onderwerpen of tegenargumenten binnen dezelfde beurt).
- Elk genoemd getal, percentage, onderzoek, of feitelijke bewering met een bron ("uit onderzoek van X blijkt...", "volgens het RIVM...") noteer je als een claim, met alleen wat letterlijk gezegd is over de bron — beoordeel nooit of het getal of de bron klopt.
- `typology`: "factual" (feiten, cijfers, beleidsinhoudelijke of bestuurlijke constateringen — bv. een norm, een fractiestandpunt, wie iets wel/niet steunt), "moral" (ethisch/waarden), "economic" (kosten/baten), "legal" (verwijst naar een specifieke wet, regelgeving, of juridische toetsing/procedure), of "other". Gebruik "legal" alleen als het echt om wetgeving/regelgeving/juridische procedure gaat — een bestuurlijke keuze, beleidsnorm (bv. een GVE-norm of bufferzone-afstand), of politieke uitspraak van een bestuurder is meestal "factual" of "other", niet "legal".
- `stance`: "pro" of "contra" volgens de pro/contra-dimensie hierboven (niet t.o.v. het onderwerp "stikstof" in abstracte zin), of "unclear" als het standpunt niet eenduidig is. Kritiek op het huidige/voorgestelde beleid is `contra`, ook als de spreker dat doet door te verwijzen naar een eigen alternatief of eerder gevoerd beleid.

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok eromheen. Formaat:

```
{"arguments": [
  {
    "stance": "pro" | "contra" | "unclear",
    "typology": "factual" | "moral" | "economic" | "legal" | "other",
    "quote_text": "letterlijk citaat uit de brontekst",
    "quote_context": "korte context (optioneel, of null)",
    "claims": [
      {"claim_text": "wat genoemd is", "attributed_source_text": "aangehaalde bron, of null"}
    ]
  }
]}
```

Als er geen argumenten zijn: `{"arguments": []}`.

Brontekst (sprekerbeurt):
"""
Mevrouw Bromet (PRO): Het gaat ons erom dat de stikstofuitstoot en de stikstofdepositie niet toenemen. Daar gaat het ons om. Die stallen in de randen van Natura 2000-gebieden zijn geen dichte stallen. Dat zijn gewoon open stallen. Dat zijn bedrijven waar de koeien het grootste gedeelte van het jaar buiten staan. Ik vind ook dat er geen percentage voor reductie opgelegd moet worden aan deze boeren, want zij hebben het al heel goed gedaan. Ik vind dat er een absolute norm moet komen voor stikstofuitstoot. Ik heb hier al een keer de draai gemaakt naar doelsturing, omdat ik dacht: oké, we geven de boeren een kans; laat ze zelf bewijzen dat ze het goed doen. Maar ik vind echt dat de boeren die het al gedaan hebben, daarvoor beloond moeten worden en dat ze daarbovenop niet nog eens een extra reductie moeten doen. Daarin kunnen we elkaar misschien wel vinden.
"""


=== document 192 (Laura Bromet) ===
Je analyseert één sprekerbeurt uit een Tweede Kamer-debat over het onderwerp "stikstof". Spreker: Laura Bromet (PRO).

Context over de pro/contra-dimensie van dit onderwerp:
Dit debat gaat over het Nederlandse stikstofbeleid: het kabinetsbeleid gericht op het verlagen van stikstofuitstoot (via normen zoals de kritische depositiewaarde/KDW, gebiedsgerichte aanpak, en verplichtende maatregelen voor onder meer de landbouw), bedoeld om aan natuurdoelen en vergunningverlening te voldoen.

PRO = steunt dit beleid (het huidige of voorgestelde kabinetsbeleid), of pleit voor verdergaande/snellere stikstofreductie.
CONTRA = verzet zich tegen dit beleid, pleit voor afzwakking, uitstel, een ander instrument, vrijwilligheid in plaats van verplichting, of een wezenlijk alternatieve aanpak.

Let op: dit is puur een classificatie-hulpmiddel om het debat te ordenen, geen waardeoordeel over welke kant gelijk heeft.

Jouw taak: identificeer elk afzonderlijk politiek argument dat deze spreker inbrengt over "stikstof". Een argument heeft altijd twee delen: een standpunt (pro/contra/onduidelijk t.o.v. de pro/contra-dimensie hierboven) ÉN een reden/onderbouwing die dat standpunt ondersteunt. Beide delen moeten in het citaat zelf aanwezig zijn.

Regels (belangrijk, volg strikt):
- Jij bent geen scheidsrechter. Beoordeel nooit of een argument klopt, terecht is, of overtuigend is. Geef nooit het ene standpunt gelijk boven het andere.
- Citeer letterlijk uit de brontekst (quote_text) — verzin of parafraseer geen tekst.
- **Geen onderbouwing = geen argument.** Een kale stellingname, intentieverklaring, wens, of statement zonder reden is GEEN argument, ook niet als het stellig of politiek geladen klinkt. Voorbeelden van wat je NIET moet extraheren: "Ik strijd hier tot de laatste dag voor de boeren" (intentie, geen reden), "Afzwakking steunen we niet" (kaal standpunt, geen reden), "Dat vinden wij een goed idee" (instemming zonder reden), "Wij vinden het natuurbelang heel erg zwaar wegen" (waardestelling zonder reden). Extraheer dit soort zinnen alleen als de reden er letterlijk bij staat.
- **Eén punt = één argument.** Als de spreker hetzelfde punt in opeenvolgende zinnen verder uitwerkt, aanvult, of herhaalt (bv. een stelling gevolgd door de reden erachter, of twee keer dezelfde kernboodschap in andere woorden binnen dezelfde beurt), voeg dit samen tot één `quote_text` (met de tussenliggende tekst inbegrepen) in plaats van het op te knippen in meerdere argumenten. Knip alleen op naar een nieuw argument als er echt een ander punt, andere reden, of ander standpunt begint.
- Procedurele tekst levert GEEN argumenten op: orde van de vergadering, spreektijd-afspraken, "ik geef het woord aan...", "ik stel voor dat...", dank-/welkomstwoorden, en vergelijkbare voorzitters-chatter. Als de hele sprekerbeurt procedureel is, geef een lege lijst terug.
- Let op het verschil tussen procedurele chatter (hierboven, GEEN argument) en metadiscours (WEL een argument, mits onderbouwd): een uiting over de legitimiteit, reikwijdte, bevoegdheid, of spelregels van het debat zelf — bv. "dit is geen dunne lijn... ik benoem hier de feiten" — is een inhoudelijk standpunt over hoe het debat gevoerd mag worden, en telt mee als argument, ook als het niet direct over "stikstof" zelf gaat. Gebruik dan `typology: "other"` en `stance: "unclear"` tenzij een pro/contra-richting t.o.v. het beleid duidelijk is. Een kale roode-lijn-verklaring zonder reden ("afzwakking steunen we niet") blijft ook hier geen argument — de "geen onderbouwing = geen argument"-regel geldt onverkort.
- Eén sprekerbeurt kan 0, 1, of meerdere argumenten bevatten (bv. bij meerdere onderwerpen of tegenargumenten binnen dezelfde beurt).
- Elk genoemd getal, percentage, onderzoek, of feitelijke bewering met een bron ("uit onderzoek van X blijkt...", "volgens het RIVM...") noteer je als een claim, met alleen wat letterlijk gezegd is over de bron — beoordeel nooit of het getal of de bron klopt.
- `typology`: "factual" (feiten, cijfers, beleidsinhoudelijke of bestuurlijke constateringen — bv. een norm, een fractiestandpunt, wie iets wel/niet steunt), "moral" (ethisch/waarden), "economic" (kosten/baten), "legal" (verwijst naar een specifieke wet, regelgeving, of juridische toetsing/procedure), of "other". Gebruik "legal" alleen als het echt om wetgeving/regelgeving/juridische procedure gaat — een bestuurlijke keuze, beleidsnorm (bv. een GVE-norm of bufferzone-afstand), of politieke uitspraak van een bestuurder is meestal "factual" of "other", niet "legal".
- `stance`: "pro" of "contra" volgens de pro/contra-dimensie hierboven (niet t.o.v. het onderwerp "stikstof" in abstracte zin), of "unclear" als het standpunt niet eenduidig is. Kritiek op het huidige/voorgestelde beleid is `contra`, ook als de spreker dat doet door te verwijzen naar een eigen alternatief of eerder gevoerd beleid.

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok eromheen. Formaat:

```
{"arguments": [
  {
    "stance": "pro" | "contra" | "unclear",
    "typology": "factual" | "moral" | "economic" | "legal" | "other",
    "quote_text": "letterlijk citaat uit de brontekst",
    "quote_context": "korte context (optioneel, of null)",
    "claims": [
      {"claim_text": "wat genoemd is", "attributed_source_text": "aangehaalde bron, of null"}
    ]
  }
]}
```

Als er geen argumenten zijn: `{"arguments": []}`.

Brontekst (sprekerbeurt):
"""
Mevrouw Bromet (PRO): Ik ken geen communisten, dus ik weet niet waar mevrouw Keijzer het over heeft. Over die voedselzekerheid zou ik wel wat willen zeggen, want het klopt gewoon niet wat mevrouw Keijzer zegt. De voedselzekerheid in Nederland wordt bedreigd doordat wij veevoer verbouwen in Nederland op grond waar je ook gewoon mensenvoer kan verbouwen. Wij hebben misschien wel een probleem met de vleeszekerheid voor de export. Dat is het probleem waar we het over hebben. Er is deze week een onderzoek verschenen van de Wageningen Universiteit, die dit onderzocht heeft. Ik zou mevrouw Keijzer dus aanraden om dat even te lezen. Dit verhaal klopt niet. Ik kan het onderzoek straks wel even opsturen, dan kan ze het lezen.
"""


=== document 218 (Laura Bromet) ===
Je analyseert één sprekerbeurt uit een Tweede Kamer-debat over het onderwerp "stikstof". Spreker: Laura Bromet (PRO).

Context over de pro/contra-dimensie van dit onderwerp:
Dit debat gaat over het Nederlandse stikstofbeleid: het kabinetsbeleid gericht op het verlagen van stikstofuitstoot (via normen zoals de kritische depositiewaarde/KDW, gebiedsgerichte aanpak, en verplichtende maatregelen voor onder meer de landbouw), bedoeld om aan natuurdoelen en vergunningverlening te voldoen.

PRO = steunt dit beleid (het huidige of voorgestelde kabinetsbeleid), of pleit voor verdergaande/snellere stikstofreductie.
CONTRA = verzet zich tegen dit beleid, pleit voor afzwakking, uitstel, een ander instrument, vrijwilligheid in plaats van verplichting, of een wezenlijk alternatieve aanpak.

Let op: dit is puur een classificatie-hulpmiddel om het debat te ordenen, geen waardeoordeel over welke kant gelijk heeft.

Jouw taak: identificeer elk afzonderlijk politiek argument dat deze spreker inbrengt over "stikstof". Een argument heeft altijd twee delen: een standpunt (pro/contra/onduidelijk t.o.v. de pro/contra-dimensie hierboven) ÉN een reden/onderbouwing die dat standpunt ondersteunt. Beide delen moeten in het citaat zelf aanwezig zijn.

Regels (belangrijk, volg strikt):
- Jij bent geen scheidsrechter. Beoordeel nooit of een argument klopt, terecht is, of overtuigend is. Geef nooit het ene standpunt gelijk boven het andere.
- Citeer letterlijk uit de brontekst (quote_text) — verzin of parafraseer geen tekst.
- **Geen onderbouwing = geen argument.** Een kale stellingname, intentieverklaring, wens, of statement zonder reden is GEEN argument, ook niet als het stellig of politiek geladen klinkt. Voorbeelden van wat je NIET moet extraheren: "Ik strijd hier tot de laatste dag voor de boeren" (intentie, geen reden), "Afzwakking steunen we niet" (kaal standpunt, geen reden), "Dat vinden wij een goed idee" (instemming zonder reden), "Wij vinden het natuurbelang heel erg zwaar wegen" (waardestelling zonder reden). Extraheer dit soort zinnen alleen als de reden er letterlijk bij staat.
- **Eén punt = één argument.** Als de spreker hetzelfde punt in opeenvolgende zinnen verder uitwerkt, aanvult, of herhaalt (bv. een stelling gevolgd door de reden erachter, of twee keer dezelfde kernboodschap in andere woorden binnen dezelfde beurt), voeg dit samen tot één `quote_text` (met de tussenliggende tekst inbegrepen) in plaats van het op te knippen in meerdere argumenten. Knip alleen op naar een nieuw argument als er echt een ander punt, andere reden, of ander standpunt begint.
- Procedurele tekst levert GEEN argumenten op: orde van de vergadering, spreektijd-afspraken, "ik geef het woord aan...", "ik stel voor dat...", dank-/welkomstwoorden, en vergelijkbare voorzitters-chatter. Als de hele sprekerbeurt procedureel is, geef een lege lijst terug.
- Let op het verschil tussen procedurele chatter (hierboven, GEEN argument) en metadiscours (WEL een argument, mits onderbouwd): een uiting over de legitimiteit, reikwijdte, bevoegdheid, of spelregels van het debat zelf — bv. "dit is geen dunne lijn... ik benoem hier de feiten" — is een inhoudelijk standpunt over hoe het debat gevoerd mag worden, en telt mee als argument, ook als het niet direct over "stikstof" zelf gaat. Gebruik dan `typology: "other"` en `stance: "unclear"` tenzij een pro/contra-richting t.o.v. het beleid duidelijk is. Een kale roode-lijn-verklaring zonder reden ("afzwakking steunen we niet") blijft ook hier geen argument — de "geen onderbouwing = geen argument"-regel geldt onverkort.
- Eén sprekerbeurt kan 0, 1, of meerdere argumenten bevatten (bv. bij meerdere onderwerpen of tegenargumenten binnen dezelfde beurt).
- Elk genoemd getal, percentage, onderzoek, of feitelijke bewering met een bron ("uit onderzoek van X blijkt...", "volgens het RIVM...") noteer je als een claim, met alleen wat letterlijk gezegd is over de bron — beoordeel nooit of het getal of de bron klopt.
- `typology`: "factual" (feiten, cijfers, beleidsinhoudelijke of bestuurlijke constateringen — bv. een norm, een fractiestandpunt, wie iets wel/niet steunt), "moral" (ethisch/waarden), "economic" (kosten/baten), "legal" (verwijst naar een specifieke wet, regelgeving, of juridische toetsing/procedure), of "other". Gebruik "legal" alleen als het echt om wetgeving/regelgeving/juridische procedure gaat — een bestuurlijke keuze, beleidsnorm (bv. een GVE-norm of bufferzone-afstand), of politieke uitspraak van een bestuurder is meestal "factual" of "other", niet "legal".
- `stance`: "pro" of "contra" volgens de pro/contra-dimensie hierboven (niet t.o.v. het onderwerp "stikstof" in abstracte zin), of "unclear" als het standpunt niet eenduidig is. Kritiek op het huidige/voorgestelde beleid is `contra`, ook als de spreker dat doet door te verwijzen naar een eigen alternatief of eerder gevoerd beleid.

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok eromheen. Formaat:

```
{"arguments": [
  {
    "stance": "pro" | "contra" | "unclear",
    "typology": "factual" | "moral" | "economic" | "legal" | "other",
    "quote_text": "letterlijk citaat uit de brontekst",
    "quote_context": "korte context (optioneel, of null)",
    "claims": [
      {"claim_text": "wat genoemd is", "attributed_source_text": "aangehaalde bron, of null"}
    ]
  }
]}
```

Als er geen argumenten zijn: `{"arguments": []}`.

Brontekst (sprekerbeurt):
"""
Mevrouw Bromet (PRO): Nou, nee. Wij zijn helemaal nooit per se voor die innovaties geweest. Dat heb ik net al gezegd. Dit is niet ons plan. Wij zijn ook niet van het kabinet, hè. Wij willen onze steun uitspreken. Wij zijn welwillend om het aan meerderheden te helpen. Wij hebben een heleboel commentaar op een heleboel dingen, maar wat voor ons echt bovenaan de lijst staat, is dat wij elke verandering die een afzwakking betekent, niet zullen steunen. Er wordt een semantisch spelletje gespeeld over of het wel of geen afzwakking is. Verbeteringen: ja, daar willen wij voorstemmen. Afzwakkingen: nee. Wij gaan niet instemmen met elke kleine afzwakking of vermindering van de effectiviteit van het plan.
"""


