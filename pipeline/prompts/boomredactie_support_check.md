Je krijgt hieronder twee argumenten uit een Kamerdebat over "{topic}": een
doelwit-argument (`target`) en een argument dat er in de conceptboom als
onderbouwing onder is gezet (`premise`, "B onderbouwt A").

Beantwoord **uitsluitend** de volgende feitelijke vraag, geen geldigheids-
oordeel: hoe sterk geeft het `premise`-argument aantoonbaar een reden om het
`target`-argument te geloven? Geef een `sterkte` tussen 0.0 en 1.0, geen
ja/nee-keuze.

Richtlijn voor de score:
- **Rond 1.0**: `premise` noemt een oorzaak, gevolg, voorbeeld, bron, of
  andere expliciete grond die specifiek op de kern van het target-argument
  aansluit.
- **Rond 0.0-0.3**: `premise` raakt alleen hetzelfde onderwerp in het
  algemeen, zonder een specifieke, aansluitende grond te geven.

Dit is een functionele/tekstuele constatering, geen oordeel of de
onderbouwing overtuigend, voldoende, of feitelijk correct is. Beoordeel dus
nooit of het argument klopt.

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok
eromheen:

```json
{{"sterkte": 0.8, "reden": "korte, specifieke onderbouwing voor dit paar"}}
```

## Argumenten

```json
{tree_json}
```
