# Performance-meting: DebateVideoView-payload (issue #119)

Samenvatting van de metingen tijdens het werk aan #119 (payload van de
`DebateVideoView`/`ClaimsHighlights`-islands compact houden). De ruwe
Lighthouse-rapporten (`localhost_4321-*.html`) zijn niet bewaard -- hieronder
de relevante cijfers.

## Uitgangspunt (vóór #119)

Volledige `Argument[]`-array als Astro-prop naar `client:only="vue"`-islands,
twee keer geserialiseerd (`DebateVideoView` én `ClaimsHighlights` kregen
allebei dezelfde array):

- Homepage-HTML: ~3,1 MB
- Debatpagina-HTML: ~2,5 MB

## Tussenstap: hele onderwerp fetchen (regressie)

Eerste poging haalde `onderwerpen/<slug>.json` (het hele onderwerp, alle
debatten) client-side op en filterde daaruit één debat. HTML kromp naar
~80 KB, maar de JSON-fetch werd groter dan het oorspronkelijke probleem:

- Homepage: 11,2 MB (energietransitie.json)
- Debatpagina: 10,5 MB (asiel.json)

Lighthouse bevestigde dat dit echt slechter was (niet alleen "meer bytes"):
performance-score 0,21, LCP 25,7 s, TBT 42-69 s, total byte weight ~40 MB
(waarvan het grootste deel overigens de echte HLS-videostream + dev-mode
ongeminificeerde JS was, niet de JSON zelf).

## Definitieve fix: per debat publiceren

`scripts/export_public_data.ts` publiceert nu ook een apart bestand per debat
(`data/export/gepubliceerd/debatten/<debateId>.json`, via
`lib/debateId.ts`'s `groupByDebateId`). `DebateVideoView`/`ClaimsHighlights`
delen één gedeelde fetch (`lib/debateArguments.ts`) van precies dát bestand.

- Homepage-HTML: ~80 KB (build: 15 KB)
- Debatpagina-HTML: ~76 KB (build: 10,5 KB)
- Debat-JSON-fetch: 1,0-1,8 MB (was 2,5-4,8 MB inline, tussentijds zelfs
  10-11 MB) -- niet-blokkerend, video start los daarvan meteen via directe
  `rawVideoUrl`/`posterUrl`-props.

## Kanttekening bij Lighthouse-scores op deze pagina's

De totale Lighthouse-score/LCP op `/` en `/debatten/[id]/` blijft laag/traag,
ook na de fix -- dat zit 'm niet in de argumentdata, maar in twee losstaande
factoren die hier altijd al golden en buiten de scope van #119 vallen:

1. De pagina speelt een echte HLS-livestream af (tientallen MB aan
   videosegmenten, autoplay) -- dat kost altijd bandbreedte, ongeacht deze
   fix.
2. `astro dev` serveert ongeminificeerde dev-bundels (hls.js alleen al ~4 MB);
   een productiebuild (`astro build`) is aanzienlijk kleiner.

Een poging om dit tijdens het testen te isoleren (autoplay/`autoStartLoad`
tijdelijk uitzetten) leverde een onbetrouwbare LCP-waarde op (55 s, terwijl
alle netwerkactiviteit al bij 5,4 s klaar was) -- vermoedelijk een
meetartefact doordat het `<video>`-element dan nooit een frame decodeert, niet
een echt performanceprobleem. Die tijdelijke wijzigingen zijn teruggedraaid;
niet meegenomen in de PR.
