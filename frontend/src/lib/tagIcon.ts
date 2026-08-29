import { ICOON_PAD, PERSPECTIEVEN } from "./tagIcons.generated";

// tagsleutel -> icoonpad, over alle perspectieven heen. Eén lookup i.p.v. dit
// in elke component die een tagicoon toont opnieuw te doorzoeken.
const TAG_ICOON_PAD = new Map<string, string>();
for (const perspectief of PERSPECTIEVEN) {
	for (const [sleutel, icoon] of Object.entries(perspectief.tags)) {
		const pad = ICOON_PAD[icoon];
		if (pad) TAG_ICOON_PAD.set(sleutel, pad);
	}
}

/** Icoonpad voor een tagsleutel, of `null` als de tag geen icoon heeft
 * (bv. de "overig"-rij uit `bucketSmallCounts`). */
export function tagIconPath(sleutel: string): string | null {
	return TAG_ICOON_PAD.get(sleutel) ?? null;
}

/** Icoon als data-URI, voor plekken waar geen los SVG-element kan (bv. een
 * ECharts as-label, dat alleen tekst + rich-text-afbeeldingen rendert). Kleur
 * moet expliciet mee, `currentColor` werkt niet in een losstaande data-URI. */
export function tagIconDataUri(sleutel: string, color: string): string | null {
	const pad = tagIconPath(sleutel);
	if (!pad) return null;
	const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="${pad}"/></svg>`;
	return `data:image/svg+xml;base64,${btoa(svg)}`;
}

// Alleen een leesbaardere weergavenaam -- de volledige naam blijft de
// matchsleutel tegen `tag.perspectief` in de databestanden en de bron voor
// slugs, dus die passen we hier bewust niet aan.
const PERSPECTIEF_KORTE_NAAM: Record<string, string> = {
	"Communicatiewetenschappelijk & Media": "Communicatie & Media",
};

/** Verkorte weergavenaam voor een perspectief, voor gebruik in koppen/kaarten. */
export function perspectiefWeergaveNaam(naam: string): string {
	return PERSPECTIEF_KORTE_NAAM[naam] ?? naam;
}
