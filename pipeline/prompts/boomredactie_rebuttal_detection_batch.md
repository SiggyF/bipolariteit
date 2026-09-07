Je krijgt hieronder een lijst `relations` (elk met `target_argument_id` en
`premise_argument_ids`) en de bijbehorende `nodes` (argumenten met citaat),
uit een Kamerdebat over "{topic}".

Beantwoord voor **elke** relatie (op volgorde, index begint bij 0) dezelfde
feitelijke vraag, onafhankelijk van de andere relaties in de lijst: reageert
het `premise`-argument aantoonbaar op de kern van het `target`-argument —
noemt het, parafraseert het, of gaat het inhoudelijk in op hetzelfde
specifieke punt (niet alleen hetzelfde onderwerp in het algemeen)?

Dit is een functionele/tekstuele constatering (net als *rebuttal detection*
bij IBM Project Debater), geen oordeel of de weerlegging steekhoudend,
logisch geldig, of overtuigend is. Beoordeel dus nooit wie gelijk heeft, en
beoordeel elke relatie op haar eigen merites — twee relaties in deze lijst
kunnen verschillend uitvallen, ook als ze op hetzelfde onderwerp gaan.

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok
eromheen:

```json
{{
  "beoordelingen": [
    {{"relation_index": 0, "reageert_op_kern": true, "reden": "korte, specifieke onderbouwing voor dit paar"}},
    {{"relation_index": 1, "reageert_op_kern": false, "reden": "..."}}
  ]
}}
```

## Argumentenboom

```json
{tree_json}
```
