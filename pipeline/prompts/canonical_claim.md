Je krijgt hieronder {n} citaten uit een Kamerdebat over "{topic}", die volgens
een embedding-clustering (cosine-similariteit tussen bge-m3-embeddings van de
citaten zelf) hetzelfde onderliggende punt maken. Alle citaten hebben dezelfde
stance ({stance}).

Formuleer **uitsluitend** de gedeelde stelling die alle citaten samen maken,
in één zin, in het Nederlands. Dit is een samenvattende, feitelijke taak
(vergelijkbaar met IBM Project Debater's Key Point Analysis) -- geen
interpretatie- of geldigheidsoordeel. Gebruik alleen wat expliciet in de
citaten staat, verzin geen extra onderbouwing of nuance die er niet in staat.

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok
eromheen:

```json
{{"canonical_claim": "de gedeelde stelling, één zin"}}
```

## Citaten

```json
{quotes_json}
```
