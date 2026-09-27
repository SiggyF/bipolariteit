// UMAP<->Mercator-hulpfuncties voor TiledPlenairMap.vue: de vector-tiles zelf
// hebben al standaard EPSG:3857-coördinaten (zie pipeline/tiling/grid.py's
// moduledocstring). MapLibre tekent achtergrond/cluster-hullen/-labels
// (GeoJSON-bronnen, dus zelf al in lng/lat, geen eigen tile<->scherm-wiskunde
// nodig). De puntenlaag zelf gaat via deck.gl (issue #259, echte
// GL-blendmodes -- zie TiledPlenairMap.vue) en decodeert de vector-tiles zelf
// (`tileBoundsMeters`/`tileLocalToLngLat` hieronder), want deck.gl's
// TileLayer kent geen pmtiles-protocol. Cluster-hullen/-centroids
// (plenair-map-clusters(-full).json) staan los, in ruwe UMAP-ruimte, en
// moeten voor een GeoJSON-source naar lng/lat omgerekend worden.

export type GridMetadata = {
	tile_size: number;
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

export type TileIndex = { x: number; y: number; z: number };

// Standaard WebMercatorQuad-tegelbounds (in EPSG:3857-meters) voor een
// (z, x, y) -- dezelfde standaard schaal die pipeline/tiling/grid.py altijd
// gebruikt (STANDARD_TMS = morecantile's WebMercatorQuad-preset), dus geen
// grid.json-extent nodig: die is per definitie altijd deze vaste halve-
// wereldextent.
const WEB_MERCATOR_HALF_EXTENT = Math.PI * WEB_MERCATOR_RADIUS;

export function tileBoundsMeters(tile: TileIndex): { minx: number; miny: number; maxx: number; maxy: number } {
	const n = 2 ** tile.z;
	const span = (2 * WEB_MERCATOR_HALF_EXTENT) / n;
	const minx = -WEB_MERCATOR_HALF_EXTENT + tile.x * span;
	// y=0 is bovenaan (corner_of_origin="topLeft"), dus y loopt van top naar bottom.
	const maxy = WEB_MERCATOR_HALF_EXTENT - tile.y * span;
	return { minx, miny: maxy - span, maxx: minx + span, maxy };
}

// MVT-quantisatie (mapbox_vector_tile.encode, default y_coord_down=False)
// slaat y gespiegeld op: `y_tile = extent - round((wereld_y - miny)/(maxy-miny) * extent)`.
// Hier de exacte inverse, direct doorgerekend naar lng/lat (voor deck.gl's
// getTileData, dat geografische coördinaten verwacht).
export function tileLocalToLngLat(tx: number, ty: number, extent: number, bounds: ReturnType<typeof tileBoundsMeters>): [number, number] {
	const worldX = bounds.minx + (tx / extent) * (bounds.maxx - bounds.minx);
	const quantizedY = extent - ty;
	const worldY = bounds.miny + (quantizedY / extent) * (bounds.maxy - bounds.miny);
	return mercatorMetersToLngLat(worldX, worldY);
}
