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

## 3. Benoem het geschilpunt en bundel gelijksoortige argumenten

Naast de structuur uit stap 2 heb je twee extra velden nodig, omdat een
mechanische samenvoeging van gists niet leesbaar genoeg is:

- **`thema`** bij elke oppositie in `oppositions[]`: een korte (richtlijn:
  max. ~8 woorden), scherpe, neutrale titel die het **daadwerkelijke
  geschilpunt** benoemt — niet een onderwerplabel, en niet simpelweg de twee
  gists achter elkaar. Formuleer het bij voorkeur als vraag of spanning.
  Voorbeeld van het verschil: *niet* "reductie opent vergunningverlening weer
  — economische lasten voor boeren" (mechanisch, twee gists aan elkaar
  geplakt), *wel* "Moet de KDW-norm losgelaten worden om vergunningen weer te
  verlenen?" (het echte geschilpunt).
- **`samenvatting`** bij elke node met `children` en bij elke coördinatieve
  `label`-groep in `pro.nodes`/`contra.nodes`: 1-2 zinnen (richtlijn: max.
  ~30 woorden) die de gebundelde argumenten samen parafraseren tot één
  leesbare, samenhangende stelling. Voor een los top-level argument zonder
  kinderen is `samenvatting` niet nodig (het citaat is al kort genoeg).

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
- `thema` mag geen cijfers, bronnen of een eigen oordeel bevatten — puur het
  geschilpunt zelf.
- `samenvatting` mag, net als `gist`, GEEN feiten, cijfers of claims
  bevatten die niet letterlijk in de geciteerde argumenten van die
  node/groep staan. Het is een leesbare laag bovenop de citaten, geen
  vervanging en geen nieuwe bewering.

## 4. Controleer je Nederlandse tekst op spelfouten

Lees je eigen `gist`, `samenvatting`, `thema` en `label`-velden na op
spelfouten voordat je antwoordt, en corrigeer ze. Dit is puur een
taalcontrole van je eigen geformuleerde tekst — de letterlijke citaten uit
de brondata blijven ongewijzigd.

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
  gekozen, elk met een `thema` uit stap 3;
- bij elke node met `children` en elke coördinatieve groep: een
  `samenvatting` uit stap 3;
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
    {{"argument_id": 12, "gist": "vergunningverlening loopt vast",
      "samenvatting": "Vergunningverlening zit vast omdat natuurvergunningen niet meer afgegeven worden.",
      "children": [
      {{"argument_id": 45, "gist": "ook natuurvergunningen vertraagd"}}
    ]}}
  ]}},
  "contra": {{"nodes": [
    {{"label": "economische lasten voor boeren",
      "samenvatting": "Boeren worden gedwongen te stoppen en biologische bedrijven zijn niet rendabel.",
      "arguments": [
      {{"argument_id": 47, "gist": "duizenden boeren gedwongen stoppen"}},
      {{"argument_id": 103, "gist": "biologische boeren niet rendabel"}}
    ], "children": []}}
  ]}},
  "oppositions": [
    {{"argument_a_id": 12, "argument_b_id": 47, "relation_type": "direct_rebuttal",
      "thema": "Moet vergunningverlening voorrang krijgen boven de gevolgen voor boeren?"}}
  ],
  "twijfelachtige_classificaties": [
    {{"argument_id": 88, "huidige_stance": "contra", "reden": "citaat pleit juist voor snellere reductie"}}
  ],
  "toelichting": "korte uitleg van de gekozen structuur"
}}
```
