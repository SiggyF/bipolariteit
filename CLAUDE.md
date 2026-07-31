# Taal: Nederlands/Engels

De site gaat over een Nederlands onderwerp; de code draait op Engelstalige frameworks
(Vue, Astro, ECharts, SQLAlchemy). Zie [issue #7](https://github.com/SiggyF/bipolariteit/issues/7)
en [docs/taalconventie.md](docs/taalconventie.md) voor de volledige toelichting en het
bestandsoverzicht. Kort samengevat:

- **Identifiers** (types, functies, variabelen, module-API's, testnamen): **Engels**, met
  een smalle, expliciete uitzondering:
  - a) domeintermen zonder goede Engelse vertaling: `kamerperiode`, `fractie`,
    `labelgroep`, `perspectief`, `drogreden`;
  - b) velden die 1:1 een externe bron spiegelen (DB-kolom, brondata-XML), ook als er wél
    een schone vertaling bestaat — bv. `TagPoint.sleutel`/`beschrijving`, die letterlijk de
    kolomnamen zijn in `pipeline/db/schema.sql`.
  - Buiten deze twee gronden: vertalen. Generieke Nederlandse namen zonder domein- of
    schemabinding (`rij`, `tabel`, `spiegel`, `driedimensionaal`, ...) horen er niet bij.
- **Domeinwaarden** (strings zoals `"partij"`, `"kamerperiode"`, en alle UI-tekst): **Nederlands**.
- **Commentaar, docstrings, `docs/`, commitberichten**: **Nederlands**.
- **Interne, nooit-gebruiker-zichtbare error-/log-strings** (bv. `"onbekende filterdimensie"`
  in `frontend/src/lib/filters.ts`): behandeld als commentaar — Nederlands is prima.

Geen big-bang-hernoeming van de hele repo; per module oppakken zodat de diff reviewbaar blijft.
