Je analyseert één sprekerbeurt uit een Tweede Kamer-debat over het onderwerp "{topic}". Spreker: {actor_name}{actor_party_suffix}.

Context over de pro/contra-dimensie van dit onderwerp:
{topic_description}

Jouw taak: identificeer elk afzonderlijk politiek argument dat deze spreker inbrengt over "{topic}". Een argument heeft altijd twee delen: een standpunt (pro/contra/onduidelijk t.o.v. de pro/contra-dimensie hierboven) ÉN een reden/onderbouwing die dat standpunt ondersteunt. Beide delen moeten in het citaat zelf aanwezig zijn.

Regels (belangrijk, volg strikt):
- Jij bent geen scheidsrechter. Beoordeel nooit of een argument klopt, terecht is, of overtuigend is. Geef nooit het ene standpunt gelijk boven het andere.
- Citeer letterlijk uit de brontekst (quote_text) — verzin of parafraseer geen tekst.
- **Geen onderbouwing = geen argument.** Een kale stellingname, intentieverklaring, wens, of statement zonder reden is GEEN argument, ook niet als het stellig of politiek geladen klinkt. Voorbeelden van wat je NIET moet extraheren: "Ik strijd hier tot de laatste dag voor de boeren" (intentie, geen reden), "Afzwakking steunen we niet" (kaal standpunt, geen reden), "Dat vinden wij een goed idee" (instemming zonder reden), "Wij vinden het natuurbelang heel erg zwaar wegen" (waardestelling zonder reden). Extraheer dit soort zinnen alleen als de reden er letterlijk bij staat.
- **Eén punt = één argument.** Als de spreker hetzelfde punt in opeenvolgende zinnen verder uitwerkt, aanvult, of herhaalt (bv. een stelling gevolgd door de reden erachter, of twee keer dezelfde kernboodschap in andere woorden binnen dezelfde beurt), voeg dit samen tot één `quote_text` (met de tussenliggende tekst inbegrepen) in plaats van het op te knippen in meerdere argumenten. Knip alleen op naar een nieuw argument als er echt een ander punt, andere reden, of ander standpunt begint.
- Procedurele tekst levert GEEN argumenten op: orde van de vergadering, spreektijd-afspraken, "ik geef het woord aan...", "ik stel voor dat...", dank-/welkomstwoorden, en vergelijkbare voorzitters-chatter. Als de hele sprekerbeurt procedureel is, geef een lege lijst terug.
- **Uitspraken over de behandeling van een voorstel leveren geen argument op**: aankondigen hoe een fractie stemt, een motie oordeel Kamer geven of ontraden, en verzoeken om een debat of een andere volgorde. Ook niet als er een reden bij staat ("we stemmen tegen omdat die afspraak niet is nagekomen") — die reden onderbouwt dan de behandeling, niet een standpunt op de as. Legt de spreker in dezelfde beurt wél uit waarom het beleid zelf goed of slecht is, extraheer dat deel dan gewoon.
- Let op het verschil tussen procedurele chatter (hierboven, GEEN argument) en metadiscours (WEL een argument, mits onderbouwd): een uiting over de legitimiteit, reikwijdte, bevoegdheid, of spelregels van het debat zelf — bv. "dit is geen dunne lijn... ik benoem hier de feiten" — is een inhoudelijk standpunt over hoe het debat gevoerd mag worden, en telt mee als argument, ook als het niet direct over "{topic}" zelf gaat. Gebruik dan `typology: "other"` en `stance: "unclear"` tenzij een pro/contra-richting t.o.v. het beleid duidelijk is. Een kale roode-lijn-verklaring zonder reden ("afzwakking steunen we niet") blijft ook hier geen argument — de "geen onderbouwing = geen argument"-regel geldt onverkort.
- Eén sprekerbeurt kan 0, 1, of meerdere argumenten bevatten (bv. bij meerdere onderwerpen of tegenargumenten binnen dezelfde beurt).
- Elk genoemd getal, percentage, onderzoek, of feitelijke bewering met een bron ("uit onderzoek van X blijkt...", "volgens het RIVM...") noteer je als een claim, met alleen wat letterlijk gezegd is over de bron — beoordeel nooit of het getal of de bron klopt.
- `typology`: "factual" (feiten, cijfers, beleidsinhoudelijke of bestuurlijke constateringen — bv. een norm, een fractiestandpunt, wie iets wel/niet steunt), "moral" (ethisch/waarden), "economic" (kosten/baten), "legal" (verwijst naar een specifieke wet, regelgeving, of juridische toetsing/procedure), of "other". Gebruik "legal" alleen als het echt om wetgeving/regelgeving/juridische procedure gaat — een bestuurlijke keuze, beleidsnorm (bv. een GVE-norm of bufferzone-afstand), of politieke uitspraak van een bestuurder is meestal "factual" of "other", niet "legal".
- `stance`: het standpunt ligt altijd op de as tussen de twee polen hierboven — niet tussen regering en oppositie, en niet t.o.v. het onderwerp "{topic}" in abstracte zin. Leid het standpunt uitsluitend af uit de onderbouwing: welke van de twee polen wordt daarmee gesteund? Dat een spreker het kabinet aanvalt of verdedigt zegt niets, want een maatregel kan volgens de spreker te ver gaan óf juist niet ver genoeg — beide zijn kritiek, maar op tegengestelde polen.
- Steunt de onderbouwing geen van beide polen, dan is het standpunt "unclear". "De wachttijden zijn te lang, want de dienst is onderbezet" is een argument met een onderbouwing, maar kiest geen pool. Verbindt de spreker er wél een richting aan ("...dus moet de instroom omlaag", "...dus moet de capaciteit omhoog"), dan bepaalt die richting het standpunt.
- Gaat het argument over een ánder onderwerp dan "{topic}" — bijvoorbeeld een aangrenzend beleidsterrein of een heel andere betekenis van hetzelfde woord — gebruik dan `stance: "ander_onderwerp"` en vul het veld `ander_onderwerp` met het onderwerp waar het wél over gaat (bv. "arbeidsmigratie"). Laat `ander_onderwerp` in alle andere gevallen weg of op null.

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok eromheen. Formaat:

```
{{"arguments": [
  {{
    "stance": "pro" | "contra" | "unclear" | "ander_onderwerp",
    "typology": "factual" | "moral" | "economic" | "legal" | "other",
    "ander_onderwerp": "alleen bij stance ander_onderwerp: het onderwerp waar dit argument wél over gaat, anders null",
    "quote_text": "letterlijk citaat uit de brontekst",
    "quote_context": "korte context (optioneel, of null)",
    "claims": [
      {{"claim_text": "wat genoemd is", "attributed_source_text": "aangehaalde bron, of null"}}
    ]
  }}
]}}
```

Als er geen argumenten zijn: `{{"arguments": []}}`.

Brontekst (sprekerbeurt):
"""
{content}
"""
