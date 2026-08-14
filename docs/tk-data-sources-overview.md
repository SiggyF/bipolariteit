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

### 5a. Embedden + deep-linken naar een spreekmoment (onderzoek issue #93/#94, 2026-08-13)

Drie routes bestaan per debat: de kale detailpagina (`/{date}/{category}/{location}/{slug}`), `/video` (zelfde route-familie, andere naam: `debate-video`, deelt hetzelfde `path` als de kale route in de router-tabel) en `/embedded` (aparte route `debate-embedded`, eigen pad `.../embedded`, bedoeld voor iframe-gebruik). Geen van de drie stuurt `X-Frame-Options`/`frame-ancestors` mee — technisch dus alle drie te iframen.

- **Deep-link-formaat**: `?event=<eventType><ISO8601-tijdstip-met-offset>` (bv. `?event=speaker2026-07-01T13%3A43%3A39%2B0200`), `eventType` uit `{chairman_change, chairman, chairman_selection, interrupter, speaker}` — dit is exact het formaat dat `pipeline/build_static_data.py` als `document.speaker_video_url` exporteert.
- **Bevestigd werkend** (live browsertest + JS-breakpoints): de kale route en `/video` passen bij het laden zowel de starttijd als autoplay correct toe (teller sprong naar het juiste offset t.o.v. debatbegin). Mechanisme: `setSeekEvent(event) → getSeekEventPdt(event)` (regex haalt het tijdstip uit de string, **ongeacht of `eventType` matcht met een echt event** — een expliciet fout tijdstip met `eventType=speaker` op een moment dat in Debat Direct's eigen `events`-log eigenlijk `chairman` is, seekt gewoon naar dat tijdstip) `→ seekToPdt(pdt)`, vereist `this.startPdt` (gevuld uit de `#EXT-X-PROGRAM-DATE-TIME`-tag van het HLS-manifest — **aanwezig bevestigd**, dus geen live-only-beperking).
- **Bevestigd kapot** op `/embedded`: dezelfde `?event=...` wordt geaccepteerd in de URL (`new URLSearchParams(location.search).get('event')` geeft de juiste waarde terug) maar nooit doorgegeven aan de player — breakpoints op zowel de declaratie als de aanroep van `getSeekEventPdt` triggeren nooit op deze route, ook niet via de "Spreekmomenten"-zijbalk (die overigens exact dezelfde functieketen gebruikt als de URL-flow, geen apart mechanisme). Debat Direct's eigen "Embed"-knop genereert bovendien altijd een kale `/embedded`-URL zonder `event`-param — dit is dus een structurele beperking van hun embed-feature, niet een missend parameter aan onze kant.
- **Geen postMessage-API**: geen berichten in beide richtingen waargenomen. THEOplayer (de player-SDK die Debat Direct gebruikt, versie 11.2.0, sinds de overname door Dolby vermarkt als "Dolby OptiView", `SEE LICENSE AT theoplayer.com/terms`, geen gratis tier) levert zelf ook geen ingebouwd postMessage-protocol voor iframe-parent-communicatie ([THEOplayer-docs](https://github.com/THEOplayer/documentation/blob/main/theoplayer/getting-started/01-sdks/01-web/03-how-can-we-embed-iframe.mdx)) — dat moet een embeddende site zelf bouwen, en Debat Direct heeft dat niet gedaan.
- **Onderliggende HLS-bron** (via Network-tab op `/video`, niet gedocumenteerd/geen publieke API): master-manifest op `https://livestreaming.b67v2.tweedekamer.nl/{date}/{location-slug}/index.m3u8?hd=1&subtitles=vod&keyframes=1&start=<ISO8601>&end=<ISO8601>` (identiek voor alle drie de routes). **CORS volledig open** (`Access-Control-Allow-Origin: *`, geverifieerd met een cross-origin `Origin`-header). **Geen encryptie** (`#EXT-X-KEY:METHOD=NONE`). Bevat `#EXT-X-PROGRAM-DATE-TIME` per segment, meerdere kwaliteitsrenditions, een audiotrack en een **Nederlandse ondertitel-track** (`subtitles/nl-pol_VOD.m3u8`). Segmenten liggen op `cdn-vos-arbor-west-01.vos360.video` (Arbor-streaming-CDN).
- **Licentie**: "Licentievoorwaarden Audiovisueel Materiaal Tweede Kamer" (1 mei 2019, PDF op `www.tweedekamer.nl/sites/default/files/atoms/files/licentievoorwaarden_audiovisueel_materiaal_tweede_kamer.pdf`, gelinkt vanaf de algemene disclaimer-pagina, niet vanaf Debat Direct zelf ondanks de suggestie in hun embed-dialoog). Kern: gratis gebruik toegestaan voor journalistiek/vrijheid van meningsuiting/onderwijs-en-onderzoek (art. 3.2), verboden voor commercieel gebruik/reclame/ledenwerving (art. 3.3); verplicht bij gebruik: zichtbare TK-bronvermelding (bv. logo/watermerk), auteursrechtvermelding, link naar de licentievoorwaarden, vermelding of bewerkt (art. 4.2); verbod op archiveren/bewaren, vernietigen binnen één maand na verkrijging (art. 4.4) — **met een uitzondering die hier van toepassing is**: "Deze verplichtingen zijn niet van toepassing op materiaal — zoals TV-uitzendingen of onderwijsmateriaal — waarin gelicentieerd Audiovisueel Materiaal in overeenstemming met de geldende Licentievoorwaarden door de Gebruiker is verwerkt." Dit platform noemt zichzelf expliciet mede onderwijsmateriaal (zie `frontend/src/pages/about.astro`), dus valt archiveren van er-in-verwerkt materiaal (bv. een gemonteerde quote-badge-overlay, niet de losse ruwe stream) onder deze uitzondering. Losstaand van de audiovisuele licentie: de ondertitel-*tekst* zelf is een woordelijke weergave van een openbare Kamervergadering en valt onder de tekstlicentie op `www.tweedekamer.nl/applicaties/disclaimer`, niet onder de audiovisuele-materiaal-voorwaarden.
- **Besluit deze sessie (embedden via `/embedded`)**: **niet opgepakt** — te veel reverse-engineering van geminificeerde, propriëtaire code nodig om de kapotte deep-link zelf te repareren, en geen enkele legale haak (geen postMessage-API) om dat van buitenaf te compenseren.

### 5b. Eigen player op het open HLS-manifest — technische PoC (2026-08-13)

Vervolg op 5a: in plaats van hun `/embedded`-route te gebruiken, een losse pagina gebouwd met **hls.js** (MIT-licentie, gratis) rechtstreeks tegen het manifest uit 5a. Doel: de drie openstaande vragen ("kunnen we de ruwe URL krijgen, hoe stabiel is die, werkt seek/overlay daadwerkelijk") hard beantwoorden i.p.v. aannemen. PoC-bestand: [docs/poc/video-eigen-player/](poc/video-eigen-player/).

- **Herkomst van de ruwe URL**: geen kant-en-klare extractor (`yt-dlp` heeft geen extractor voor `debatdirect.tweedekamer.nl` — SPA, geen `<video>`-tag in de server-HTML). Wel bevestigd via de Network-tab tijdens normaal gebruik (zie 5a).
- **Stabiliteit, met historisch bewijs**: het eigen `~/src/echokamer`-project (2023, `data/youtube.jl`) bevat een `video_src` van toen: `https://livestreaming.b67.tweedekamer.nl/live/troelstrazaal/index.m3u8?hd=1&sourcetimestamps=1&subtitles=vod&start=...&end=...` — zelfde CDN-familie, zelfde queryparam-stijl als vandaag, maar **wel al gemigreerd**: domein `b67` (Azure Front Door, `tm-azurefd.net`) → `b67v2` (Akamai), padstructuur `live/{zaal}` → `{datum}/{zaal}`. Het oude domein resolvt nog in DNS maar geeft nu HTTP 500 op het oude pad. Conclusie: het *concept* is 3+ jaar stabiel, de *concrete URL* is minstens één keer gemigreerd — niet geschikt om langdurig op te slaan (in tegenstelling tot de `debatdirect.tweedekamer.nl/.../video`-paginalink, die we al wel opslaan als `video_url`).
- **CORS**: volledig open (`Access-Control-Allow-Origin: *`) op zowel het video/audio- als het ondertitel-manifest, geverifieerd met een cross-origin `Origin`-header.
- **Codecs**: `avc1` (H.264 High Profile) video, `mp4a.40.2` (AAC-LC) audio — beide alledaags, geen DRM (`EXT-X-KEY:METHOD=NONE`). In headless Playwright-Chromium gaf dit een `bufferIncompatibleCodecsError` (`MediaSource.isTypeSupported()` → `false`), maar dat bleek een beperking van die specifieke kale Linux-Chromium-build (zelfde patroon als de eerdere Widevine-non-bevinding) — **in een echte browser bevestigd werkend**: afspelen, `video.currentTime`-seek, en een transparante SVG-overlay (pointer-events: none, dus klikt door naar de native player-controls) werken allemaal.
- **Ondertitel-sync (nieuw, niet in het oorspronkelijke issue #94-voorstel)**: de NL-ondertitel-track (`subtitles/nl-pol_VOD.m3u8`, één groot WebVTT-bestand per debat) bevat de volledige woordelijke tekst met tijdcodes. In plaats van zelf de `X-TIMESTAMP-MAP`-omrekening te doen (foutgevoelig, cue-klok ≠ videoklok), laat je hls.js het spoor laden als een native `TextTrack` (`hls.subtitleTrack = 0`, spoor op `mode:'hidden'` gezet zodat de ondertiteling zelf niet getoond wordt) — de browser levert dan `cue.startTime`/`endTime` al correct uitgelijnd met `video.currentTime`. **Bevestigd werkend**: `arguments.quote_text` van een echt argument (id 23, stikstof-topic) woordelijk teruggevonden in de cues (lopende-tekst-met-offset-matching i.p.v. brossen cue-voor-cue-vensters, want een quote kan over meerdere cues lopen) — resultaat exact bruikbaar als seek-doel en als venster om een visuele marker (bv. een "drogreden"-badge) precies tijdens die zin te tonen, geverifieerd met een badge die alleen oplicht binnen het gematchte cue-tijdvak.
- **Consequentie voor #94**: dit is preciezer dan het oorspronkelijke idee (marker per hele sprekersbeurt) — een marker/overlay kan nu in principe **per zin/quote** i.p.v. per document/sprekersbeurt, zonder dat we zelf tijdcodes hoeven te schatten of bij te houden.
- **Openstaand**: dit is een PoC op één debat, niet geautomatiseerd of geschaald (geen bulk-matching, geen foutafhandeling voor quotes die niet woordelijk in de ondertitels staan door verschillen tussen VLOS-transcriptie en live-ondertiteling, geen omgang met de al genoemde URL-instabiliteit in productie). Licentieverplichtingen uit 5a gelden onverkort, met de onderwijsmateriaal-uitzondering (art. 4.4) en de aparte tekstlicentie voor de ondertitels zelf die daar staan beschreven — vandaar dat `pipeline/fetch_subtitles.py` (zie 5c) het VTT-bestand wél lokaal cachet.

### 5c. Server-side ondertitels ophalen (issue #93/#94, 2026-08-14)

Vervolg op 5b, nu zonder browser: `pipeline/fetch_subtitles.py` haalt en cachet het NL-ondertitel-VTT per debat, als voorbereiding op het zin-precies vullen van `arguments.start_seconds`/`end_seconds` (schema.sql, zie ook docs/design/videoplayer/README.md "Spannes verrijken"). Twee dingen die de 5b-PoC niet had (die draaide via de browser/hls.js) moesten hiervoor server-side alsnog uitgezocht worden:

- **Ruwe manifest-URL zonder locationId-naar-padnaam-vertaling**: `https://api.debatdirect.tweedekamer.nl/debates/{id}` (zelfde debat-GUID als de zoek-API uit punt 5, nu opgeslagen als `documents.debatdirect_id`) geeft direct `video.vodUrl` terug (bv. `.../2026-07-01/plenairezaal/index.m3u8?hd=1&subtitles=vod&keyframes=1`) — geen aparte afleiding nodig van `locationId` (`plenaire-zaal`, met streepje) naar het pad-segment in het manifest (`plenairezaal`, zonder streepje).
- **`start`/`end`-query-params zijn verplicht voor de ondertitel-rendition**: zonder die twee params ontbreekt de `#EXT-X-MEDIA:TYPE=SUBTITLES`-regel in het manifest stilzwijgend (geen fout, gewoon geen track). De API's eigen `startsAt`/`endsAt` (bv. `2026-07-01T13:35:26+0200`) volstaan als waarde; de server normaliseert zelf naar de fijnmazigere notatie die in de resulterende sub-playlist-URI verschijnt.
- **`X-TIMESTAMP-MAP`-klok is niet nul bij videobegin**: de cues in het VTT-bestand lopen op een eigen doorlopende klok (bv. begint bij `05:02:56` voor een debat dat om `13:35:26` startte), ondanks de `LOCAL:00:00:00.000`-header — vermoedelijk de encoder-uptime van die dag, niet iets met betekenis voor ons. Bevestigd bruikbaar als *relatieve* klok: het verschil tussen de cue van de allereerste zin van het debat en de cue van een bekende quote (argument 21, Van der Plas, "breed lachend het einde van duizenden boeren") kwam op ~359s uit, tegenover de spreektempo-schatting van 347s in `arguments-timed.json` — dicht genoeg om te bevestigen dat "eerste cue = ankerpunt t=0" een bruikbare calibratiestrategie is voor de matching-stap.
- **CDN-cachebug op het `.vtt`-endpoint** (Akamai): de respons wordt een aantal seconden gecachet **op path alleen, de querystring (`start`/`end`) genegeerd**. Twee activiteiten in dezelfde zaal op dezelfde dag (één doorlopende vergadering, meerdere agendapunten) die kort na elkaar opgevraagd worden, kregen zo allebei de VTT van de eerst-opgevraagde activiteit terug — zelfde bug bevestigd op zowel de master- als sub-playlist-stap. Reproduceerbaar met losse `curl`-requests (<5s ertussen: identieke, dus foute, content; 12s ertussen: correcte, verschillende content). Een extra cache-bustende querystring-param bleek **niet** te helpen (nog steeds gecachet op path); de oplossing in `pipeline/fetch_subtitles.py` is een throttle van 20s tussen opeenvolgende `.vtt`-requests op hetzelfde onderliggende pad (datum+zaal), gedeeld tussen alle activiteiten van diezelfde vergadering.
- **Matching + kalibratie nu gebouwd**: `pipeline/match_argument_spans.py` matcht `quote_text` woordelijk tegen de aaneengeregen, genormaliseerde cue-tekst (een quote kan over meerdere cues lopen) en kalibreert per debat via de mediaan van (ruwe cue-tijd − grove `published_at`-schatting) over alle gematchte quotes in dat debat — zie de docstring van dat bestand voor de volledige toelichting. Op het stikstof-topic (2026-08-14): 1798 van 2049 argumenten (88%) gematcht+gekalibreerd; de rest zijn vrijwel allemaal quotes uit één debat zonder live-ondertiteling (lege VTT, geen fout).

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

## 10. Officiële Bekendmakingen / KOOP (Handelingen — leesbare + machine-XML tekst)

Toegevoegd tijdens het uitzoeken van de "Check de Kamer"-brondeeplink (v1-launchplan): een
**derde, geheel apart systeem** naast OData en Debat Direct, met zijn eigen identifiers,
voor de officiële, gecorrigeerde Handelingen-tekst (het woordelijk verslag zoals het na
correctie definitief gepubliceerd wordt door KOOP/Overheid.nl — niet hetzelfde document als
de OData `Verslag`-resource, zie tabel hieronder).

- **SRU-zoekservice** (het opzoekmechanisme, geen documentbron zelf): `https://repository.overheid.nl/sru`
  — officiële "Search & Retrieve by URL"-standaard, handleiding lokaal in `docs/HandleidingSRU2.0.pdf`.
  Voorbeeldquery (vergaderjaar + vergaderingnummer → alle agendapunten van die dag):
  `https://repository.overheid.nl/sru?query=c.product-area==officielepublicaties AND dt.type=="Handeling" AND w.vergaderjaar=="2024-2025" AND w.publicatienummer=="87"&maximumRecords=100`
  — **let op de exacte veldnamen** (bevestigd via `?operation=explain&version=2.0`, niet zomaar aan te nemen uit de handleiding-tekst): `w.publicatienummer` (niet `publicationnummer`), `w.vergaderjaar`, `dt.type=="Handeling"` **enkelvoud** (niet `"Handelingen"` — die waarde bestaat ook maar is dan het verkeerde niveau/type).
- **Identifier-vorm**: `h-tk-{vergaderjaar zonder streepje}-{vergaderingnummer}-{agendapunt-itemnummer}`, bv. `h-tk-20242025-87-15`. Volledig losstaand van OData's GUID-identifiers (`Verslag.Id`, `Vergadering.Id`) — de enige gedeelde sleutel is `vergaderjaar`+`vergaderingnummer` (beide al beschikbaar via OData's `Vergadering`-entiteit, zie sectie 1), **niet** het agendapunt-itemnummer: dat moet je alsnog matchen op titel-tekst (bv. `Activiteit.Onderwerp` tegen `dcterms:title` van elk SRU-resultaat), want er is geen numerieke join op dat niveau.
- **Alleen gecorrigeerde/definitieve debatten hebben een Handeling-record.** Recente debatten (OData `Verslag.Status == "Ongecorrigeerd"`) leveren 0 SRU-resultaten op — dit is normaal, geen fout, en moet in een backfill-script gewoon `NULL` opleveren i.p.v. hard falen.

### Overzichtstabel: welke bron voor welk doel

| Doel | Bron/systeem | Identifier | Voorbeeld-URL |
|---|---|---|---|
| Machine-leesbare XML, **ruwe/lopende** tekst (incl. niet-gecorrigeerd) | OData `Verslag`-resource | GUID (`Verslag.Id`) | `https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0/Verslag/1b96d9e0-.../resource` |
| Mens-leesbare pagina, **video** van het debat | Debat Direct | slug (datum/categorie/locatie/titel) | `https://debatdirect.tweedekamer.nl/2025-05-22/natuur-en-milieu/plenaire-zaal/verslag-.../video` |
| Mens-leesbare pagina, **officieel gecorrigeerde tekst** van één agendapunt | Overheid.nl (KOOP), via SRU | `h-tk-{jaar}-{vergadering}-{item}` | `https://zoek.officielebekendmakingen.nl/h-tk-20242025-87-15.html` |
| Machine-leesbare XML van diezelfde **gecorrigeerde** tekst | Overheid.nl (KOOP), zelfde identifier | `h-tk-{jaar}-{vergadering}-{item}` | `https://zoek.officielebekendmakingen.nl/h-tk-20242025-87-15.xml` |
| PDF van diezelfde gecorrigeerde tekst (FRBR-repository, versiegeteld) | `repository.overheid.nl`, zelfde identifier | `h-tk-{jaar}-{vergadering}-{item}`, plus expliciet versienummer (`/1/`) | `https://repository.overheid.nl/frbr/officielepublicaties/h-tk/20242025/h-tk-20242025-87-13/1/pdf/h-tk-20242025-87-13.pdf` |
| Machine-leesbare XML, zelfde FRBR-repository-vorm | `repository.overheid.nl`, zelfde identifier | idem | `https://repository.overheid.nl/frbr/officielepublicaties/h-tk/20242025/h-tk-20242025-87-13/1/xml/h-tk-20242025-87-13.xml` |

Twee dingen vallen op: (1) de mens-leesbare en machine-leesbare varianten van de **gecorrigeerde**
Handelingen-tekst bestaan zowel op `zoek.officielebekendmakingen.nl` (kort, geen versienummer
— gebruik dit als canonieke link, komt overeen met SRU's `gzd:preferredUrl`) als op
`repository.overheid.nl/frbr/...` (met expliciet `/1/`-versienummer, ook pdf/odt beschikbaar);
(2) dit is een volledig ander document dan de OData `Verslag`-resource — twee aparte bronnen
voor twee aparte redenen (ruwe/altijd-beschikbare tekst vs. officieel gecorrigeerde tekst),
niet twee vormen van hetzelfde bestand.

## 11. tweedekamer.nl Activiteit-detailpagina via `Activiteit.Nummer` (opgelost: veruit de eenvoudigste "Check de Kamer"-link)

**Dit maakt sectie 10 grotendeels overbodig voor de v1-brondeeplink.** Gevonden via de officiële
FAQ ["Zijn de data gekoppeld aan de website van de Tweede Kamer?"](https://opendata.tweedekamer.nl/veelgestelde-vraag/zijn-de-data-gekoppeld-aan-de-website-van-de-tweede-kamer-0):
het attribuut `Activiteit.Nummer` (bv. `"2025A03345"`, een leesbare code — niet de GUID `Id`) bouwt
direct een URL naar de eigen tweedekamer.nl-detailpagina van die Activiteit:

- Plenaire vergaderingen: `https://tweedekamer.nl/debat_en_vergadering/plenaire_vergaderingen/details/activiteit?id=` + `Nummer`
- Commissievergaderingen: `https://tweedekamer.nl/debat_en_vergadering/commissievergaderingen/details?id=` + `Nummer`

**Geverifieerd, twee gevallen:**
1. `https://www.tweedekamer.nl/debat_en_vergadering/plenaire_vergaderingen/details/activiteit?id=2025A03345` (`Activiteit.Nummer` voor de bekende stikstofdebat van 22 mei 2025, `Onderwerp="Debat over het verslag van de ministeriële commissie Economie en Natuurherstel inzake de stikstofproblemen"`) — HTTP 200, pagina bevat zowel "verslag" (Handelingen-link) als "Debat Direct" (video-link). **Eén pagina die beide al voor ons koppelt** — geen aparte SRU-lookup of titel-matching (sectie 10) nodig.
2. `https://www.tweedekamer.nl/debat_en_vergadering/plenaire_vergaderingen/details/activiteit?id=2026A02765` (`Activiteit.Nummer` voor het recente, nog niet gecorrigeerde stikstofdebat van 1 juli 2026) — ook HTTP 200. **Werkt dus ook voor debatten die nog geen Handelingen-record hebben** (sectie 10's grootste beperking), waarschijnlijk omdat de pagina zelf degradeert naar wat er wél al is (video/agenda) als de Handelingen-tekst nog ontbreekt.

**Waarom dit praktisch zoveel simpeler is dan sectie 10**: onze crawler (`crawlers/tweede_kamer/tweede_kamer/odata.py`) doorloopt nu al de keten `Activiteit -> Vergadering -> Verslag` om een debat op onderwerp te vinden (zie sectie 1) — we hébben de juiste `Activiteit`-rij dus al te pakken tijdens het crawlen, `Nummer` zit al in die respons. Geen extra systeem (SRU), geen fuzzy titel-matching, geen aparte "nog niet gepubliceerd"-uitzondering nodig.

**Nog te doen voor implementatie**: `Activiteit.Nummer` + `Soort` (voor plenair-vs-commissie-URL-keuze) moeten nog daadwerkelijk doorgegeven worden van de crawler naar `pipeline/ingest/ingest_tk.py` (momenteel wordt de Activiteit alleen gebruikt om het juiste debat te *vinden*, niet opgeslagen als brondata voor `documents`) — dit is de kolom die eerder `handelingen_url` genoemd was in het schema/plan; gezien deze vondst is een neutralere naam als `documents.tweedekamer_activiteit_url` toepasselijker (dekt zowel plenair als commissie, en linkt naar meer dan alleen de Handelingen-tekst).

## Open vragen voor een vervolgsessie

1. Is er een productievere combinatie van deze bronnen voor topic-discovery dan onze huidige `Activiteit.Onderwerp`-substring-match (bv. Debat Direct's `q=`-zoekfunctie, of `Zaak`/`Kamerstukdossier`)?
2. Is de tweedekamer.nl Autonomy-zoekfunctie praktisch bruikbaar (programmatisch, zonder sessiegebonden `form_build_id`-problemen)?
3. Is het de moeite waard om alsnog een issue bij de officiële maintainers in te dienen over Activiteit↔Vergadering — en zo ja, met welke argumentatie (zie de eerdere reflectie: het concrete topic→transcript-gebruiksdoel, niet "andere projecten hebben dit ook niet")?
4. Wil je `video_url` daadwerkelijk implementeren via de `tkconv`-aanpak (Debat Direct search + heuristiek), en zo ja, in `build_static_data.py` of een aparte enrichmentstap?
5. ~~Hoe robuust moet de titel-matching worden tussen `Activiteit.Onderwerp` (OData) en `dcterms:title` (SRU/Handelingen)...~~ **Vervallen** — zie sectie 11: `Activiteit.Nummer` geeft een directe tweedekamer.nl-link zonder titel-matching, dus dit is niet meer nodig voor de brondeeplink.
