Je labelt één reeds geëxtraheerd politiek argument over "{topic}" met tags uit een vaste taxonomie, aangeleverd door een argumentatie-onderzoeker.

Argument (spreker: {actor_name}{actor_party_suffix}, standpunt: {stance}, typologie: {typology}):
"""
{quote_text}
"""
{quote_context_block}

Belangrijk:
- Jij beoordeelt nooit of het argument klopt, terecht is, of overtuigend is. Dat geldt ook voor de labelgroep "Debatzetten": je labelt de argumentatieve VORM (bv. "dit is een ad-hominem-constructie"), nooit of dat gebruik van die vorm hier eerlijk, onterecht of overtuigend is. Een ad hominem of ander patroon kan een volkomen redelijk punt zijn -- dat is niet aan jou om te beoordelen.
- Ken alleen tags toe die je uit onderstaande lijst kiest, letterlijk overgenomen (exacte sleutel, geen parafrase, geen nieuwe tags verzinnen).
- Bij een labelgroep die "kies precies één" zegt: kies er ook echt maar één, of `null` als geen enkele optie past.
- Bij een labelgroep die "kies nul of meer" zegt: een lege lijst `[]` mag als niets van toepassing is.
- Elke toegekende tag krijgt een `reden`: één korte zin die uitlegt waarom DEZE tag op DIT specifieke argument van toepassing is (bv. citeer of parafraseer het deel van de tekst dat het patroon laat zien). Herhaal niet de generieke tag-beschrijving uit de taxonomie hieronder -- die kent de lezer al.

Taxonomie:
{tag_catalogue}

Antwoord ALLEEN met geldige JSON, geen uitleg, geen markdown-codeblok eromheen, in dit exacte formaat:

```
{tag_json_skeleton}
```
