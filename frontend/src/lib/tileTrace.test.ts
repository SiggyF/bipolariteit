import { describe, expect, it } from "vitest";
import { countVertices, firstOccurrences, groupResources, percentile, summarizeTiles, type TileStat } from "./tileTrace";

function tile(overrides: Partial<TileStat>): TileStat {
	return { z: 3, x: 0, y: 0, bytes: 100, points: 10, represented: 10, fetchMs: 5, decodeMs: 1, densityPoints: 0, densityMin: null, densityMax: null, densityMean: null, ...overrides };
}

describe("percentile", () => {
	it("geeft 0 voor een lege lijst", () => {
		expect(percentile([], 50)).toBe(0);
	});

	it("interpoleert lineair tussen de buren", () => {
		expect(percentile([10, 20, 30, 40], 50)).toBe(25);
		expect(percentile([10, 20, 30, 40], 100)).toBe(40);
		expect(percentile([40, 10], 0)).toBe(10);
	});
});

describe("summarizeTiles", () => {
	it("groepeert per zoomniveau, laag naar hoog", () => {
		const summary = summarizeTiles([tile({ z: 5, points: 7 }), tile({ z: 3, points: 10 }), tile({ z: 5, points: 3, x: 1 })]);
		expect(summary.map((s) => s.z)).toEqual([3, 5]);
		expect(summary[1]).toMatchObject({ tiles: 2, points: 10 });
	});

	it("telt bytes en vertegenwoordigde spreekbeurten op", () => {
		const [only] = summarizeTiles([tile({ bytes: 100, represented: 40 }), tile({ x: 1, bytes: 50, represented: 60 })]);
		expect(only.bytes).toBe(150);
		expect(only.represented).toBe(100);
	});
});

describe("firstOccurrences", () => {
	it("bewaart per naam alleen het eerste tijdstip", () => {
		const first = firstOccurrences([
			{ name: "map:load", t: 300 },
			{ name: "map:idle", t: 500 },
			{ name: "map:load", t: 900 },
		]);
		expect(first.get("map:load")).toBe(300);
		expect(first.get("map:idle")).toBe(500);
	});
});

describe("countVertices", () => {
	it("telt coördinaten door polygonen en multipolygonen heen", () => {
		const collection = {
			type: "FeatureCollection",
			features: [
				{ type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [[[0, 0], [1, 0], [1, 1], [0, 0]]] } },
				{
					type: "Feature",
					properties: {},
					geometry: { type: "MultiPolygon", coordinates: [[[[0, 0], [1, 0], [0, 0]]], [[[2, 2], [3, 2], [2, 2]]]] },
				},
			],
		} as GeoJSON.FeatureCollection;
		expect(countVertices(collection)).toBe(4 + 3 + 3);
	});
});

describe("groupResources", () => {
	it("voegt range-verzoeken naar hetzelfde bestand samen", () => {
		const groups = groupResources([
			{ name: "https://x/a/plenair-map-full.pmtiles", startTime: 100, responseEnd: 150, duration: 50, transferSize: 1000, encodedBodySize: 900 },
			{ name: "https://x/a/plenair-map-full.pmtiles", startTime: 120, responseEnd: 400, duration: 280, transferSize: 5000, encodedBodySize: 4900 },
			{ name: "https://x/a/grid.json?v=1", startTime: 10, responseEnd: 40, duration: 30, transferSize: 300, encodedBodySize: 200 },
		]);
		expect(groups.map((g) => g.file)).toEqual(["grid.json", "plenair-map-full.pmtiles"]);
		expect(groups[1]).toMatchObject({ requests: 2, transferBytes: 6000, maxDurationMs: 280, firstStartMs: 100, lastEndMs: 400 });
	});
});
