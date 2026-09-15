Je beoordeelt of één specifieke tag uit een vaste taxonomie van toepassing is op één reeds geëxtraheerd politiek argument over "{topic}", aangeleverd door een argumentatie-onderzoeker.

Argument (spreker: {actor_name}{actor_party_suffix}, standpunt: {stance}, typologie: {typology}):
"""
{quote_text}
"""
{quote_context_block}

Te beoordelen tag -- labelgroep {labelgroep} ({labelgroep_beschrijving}):
- {tag_sleutel}: {tag_beschrijving}
{voorbeelden_block}
Belangrijk:
- Jij beoordeelt nooit of het argument klopt, terecht is, of overtuigend is -- uitsluitend of dit ene patroon hier aanwezig is.
- Twijfelgeval? Kies dan "van_toepassing": false (nooit gokken).
- Bij "van_toepassing": true hoort een "reden": één korte zin, argument-specifiek (niet de generieke tag-beschrijving hierboven herhalen), en een "quote_fragment": een kort, aaneengesloten stukje tekst LETTERLIJK overgenomen uit de quote hierboven dat aanwijst waar de tag op slaat (of null als de tag op de hele quote slaat).
- Bij "van_toepassing": false blijven "reden" en "quote_fragment" null.

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok eromheen, in dit exacte formaat:

```
{{"van_toepassing": true of false, "reden": "<korte onderbouwing, of null>", "quote_fragment": "<letterlijk fragment, of null>"}}
```
