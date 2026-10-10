// Trace-events van TiledPlenairMap.vue voor de benchmark-/debugpagina
// (/tests/tiled-layer-benchmark/, issue #390). De kaart zelf stuurt alleen
// ruwe events uit (`emit("trace", ...)`); alles wat hier staat is pure
// aggregatie, zodat het zonder browser te testen is.

export type TraceEvent = {
	/** Naam met dubbele punt-namespace, bv. "map:load" of "tile:loaded". */
	name: string;
	/** `performance.now()`: ms sinds navigatiestart, dus inclusief hydratatie. */
	t: number;
	detail?: Record<string, unknown>;
};

export type TileStat = {
	z: number;
	x: number;
	y: number;
	/** Bytes van de ruwe (gedecomprimeerde) MVT-tegel. */
	bytes: number;
	/** Aantal features in de tegel. */
	points: number;
	/** Som van `point_count`: aantal spreekbeurten dat de tegel vertegenwoordigt. */
	represented: number;
	/** Tijd in pmtiles.getZxy() (netwerk + directory + eventuele decompressie). */
	fetchMs: number;
	/** Tijd voor MVT-decodering + omrekening naar lng/lat. */
	decodeMs: number;
	/** Aantal punten met een `density`-property, en de spreiding daarvan (null zonder). */
	densityPoints: number;
	densityMin: number | null;
	densityMax: number | null;
	densityMean: number | null;
};

export type ZoomSummary = {
	z: number;
	tiles: number;
	points: number;
	represented: number;
	bytes: number;
	fetchP50: number;
	fetchP95: number;
	decodeP50: number;
	decodeP95: number;
};

/** Percentiel met lineaire interpolatie; 0 voor een lege lijst. */
export function percentile(values: number[], p: number): number {
	if (values.length === 0) return 0;
	const sorted = [...values].sort((a, b) => a - b);
	const rank = (p / 100) * (sorted.length - 1);
	const lo = Math.floor(rank);
	const hi = Math.ceil(rank);
	return sorted[lo] + (sorted[hi] - sorted[lo]) * (rank - lo);
}

/** Per zoomniveau: aantal tegels, punten, bytes en fetch-/decodeertijden. */
export function summarizeTiles(tiles: TileStat[]): ZoomSummary[] {
	const byZoom = new Map<number, TileStat[]>();
	for (const tile of tiles) {
		const list = byZoom.get(tile.z);
		if (list) list.push(tile);
		else byZoom.set(tile.z, [tile]);
	}
	return [...byZoom]
		.sort(([a], [b]) => a - b)
		.map(([z, list]) => ({
			z,
			tiles: list.length,
			points: list.reduce((sum, t) => sum + t.points, 0),
			represented: list.reduce((sum, t) => sum + t.represented, 0),
			bytes: list.reduce((sum, t) => sum + t.bytes, 0),
			fetchP50: percentile(list.map((t) => t.fetchMs), 50),
			fetchP95: percentile(list.map((t) => t.fetchMs), 95),
			decodeP50: percentile(list.map((t) => t.decodeMs), 50),
			decodeP95: percentile(list.map((t) => t.decodeMs), 95),
		}));
}

/** Tijdstip van de eerste keer dat elk event voorkwam, op naam. */
export function firstOccurrences(events: TraceEvent[]): Map<string, number> {
	const first = new Map<string, number>();
	for (const event of events) {
		if (!first.has(event.name)) first.set(event.name, event.t);
	}
	return first;
}

/** Aantal punten in een GeoJSON-collectie: eerste ring-coördinaten, voor de bronnen-tabel. */
export function countVertices(collection: GeoJSON.FeatureCollection): number {
	let total = 0;
	const walk = (coords: unknown): void => {
		if (!Array.isArray(coords)) return;
		if (typeof coords[0] === "number") {
			total += 1;
			return;
		}
		for (const inner of coords) walk(inner);
	};
	for (const feature of collection.features) {
		const geometry = feature.geometry as { coordinates?: unknown } | null;
		if (geometry) walk(geometry.coordinates);
	}
	return total;
}

/** Eén groep netwerkverzoeken (PerformanceResourceTiming) per bestand. */
export type ResourceGroup = {
	file: string;
	requests: number;
	transferBytes: number;
	bodyBytes: number;
	maxDurationMs: number;
	firstStartMs: number;
	lastEndMs: number;
};

export type ResourceSample = {
	name: string;
	startTime: number;
	responseEnd: number;
	duration: number;
	transferSize: number;
	encodedBodySize: number;
};

/** Groepeert resource-timings op bestandsnaam (een pmtiles-bestand = veel range-verzoeken). */
export function groupResources(samples: ResourceSample[]): ResourceGroup[] {
	const groups = new Map<string, ResourceGroup>();
	for (const sample of samples) {
		const file = sample.name.split("?")[0].split("/").pop() || sample.name;
		const group = groups.get(file) ?? {
			file,
			requests: 0,
			transferBytes: 0,
			bodyBytes: 0,
			maxDurationMs: 0,
			firstStartMs: Infinity,
			lastEndMs: 0,
		};
		group.requests += 1;
		group.transferBytes += sample.transferSize;
		group.bodyBytes += sample.encodedBodySize;
		group.maxDurationMs = Math.max(group.maxDurationMs, sample.duration);
		group.firstStartMs = Math.min(group.firstStartMs, sample.startTime);
		group.lastEndMs = Math.max(group.lastEndMs, sample.responseEnd);
		groups.set(file, group);
	}
	return [...groups.values()].sort((a, b) => a.firstStartMs - b.firstStartMs);
}
