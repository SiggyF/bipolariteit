# QGIS-schets: A0-printkaart plenaire/debattenkaart

Verkennende QGIS-schets voor [issue #215](https://github.com/SiggyF/bipolariteit/issues/215)
(hoge-resolutie A0-PDF-export van de plenaire/debattenkaart). Dit is een
losse schets, geen vastgelegde eindrichting -- zie `README.md` in deze map
voor het bijbehorende designer-pakket (met deze schets als een van de twee
referentiebeelden).

## Bestanden

- **`a0-umap.qgz`** -- het QGIS-projectbestand, staat in deze map (samen met
  het designer-pakket, zie hierboven). Verwijst (relatief) naar:
  - `../../plenair-map-clusters-full.geojson` (clusterhulls, gegenereerd
    door `scripts/a0_map/export_clusters_geojson.py`)
  - `../../plenair-map-full.pmtiles` (puntenlaag, laag `points`, gegenereerd
    door `pipeline/tiling/build_pyramid.py`)

  Beide export-bestanden zelf zijn NIET ingecheckt (`.gitignore`, zie
  `data/export/*-full.geojson`/`*.pmtiles`) -- regenereer ze lokaal voor je
  het project opent:
  ```
  uv run python -m pipeline.plenary_map.cluster --start 2000-01-01 --end 2026-08-30 \
      --label full --full-range-topics stikstof,abortus,asiel,energietransitie \
      --export-frontend --export-suffix=-full --cluster-level-sizes 4000,1200,350,100,30
  uv run python -m pipeline.tiling.build_pyramid \
      --input data/export/plenair-map-full.json \
      --out data/export/plenair-map-full.pmtiles \
      --grid-out data/export/plenair-map-full-grid.json
  uv run python scripts/a0_map/export_clusters_geojson.py \
      data/export/plenair-map-clusters-full.json \
      data/export/plenair-map-clusters-full.geojson \
      --grid data/export/plenair-map-full-grid.json
  ```
  Projectie: EPSG:3857 (Pseudo-Mercator) -- de clusterlaag gaat via een
  echte 3857->WGS84-terugprojectie (zie `export_clusters_geojson.py`'s
  `make_rescaler()`), zodat de vervorming consistent is met hoe de
  `.pmtiles`-puntenlaag zelf al (impliciet, via standaard tegeladressering)
  gepositioneerd wordt.
- **`clusters.qml`** -- stijl voor de clusterlaag: categorized-by-`parent_id`
  (elke ouder-cluster en zijn kinderen krijgen dezelfde kleurfamilie),
  labeling aan.
- **`points.qml`** -- stijl voor de puntenlaag: simpele semi-transparante
  zwarte cirkels (geen per-onderwerp-kleur op dit moment).
- **`screenshots/qgis-sketch.png`** -- geëxporteerde preview van
  bovenstaande styling.

## Bekende beperkingen van deze schets

- De clusternamen in `screenshots/qgis-sketch.png` zijn nog de OUDE TF-IDF-namen
  (bv. "Schors", "Apel", "Scale", "Knmt") -- op het moment van deze schets
  liep de gefixte/verbeterde LLM-naamgeving (zie `docs/handoff.md`,
  `label_clusters_with_llm()`) nog op de achtergrond. Regenereer
  `plenair-map-clusters-full.geojson` na afloop daarvan voor zinnige namen.
- Alle 5 clusterniveaus worden hier even zwaar gestijld (geen dikte-verschil
  per niveau) -- het gekozen ontwerp ("lijndikte = niveau") is nog niet in
  `clusters.qml` verwerkt, dat vergt een graduated/rule-based symbologie op
  het `level`- of `stroke_width`-veld i.p.v. de huidige categorized-by-
  `parent_id`.
- Dit is de puntenlaag via `.pmtiles`/vector tiles, niet de geplande
  `datashader`-rasterrender voor de uiteindelijke print-versie (zie het
  plan in `docs/handoff.md`) -- prima voor snelle iteratie, maar niet de
  bron voor de definitieve A0-export.
