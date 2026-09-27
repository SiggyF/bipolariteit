// UMAP<->Mercator-hulpfuncties voor TiledPlenairMap.vue (MapLibre GL): de
// vector-tiles zelf hebben al standaard EPSG:3857-coördinaten (zie
// pipeline/tiling/grid.py's moduledocstring -- MapLibre projecteert een
// pmtiles-vectorbron altijd als standaard Web-Mercator, geen eigen
// tile<->scherm-wiskunde hier meer nodig). Alleen de cluster-hullen/-centroids
// (plenair-map-clusters(-full).json) staan nog los, in ruwe UMAP-ruimte, en
// moeten voor een GeoJSON-source naar lng/lat omgerekend worden.

export type GridMetadata = {
	minzoom: number;
	maxzoom: number;
	umap_scale: number;
	umap_center: [number, number];
};

// Exacte spiegeling van pipeline/tiling/grid.py's umap_to_mercator(): UMAP-
// coördinaat -> EPSG:3857-meters.
export function umapToMercator(x: number, y: number, grid: GridMetadata): [number, number] {
	const [cx, cy] = grid.umap_center;
	return [(x - cx) * grid.umap_scale, (y - cy) * grid.umap_scale];
}

// Standaard sferische Web-Mercator-inverse (EPSG:3857 -> EPSG:4326), zelfde
// radius als pyproj's CRS.from_epsg(3857) hanteert -- nodig omdat een
// MapLibre GeoJSON-source lng/lat verwacht, in tegenstelling tot een
// vector-tile-source (die zijn eigen Mercator-tegelbounds al kent).
const WEB_MERCATOR_RADIUS = 6378137;

export function mercatorMetersToLngLat(mx: number, my: number): [number, number] {
	const lng = (mx / WEB_MERCATOR_RADIUS) * (180 / Math.PI);
	const lat = (2 * Math.atan(Math.exp(my / WEB_MERCATOR_RADIUS)) - Math.PI / 2) * (180 / Math.PI);
	return [lng, lat];
}
