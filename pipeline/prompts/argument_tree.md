Je krijgt de volledige lijst van reeds geëxtraheerde, letterlijke argumenten met standpunt "{stance}" over het onderwerp "{topic}". De boomstructuur zelf (onderwerp → standpunt) staat al vast; jouw taak is uitsluitend het structureren van déze argumenten in een argumentatieboom, volgens het pragma-dialectische onderscheid tussen coördinatieve en subordinatieve argumentatie:

- **Coördinatief**: een groep argumenten die *gezamenlijk* het standpunt (of een ander argument) dragen — los van elkaar zou geen van beide voldoende zijn, samen wel. Bijvoorbeeld: "de maatregel is te duur" + "de maatregel raakt vooral kleine bedrijven" kunnen samen één economische lijn vormen.
- **Subordinatief**: argument B verdedigt niet het standpunt zelf, maar juist argument A (B is een reden om A te geloven — "A, want B"). Dat geeft diepte: A staat direct onder het standpunt, B (en eventueel C die op zijn beurt B verdedigt) staat als kind onder A.
- **Meervoudig (multiple)**: twee argumenten die *onafhankelijk* van elkaar het standpunt dragen (elk zou op zichzelf al genoeg zijn) horen gewoon als aparte top-level knopen naast elkaar, niet in dezelfde coördinatieve groep.

Regels (belangrijk, volg strikt):
- Jij bent geen scheidsrechter. Beoordeel nooit of een argument klopt, terecht is, of overtuigend is. Geef nooit het ene argument gelijk boven het andere.
- Jij verzint of parafraseert GEEN argumenttekst. Elk argument heeft al een eigen `id` en letterlijke `quote_text` in de input — jouw enige taak is de structuur (welk argument staat waar, en welke argumenten vormen samen een coördinatieve groep) te bepalen.
- Een `label` (bij een coördinatieve groep) is een korte, neutrale samenvatting (max. ~8 woorden) van de gedeelde reden — geen oordeel, geen aanname die niet in de citaten zelf staat.
- Ken alleen een subordinatieve relatie toe (`children`) als B *expliciet* een reden geeft om A te geloven, niet alleen omdat ze over hetzelfde thema gaan — bij twijfel: laat B als eigen top-level knoop staan (of in een coördinatieve groep) in plaats van als kind van A.
- Wees terughoudend met diepte: de meeste argumenten hebben geen subordinatieve kinderen. Verzin geen relatie om de boom interessanter te maken.
- Elk `id` uit de input moet **exact één keer** ergens in de boom voorkomen (als los top-level argument, als lid van een coördinatieve groep, of als subordinatief kind) — nooit twee keer, nooit ontbrekend.

Argumenten (`id`: citaat, typologie, tags):
{arguments_block}

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok eromheen. Elke knoop is óf een los argument (`"argument_id"`) óf een coördinatieve groep (`"label"` + `"argument_ids"`, minimaal 2 ids); beide mogen optioneel `"children"` hebben voor subordinatieve argumenten. Formaat:

```
{{"nodes": [
  {{"argument_id": 12, "children": [
    {{"argument_id": 45}}
  ]}},
  {{"label": "korte samenvatting van de gedeelde reden", "argument_ids": [47, 103], "children": []}}
]}}
```
