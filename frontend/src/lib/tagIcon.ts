import { ICOON_PAD, PERSPECTIEVEN } from "./tagIcons.generated";
import { PERSPECTIEF_SLOT } from "./vloeiChart";

const PERSPECTIEF_SLOT_VAR = ["var(--vl-indigo)", "var(--vl-oker)", "var(--vl-pruim)", "var(--vl-hemel)"];

/** Vloei-categorische kleur voor een perspectief, als CSS custom property --
 * voor gewone HTML/Astro-markup (geen canvas, dus geen hex per modus nodig
 * zoals `perspectiefKleur()` in vloeiChart.ts; de dark-variant volgt via
 * `:root[data-theme="dark"]` in main.css). Zelfde slotvolgorde als
 * `PERSPECTIEF_SLOT`, zodat eenzelfde perspectief overal dezelfde kleur
 * draagt, in grafieken en daarbuiten. */
export function perspectiefKleurVar(naam: string): string {
	const slot = PERSPECTIEF_SLOT[naam];
	return slot === undefined ? "var(--vl-overig)" : PERSPECTIEF_SLOT_VAR[slot];
}

// tagsleutel -> icoonpad/perspectiefkleur, over alle perspectieven heen. Eén
// lookup i.p.v. dit in elke component die een tagicoon/-kleur toont opnieuw
// te doorzoeken.
const TAG_ICOON_PAD = new Map<string, string>();
const TAG_KLEUR = new Map<string, string>();
for (const perspectief of PERSPECTIEVEN) {
	for (const [sleutel, icoon] of Object.entries(perspectief.tags)) {
		const pad = ICOON_PAD[icoon];
		if (pad) TAG_ICOON_PAD.set(sleutel, pad);
		TAG_KLEUR.set(sleutel, perspectiefKleurVar(perspectief.naam));
	}
}

/** Icoonpad voor een tagsleutel, of `null` als de tag geen icoon heeft
 * (bv. de "overig"-rij uit `bucketSmallCounts`). */
export function tagIconPath(sleutel: string): string | null {
	return TAG_ICOON_PAD.get(sleutel) ?? null;
}

/** Perspectiefkleur voor een tagsleutel (zelfde kleur als de tag overal
 * elders draagt, bv. DebateVideoView.vue's perspective-toggles/
 * ActorTagUsage.vue), of `null` als de tag bij geen bekend perspectief hoort. */
export function tagKleur(sleutel: string): string | null {
	return TAG_KLEUR.get(sleutel) ?? null;
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
