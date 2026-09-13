Je analyseert één sprekerbeurt uit een {debate_context} over het onderwerp "{topic}". Spreker: {actor_name}{actor_party_suffix}.

Context:
{topic_description}

Jouw taak: identificeer elk afzonderlijk argument dat deze spreker inbrengt, volgens de annotatierichtlijn van Haddadan, Cabrio & Villata (2019, "Yes, we can! Mining arguments in 50 years of US presidential campaign debates") voor precies dit soort Amerikaanse verkiezingsdebatten:

- **Claim**: een uitspraak die de spreker moet rechtvaardigen om geaccepteerd te worden -- een beleidsstandpunt, stellingname, mening, of persoonlijk oordeel. Een claim is het doel van een argument.
- **Premise**: een bewering die de spreker geeft ter ondersteuning van een claim (reden, rechtvaardiging, voorbeeld, statistiek, beroep op ervaring).
- **Een kale claim is ook een geldig argument.** In tegenstelling tot wat je misschien zou verwachten, hoeft een claim GEEN onderbouwing te hebben om mee te tellen -- er zijn veel gevallen waarin een spreker een standpunt inneemt zonder daar in dezelfde beurt een reden voor te geven. Extraheer die kale claim dan gewoon als eigen argument (quote_text = alleen de claim).
- **Herhaalde claim = claim + premise.** Als de spreker hetzelfde kernpunt kort na elkaar in andere woorden herhaalt, geldt wat daartussen (of direct ertussenin) staat als premise voor die claim -- ook als dat tussenliggende deel zelf maar kort is of grotendeels dezelfde woorden herhaalt. Voorbeeld uit de richtlijn (Trump-Clinton, 26 september 2016): "Your husband signed NAFTA, which was one of the worst things that ever happened to the manufacturing industry. You go to New England, you go to Ohio, Pennsylvania, you go anywhere you want, Secretary Clinton, and you will see devastation where manufacture is down 30, 40, sometimes 50 percent. NAFTA is the worst trade deal maybe ever signed anywhere, but certainly ever signed in this country." -- de eerste en laatste zin herhalen dezelfde claim (NAFTA is een slechte deal), de middelste zin is de premise. Neem in zo'n geval de HELE combinatie (eerste claim + premise + herhaalde claim) op als één `quote_text`, ook als de "premise" zelf weinig meer is dan een korte herbevestiging.
- Een clausule is nooit tegelijk claim en premise.

Regels:
- Citeer letterlijk uit de brontekst (quote_text) -- verzin of parafraseer geen tekst.
- Eén sprekerbeurt kan 0, 1, of meerdere argumenten bevatten.
- Procedurele tekst (orde van de vergadering, "ik geef het woord aan...", dank-/welkomstwoorden) levert geen argument op.
- Jij bent geen scheidsrechter: beoordeel nooit of een argument klopt of overtuigend is.
- `stance`: gebruik altijd "unclear" (wordt in deze evaluatie niet beoordeeld).
- `typology`: "factual" (feiten, cijfers, constateringen), "moral" (ethisch/waarden), "economic" (kosten/baten), "legal" (wetgeving/regelgeving), of "other".

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok eromheen. Formaat:

```
{{"arguments": [
  {{
    "stance": "unclear",
    "typology": "factual" | "moral" | "economic" | "legal" | "other",
    "quote_text": "letterlijk citaat uit de brontekst (claim, of claim+premise samen)",
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
