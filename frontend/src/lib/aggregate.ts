import { NO_PARTY, TYPOLOGIES, type Argument, type Sprekerbeurt, type Stance, type Typology } from "./types";

// Afgeleide cijfers voor de grafieken. Stonden eerder voorberekend in de
// export (build_stats/build_tags_per_party); nu leiden we ze af uit dezelfde
// argumentenlijst die de kolommen tonen, zodat een grafiek per constructie
// niet iets anders kan beweren dan de kolom ernaast.

export interface StanceCounts {
	total: number;
	pro: number;
	contra: number;
	unclear: number;
	pro_pct: number;
	contra_pct: number;
	unclear_pct: number;
}

export interface PartyStats extends StanceCounts {
	party: string;
}

export function pct(n: number, total: number): number {
	return total ? Math.round((1000 * n) / total) / 10 : 0;
}

export function stanceCounts(argumentList: Argument[]): StanceCounts {
	const count = (stance: Stance) => argumentList.filter((a) => a.stance === stance).length;
	const total = argumentList.length;
	const pro = count("pro");
	const contra = count("contra");
	const unclear = count("unclear");
	return {
		total,
		pro,
		contra,
		unclear,
		pro_pct: pct(pro, total),
		contra_pct: pct(contra, total),
		unclear_pct: pct(unclear, total),
	};
}

export interface TypologyStanceCounts {
	typology: Typology;
	pro: number;
	contra: number;
	unclear: number;
	total: number;
}

/** Verdeling van argumenttypes (feitelijk/moreel/economisch/...) over
 * pro/contra/onduidelijk, voor TypologyStanceBars.vue (issue #137). Alle vijf
 * typologieën komen terug, ook als een ervan 0 argumenten heeft in deze
 * selectie -- anders verspringt de rijenlijst bij het filteren. */
export function countByTypologyAndStance(argumentList: Argument[]): TypologyStanceCounts[] {
	const counts = new Map<Typology, { pro: number; contra: number; unclear: number }>(
		TYPOLOGIES.map((t) => [t, { pro: 0, contra: 0, unclear: 0 }]),
	);
	for (const argument of argumentList) {
		const row = counts.get(argument.typology);
		if (row) row[argument.stance] += 1;
	}
	return [...counts.entries()]
		.map(([typology, c]) => ({ typology, ...c, total: c.pro + c.contra + c.unclear }))
		.sort((a, b) => b.total - a.total);
}

function groupByParty(argumentList: Argument[]): Map<string, Argument[]> {
	const byParty = new Map<string, Argument[]>();
	for (const argument of argumentList) {
		const party = argument.actor.party ?? NO_PARTY;
		const bucket = byParty.get(party);
		if (bucket) bucket.push(argument);
		else byParty.set(party, [argument]);
	}
	return byParty;
}

export function deriveStats(argumentList: Argument[]) {
	const byParty = [...groupByParty(argumentList)].map(([party, argumentsOfParty]) => ({
		party,
		...stanceCounts(argumentsOfParty),
	}));
	byParty.sort((a, b) => b.pro_pct - a.pro_pct);
	return { overall: stanceCounts(argumentList), by_party: byParty };
}

// Leesbaarheids-/dichtheidsmaten per spreker (issue #155), afgeleid uit de
// platte sprekerbeurten- en argumentenlijst -- zelfde reductie-vorm als
// aggregeer_per_actor() in scripts/experiment_verbositeit.py, hier per actor
// (of over het volledige corpus) toegepast op de al gefilterde lijsten.
export interface VerbositeitStats {
	nSprekerbeurten: number;
	nArgumenten: number;
	gemSprekerbeurtLengte: number;
	gemZinslengte: number;
	fleschDouma: number;
	lix: number;
	// Word-count-gewogen gemiddelde van per-sprekerbeurt TTR (Mean Segmental
	// TTR): Σ(unique_word_count) / Σ(word_count). Reconstrueerbaar uit alleen
	// de opgeslagen per-document tellingen (geen ruwe tekst nodig), en minder
	// gevoelig voor totale spreektijd dan een kale corpus-brede TTR.
	msttr: number;
	tokensPerZin: number;
	argumentenPer1000Tekens: number;
	claimsPerArgument: number;
	gemQuoteLengte: number;
}

export function deriveVerbositeitStats(sprekerbeurtList: Sprekerbeurt[], argumentList: Argument[]): VerbositeitStats {
	const totaalTekens = sprekerbeurtList.reduce((sum, s) => sum + s.char_count, 0);
	const totaalWoorden = sprekerbeurtList.reduce((sum, s) => sum + s.word_count, 0);
	const totaalZinnen = sprekerbeurtList.reduce((sum, s) => sum + s.sentence_count, 0);
	const totaalLettergrepen = sprekerbeurtList.reduce((sum, s) => sum + s.syllable_count, 0);
	const totaalLangeWoorden = sprekerbeurtList.reduce((sum, s) => sum + s.long_word_count, 0);
	const totaalUniekeWoorden = sprekerbeurtList.reduce((sum, s) => sum + s.unique_word_count, 0);
	const totaalTokens = sprekerbeurtList.reduce((sum, s) => sum + s.token_count, 0);

	const nArgumenten = argumentList.length;
	const totaalClaims = argumentList.reduce((sum, a) => sum + a.claims.length, 0);
	const totaalQuoteLengte = argumentList.reduce((sum, a) => sum + a.quote_text.length, 0);

	const gemZinslengte = totaalZinnen ? totaalWoorden / totaalZinnen : 0;
	const gemLettergrepenPerWoord = totaalWoorden ? totaalLettergrepen / totaalWoorden : 0;

	return {
		nSprekerbeurten: sprekerbeurtList.length,
		nArgumenten,
		gemSprekerbeurtLengte: sprekerbeurtList.length ? totaalTekens / sprekerbeurtList.length : 0,
		gemZinslengte,
		fleschDouma: 206.84 - 0.93 * gemZinslengte - 77 * gemLettergrepenPerWoord,
		lix: gemZinslengte + (totaalWoorden ? (totaalLangeWoorden * 100) / totaalWoorden : 0),
		msttr: totaalWoorden ? totaalUniekeWoorden / totaalWoorden : 0,
		tokensPerZin: totaalZinnen ? totaalTokens / totaalZinnen : 0,
		argumentenPer1000Tekens: totaalTekens ? (nArgumenten * 1000) / totaalTekens : 0,
		claimsPerArgument: nArgumenten ? totaalClaims / nArgumenten : 0,
		gemQuoteLengte: nArgumenten ? totaalQuoteLengte / nArgumenten : 0,
	};
}

export function median(values: number[]): number {
	if (!values.length) return 0;
	const sorted = [...values].sort((a, b) => a - b);
	const mid = Math.floor(sorted.length / 2);
	return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

/** Mediaan per verbositeitsmaat over alle sprekers (elk met minstens
 * `minSprekerbeurten` sprekerbeurten), i.p.v. het gemiddelde over de gepoolde
 * corpustekst -- bij deze dichtheidsmaten (0,03 tot 1,6 argumenten/1000
 * tekens) trekt een enkele extreme spreker het gemiddelde flink omhoog, de
 * mediaan is dan een representatiever "typische spreker"-ijkpunt. */
export function deriveVerbositeitMedians(
	sprekerbeurtList: Sprekerbeurt[],
	argumentList: Argument[],
	minSprekerbeurten: number,
): VerbositeitStats {
	const sprekerbeurtenPerActor = new Map<string, Sprekerbeurt[]>();
	for (const s of sprekerbeurtList) {
		const bucket = sprekerbeurtenPerActor.get(s.actor.name);
		if (bucket) bucket.push(s);
		else sprekerbeurtenPerActor.set(s.actor.name, [s]);
	}
	const argumentenPerActor = new Map<string, Argument[]>();
	for (const a of argumentList) {
		const bucket = argumentenPerActor.get(a.actor.name);
		if (bucket) bucket.push(a);
		else argumentenPerActor.set(a.actor.name, [a]);
	}

	const perActor: VerbositeitStats[] = [];
	for (const [actor, sprekerbeurten] of sprekerbeurtenPerActor) {
		if (sprekerbeurten.length < minSprekerbeurten) continue;
		perActor.push(deriveVerbositeitStats(sprekerbeurten, argumentenPerActor.get(actor) ?? []));
	}

	const veld = (key: keyof VerbositeitStats) => median(perActor.map((s) => s[key]));
	return {
		nSprekerbeurten: veld("nSprekerbeurten"),
		nArgumenten: veld("nArgumenten"),
		gemSprekerbeurtLengte: veld("gemSprekerbeurtLengte"),
		gemZinslengte: veld("gemZinslengte"),
		fleschDouma: veld("fleschDouma"),
		lix: veld("lix"),
		msttr: veld("msttr"),
		tokensPerZin: veld("tokensPerZin"),
		argumentenPer1000Tekens: veld("argumentenPer1000Tekens"),
		claimsPerArgument: veld("claimsPerArgument"),
		gemQuoteLengte: veld("gemQuoteLengte"),
	};
}

export interface PartyTagCount {
	party: string;
	tag_count: number;
}

/** Aantal LLM-toegekende tags per partij. De deterministisch afgeleide tags
 * (Actor Type/Issue Arena/Parlementaire Context) tellen niet mee: die zijn bij
 * TK-data voor vrijwel elk argument gelijk en dragen geen signaal. Partijloze
 * sprekers vallen onder de sentinel "Onbekend" i.p.v. weggelaten te worden --
 * dat wijkt af van de oude SQL (`a.party IS NOT NULL`), maar sluit aan bij hoe
 * de rest van de pagina ze telt. */
export function deriveTagsPerParty(argumentList: Argument[]): PartyTagCount[] {
	const totals = new Map<string, number>();
	for (const argument of argumentList) {
		const party = argument.actor.party ?? NO_PARTY;
		const llmTags = argument.tags.filter((t) => t.created_by === "llm").length;
		if (llmTags) totals.set(party, (totals.get(party) ?? 0) + llmTags);
	}
	return [...totals]
		.map(([party, tag_count]) => ({ party, tag_count }))
		.sort((a, b) => b.tag_count - a.tag_count);
}

export interface TagUsageRow {
	sleutel: string;
	beschrijving: string;
	labelgroep: string;
	perspectief: string;
	count: number;
}

/** Aantal toekenningen per tag over een (al gefilterde) argumentenlijst --
 * bedoeld voor de partij-/persoonpagina's, die hier alleen de argumenten van
 * één actor in stoppen. Alleen LLM-toegekende tags, zelfde reden als
 * `deriveTagsPerParty`: de 3 deterministische labelgroepen zijn bij TK-data
 * vrijwel overal gelijk en dragen geen signaal. */
export function deriveTagUsage(argumentList: Argument[]): TagUsageRow[] {
	const rows = new Map<string, TagUsageRow>();
	for (const argument of argumentList) {
		for (const tag of argument.tags) {
			if (tag.created_by !== "llm") continue;
			const existing = rows.get(tag.sleutel);
			if (existing) existing.count += 1;
			else
				rows.set(tag.sleutel, {
					sleutel: tag.sleutel,
					beschrijving: tag.beschrijving,
					labelgroep: tag.labelgroep,
					perspectief: tag.perspectief,
					count: 1,
				});
		}
	}
	return [...rows.values()].sort((a, b) => b.count - a.count || a.sleutel.localeCompare(b.sleutel, "nl"));
}

/** Beperkt elk argument tot de LLM-toegekende tags van één perspectief.
 * Bedoeld om de correspondentiekaart en de partij-/labelgroepgrafieken op een
 * perspectiefpagina te schalen zonder `correspondence.ts` zelf aan te passen
 * -- die kijkt toch alleen naar `argument.tags`. */
export function filterTagsByPerspectief<T extends Argument>(argumentList: T[], perspectief: string): T[] {
	return argumentList.map((argument) => ({
		...argument,
		tags: argument.tags.filter((t) => t.created_by === "llm" && t.perspectief === perspectief),
	}));
}

/** Beperkt elk argument tot toekenningen van één tagsleutel, en laat alleen
 * argumenten staan die de tag dragen. Filtert niet op created_by: een sleutel
 * is per labelgroep altijd 'llm' óf altijd 'derived' (zie
 * pipeline/tag_arguments.py), de aanroeper beslist zelf hoe daarmee om te gaan. */
export function filterArgumentsByTag<T extends Argument>(argumentList: T[], sleutel: string): T[] {
	return argumentList
		.filter((a) => a.tags.some((t) => t.sleutel === sleutel))
		.map((a) => ({ ...a, tags: a.tags.filter((t) => t.sleutel === sleutel) }));
}

export interface PartyTagIndexEntry {
	party: string;
	total: number;
	tagCounts: Map<string, number>;
}

/** Eén doorloop over de volledige, niet-gefilterde argumentenlijst -- zelfde
 * reden als `derivePersonTagIndex`: de noemer voor een percentage moet een
 * partijtotaal zijn (alle onderwerpen, alle perspectieven), niet alleen het
 * aandeel binnen één perspectief. Voedt de partij x tag-heatmap op een
 * perspectiefpagina. */
export function derivePartyTagIndex(argumentList: Argument[]): Map<string, PartyTagIndexEntry> {
	const index = new Map<string, PartyTagIndexEntry>();
	for (const argument of argumentList) {
		const party = argument.actor.party ?? NO_PARTY;
		const entry = index.get(party) ?? { party, total: 0, tagCounts: new Map<string, number>() };
		entry.total += 1;
		for (const tag of argument.tags) {
			if (tag.created_by !== "llm") continue;
			entry.tagCounts.set(tag.sleutel, (entry.tagCounts.get(tag.sleutel) ?? 0) + 1);
		}
		index.set(party, entry);
	}
	return index;
}

export interface PersonTagIndexEntry {
	person: string;
	party: string | null;
	total: number;
	tagCounts: Map<string, number>;
}

/** Eén doorloop over de volledige, niet-gefilterde argumentenlijst (alle
 * onderwerpen, alle perspectieven) -- de noemer voor "1 op de N argumenten"
 * moet iemands totaal zijn, niet alleen hun aandeel binnen één perspectief
 * (zie het open punt in issue #5 over een ondergrens per persoon). */
export function derivePersonTagIndex(argumentList: Argument[]): Map<string, PersonTagIndexEntry> {
	const index = new Map<string, PersonTagIndexEntry>();
	for (const argument of argumentList) {
		const person = argument.actor.name;
		const entry = index.get(person) ?? { person, party: argument.actor.party ?? null, total: 0, tagCounts: new Map<string, number>() };
		entry.total += 1;
		for (const tag of argument.tags) {
			if (tag.created_by !== "llm") continue;
			entry.tagCounts.set(tag.sleutel, (entry.tagCounts.get(tag.sleutel) ?? 0) + 1);
		}
		index.set(person, entry);
	}
	return index;
}

// JSON-vriendelijke vorm van PartyTagIndexEntry/PersonTagIndexEntry -- Astro-
// props moeten serialiseerbaar zijn en een Map overleeft die grens niet.
// Gebruikt om derivePartyTagIndex/derivePersonTagIndex build-time te kunnen
// uitrekenen (over het volledige corpus) en het resultaat als lichte prop
// mee te geven, i.p.v. de ruwe argumentenlijst naar de client te sturen
// zodat de index daar client-side herberekend kan worden (zie issue #163).
export type SerializedPartyTagIndexEntry = { party: string; total: number; tagCounts: [string, number][] };
export type SerializedPersonTagIndexEntry = { person: string; party: string | null; total: number; tagCounts: [string, number][] };

export function serializePartyTagIndex(index: Map<string, PartyTagIndexEntry>): SerializedPartyTagIndexEntry[] {
	return [...index.values()].map((e) => ({ party: e.party, total: e.total, tagCounts: [...e.tagCounts] }));
}

export function deserializePartyTagIndex(rows: SerializedPartyTagIndexEntry[]): Map<string, PartyTagIndexEntry> {
	return new Map(rows.map((r) => [r.party, { party: r.party, total: r.total, tagCounts: new Map(r.tagCounts) }]));
}

export function serializePersonTagIndex(index: Map<string, PersonTagIndexEntry>): SerializedPersonTagIndexEntry[] {
	return [...index.values()].map((e) => ({ person: e.person, party: e.party, total: e.total, tagCounts: [...e.tagCounts] }));
}

export function deserializePersonTagIndex(rows: SerializedPersonTagIndexEntry[]): Map<string, PersonTagIndexEntry> {
	return new Map(rows.map((r) => [r.person, { person: r.person, party: r.party, total: r.total, tagCounts: new Map(r.tagCounts) }]));
}

export interface TopPersonRow {
	person: string;
	party: string | null;
	tagCount: number;
	total: number;
	ratio: number;
}

// minTagCount: zelfde ondergrens als PERSON_TAG_THRESHOLD in ActorTagUsage.vue
// -- bij 1-2 toekenningen zegt een ranglijst niets. minTotal: nieuw hier, want
// zonder ondergrens op het totaal leest iemand met 4 argumenten waarvan 3 met
// deze tag als "1 op de 1,3" -- een schijnprecisie die de brede persoonstotalen
// elders op de site niet hebben.
const DEFAULT_MIN_TAG_COUNT = 3;
const DEFAULT_MIN_TOTAL = 8;

/** Top-N personen voor één tag, gerangschikt op relatief aandeel (tagCount/total)
 * i.p.v. absoluut aantal -- zo wint niet automatisch de meest actieve spreker. */
export function deriveTopPersonsForTag(
	index: Map<string, PersonTagIndexEntry>,
	sleutel: string,
	options: { top?: number; minTagCount?: number; minTotal?: number } = {},
): TopPersonRow[] {
	const top = options.top ?? 5;
	const minTagCount = options.minTagCount ?? DEFAULT_MIN_TAG_COUNT;
	const minTotal = options.minTotal ?? DEFAULT_MIN_TOTAL;
	const rows: TopPersonRow[] = [];
	for (const entry of index.values()) {
		const tagCount = entry.tagCounts.get(sleutel) ?? 0;
		if (tagCount < minTagCount || entry.total < minTotal) continue;
		rows.push({ person: entry.person, party: entry.party, tagCount, total: entry.total, ratio: tagCount / entry.total });
	}
	rows.sort((a, b) => b.ratio - a.ratio || b.tagCount - a.tagCount);
	return rows.slice(0, top);
}

/** Vouwt tags met minder dan `threshold` toekenningen samen tot één "overig"-
 * rij. Bij deze taggingvolumes heeft een individuele spreker vaak maar 1-3
 * toekenningen van een tag; die als ranglijst tonen suggereert een patroon dat
 * er niet is (zie issue #5). Alleen zinvol op persoonsniveau -- partijvolumes
 * zijn hoog genoeg om dit niet nodig te hebben. */
export function bucketSmallCounts(rows: TagUsageRow[], threshold: number): TagUsageRow[] {
	const kept = rows.filter((r) => r.count >= threshold);
	const rest = rows.filter((r) => r.count < threshold);
	if (!rest.length) return kept;
	const restTotal = rest.reduce((sum, r) => sum + r.count, 0);
	return [
		...kept,
		{
			sleutel: "overig",
			beschrijving: `${rest.length} tags met elk minder dan ${threshold} toekenningen`,
			labelgroep: "",
			perspectief: "",
			count: restTotal,
		},
	];
}
