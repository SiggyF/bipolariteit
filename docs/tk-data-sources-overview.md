# Overzicht: Tweede Kamer data-bronnen, API's en libraries

Verzameld tijdens een verkenningssessie (2026-07-22). Doel: een feitelijke
inventarisatie van wat er allemaal bestaat rond Tweede Kamer open data, zodat
een vervolgsessie kan bepalen hoe we deze het beste inzetten — geen
conclusies of keuzes hierin, puur een overzicht van wat is aangetroffen en
wat nog niet is uitgezocht.

**Niet gedaan**: een GitHub-issue richting de officiële maintainers over de
ontbrekende Activiteit↔Vergadering-relatie. Eerdere aanname dat `tkapi` en
`tkconv` hetzelfde probleem "bevestigden" klopte niet bij nader inzien —
`tkapi` implementeert de relatie simpelweg niet (zegt niets over of hij
bestaat), en `tkconv`s workaround betreft een andere relatie (video↔Activiteit,
niet Activiteit↔Vergadering). Pas een issue overwegen ná een vervolgsessie
die dit gedegen uitzoekt.

## 1. OData API (officieel)

- **Basis-URL**: `https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0`
- **Docs**: https://opendata.tweedekamer.nl/documentatie/odata-api, informatiemodel: https://opendata.tweedekamer.nl/documentatie/informatiemodel
- Gestructureerde entiteiten: `Activiteit`, `Vergadering`, `Verslag`, `Persoon`, `Fractie`, `Zaak`, `Document`, `Kamerstukdossier`, `Agendapunt`, `Commissie`, e.a.
- **Bevestigde relatie**: `Verslag` ↔ `Vergadering` (echte FK, `Vergadering_Id`-veld op `Verslag`; ook zichtbaar via SyncFeed-content).
- **Bevestigd ontbrekend**: geen enkel veld/relatie tussen `Activiteit` en `Vergadering` — gecontroleerd via (a) een volledig live `Activiteit`-record (alle velden bekeken, geen Vergadering-referentie), (b) het informatiemodel (Vergadering niet vermeld als gerelateerde entiteit van Activiteit, vice versa), (c) `tkapi`'s eigen klassen (zie punt 3).
- Onze eigen workaround (`crawlers/tweede_kamer/tweede_kamer/odata.py`): datum/tijd-heuristiek (±1 dag vanwege tijdzone-valkuil, gefilterd op Kamer/Soort, dichtstbijzijnde datum). Werkt in de praktijk (getest tegen 10+ debatten), geen gegarandeerde 1-op-1 relatie.
- **Nog niet uitgezocht**: of `Zaak`/`Kamerstukdossier` een betere/directere route bieden voor topic-discovery dan `Activiteit.Onderwerp` (genoemd als open vraag in `docs/plan.md` sinds de eerste spike, nooit vervolgd).

## 2. SyncFeed API (officieel)

- **Basis-URL**: `https://gegevensmagazijn.tweedekamer.nl/SyncFeed/2.0/Feed?category=<Entiteit>`
- **Docs**: https://opendata.tweedekamer.nl/documentatie/syncfeed-api
- Atom 1.0-feed, bedoeld voor incrementele synchronisatie (`<link rel="next">`), niet voor gericht queryen.
- **Bevestigd**: bevat geen relatiedata die niet ook al via OData beschikbaar is. `Verslag`-entries tonen een `Vergadering`-ref, maar dat is dezelfde info als `Vergadering_Id` in OData (geen nieuwe brug). `Activiteit`-entries in de steekproef waren merendeels verwijder-tombstones; niet gecontroleerd of levende `Activiteit`-entries wél een Vergadering-ref bevatten (klein herhalingsrisico, laag prioriteit — de officiële docs bevestigen sowieso al dat er geen relatie gedocumenteerd is).

## 3. `tkapi` (Python library)

- **Repo**: https://github.com/openkamer/tkapi (lokaal aanwezig: `~/src/tkapi`, recent bijgewerkt door gebruiker naar de huidige versie)
- Python ORM-wrapper rond de OData API. Synchroon/blokkerend (`requests.get`, geen async) — niet direct verenigbaar met een Scrapy-gebaseerde aanpak zonder thread-adapters.
- `Activiteit`- en `Vergadering`-klassen hebben geen enkele kruisverwijzing naar elkaar (`tkapi/activiteit.py`, `tkapi/vergadering.py`) — bevestigt dat de relatie niet bestaat, maar dit was geen bewuste keuze van `tkapi` om een workaround te vermijden; de library probeert het simpelweg niet.
- Wél aanwezig: `get_resource_url_or_none()` (bouwt de resource-URL via een OData-annotatie) en een rijke set filters/enums per entiteit.
- **Conclusie vorige sessie** (zie eerdere reflectie): had ons hooguit ~25 regels aan query-boilerplate bespaard; lost geen van beide kernproblemen (Activiteit↔Vergadering, resource-download) op, en het synchrone model past niet goed bij Scrapy.

## 4. `tkconv` (C++ project, Bert Hubert)

- **Repo**: https://github.com/berthubert/tkconv (lokaal aanwezig: `~/src/tkconv`)
- Actief onderhouden, vergelijkbare architectuur als de onze: TK open data → SQLite → website.
- Segmenteert `Verslag` per sprekerbeurt (`VergaderingSpreker`/`VergaderingSprekerTekst`-tabellen, `tkparse.cc`) via de échte `Verslag→Vergadering`-FK — heeft dus, net als wij, geen Activiteit↔Vergadering-brug nodig voor de kernfunctionaliteit (sprekersegmentatie).
- Lost een ánder probleem op met een datum/tijd-heuristiek: video-koppeling. Zie `tkserv.cc` (rond regel 1130-1195, [permalink](https://github.com/berthubert/tkconv/blob/2e80cfbc150e4d66c828b6816bfb3ba8152cbbf8/tkserv.cc#L1130-L1195)): queryt Debat Direct's zoek-API op datum, matcht kandidaten op tijdstip-middelpunt-nabijheid + zaalnaam + duur-ratio-sanitycheck.
- URL-opbouw (uit `partials/activiteit.html`): `videourl = https://debatdirect.tweedekamer.nl/{debateDate}/{categoryIds[0]}/{locationId}/{slug}`, met `+'/video'` (directe link) en `+'/embedded'` (iframe-embed, stabiel opslaanbaar).

## 5. Debat Direct (voorheen "Debat Gemist")

- **Front-end**: https://debatdirect.tweedekamer.nl (JS SPA; opvolger van `debatgemist.tweedekamer.nl`, die er nu naartoe redirect)
- **API**: `https://api.debatdirect.tweedekamer.nl/debates/{id}` — geeft debatmetadata terug incl. een `meetingId`-veld (GUID-vorm, lijkt op `Vergadering.Id` maar **niet geverifieerd** of het daadwerkelijk matcht) en een `events`-array (chairman/speaker-wissels met timestamps).
- **Zoek-API**: `https://cdn.debatdirect.tweedekamer.nl/search` (Elasticsearch-backed, `APP_ELASTIC_URL` in de front-end bundle). Ondersteunt:
  - Datumbereik: `?van=YYYY-MM-DD&tot=YYYY-MM-DD`
  - Vrije tekst: `?q=<zoekterm>` — **getest**: `q=stikstof` geeft 20 hits per pagina, `hits.total.value=137`, met relevantere/breder resultaat dan een letterlijke substring-match op `Activiteit.Onderwerp` (bv. "Landbouw- en natuurbeleid" matcht ook, wat geen "stikstof" bevat).
  - Paginering: `vanaf=<offset>` (bevestigd werkend, 20 per pagina)
  - Verplichte overige params: `sortering=relevant`, `appVersion=<versie>`, `platform=web`, `totalFormat=new`
  - Resultaatvelden: `name`, `slug`, `startsAt`/`endsAt`, `locationName`, `debateDate`, `categoryIds`, `locationId` — **geen** directe OData-ID's.
- **Video**: de `<video>`-tag op de site gebruikt een `blob:`-URL (browser-lokaal, MediaSource-based) — niet direct opslaanbaar. De stabiele URL-vorm zit in `tkconv`'s aanpak (zie punt 4).
- **Bevestigd werkend**: alle 5 eigen bekende stikstofdebatten succesvol teruggevonden door op debatdatum te zoeken en de kandidaat met de dichtstbijzijnde starttijd + `locationName == "Plenaire zaal"` te kiezen — inclusief een geval met twee gelijknamige sessies op dezelfde dag, correct gedisambigueerd op tijdstip-nabijheid (2 min vs. ~3 uur verschil).

## 6. `debatgemist.tweedekamer.nl` (legacy, dood)

- Oude, server-side gerenderde site. Had een eigen Drupal-volltekstzoekfunctie (`search_api_views_fulltext`), gescraped door `~/src/echokamer`'s `zoeken.py` (Scrapy-spider + BeautifulSoup).
- Redirect nu (301) naar `debatdirect.tweedekamer.nl`. De oude scraping-aanpak werkt niet meer (JS-SPA, geen server-rendered HTML meer).

## 7. `tweedekamer.nl/zoeken` (officiële site search)

- **URL-vorm**: `https://www.tweedekamer.nl/zoeken?qry=<term>&fld_tk_categorie=Kamerstukken&srt=date:desc:date&form_build_id=...&form_id=tk_external_data_autonomy_search_form`
- Drupal-formulier (`data-drupal-selector="tk-external-data-autonomy-search-form"`), backend genaamd naar **HP/Micro Focus Autonomy IDOL** — een derde, geheel apart zoeksysteem naast OData en Debat Direct's Elasticsearch.
- Indexeert een andere corpus (Kamerstukken/officiële documenten, niet debatten/video).
- **Nog niet uitgezocht**: wat de daadwerkelijke resultaten bevatten, of er een stabiele/programmatische manier is om te queryen (Drupal `form_build_id` is normaliter sessiegebonden, wat statisch/herhaalbaar queryen kan bemoeilijken — niet getest), en of dit een betere route biedt richting `Zaak`/`Kamerstukdossier` (die wél echte OData-relaties hebben, in tegenstelling tot Activiteit↔Vergadering).

## 8. `~/src/echokamer` (eigen project, 2023)

- Scrapy-project van de gebruiker zelf: scrapete het oude `debatgemist.tweedekamer.nl` (nu dood) en gebruikte daarnaast `tkapi` direct tegen de OData API (`notebooks/verslagen-rss.ipynb`).
- **Relevant**: cellen 13-18 van dat notebook laten zien dat de gebruiker in 2023 al `Vergaderingen` én `Activiteiten` apart ophaalde via `tkapi`, maar nooit een werkende join tussen beide heeft gebouwd — onafgemaakte verkenning, geen antwoord.
- Downloadt videofragmenten van de oude debatgemist-site via `ffmpeg` (notebooks `parliament-scraper.ipynb`, `faces.ipynb`) voor een "supercuts"-achtig doel (herhalende zinsneden in de Kamer).

## 9. OpenDataPortaal GitHub-issues (officieel)

- **Repo**: https://github.com/TweedeKamerDerStaten-Generaal/OpenDataPortaal/issues
- [#115](https://github.com/TweedeKamerDerStaten-Generaal/OpenDataPortaal/issues/115) — officiële bevestiging dat videoverslagen geen ID-koppeling hebben met het gegevensmagazijn ("op geen enkele manier opgenomen"), staat op de backlog. Bert Hubert reageert hier ook, met de link naar zijn `tkconv`-aanpak.
- Geen bestaande issue specifiek over Activiteit↔Vergadering (gecontroleerd, geen duplicaat-risico als hier later alsnog een issue over komt).
- Andere issues gecontroleerd (#87, #75) betreffen Document↔Zaak-relaties, niet relevant voor dit onderwerp.

## Open vragen voor een vervolgsessie

1. Is er een productievere combinatie van deze bronnen voor topic-discovery dan onze huidige `Activiteit.Onderwerp`-substring-match (bv. Debat Direct's `q=`-zoekfunctie, of `Zaak`/`Kamerstukdossier`)?
2. Is de tweedekamer.nl Autonomy-zoekfunctie praktisch bruikbaar (programmatisch, zonder sessiegebonden `form_build_id`-problemen)?
3. Is het de moeite waard om alsnog een issue bij de officiële maintainers in te dienen over Activiteit↔Vergadering — en zo ja, met welke argumentatie (zie de eerdere reflectie: het concrete topic→transcript-gebruiksdoel, niet "andere projecten hebben dit ook niet")?
4. Wil je `video_url` daadwerkelijk implementeren via de `tkconv`-aanpak (Debat Direct search + heuristiek), en zo ja, in `build_static_data.py` of een aparte enrichmentstap?
