# Overzicht van op te ruimen bestanden

Dit overzicht toont bestanden die na afronding van de Zenodo-upload en de introductie van de geroteerde kaarten (_rotated) opgeruimd kunnen worden.

---

## Categorie 1: Tussenstappen, previews en test-artefacten (~50 tot 100 MB)

### Vergelijkingsafbeeldingen van kleur en verzadiging (data/export/a0-map/)
- data/export/a0-map/preview_gentle_saturation_comparison.png
- data/export/a0-map/preview_pc1_saturation_comparison.png
- data/export/a0-map/preview_red_boost_comparison.png
- data/export/a0-map/preview_step_saturation_comparison.png
- data/export/a0-map/preview_tanh_saturation_comparison.png
- data/export/a0-map/pca_dimensions_comparison.png
- data/export/a0-map/pca_mixes_23_vs_45.png
- data/export/a0-map/pca_mixes_comparison.png
- data/export/a0-map/pca_color_preview.png
- data/export/a0-map/pca_color_preview_full.png
- data/export/a0-map/pca_color_preview_refined.png
- data/export/a0-map/pca_color_rotated_preview.png
- data/export/a0-map/pca_color_substantive_preview.png
- data/export/a0-map/colofon.aux
- data/export/a0-map/colofon.log

### Oude handoff-archieven en batch logs
- data/export/design-handoff/argumentenboom-stikstof.zip
- data/export/design-handoff/debattenlijst-tijdlijn.zip
- data/export/design-handoff/deelknoppen-preview.zip
- data/export/design-handoff/plenaire-kaart-print.zip
- data/export/run-logs/agy_extraction_batch.log
- data/export/run-logs/agy_tagging_batch.log
- data/export/run-logs/agy_tagging_batch_2.log
- data/export/run-logs/agy_tagging_batch_3.log
- data/export/run-logs/agy_tagging_batch_4.log
- data/export/run-logs/extract_batch_full.log
- data/export/batch-experiment/
- data/export/tag_batch_stikstof.md
- data/export/tag_batch_stikstof_response.json
- data/export/tag_quality_review.md
- data/export/extractie_review_feedback.md
- data/export/extractie_review_stikstof.md

---

## Categorie 2: Oude monochrome en niet-geroteerde rasters (~320 MB)
Vervangen door density_color_a0_300dpi_rotated.tif.

### Oude monochrome rasters
- data/export/a0-map/density_a0_300dpi.tif (235 MB)
- data/export/a0-map/density_a0_300dpi.tfw
- data/export/a0-map/density_a0_300dpi.prj
- data/export/a0-map/density_a0_300dpi.tif.aux.xml
- data/export/a0-map/density_a0_preview.tif (9.4 MB)
- data/export/a0-map/density_a0_preview.tfw
- data/export/a0-map/density_a0_preview.prj

### Oude niet-geroteerde kleurentifs
- data/export/a0-map/density_color_a0_300dpi.tif (80 MB)
- data/export/a0-map/density_color_a0_300dpi.tfw
- data/export/a0-map/density_color_a0_300dpi.prj
- data/export/a0-map/density_color_a0_300dpi.tif.aux.xml
- data/export/a0-map/density_color_a0_preview.tif (5 MB)
- data/export/a0-map/density_color_a0_preview.tfw
- data/export/a0-map/density_color_a0_preview.prj

---

## Categorie 3: Oude niet-geroteerde PMTiles datasets (~270 MB)
Vervangen door plenair-map-full_rotated.pmtiles.

- data/export/plenair-map-full.pmtiles (241 MB)
- data/export/plenair-map-full.json (23 MB - optioneel, hergenereerbaar uit database)

---

## Categorie 4: Grote archieven (alleen indien Zenodo-upload compleet is) (~3.2 GB)

- data/embeddings/ (~2.5 GB)
  - text-embedding-bge-m3_plenair-full.npz en losse embedding vectors
- data/raw/ (~768 MB)
  - Ruwe gecrawlde XML-bestanden van de Tweede Kamer (staan al volledig in data/bipolariteit.db)
