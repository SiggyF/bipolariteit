# COLOFON & METHODOLOGISCHE VERANTWOORDING
**DE PARLEMENTAIRE KAART VAN NEDERLAND · ZITTINGSJAAR 2025–2026**

### DATA & BRONVERMELDING
- **Bron**: Tweede Kamer der Staten-Generaal — Open Data Portaal (`OData v4 / VLOS`) & Kamerstukdossiers
- **Omvang**: 135.633 spreekbeurten uit alle openbare plenaire debatten en commissievergaderingen
- **Periode**: Zittingsjaar 2025–2026 (`nov 2025 – sep 2026`)

### MACHINE LEARNING & CARTOGRAFIE
- **Embedding**: BGE-M3 meertalig taalmodel (`1024D Dense Vectors`)
- **Dimensiereductie**: UMAP 2D-topologische reductie (`1024D → 2D (x, y)`)
- **Semantische Kleur**: CIELAB projectie (`PC 2 & PC 3 → (a*, b*)`) met procedurele demping
- **Clustering**: HDBSCAN 5-traps hiërarchische dichtheidsclustering (8 hoofddomeinen tot 573 sub-debatten)
- **Thematische Duiding**: TF-IDF synthese & 1.521 officiële Kamerstukdossiers
- **Cartografie**: 300 DPI RGBA kleurendichtheidsraster, vectorstippeling en matglazen typografie

### OPEN SCIENCE & COLOFON
- **Project**: `Bipolariteit.org`
- **Data DOI**: `10.5281/zenodo.22236363`
- **Licentie**: `CC BY-SA 4.0` (Creative Commons Naamsvermelding-GelijkDelen)
- **Typografie**: Libre Caslon Display & Text, Work Sans, IBM Plex Mono
- **Uitgave**: Eerste Druk, September 2026

---
*© 2026 Bipolariteit.org · Licentie: Creative Commons CC BY-SA 4.0 · Printresolutie 300 DPI (A0)*
