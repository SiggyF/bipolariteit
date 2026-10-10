import { describe, expect, it } from "vitest";
import {
	BLEND_DEFAULT_STRENGTH,
	DEFAULT_POINT_STYLE,
	MEASURED_INK_FALLBACK,
	inkDensity,
	neutralFirst,
	resolvePointStyle,
	zoomFraction,
} from "./pointStyle";
import type { InkTable } from "./tiledMapTransform";

function table(rows: [number, number][]): InkTable {
	return {
		render_tile_px: 512,
		cell_px: 16,
		zooms: rows.map(([zoom, p90]) => ({ zoom, tiles: 1, points: 1, per_px2_p50: p90 / 2, per_px2_p90: p90, per_px2_p99: p90 * 2 })),
	};
}

describe("zoomFraction", () => {
	it("loopt van 0 op het grofste tot 1 op het fijnste niveau en klemt daarbuiten", () => {
		expect(zoomFraction(0, 0, 8)).toBe(0);
		expect(zoomFraction(4, 0, 8)).toBe(0.5);
		expect(zoomFraction(12, 0, 8)).toBe(1);
		expect(zoomFraction(3, 5, 5)).toBe(0);
	});
});

describe("inkDensity", () => {
	it("geeft null zonder tabel", () => {
		expect(inkDensity(undefined, 3)).toBeNull();
		expect(inkDensity(table([]), 3)).toBeNull();
	});

	it("valt terug op het dichtstbijzijnde lagere niveau", () => {
		const ink = table([[2, 0.2], [4, 0.1]]);
		expect(inkDensity(ink, 3)).toBe(0.2);
		expect(inkDensity(ink, 8)).toBe(0.1);
	});

	it("gebruikt het laagste niveau onder het bereik", () => {
		expect(inkDensity(table([[2, 0.2], [4, 0.1]]), 0)).toBe(0.2);
	});
});

describe("resolvePointStyle", () => {
	const style = { ...DEFAULT_POINT_STYLE, targetOverlap: 1, radiusMin: 0.5, radiusMax: 5, strength: 0.4 };

	it("houdt de verwachte overlap gelijk over zoomniveaus heen", () => {
		const ink = table([[3, 0.16], [5, 0.04]]);
		for (const zoom of [3, 5]) {
			const { radius } = resolvePointStyle(ink, zoom, 0, 8, style, false);
			const density = inkDensity(ink, zoom) as number;
			expect(density * Math.PI * radius ** 2).toBeCloseTo(1, 5);
		}
	});

	it("begrenst de straal naar boven en naar beneden", () => {
		const sparse = table([[8, 0.0001]]);
		const dense = table([[0, 50]]);
		expect(resolvePointStyle(sparse, 8, 0, 8, style, false).radius).toBe(5);
		expect(resolvePointStyle(dense, 0, 0, 8, style, false).radius).toBe(0.5);
	});

	it("valt zonder tabel terug op een lineaire straal", () => {
		expect(resolvePointStyle(undefined, 0, 0, 8, style, false).radius).toBe(0.5);
		expect(resolvePointStyle(undefined, 8, 0, 8, style, false).radius).toBe(5);
		expect(resolvePointStyle(undefined, 4, 0, 8, style, false).radius).toBeCloseTo(2.75);
	});

	it("gebruikt per thema de eigen sterkte en blend-modus", () => {
		const custom = { ...style, darkStrength: 0.7, blendLight: "mix" as const, blendDark: "screen" as const };
		expect(resolvePointStyle(undefined, 3, 0, 8, custom, true)).toMatchObject({ strength: 0.7, blend: "screen" });
		expect(resolvePointStyle(undefined, 3, 0, 8, custom, false)).toMatchObject({ strength: 0.4, blend: "mix" });
	});

	it("gebruikt standaard multiply (licht) en screen (donker, helderheid 0,43)", () => {
		expect(resolvePointStyle(undefined, 3, 0, 8, DEFAULT_POINT_STYLE, false).blend).toBe("multiply");
		const dark = resolvePointStyle(undefined, 3, 0, 8, DEFAULT_POINT_STYLE, true);
		expect(dark).toMatchObject({ strength: 0.43, blend: "screen" });
	});

	it("gebruikt per thema een eigen doeloverlap", () => {
		const ink = table([[3, 0.16]]);
		const custom = { ...style, targetOverlap: 1.5, darkTargetOverlap: 0.5 };
		expect(resolvePointStyle(ink, 3, 0, 8, custom, false).radius).toBeGreaterThan(resolvePointStyle(ink, 3, 0, 8, custom, true).radius);
		expect(DEFAULT_POINT_STYLE.darkTargetOverlap).toBe(0.85);
	});
});

describe("BLEND_DEFAULT_STRENGTH", () => {
	it("sluit voor de standaardmodi aan op de standaardstijl", () => {
		expect(BLEND_DEFAULT_STRENGTH[DEFAULT_POINT_STYLE.blendLight]).toBe(DEFAULT_POINT_STYLE.strength);
		expect(BLEND_DEFAULT_STRENGTH[DEFAULT_POINT_STYLE.blendDark]).toBe(DEFAULT_POINT_STYLE.darkStrength);
	});

	it("houdt mix doorzichtiger dan multiply", () => {
		expect(BLEND_DEFAULT_STRENGTH.mix).toBeLessThan(BLEND_DEFAULT_STRENGTH.multiply);
	});
});

describe("neutralFirst", () => {
	it("zet neutrale punten vooraan en behoudt de volgorde binnen elke groep", () => {
		const points = [
			{ id: 1, neutral: false },
			{ id: 2, neutral: true },
			{ id: 3, neutral: false },
			{ id: 4, neutral: true },
		];
		expect(neutralFirst(points, (p) => p.neutral).map((p) => p.id)).toEqual([2, 4, 1, 3]);
	});

	it("wijzigt de invoer niet", () => {
		const points = [{ id: 1, neutral: false }, { id: 2, neutral: true }];
		neutralFirst(points, (p) => p.neutral);
		expect(points.map((p) => p.id)).toEqual([1, 2]);
	});
});

describe("MEASURED_INK_FALLBACK", () => {
	it("dekt elk zoomniveau van 0 t/m 8 met een positieve dichtheid", () => {
		for (let zoom = 0; zoom <= 8; zoom++) {
			expect(inkDensity(MEASURED_INK_FALLBACK, zoom)).toBeGreaterThan(0);
		}
	});

	it("laat de doeloverlap de straal sturen", () => {
		const low = resolvePointStyle(MEASURED_INK_FALLBACK, 4, 0, 8, { ...DEFAULT_POINT_STYLE, targetOverlap: 0.5 }, false).radius;
		const high = resolvePointStyle(MEASURED_INK_FALLBACK, 4, 0, 8, { ...DEFAULT_POINT_STYLE, targetOverlap: 2 }, false).radius;
		expect(high).toBeGreaterThan(low);
	});
});
