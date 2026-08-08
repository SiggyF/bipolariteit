import { describe, expect, it } from "vitest";
import { buildTimeline, yearTicks } from "./timeline";
import { TYPOLOGIES, type Argument } from "./types";
import topic from "../../../data/export/topics/stikstof.json";

const argumenten = topic.arguments as unknown as Argument[];

describe("buildTimeline op de stikstofexport", () => {
	const timeline = buildTimeline(argumenten)!;

	it("bucket op dag levert één bucket per debatdag", () => {
		expect(timeline.buckets).toHaveLength(8);
	});

	it("telt alle argumenten mee over de buckets heen", () => {
		const totaal = timeline.buckets.reduce((n, b) => n + b.total, 0);
		expect(totaal).toBe(argumenten.length);
		expect(timeline.zonderDatum).toBe(0);
	});

	it("offset loopt monotoon op van 0 tot 1", () => {
		const offsets = timeline.buckets.map((b) => b.offset);
		expect(offsets[0]).toBe(0);
		expect(offsets[offsets.length - 1]).toBe(1);
		for (let i = 1; i < offsets.length; i++) expect(offsets[i]).toBeGreaterThanOrEqual(offsets[i - 1]);
	});

	it("typologiepercentages volgen de vaste TYPOLOGIES-volgorde en tellen op tot ~100", () => {
		for (const bucket of timeline.buckets) {
			expect(bucket.typology.map((t) => t.typology)).toEqual(TYPOLOGIES);
			const som = bucket.typology.reduce((n, t) => n + t.pct, 0);
			expect(som).toBeGreaterThan(99.4);
			expect(som).toBeLessThan(100.6);
		}
	});

	it("elke bucket-range dekt precies de eigen debatdag", () => {
		for (const bucket of timeline.buckets) {
			expect(bucket.van).toBe(bucket.key);
			expect(bucket.tot).toBe(bucket.key);
		}
	});
});

describe("buildTimeline met kwartaalbuckets", () => {
	it("rolt de debatdagen samen tot 5 kwartalen", () => {
		const timeline = buildTimeline(argumenten, { unit: "kwartaal" })!;
		expect(timeline.buckets).toHaveLength(5);
		expect(timeline.buckets.map((b) => b.key)).toEqual(["2024-Q2", "2024-Q4", "2025-Q1", "2025-Q2", "2026-Q3"]);
		expect(timeline.buckets.reduce((n, b) => n + b.total, 0)).toBe(argumenten.length);
	});
});

describe("yearTicks", () => {
	it("levert oplopende jaartallen binnen het corpusbereik van stikstof", () => {
		const timeline = buildTimeline(argumenten)!;
		const ticks = yearTicks(timeline);
		// De eerste debatdag valt medio 2024, dus 1 januari 2024 valt buiten het
		// bereik en hoort niet mee te tellen als aslabel.
		expect(ticks.map((t) => t.label)).toEqual(["2025", "2026"]);
		for (let i = 1; i < ticks.length; i++) expect(ticks[i].offset).toBeGreaterThan(ticks[i - 1].offset);
	});
});

describe("randgevallen", () => {
	it("geeft null bij een lege lijst", () => {
		expect(buildTimeline([])).toBeNull();
	});

	it("telt argumenten zonder published_at apart, niet in een bucket", () => {
		const zonderDatum: Argument = { ...argumenten[0], document: { ...argumenten[0].document, published_at: null } };
		const timeline = buildTimeline([zonderDatum, argumenten[1]])!;
		expect(timeline.zonderDatum).toBe(1);
		expect(timeline.buckets.reduce((n, b) => n + b.total, 0)).toBe(1);
	});

	it("gebruikt offset 0.5 als alle argumenten op dezelfde dag vallen", () => {
		const eenDag: Argument = { ...argumenten[0], document: { ...argumenten[0].document, published_at: "2024-01-01T10:00:00" } };
		const timeline = buildTimeline([eenDag])!;
		expect(timeline.buckets).toHaveLength(1);
		expect(timeline.buckets[0].offset).toBe(0.5);
	});
});
