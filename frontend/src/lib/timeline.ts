import { pct, stanceCounts, type StanceCounts } from "./aggregate";
import { TYPOLOGIES, type Argument, type Typology } from "./types";

// De argumententijdlijn (issue #54). Argumenten komen uit Kamerdebatten, dus
// ze klonteren op een handvol debatdagen -- geen continue tijdreeks. Daarom
// bucketen we op dag (default) en niet op maand: een maandhistogram zou voor
// het grootste deel uit lege bakken bestaan. published_at is naive lokale
// tijd; net als filters.ts werken we op het ISO-datumdeel als string, niet
// als Date, en vergelijken lexicografisch -- dat klopt voor ISO-8601.

export type BucketUnit = "dag" | "maand" | "kwartaal";

export interface TypologyShare {
	typology: Typology;
	n: number;
	pct: number;
}

export interface TimelineBucket {
	/** "2024-06-20" | "2024-06" | "2024-Q2", afhankelijk van de bucket-eenheid. */
	key: string;
	/** yyyy-mm-dd, inclusief -- voert direct setDateRange(). */
	van: string;
	tot: string;
	/** Positie op de lineaire tijdas, 0..1. */
	offset: number;
	total: number;
	stance: StanceCounts;
	/** In de vaste TYPOLOGIES-volgorde, ook waarden met n=0. */
	typology: TypologyShare[];
}

export interface Timeline {
	buckets: TimelineBucket[];
	/** Corpusbereik (yyyy-mm-dd), voor de aslabels. */
	van: string;
	tot: string;
	/** Hoogste bucket-total, om de as van paneel A op te schalen. */
	maxTotal: number;
	/** Argumenten zonder published_at: apart geteld, niet in een bucket. */
	zonderDatum: number;
}

function bucketKey(date: string, unit: BucketUnit): string {
	if (unit === "dag") return date.slice(0, 10);
	if (unit === "maand") return date.slice(0, 7);
	const [year, month] = date.slice(0, 7).split("-");
	const kwartaal = Math.floor((Number(month) - 1) / 3) + 1;
	return `${year}-Q${kwartaal}`;
}

function bucketRange(key: string, unit: BucketUnit): { van: string; tot: string } {
	if (unit === "dag") return { van: key, tot: key };
	if (unit === "maand") {
		const [year, month] = key.split("-").map(Number);
		const lastDay = new Date(Date.UTC(year, month, 0)).getUTCDate();
		return { van: `${key}-01`, tot: `${key}-${String(lastDay).padStart(2, "0")}` };
	}
	const [year, q] = key.split("-Q").map(Number);
	const startMonth = (q - 1) * 3 + 1;
	const endMonth = startMonth + 2;
	const lastDay = new Date(Date.UTC(year, endMonth, 0)).getUTCDate();
	return {
		van: `${year}-${String(startMonth).padStart(2, "0")}-01`,
		tot: `${year}-${String(endMonth).padStart(2, "0")}-${String(lastDay).padStart(2, "0")}`,
	};
}

function daysBetween(a: string, b: string): number {
	const [ay, am, ad] = a.split("-").map(Number);
	const [by, bm, bd] = b.split("-").map(Number);
	return (Date.UTC(by, bm - 1, bd) - Date.UTC(ay, am - 1, ad)) / 86_400_000;
}

function typologyShares(argumentList: Argument[]): TypologyShare[] {
	const total = argumentList.length;
	return TYPOLOGIES.map((typology) => {
		const n = argumentList.filter((a) => a.typology === typology).length;
		return { typology, n, pct: pct(n, total) };
	});
}

export function buildTimeline(argumentList: Argument[], options?: { unit?: BucketUnit }): Timeline | null {
	const unit = options?.unit ?? "dag";

	const gedateerd: { argument: Argument; date: string }[] = [];
	let zonderDatum = 0;
	for (const argument of argumentList) {
		const date = argument.document.published_at?.slice(0, 10);
		if (date) gedateerd.push({ argument, date });
		else zonderDatum++;
	}
	if (!gedateerd.length) return null;

	const byBucket = new Map<string, Argument[]>();
	for (const { argument, date } of gedateerd) {
		const key = bucketKey(date, unit);
		const bucket = byBucket.get(key);
		if (bucket) bucket.push(argument);
		else byBucket.set(key, [argument]);
	}

	const sortedKeys = [...byBucket.keys()].sort();
	const van = bucketRange(sortedKeys[0], unit).van;
	const tot = bucketRange(sortedKeys[sortedKeys.length - 1], unit).tot;
	const span = daysBetween(van, tot);

	const buckets: TimelineBucket[] = sortedKeys.map((key) => {
		const argumentsOfBucket = byBucket.get(key)!;
		const range = bucketRange(key, unit);
		return {
			key,
			van: range.van,
			tot: range.tot,
			offset: span > 0 ? daysBetween(van, range.van) / span : 0.5,
			total: argumentsOfBucket.length,
			stance: stanceCounts(argumentsOfBucket),
			typology: typologyShares(argumentsOfBucket),
		};
	});

	return {
		buckets,
		van,
		tot,
		maxTotal: Math.max(...buckets.map((b) => b.total)),
		zonderDatum,
	};
}

/** Jaartallen als aslabels op dezelfde lineaire schaal als bucket.offset,
 * geknipt tot het corpusbereik (een 1 januari buiten [van, tot] valt weg). */
export function yearTicks(timeline: Timeline): { label: string; offset: number }[] {
	const span = daysBetween(timeline.van, timeline.tot);
	const startYear = Number(timeline.van.slice(0, 4));
	const endYear = Number(timeline.tot.slice(0, 4));
	const ticks: { label: string; offset: number }[] = [];
	for (let year = startYear; year <= endYear; year++) {
		const jan1 = `${year}-01-01`;
		if (jan1 < timeline.van || jan1 > timeline.tot) continue;
		ticks.push({ label: String(year), offset: span > 0 ? daysBetween(timeline.van, jan1) / span : 0 });
	}
	return ticks;
}
