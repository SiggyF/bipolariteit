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
	// Punten per px² per zoomniveau (pipeline/tiling/ink.py, `make tiles-full`);
	// ontbreekt in oudere grid.json-bestanden.
	ink?: InkTable;
};

export type InkTable = {
	render_tile_px: number;
	cell_px: number;
	zooms: { zoom: number; tiles: number; points: number; per_px2_p50: number; per_px2_p90: number; per_px2_p99: number }[];
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

// Ronde, "vloeiende" cluster-hullen i.p.v. de hoekige oorspronkelijke
// concave-hull-polygonen -- zelfde motivatie als scripts/a0_map's
// export_clusters_geojson.py's smooth_hull() (periodieke cubic B-spline via
// scipy), maar hier als een centripetale Catmull-Rom-spline door de originele
// hoekpunten (geen scipy-afhankelijkheid nodig in de frontend). Centripetaal
// (alpha=0.5) i.p.v. de klassieke uniforme Catmull-Rom, want uniform kan bij
// ongelijk verdeelde hoekpunten (typisch voor een concave hull) lussen/self-
// intersecties geven; centripetaal niet.
function catmullRomPoint(
	p0: [number, number],
	p1: [number, number],
	p2: [number, number],
	p3: [number, number],
	t: number,
): [number, number] {
	// Centripetale parametrisatie: elk segment krijgt een "tijd"-interval
	// evenredig aan sqrt(afstand) i.p.v. altijd 1.
	const alpha = 0.5;
	const dist = (a: [number, number], b: [number, number]) => Math.hypot(b[0] - a[0], b[1] - a[1]) ** alpha || 1e-9;
	const t0 = 0;
	const t1 = t0 + dist(p0, p1);
	const t2 = t1 + dist(p1, p2);
	const t3 = t2 + dist(p2, p3);
	const tt = t1 + t * (t2 - t1);

	function interp(pa: [number, number], pb: [number, number], ta: number, tb: number): [number, number] {
		const f = ta === tb ? 0 : (tt - ta) / (tb - ta);
		return [pa[0] + (pb[0] - pa[0]) * f, pa[1] + (pb[1] - pa[1]) * f];
	}
	const a1 = interp(p0, p1, t0, t1);
	const a2 = interp(p1, p2, t1, t2);
	const a3 = interp(p2, p3, t2, t3);
	const b1 = interp(a1, a2, t0, t2);
	const b2 = interp(a2, a3, t1, t3);
	return interp(b1, b2, t1, t2);
}

export function smoothClosedRing(points: [number, number][], samplesPerSegment = 8): [number, number][] {
	const n = points.length;
	if (n < 4) return points;
	const smoothed: [number, number][] = [];
	for (let i = 0; i < n; i++) {
		const p0 = points[(i - 1 + n) % n];
		const p1 = points[i];
		const p2 = points[(i + 1) % n];
		const p3 = points[(i + 2) % n];
		for (let s = 0; s < samplesPerSegment; s++) {
			smoothed.push(catmullRomPoint(p0, p1, p2, p3, s / samplesPerSegment));
		}
	}
	return smoothed;
}
