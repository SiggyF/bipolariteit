# PoC: eigen videoplayer op Debat Direct's open HLS-manifest

Losstaande, statische HTML-pagina (geen build-stap, geen dependency op de rest van de
repo) die aantoont dat een eigen player (hls.js) tegen Debat Direct's onderliggende,
niet-officiële HLS-manifest kan afspelen, seeken en een transparante overlay tonen —
inclusief zin-precieze synchronisatie via de Nederlandse ondertitel-track.

Achtergrond en volledige bevindingen: zie
[docs/tk-data-sources-overview.md](../../tk-data-sources-overview.md), secties 5a/5b,
en [issue #93](https://github.com/SiggyF/bipolariteit/issues/93) /
[issue #94](https://github.com/SiggyF/bipolariteit/issues/94).

## Gebruik

```
python3 -m http.server 8912
```

en open `http://localhost:8912/docs/poc/video-eigen-player/poc_ownplayer.html`.

## Debugtool: `frontend/public/playback_debug.html` (issue #148)

Los van de PoC hierboven staat in
[`frontend/public/playback_debug.html`](../../../frontend/public/playback_debug.html): geen
argumentmatching-demo, maar een diagnosetool voor afspeelproblemen (bv.
[issue #148](https://github.com/SiggyF/bipolariteit/issues/148), "Chrome Android speelt geen
video af"). Staat in `frontend/public/` (niet hier) zodat hij meedraait met de gewone
`make dev`-server -- geen aparte service nodig om hem op een telefoon te openen. Toont op het
scherm zelf (geen devtools nodig) omgevingsinfo, codec-/`Hls.isSupported()`-checks, een losse
fetch-check van het manifest (om CORS/providerproxy-problemen te onderscheiden van een
hls.js/video-elementprobleem) en een volledige event-/foutenlog (ook niet-fatale
hls.js-events, met een "kopieer log"-knop). Accepteert een alternatieve manifest-URL via het
invoerveld of `?src=`.

## Let op: dit is een throwaway PoC, geen productiecode

- De manifest-/ondertitel-URL en de gezochte quote (`QUOTE_NEEDLE`) zijn hardgecodeerd
  voor één specifiek debat (stikstof, 2026-07-01). Werkt niet voor andere debatten
  zonder aanpassing.
- Geen foutafhandeling voor quotes die niet woordelijk in de ondertitels voorkomen
  (VLOS-transcriptie en live-ondertiteling kunnen verschillen).
- De ruwe CDN-URL is niet gedocumenteerd/niet stabiel op lange termijn (zie sectie 5b) —
  in een echte implementatie zou deze per bezoek afgeleid moeten worden, niet
  opgeslagen.
- Licentievoorwaarden (attributie, geen archivering) uit sectie 5a zijn hier niet
  geïmplementeerd — nog te doen vóór eventueel productiegebruik.
