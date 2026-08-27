import type { Argument } from "./types";

// Eén "debat" (issue #94) is één raw_video_url (het HLS-manifest), niet één
// document.id: elke spreekbeurt heeft een eigen document-rij, maar deelt de
// raw_video_url met alle andere spreekbeurten in datzelfde debat. Overal waar
// we naar /debat/[id]/ linken of die route opbouwen, moet dezelfde sleutel
// gebruikt worden -- vandaar deze ene functie i.p.v. m.document.id te pakken.
// FNV-1a, 32-bit: geen cryptografische eis, alleen een korte, stabiele,
// URL-veilige sleutel per raw_video_url.
export function debateId(rawVideoUrl: string): string {
	let hash = 0x811c9dc5;
	for (let i = 0; i < rawVideoUrl.length; i++) {
		hash ^= rawVideoUrl.charCodeAt(i);
		hash = Math.imul(hash, 0x01000193);
	}
	return (hash >>> 0).toString(36);
}

// Groepeert een argumentenlijst per debat (raw_video_url) en sorteert elke
// groep op videotijd -- gebruikt door scripts/export_public_data.ts om per
// debat een eigen, klein gepubliceerd bestand te schrijven
// (data/export/gepubliceerd/debatten/<id>.json, issue #119-vervolg: eerst
// filterde DebateVideoView.vue dit zelf uit het hele, veel grotere
// onderwerp-bestand, wat de client een compleet onderwerp (tot ~11 MB) liet
// downloaden voor één debat van een fractie daarvan). Argumenten zonder
// raw_video_url horen bij geen enkel debat en vallen weg.
export function groupByDebateId(argumentList: Argument[]): Map<string, Argument[]> {
	const groups = new Map<string, Argument[]>();
	for (const argument of argumentList) {
		const rawVideoUrl = argument.document.raw_video_url;
		if (!rawVideoUrl) continue;
		const id = debateId(rawVideoUrl);
		const group = groups.get(id);
		if (group) group.push(argument);
		else groups.set(id, [argument]);
	}
	for (const group of groups.values()) {
		group.sort((a, b) => {
			if (a.start_seconds === null) return 1;
			if (b.start_seconds === null) return -1;
			return a.start_seconds - b.start_seconds;
		});
	}
	return groups;
}
