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
	/** Positie op de as, 0..1. Ordinaal (elke bucket een vaste basiseenheid),
	 * niet lineair op kalenderdagen -- zie buildOffsets(). */
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

// Een lineaire tijdas met écht kalenderdagen dringt debatdagen die kort na
// elkaar liggen tot een onleesbare kluit samen, terwijl een stilte van twee
// jaar de rest van de as tot bijna niets platdrukt. Ordinaal (elke bucket een
// vaste basiseenheid) lost het eerste op, maar veegt dan de stilte zelf onder
// tafel. Dit is de tussenweg: elke bucket krijgt sowieso 1 eenheid, en een
// stilte van GAP_MAAND_DAGEN of meer voor die bucket koopt er per volle maand
// stilte nog een eenheid bij -- geplafonneerd, zodat een stilte van een jaar
// niet 12x zoveel plek claimt als een stilte van één maand.
const GAP_MAAND_DAGEN = 30;
const MAX_EXTRA_EENHEDEN = 3;

function buildOffsets(ranges: { van: string; tot: string }[]): number[] {
	if (ranges.length <= 1) return ranges.map(() => 0.5);

	const posities = [0];
	for (let i = 1; i < ranges.length; i++) {
		const stilte = daysBetween(ranges[i - 1].tot, ranges[i].van);
		const extra = stilte >= GAP_MAAND_DAGEN ? Math.min(MAX_EXTRA_EENHEDEN, Math.floor(stilte / GAP_MAAND_DAGEN)) : 0;
		posities.push(posities[i - 1] + 1 + extra);
	}
	const maxPositie = posities[posities.length - 1];
	return posities.map((p) => p / maxPositie);
}

const MAAND_KORT = ["jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"];

/** Korte aslabel voor onder een staaf, bv. "20 jun '24". Puur stringwerk op de
 * bucketsleutel, geen Date-object nodig. */
export function bucketLabel(key: string, unit: BucketUnit): string {
	if (unit === "dag") {
		const [year, month, day] = key.split("-").map(Number);
		return `${day} ${MAAND_KORT[month - 1]} '${String(year).slice(2)}`;
	}
	if (unit === "maand") {
		const [year, month] = key.split("-").map(Number);
		return `${MAAND_KORT[month - 1]} '${String(year).slice(2)}`;
	}
	const [year, kwartaal] = key.split("-Q");
	return `Q${kwartaal} '${year.slice(2)}`;
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

	const ranges = sortedKeys.map((key) => bucketRange(key, unit));
	const offsets = buildOffsets(ranges);

	const buckets: TimelineBucket[] = sortedKeys.map((key, i) => {
		const argumentsOfBucket = byBucket.get(key)!;
		return {
			key,
			van: ranges[i].van,
			tot: ranges[i].tot,
			offset: offsets[i],
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
