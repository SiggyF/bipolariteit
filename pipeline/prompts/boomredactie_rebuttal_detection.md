Je krijgt hieronder twee argumenten uit een Kamerdebat over "{topic}": een
doelwit-argument (`target`) en een argument dat er in de conceptboom tegenover
is gezet (`premise`).

Beantwoord **uitsluitend** de volgende feitelijke vraag, geen geldigheids-
oordeel: hoe sterk nemen `premise` en `target` een tegengestelde positie in
op hetzelfde specifieke geschilpunt (niet alleen hetzelfde onderwerp in het
algemeen)? Geef een `sterkte` tussen 0.0 en 1.0, geen ja/nee-keuze -- twee
argumenten kunnen elkaar gedeeltelijk raken zonder dat je gedwongen wordt dat
af te ronden naar een keuze.

Richtlijn voor de score:
- **Rond 1.0**: `premise` reageert expliciet op, parafraseert, of weerspreekt
  een claim uit `target`.
- **Rond 0.6-0.9**: `premise` geeft een eigen, zelfstandige reden die
  rechtstreeks een tegenovergestelde conclusie trekt over datzelfde
  specifieke deelvraagstuk -- ook als `premise` `target` niet noemt of
  citeert. Kamerdebatten bestaan grotendeels uit zelfstandig geformuleerde
  standpunten naast elkaar, niet uit letterlijke weerleggingen van elkaars
  woorden; eis dat laatste dus niet voor een hoge score.
- **Rond 0.0-0.3**: `premise` gaat over een ander deelaspect van hetzelfde
  bredere onderwerp (bv. "is kernenergie te duur" en "moet kernenergie de
  basis vormen" raken allebei kernenergie, maar zijn twee verschillende
  geschilpunten, geen weerlegging van elkaar), of raakt alleen hetzelfde
  onderwerp in het algemeen.

Dit is een functionele/tekstuele constatering (net als *rebuttal detection*
bij IBM Project Debater), geen oordeel of de weerlegging steekhoudend,
logisch geldig, of overtuigend is. Beoordeel dus nooit wie gelijk heeft.

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok
eromheen:

```json
{{"sterkte": 0.8, "reden": "korte, specifieke onderbouwing voor dit paar"}}
```

## Argumenten

```json
{tree_json}
```
