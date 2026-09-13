# Taalconventie: Nederlands/Engels

Aanleiding: [issue #7](https://github.com/SiggyF/bipolariteit/issues/7). De codebase mengde
Nederlands en Engels zonder afgesproken grens, soms binnen één bestand of zelfs één functie
(`frontend/src/lib/correspondence.ts`, `frontend/src/components/TagCorrespondenceMap.vue`).
Dat kost telkens een denkstap ("heet dit nu `rows` of `rijen`?").

De site gaat over een Nederlands onderwerp — het domein is Nederlands. Puur Engels zou dus
alsnog half-Nederlandse namen opleveren (vertaald en daardoor minder precies), en puur
Nederlands botst met de frameworks (Vue, Astro, ECharts, SQLAlchemy) waarvan de API's Engels
zijn en blijven. De vraag is dus niet "welke taal", maar "welke taal waar".

## De regel

1. **Identifiers** (bestandsnamen, types, functie-/variabelenamen, module-API's, testnamen):
   **Engels als default.**
2. **Uitzondering, twee gronden, beide smal en expliciet** — geen "elk domeinwoord mag",
   maar een concrete lijst:
   - **a) Onvertaalbare domeintermen** — een Nederlands domeinbegrip dat als identifier
     betekenis verliest bij vertaling: `kamerperiode`, `fractie`, `labelgroep`, `perspectief`,
     `drogreden`. Consequent gebruiken, niet naast een Engels synoniem in hetzelfde bestand.
   - **b) Schema-gespiegelde velden** — een veld dat 1:1 een externe bron volgt (DB-kolom,
     brondata-XML), ook als er wél een schone Engelse vertaling bestaat. Voorbeeld:
     `TagPoint.sleutel`/`beschrijving` (`frontend/src/lib/correspondence.ts`) zijn letterlijk
     de kolomnamen `sleutel`/`beschrijving` in `pipeline/db/schema.sql`. Reden: zo blijft
     DB → pipeline → frontend grep-baar zonder vertaaltabel in je hoofd.
   - Alles daarbuiten wordt vertaald. Generieke Nederlandse namen zonder domein- of
     schemabinding (`rij`, `tabel`, `spiegel`, `driedimensionaal`, `gefilterd`, ...) vallen
     niet onder de uitzondering, ook al voelen ze "Nederlands genoeg" aan.
   - **Mapnamen onder `data/` zijn ook bestandsnamen** (regel 1) — expliciet gemaakt bij de
     data-opruiming van issue #316, waar dit gaandeweg was scheefgegroeid (`data/plenary-map/`
     Engels naast `data/export/plenair-map/` Nederlands voor exact hetzelfde dataset). Geen
     terugwerkende-krachthernoeming van bestaande mappen die al ingeburgerd zijn (`plenair-map`
     blijft `plenair-map`, ook al staat "plenair" niet op de uitzonderingslijst hierboven — de
     naam zit te diep verweven in bestandsnamen/Vue-componenten/gepubliceerde data om nu om te
     draaien), maar een **nieuwe** map onder `data/` krijgt een Engelse naam tenzij hij onder
     a) of b) hierboven valt.
3. **Domeinwaarden** (string-*waarden*, niet identifiers): **Nederlands**. Bijvoorbeeld
   `"partij"`, `"persoon"`, `"kamerperiode"` als waarden van `RowUnit`, en alle tekst die de
   gebruiker op het scherm ziet.
   - **URL-routes vallen hieronder, niet onder regel 1.** Een Astro-routebestand
     (`pages/onderwerpen/index.astro`) is tegelijk bestandsnaam én de URL zelf — in
     file-based routing vallen die twee samen. Maar de *reden* achter regel 1
     (grep-baarheid, aansluiten bij Engelse framework-API's) gaat over interne
     code-samenhang die een eindgebruiker nooit ziet; een URL is het tegenovergestelde
     daarvan: het adres dat iemand leest, typt, deelt, bookmarkt. Dus Nederlands, en —
     net als bij UI-tekst — één woord per entiteitstype, consequent meervoud, index en
     detail genest onder hetzelfde segment (`/onderwerpen/`, `/onderwerpen/[slug]/`, niet
     twee verschillende woorden zoals voorheen `/debatten/` naast `/debat/[id]/`).
     Vastgesteld bij de hernoeming van `/topics/`→`/onderwerpen/`, `/about/`→`/over/`,
     `/partij/`→`/partijen/`, `/persoon/`→`/personen/`, `/perspectief/`→`/perspectieven/`
     en het samenvoegen van `/debat/[id]/` in `/debatten/[id]/`. Data-bestandsnamen
     (`data/export/topics/*.json`) zijn geen URL's en blijven identifiers (regel 1).
4. **Commentaar, docstrings, `docs/`, commitberichten, issue-teksten**: **Nederlands**. Dat is
   de taal waarin over dit project nagedacht wordt en het publiek is Nederlands.
5. **Interne, nooit-gebruiker-zichtbare error-/log-strings**: behandeld als commentaar-achtig,
   dus **Nederlands is prima**. Bijvoorbeeld `"onbekende filterdimensie"` in
   `frontend/src/lib/filters.ts` — die tekst komt nooit in de UI terecht, dus hoeft niet aan de
   identifier-regel te voldoen.
6. **Geen big-bang.** Per module opruimen zodat de diff reviewbaar blijft.

## Bestandsoverzicht

Niet uitputtend — de bestanden die de oorspronkelijke issue noemde, met besluit:

| Bestand | Besluit | Waarom |
|---|---|---|
| `frontend/src/lib/correspondence.ts` | Hernoemd (issue #7) | Module-interne namen (`rij`, `tabel`, `spiegel`, `tekens`, ...) vertaald naar Engels; geëxporteerde API en schema-velden ongewijzigd |
| `frontend/src/components/TagCorrespondenceMap.vue` | Hernoemd (issue #7) | Zelfde aanpak: script-locals vertaald, domeinvelden en Nederlandse UI-tekst blijven staan |
| `frontend/src/lib/types.ts` (`Tag.sleutel/beschrijving/labelgroep/perspectief`) | Laten staan | Uitzondering a (`labelgroep`, `perspectief`) / b (`sleutel`, `beschrijving` spiegelen DB-kolommen) |
| `frontend/src/lib/filters.ts` (dimension-keys, error-strings) | Laten staan | Dimension-keys zijn domeinwaarden (regel 3); error-strings vallen onder regel 5 |
| `pipeline/db/schema.sql`, `pipeline/db/seed_tags.py`, `pipeline/build_static_data.py` | Laten staan | Dit is de bron voor uitzondering b — tabel-/kolomnamen `labelgroep`, `perspectief` |
| `pipeline/periodes.py` (`kamerperiode`) | Laten staan | Uitzondering a, met naam genoemd in de issue |
| `pipeline/ingest/ingest_tk.py` (`fractie`) | Laten staan | Uitzondering a; komt bovendien direct uit externe XML-brondata (Tweede Kamer VLOS) |
| `docs/*.md` met Nederlandse titels | Laten staan | Docs zijn Nederlands per regel 4 |
| `crawlers/tweede_kamer/` | Laten staan | Pakketnaam = domeinnaam van de bron, geen losse identifier-keuze |

Andere modules die niet in de oorspronkelijke issue staan maar wel Nederlandse identifiers
bevatten (bv. verspreide plekken in `pipeline/`) worden per stuk opgepakt wanneer dat werk
toch al gebeurt — geen aparte hernoemingsronde voor de hele repo.
