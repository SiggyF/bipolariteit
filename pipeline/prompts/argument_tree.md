Je krijgt de volledige lijst van reeds geëxtraheerde, letterlijke argumenten met standpunt "{stance}" over het onderwerp "{topic}". De boomstructuur zelf (onderwerp → standpunt) staat al vast; jouw taak heeft twee onderdelen:

1. **Structureren** van déze argumenten in een argumentatieboom, volgens het pragma-dialectische onderscheid tussen coördinatieve en subordinatieve argumentatie.
2. **Samenvatten**: elk argument krijgt een `gist` van **maximaal 3-4 woorden** — puur zodat iemand die de hele boom in één oogopslag bekijkt, meteen ziet waar elk argument over gaat, zonder alle citaten te hoeven lezen.

Structuur (pragma-dialectisch):
- **Coördinatief**: een groep argumenten die *gezamenlijk* het standpunt (of een ander argument) dragen — los van elkaar zou geen van beide voldoende zijn, samen wel. Bijvoorbeeld: "de maatregel is te duur" + "de maatregel raakt vooral kleine bedrijven" kunnen samen één economische lijn vormen.
- **Subordinatief**: argument B verdedigt niet het standpunt zelf, maar juist argument A (B is een reden om A te geloven — "A, want B"). Dat geeft diepte: A staat direct onder het standpunt, B (en eventueel C die op zijn beurt B verdedigt) staat als kind onder A.
- **Meervoudig (multiple)**: twee argumenten die *onafhankelijk* van elkaar het standpunt dragen (elk zou op zichzelf al genoeg zijn) horen gewoon als aparte top-level knopen naast elkaar, niet in dezelfde coördinatieve groep.

Regels (belangrijk, volg strikt):
- Jij bent geen scheidsrechter. Beoordeel nooit of een argument klopt, terecht is, of overtuigend is. Geef nooit het ene argument gelijk boven het andere.
- Jij verzint of parafraseert GEEN argumenttekst. Elk argument heeft al een eigen `id` en letterlijke `quote_text` in de input, die blijft de bron van waarheid — `gist` is uitsluitend een compacte samenvatting voor de boomweergave, geen vervanging van het citaat.
- `gist`: maximaal 3-4 woorden, geen volledige zin, geen lidwoord-opsmuk ("de", "een" mag je weglaten als het korter kan). Neutraal, geen oordeel, geen aanname die niet letterlijk in het citaat staat. Bijvoorbeeld bij het citaat "De vergunningverlening voor de bouw van huizen is compleet vastgelopen" is een goede gist "vergunningverlening loopt vast", niet "de spreker vindt dat de vergunningverlening voor woningbouw is vastgelopen".
- `label` (bij een coördinatieve groep) is óók een korte, neutrale samenvatting (max. ~6 woorden) van de gedeelde reden — geen oordeel, geen aanname die niet in de citaten zelf staat.
- Ken alleen een subordinatieve relatie toe (`children`) als B *expliciet* een reden geeft om A te geloven, niet alleen omdat ze over hetzelfde thema gaan — bij twijfel: laat B als eigen top-level knoop staan (of in een coördinatieve groep) in plaats van als kind van A.
- Wees terughoudend met diepte: de meeste argumenten hebben geen subordinatieve kinderen. Verzin geen relatie om de boom interessanter te maken.
- Elk `id` uit de input moet **exact één keer** ergens in de boom voorkomen (als los top-level argument, als lid van een coördinatieve groep, of als subordinatief kind) — nooit twee keer, nooit ontbrekend. Elk voorkomen van een `argument_id` heeft een eigen `gist`.

Argumenten (`id`: citaat, typologie, tags):
{arguments_block}

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok eromheen. Elke knoop is óf een los argument (`"argument_id"` + `"gist"`) óf een coördinatieve groep (`"label"` + `"arguments"`, een lijst van minimaal 2 `{{"argument_id", "gist"}}`-objecten); beide mogen optioneel `"children"` hebben voor subordinatieve argumenten (zelfde vorm: `"argument_id"` + `"gist"`). Formaat:

```
{{"nodes": [
  {{"argument_id": 12, "gist": "vergunningverlening loopt vast", "children": [
    {{"argument_id": 45, "gist": "ook natuurvergunningen vertraagd"}}
  ]}},
  {{"label": "economische lasten voor boeren", "arguments": [
    {{"argument_id": 47, "gist": "duizenden boeren gedwongen stoppen"}},
    {{"argument_id": 103, "gist": "biologische boeren niet rendabel"}}
  ], "children": []}}
]}}
```
