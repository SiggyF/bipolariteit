import { NO_PARTY, type Argument, type Stance } from "./types";

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

function pct(n: number, total: number): number {
	return total ? Math.round((1000 * n) / total) / 10 : 0;
}

function stanceCounts(argumentList: Argument[]): StanceCounts {
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
