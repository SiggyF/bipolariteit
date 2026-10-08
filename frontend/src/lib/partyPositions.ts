// Partij-iconen per positie op de onderwerpenindex (issue #250), vervangt
// het kale argumentenaantal op elke tegel. De ruwe tellingen per partij komen
// voorberekend uit pipeline/build_static_data.py (party_position_counts) --
// welke partijen zichtbaar worden (top-N, +N-overflow) blijft hier, net als
// TOP_N in DebateCardTagBar.vue.

export interface TopicPartyCount {
	party: string;
	pro: number;
	contra: number;
	unclear: number;
}

export interface PartyPositionGroup {
	party: string;
	count: number;
}

export interface PartyPositionColumns {
	pro: PartyPositionGroup[];
	proRest: number;
	contra: PartyPositionGroup[];
	contraRest: number;
}

const TOP_N = 4;

/** Dominante stance van een partij binnen dit onderwerp: de stance waarop de
 * partij het vaakst argumenteert. Bij een dominante "unclear" telt de partij
 * in geen van beide kolommen mee -- vgl. issue #250: "partijen sorteren in
 * links en rechts [...]", een middenkolom is voor een latere iteratie. */
function dominantStance(count: TopicPartyCount): "pro" | "contra" | "unclear" {
	if (count.pro >= count.contra && count.pro >= count.unclear) return "pro";
	if (count.contra >= count.pro && count.contra >= count.unclear) return "contra";
	return "unclear";
}

export function groupPartyPositions(counts: TopicPartyCount[]): PartyPositionColumns {
	const pro = counts
		.filter((c) => dominantStance(c) === "pro")
		.map((c) => ({ party: c.party, count: c.pro }))
		.sort((a, b) => b.count - a.count);
	const contra = counts
		.filter((c) => dominantStance(c) === "contra")
		.map((c) => ({ party: c.party, count: c.contra }))
		.sort((a, b) => b.count - a.count);

	return {
		pro: pro.slice(0, TOP_N),
		proRest: Math.max(0, pro.length - TOP_N),
		contra: contra.slice(0, TOP_N),
		contraRest: Math.max(0, contra.length - TOP_N),
	};
}
