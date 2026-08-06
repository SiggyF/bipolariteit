Je krijgt hierboven (of als bijgevoegd bestand) een document met alle reeds
geëxtraheerde, letterlijke argumenten over het onderwerp "{topic}", verdeeld
in pro- en contra-argumenten. Het document begint met de pro/contra-
dimensie van dit onderwerp ("Pro/contra-dimensie van dit onderwerp") —
lees die eerst: "pro" en "contra" zijn geen eigenschap van het argument op
zich, maar een classificatie t.o.v. die dimensie, en dezelfde definitie is
ook bij de extractie van de argumenten gebruikt. Elk argument heeft
daarnaast een `id`, een letterlijk citaat, een typologie
(factual/moral/economic/legal/other), tags, en eventueel onderbouwende
claims. Dit is de volledige set, niet een voorgeselecteerde steekproef.

**Voorbehoud:** de pro/contra-indeling komt uit een eerdere, niet-foutloze
automatische classificatie — vertrouw er niet blind op. Zie je een argument
dat overduidelijk verkeerd staat, gebruik het dan niet in je selectie, en
rapporteer het apart onder `twijfelachtige_classificaties` in de output.

Je taak heeft twee onderdelen:

## 1. Selecteer een subset van elkaar weersprekende argumenten

Kies uit de volledige pro- en contra-lijst een beperkte, behapbare subset
(richtlijn: 15-30 argumenten per standpunt, niet honderden) van argumenten
die inhoudelijk het scherpst tegenover elkaar staan — d.w.z. een pro- en een
contra-argument die dezelfde onderliggende kwestie raken, zodat je ze samen
kunt lezen als een debat over dat deelthema. Argumenten die geen duidelijke
tegenhanger aan de andere kant hebben, laat je weg: liever een kleine,
scherpe selectie dan een volledige maar vlakke lijst.

Er is nog geen vooraf ingevulde lijst met bekende opposities meegegeven —
zoek zelf, puur op basis van de citaten, welke pro- en contra-argumenten
inhoudelijk het scherpst tegenover elkaar staan.

## 2. Structureer de selectie in een argumentatieboom

Volg het pragma-dialectische onderscheid tussen coördinatieve en
subordinatieve argumentatie:

- **Coördinatief**: een groep argumenten die *gezamenlijk* het standpunt (of
  een ander argument) dragen — los van elkaar zou geen van beide voldoende
  zijn, samen wel.
- **Subordinatief**: argument B is de onderbouwing van argument A, niet van
  het standpunt zelf (B is een reden om A te geloven — "A, want B"). Dat
  geeft diepte: A staat direct onder het standpunt, B staat als `children`
  onder A. Dit is de "fundering" die we vandaag specifiek zoeken — gebruik
  ook de vermelde `claims` (genoemde cijfers/bronnen) bij een argument als
  signaal dat het argument extra onderbouwd is, al zijn claims zelf geen
  aparte node.
- **Meervoudig**: argumenten die *onafhankelijk* van elkaar het standpunt
  dragen horen als aparte top-level knopen naast elkaar, niet in dezelfde
  coördinatieve groep.

Elk argument krijgt een `gist` van **maximaal 3-4 woorden**.

Regels (belangrijk, volg strikt):
- Jij bent geen scheidsrechter. Beoordeel nooit of een argument klopt,
  terecht is, of overtuigend is. Geef nooit het ene argument gelijk boven
  het andere.
- Jij verzint of parafraseert GEEN argumenttekst. `gist` is uitsluitend een
  compacte samenvatting voor de boomweergave, geen vervanging van het
  citaat — en elk `argument_id` dat je gebruikt moet een `id` uit het
  document zijn, nooit verzonnen.
- Niet elk `id` uit het document hoeft in de boom voor te komen — je hebt
  immers al geselecteerd in stap 1. Wél moet elk `argument_id` dat je
  gebruikt hooguit één keer voorkomen (nooit twee keer).
- Ken alleen een subordinatieve relatie toe (`children`) als B *expliciet*
  een reden geeft om A te geloven, niet alleen omdat ze over hetzelfde thema
  gaan. Wees terughoudend met diepte.
- `label` (bij een coördinatieve groep) is een korte, neutrale samenvatting
  (max. ~6 woorden) van de gedeelde reden.

## Output

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok
eromheen. Er is nog geen vastgelegd formaat voor dit resultaat — kies zelf
een heldere, consistente structuur die in elk geval bevat:

- per standpunt (pro/contra) de geselecteerde argumenten, elk met hun `id`
  en een korte `gist` (max. 3-4 woorden);
- de coördinatieve/subordinatieve structuur uit stap 2 (welke argumenten
  samen een groep vormen, welke argumenten onderbouwing zijn van welk ander
  argument);
- de pro/contra-paren die je als elkaars scherpste tegenhanger hebt
  gekozen;
- `twijfelachtige_classificaties`: argumenten die je bent tegengekomen met
  een overduidelijk verkeerde pro/contra-stance (uit stap 1), met hun `id`,
  de huidige (foute) stance, en een korte reden.

Licht kort (een paar zinnen) toe waarom je voor die structuur gekozen hebt,
zodat we samen kunnen beoordelen of dit een bruikbaar formaat is voordat we
het ergens op vastleggen.

Voorbeeld (puur ter illustratie van het soort structuur, geen vast format —
kies zelf betere veldnamen/vorm als dat logischer is):

```json
{{
  "pro": {{"nodes": [
    {{"argument_id": 12, "gist": "vergunningverlening loopt vast", "children": [
      {{"argument_id": 45, "gist": "ook natuurvergunningen vertraagd"}}
    ]}}
  ]}},
  "contra": {{"nodes": [
    {{"label": "economische lasten voor boeren", "arguments": [
      {{"argument_id": 47, "gist": "duizenden boeren gedwongen stoppen"}},
      {{"argument_id": 103, "gist": "biologische boeren niet rendabel"}}
    ], "children": []}}
  ]}},
  "oppositions": [
    {{"argument_a_id": 12, "argument_b_id": 47, "relation_type": "direct_rebuttal"}}
  ],
  "twijfelachtige_classificaties": [
    {{"argument_id": 88, "huidige_stance": "contra", "reden": "citaat pleit juist voor snellere reductie"}}
  ],
  "toelichting": "korte uitleg van de gekozen structuur"
}}
```
