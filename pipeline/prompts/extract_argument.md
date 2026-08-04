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
- Ook aangekleed stemgedrag blijft procedureel: aankondigen hoe een fractie stemt, een motie oordeel Kamer geven of ontraden, of vragen om een andere volgorde van behandeling is GEEN argument, ook niet als er een reden bij staat ("we stemmen tegen omdat die afspraak niet is nagekomen", "ik ontraad deze motie want het klopt feitelijk niet"). Het gaat dan over de behandeling van een voorstel, niet over de inhoudelijke pro/contra-dimensie. Extraheer wél de inhoudelijke onderbouwing als de spreker in dezelfde beurt uitlegt wáárom het beleid zelf goed of slecht is.
- Let op het verschil tussen procedurele chatter (hierboven, GEEN argument) en metadiscours (WEL een argument, mits onderbouwd): een uiting over de legitimiteit, reikwijdte, bevoegdheid, of spelregels van het debat zelf — bv. "dit is geen dunne lijn... ik benoem hier de feiten" — is een inhoudelijk standpunt over hoe het debat gevoerd mag worden, en telt mee als argument, ook als het niet direct over "{topic}" zelf gaat. Gebruik dan `typology: "other"` en `stance: "unclear"` tenzij een pro/contra-richting t.o.v. het beleid duidelijk is. Een kale roode-lijn-verklaring zonder reden ("afzwakking steunen we niet") blijft ook hier geen argument — de "geen onderbouwing = geen argument"-regel geldt onverkort.
- Eén sprekerbeurt kan 0, 1, of meerdere argumenten bevatten (bv. bij meerdere onderwerpen of tegenargumenten binnen dezelfde beurt).
- Elk genoemd getal, percentage, onderzoek, of feitelijke bewering met een bron ("uit onderzoek van X blijkt...", "volgens het RIVM...") noteer je als een claim, met alleen wat letterlijk gezegd is over de bron — beoordeel nooit of het getal of de bron klopt.
- `typology`: "factual" (feiten, cijfers, beleidsinhoudelijke of bestuurlijke constateringen — bv. een norm, een fractiestandpunt, wie iets wel/niet steunt), "moral" (ethisch/waarden), "economic" (kosten/baten), "legal" (verwijst naar een specifieke wet, regelgeving, of juridische toetsing/procedure), of "other". Gebruik "legal" alleen als het echt om wetgeving/regelgeving/juridische procedure gaat — een bestuurlijke keuze, beleidsnorm (bv. een GVE-norm of bufferzone-afstand), of politieke uitspraak van een bestuurder is meestal "factual" of "other", niet "legal".
- `stance`: "pro" of "contra" volgens de pro/contra-dimensie hierboven (niet t.o.v. het onderwerp "{topic}" in abstracte zin), of "unclear" als het standpunt niet eenduidig is. Bepaal de richting aan de hand van wélke pool de onderbouwing steunt, niet aan de hand van of de spreker het kabinet steunt of bekritiseert: kritiek op het beleid komt van beide polen (het gaat te ver, of juist niet ver genoeg). Alleen als de onderbouwing geen kant kiest, is het `unclear`.

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok eromheen. Formaat:

```
{{"arguments": [
  {{
    "stance": "pro" | "contra" | "unclear",
    "typology": "factual" | "moral" | "economic" | "legal" | "other",
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
