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

Dit is de eerste van drie stappen die samen de argumentenboom bouwen (zie
`pipeline/prompts/boomredactie.md` voor de twee redactiestappen die hierna
op jouw resultaat volgen). Jij structureert; de redactie beoordeelt en
verzwakt waar nodig — jij hoeft dus niet zelf al te wikken of een
onderbouwing/weerlegging sterk genoeg is, wel om 'm alleen aan te dragen als
je 'm oprecht plausibel vindt.

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

## 2. Structureer de selectie in relaties

Elke relatie tussen twee (of meer) argumenten heeft dezelfde vorm: een
`relation_type` (`support` of `conflict`), één of meer `premise_argument_ids`
die de relatie voeden, en één `target_argument_id` die ondersteund of
aangevallen wordt. Volg het pragma-dialectische onderscheid tussen
coördinatieve en subordinatieve argumentatie om te bepalen welke relatie
van toepassing is:

- **Subordinatief -> `support` met 1 premisse**: argument B is de
  onderbouwing van argument A, niet van het standpunt zelf (B is een reden
  om A te geloven — "A, want B"). `premise_argument_ids: [B]`,
  `target_argument_id: A`. Dit is de "fundering" die we specifiek zoeken —
  gebruik ook de vermelde `claims` (genoemde cijfers/bronnen) bij een
  argument als signaal dat het argument extra onderbouwd is, al zijn claims
  zelf geen aparte node.
- **Coördinatief, en samen een ander argument onderbouwend -> `support` met
  meerdere premissen**: een groep argumenten die *gezamenlijk* een ander
  argument (of elkaar) dragen — los van elkaar zou geen van beide voldoende
  zijn, samen wel. `premise_argument_ids: [B, C, ...]`,
  `target_argument_id: A`.
- **Coördinatief, zonder een ander argument te onderbouwen -> een
  `coordinatieve_groepen`-entry**: argumenten die *onafhankelijk* van elkaar
  eenzelfde punt maken, zonder dat ze een ander argument onderbouwen en
  zonder dat ze zelf in een `conflict`-relatie zitten. Dit is een puur
  weergavebundel voor buiten de confrontatie-as, geen `relations`-entry.
- **Weersproken -> `conflict`**: een pro- en een contra-argument die je als
  elkaars scherpste tegenhanger hebt gekozen (stap 1).
  `premise_argument_ids: [het aanvallende argument]`,
  `target_argument_id: [het aangevallen argument]`. Geef er meteen een
  `thema` bij: een korte (richtlijn: max. ~8 woorden), scherpe, neutrale
  titel die het **daadwerkelijke geschilpunt** benoemt — niet een
  onderwerplabel, en niet simpelweg de twee gists achter elkaar. Formuleer
  het bij voorkeur als vraag of spanning. Voorbeeld van het verschil: *niet*
  "reductie opent vergunningverlening weer — economische lasten voor
  boeren" (mechanisch, twee gists aan elkaar geplakt), *wel* "Moet de
  KDW-norm losgelaten worden om vergunningen weer te verlenen?" (het echte
  geschilpunt).

Elk argument krijgt een `gist` van **maximaal 3-4 woorden**, beginnend met
een hoofdletter (het is een korte titel, geen zinsfragment), en waar
zinvol een `samenvatting`: 1-2 zinnen (richtlijn: max. ~30 woorden) die
het argument samen met alles wat eronder hangt parafraseert tot één
leesbare, samenhangende stelling. Voor een los top-level argument zonder
onderbouwing is `samenvatting: null` (het citaat is al kort genoeg).

Regels (belangrijk, volg strikt):
- Jij bent geen scheidsrechter. Beoordeel nooit of een argument klopt,
  terecht is, of overtuigend is. Geef nooit het ene argument gelijk boven
  het andere.
- Jij verzint of parafraseert GEEN argumenttekst. `gist`/`samenvatting` zijn
  uitsluitend compacte samenvattingen voor de boomweergave, geen vervanging
  van het citaat — en elk `argument_id` dat je gebruikt moet een `id` uit
  het document zijn, nooit verzonnen.
- Niet elk `id` uit het document hoeft in de boom voor te komen — je hebt
  immers al geselecteerd in stap 1.
- Ken alleen een `support`-relatie toe als B *expliciet* een reden geeft om
  A te geloven, niet alleen omdat ze over hetzelfde thema gaan. Wees
  terughoudend met diepte.
- `thema` mag geen cijfers, bronnen of een eigen oordeel bevatten — puur het
  geschilpunt zelf. `samenvatting` mag, net als `gist`, GEEN feiten, cijfers
  of claims bevatten die niet letterlijk in de geciteerde argumenten staan.
- `scheme` mag je bij een `support`-relatie invullen als er overduidelijk
  een Walton-redeneerschema van toepassing is (bv. "Argument from Cause to
  Effect"), anders `null` — nooit gokken.

## 3. Controleer je Nederlandse tekst op spelfouten

Lees je eigen `gist`, `samenvatting`, `thema` en `label`-velden na op
spelfouten voordat je antwoordt, en corrigeer ze. Dit is puur een
taalcontrole van je eigen geformuleerde tekst — de letterlijke citaten uit
de brondata blijven ongewijzigd.

## Output

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok
eromheen, in dit exacte formaat (dit is een tussenformaat -- de redactiecheck
die hierna per relatie volgt vult `reden` pas in, dus dat veld laat jij hier
weg):

```json
{{
  "nodes": [
    {{"argument_id": 12, "gist": "Vergunningverlening loopt vast",
      "samenvatting": "Vergunningverlening zit vast omdat natuurvergunningen niet meer afgegeven worden."}},
    {{"argument_id": 45, "gist": "Ook natuurvergunningen vertraagd", "samenvatting": null}},
    {{"argument_id": 47, "gist": "Duizenden boeren gedwongen stoppen", "samenvatting": null}},
    {{"argument_id": 103, "gist": "Biologische boeren niet rendabel", "samenvatting": null}}
  ],
  "relations": [
    {{"relation_type": "support", "premise_argument_ids": [45], "target_argument_id": 12, "thema": null, "scheme": null}},
    {{"relation_type": "conflict", "premise_argument_ids": [47], "target_argument_id": 12,
      "thema": "Moet vergunningverlening voorrang krijgen boven de gevolgen voor boeren?", "scheme": null}}
  ],
  "coordinatieve_groepen": [
    {{"label": "economische lasten voor boeren", "samenvatting": "Boeren worden gedwongen te stoppen en biologische bedrijven zijn niet rendabel.",
      "argument_ids": [47, 103]}}
  ],
  "twijfelachtige_classificaties": [
    {{"argument_id": 88, "huidige_stance": "contra", "reden": "citaat pleit juist voor snellere reductie"}}
  ]
}}
```

Let op: argument 47 komt hier zowel in een `coordinatieve_groepen`-entry als in een `conflict`-relatie
voor -- dat mag. Een groepslid dat *zelf* ook een scherpe weerlegging is, wordt met zijn eigen kaart
uit de confrontatie-as getrokken; de rest van de groep (hier: 103) blijft als bundel buiten de
confrontatie-as staan.
