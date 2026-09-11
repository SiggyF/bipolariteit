// Wereld<->tile<->scherm-transform voor TiledPlenairMap.vue, gespiegeld tegen
// de Python-kant (pipeline/tiling/grid.py + pipeline/tiling/encode.py) zodat
// dezelfde `(z, x, y)`-tile-indexering en dezelfde MVT-quantisatie hier exact
// worden teruggerekend. Bewust los van PlenairMap.vue's worldToScreen: die is
// canvas-aspect-ratio-afhankelijk (bakt canvasbreedte/-hoogte in de
// puntcoördinaten zelf), wat niet samengaat met een tile-grid met vaste
// CRS-bounds (zie issue #215-verkenning).

export type GridMetadata = {
	tile_size: number;
	minzoom: number;
	maxzoom: number;
	extent: [number, number, number, number]; // [minx, miny, maxx, maxy], altijd de volle Web-Mercator-extent
	umap_scale: number;
	umap_center: [number, number];
};

// UMAP-coördinaten (bv. cluster-hull-polygonen/-centroids uit
// plenair-map-clusters(-full).json, die los van de tile-pyramide staan en
// dus niet zelf al naar Mercator-meters herschaald zijn) omrekenen naar
// dezelfde ruimte als de punten die uit de tiles gedecodeerd worden -- zie
// pipeline/tiling/grid.py's `umap_to_mercator()`, exacte spiegeling hiervan.
export function umapToMercator(x: number, y: number, grid: GridMetadata): [number, number] {
	const [cx, cy] = grid.umap_center;
	return [(x - cx) * grid.umap_scale, (y - cy) * grid.umap_scale];
}

export type WorldBounds = { minx: number; miny: number; maxx: number; maxy: number };

export type TileKey = { z: number; x: number; y: number };

// morecantile's `custom()` maakt de bounding box vierkant (breedte == hoogte)
// voordat de tile-matrix erover gelegd wordt (zie grid.py-docstring) -- dus
// hier volstaat simpele 2^z-verdeling i.p.v. een volledige morecantile-poort.
export function tileBounds(grid: GridMetadata, tile: TileKey): WorldBounds {
	const [left, bottom, right, top] = grid.extent;
	const span = right - left;
	const n = 2 ** tile.z;
	const tileSpan = span / n;
	const minx = left + tile.x * tileSpan;
	const maxx = left + (tile.x + 1) * tileSpan;
	const maxy = top - tile.y * tileSpan;
	const miny = top - (tile.y + 1) * tileSpan;
	return { minx, miny, maxx, maxy };
}

// Welke tiles overlappen een wereld-rechthoek op een gegeven zoomniveau
// (geclampt aan grid.extent en grid.minzoom/maxzoom).
export function tilesForWorldRect(grid: GridMetadata, zoom: number, rect: WorldBounds): TileKey[] {
	const z = Math.max(grid.minzoom, Math.min(grid.maxzoom, Math.round(zoom)));
	const [left, bottom, right, top] = grid.extent;
	const span = right - left;
	const n = 2 ** z;
	const tileSpan = span / n;

	const clampedMinX = Math.max(rect.minx, left);
	const clampedMaxX = Math.min(rect.maxx, right);
	const clampedMinY = Math.max(rect.miny, bottom);
	const clampedMaxY = Math.min(rect.maxy, top);
	if (clampedMinX > clampedMaxX || clampedMinY > clampedMaxY) return [];

	const xMin = Math.max(0, Math.floor((clampedMinX - left) / tileSpan));
	const xMax = Math.min(n - 1, Math.floor((clampedMaxX - left) / tileSpan - 1e-9));
	// y=0 is bovenaan (corner_of_origin="topLeft" in grid.py), dus y loopt van top naar bottom.
	const yMin = Math.max(0, Math.floor((top - clampedMaxY) / tileSpan));
	const yMax = Math.min(n - 1, Math.floor((top - clampedMinY) / tileSpan - 1e-9));

	const tiles: TileKey[] = [];
	for (let x = xMin; x <= xMax; x++) {
		for (let y = yMin; y <= yMax; y++) {
			tiles.push({ z, x, y });
		}
	}
	return tiles;
}

// MVT-quantisatie (mapbox_vector_tile.encode, default y_coord_down=False)
// slaat y gespiegeld op: `y_tile = extent - round((wereld_y - miny)/(maxy-miny) * extent)`.
// Hier de exacte inverse, zodat gedecodeerde punten weer in dezelfde
// wereld-coördinaten staan als de brondata (UMAP-x/y, "y omhoog").
export function tileLocalToWorld(tx: number, ty: number, extent: number, bounds: WorldBounds): [number, number] {
	const worldX = bounds.minx + (tx / extent) * (bounds.maxx - bounds.minx);
	const quantizedY = extent - ty;
	const worldY = bounds.miny + (quantizedY / extent) * (bounds.maxy - bounds.miny);
	return [worldX, worldY];
}

// Zelfde opzet als PlenairMap.vue's worldToScreen: een vaste wereld-bounding-box
// (hier: grid.extent i.p.v. per-canvasgrootte herberekende rawBounds) genormaliseerd
// naar canvaspixels bij zoom=1, met de d3-zoomtransform er bovenop toegepast.
export function makeWorldToScreen(
	grid: GridMetadata,
	canvasWidth: number,
	canvasHeight: number,
	transform: { x: number; y: number; k: number },
) {
	const [left, bottom, right, top] = grid.extent;
	const cx = (left + right) / 2;
	const cy = (bottom + top) / 2;
	const spanX = right - left;
	const spanY = top - bottom;

	return function worldToScreen(wx: number, wy: number): [number, number] {
		const nx = (wx - cx) / (spanX / 2);
		const ny = (wy - cy) / (spanY / 2);
		const baseX = canvasWidth / 2 + nx * (canvasWidth / 2);
		const baseY = canvasHeight / 2 - ny * (canvasHeight / 2);
		return [transform.x + transform.k * baseX, transform.y + transform.k * baseY];
	};
}

export function makeScreenToWorld(
	grid: GridMetadata,
	canvasWidth: number,
	canvasHeight: number,
	transform: { x: number; y: number; k: number },
) {
	const [left, bottom, right, top] = grid.extent;
	const cx = (left + right) / 2;
	const cy = (bottom + top) / 2;
	const spanX = right - left;
	const spanY = top - bottom;

	return function screenToWorld(sx: number, sy: number): [number, number] {
		const baseX = (sx - transform.x) / transform.k;
		const baseY = (sy - transform.y) / transform.k;
		const nx = (baseX - canvasWidth / 2) / (canvasWidth / 2);
		const ny = (canvasHeight / 2 - baseY) / (canvasHeight / 2);
		return [cx + nx * (spanX / 2), cy + ny * (spanY / 2)];
	};
}
