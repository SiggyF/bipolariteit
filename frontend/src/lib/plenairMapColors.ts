// Topic-kleuren voor de plenaire/debattenkaart. Losgetrokken uit
// PlenairMap.vue (die zelf ongewijzigd blijft, zie issue #215) zodat
// TiledPlenairMap.vue dezelfde kleuren gebruikt zonder ze te dupliceren.
// Neutrale punten (overig plenair, geen cluster/partij/jaar): een koel grijs op
// dezelfde tint als --lijn en --galnoot-zacht (blauwgrijs), met ongeveer
// dezelfde helderheid als het eerdere beige #a89e8c. Dat beige was een
// overblijfsel van de oude A0-kaart-tokens en botste met het koele Vloei-palet.
export const NEUTRAL_POINT_COLOR = "#8f96a3";

export const TOPIC_COLOR: Record<string, string> = {
	stikstof: "#4a7a4a",
	abortus: "#a64d5f",
	asiel: "#c07a2e",
	energietransitie: "#3d6e8f",
	// Alleen aanwezig in de volle dataset (plenair-map-full.json), niet in de
	// kleine steekproef die PlenairMap.vue gebruikt -- vandaar dat die
	// component's eigen (ongewijzigde) topic-kleurenkaart dit topic mist en dat
	// hier geen probleem is.
	oekraine: "#a68a3e",
	plenair: NEUTRAL_POINT_COLOR,
};

export const DEFAULT_TOPIC_COLOR = NEUTRAL_POINT_COLOR;

// Categorische kleur per cluster-id (voor "kleur op cluster" i.p.v. topic,
// issue #259): geen zelfgemaakte hue-formule meer (die oogde met de
// gulden-hoek-stap toch nog "systematisch" voor opeenvolgende ids) -- een
// standaard, herkenbare categorische kleurenset (Tableau10, ook de default in
// o.a. matplotlib/Vega-Lite) met van nature al vergelijkbare
// saturatie/helderheid per kleur, willekeurig toegewezen per cluster-id via
// een integer-hash (Thomas Wang) zodat naburige ids geen voorspelbare
// kleurvolgorde krijgen. Clusters zijn een open-eind aantal, dus bij meer dan
// 10 clusters herhaalt het palet -- inherent aan een categorische kleurenset.
// Tableau10 is behoorlijk fel/verzadigd vergeleken met de rest van de site
// (TOPIC_COLOR hierboven, THEME_COLOR in TiledPlenairMap.vue: allemaal
// gedempte, aardse tinten) -- elke kleur wordt daarom richting zijn eigen
// grijswaarde getrokken, zodat het palet onderscheidend blijft maar wat beter
// bij de rest van de site past.
function desaturate([r, g, b]: [number, number, number], amount: number): [number, number, number] {
	const gray = 0.2126 * r + 0.7152 * g + 0.0722 * b;
	const mix = (channel: number) => Math.round(gray + (channel - gray) * amount);
	return [mix(r), mix(g), mix(b)];
}

const CLUSTER_PALETTE: [number, number, number][] = (
	[
		[78, 121, 167], // tab:blue
		[242, 142, 43], // tab:orange
		[225, 87, 89], // tab:red
		[118, 183, 178], // tab:teal
		[89, 161, 79], // tab:green
		[237, 201, 72], // tab:yellow
		[176, 122, 161], // tab:purple
		[255, 157, 167], // tab:pink
		[156, 117, 95], // tab:brown
		[186, 176, 172], // tab:gray
	] as [number, number, number][]
).map((rgb) => desaturate(rgb, 0.65));

function hashInt(n: number): number {
	let x = n | 0;
	x = ((x >> 16) ^ x) * 0x45d9f3b;
	x = ((x >> 16) ^ x) * 0x45d9f3b;
	x = (x >> 16) ^ x;
	return x >>> 0;
}

export function clusterColorRgb(clusterId: number): [number, number, number] {
	return CLUSTER_PALETTE[hashInt(clusterId) % CLUSTER_PALETTE.length];
}

// FNV-1a -- zelfde reden als hashInt() hierboven, maar voor een string-sleutel
// (partijnaam) i.p.v. een numerieke id.
function hashString(s: string): number {
	let h = 0x811c9dc5;
	for (let i = 0; i < s.length; i++) {
		h ^= s.charCodeAt(i);
		h = Math.imul(h, 0x01000193);
	}
	return h >>> 0;
}

// Zelfde Tableau10-palet als clusters, maar op partijnaam gehashed -- een
// aparte, curated partijkleurenkaart (VVD-blauw, PvdA-rood, ...) zou mooier
// zijn maar bestaat nergens in deze codebase (PartyLogo.vue gebruikt logo's,
// geen kleuren) en is voor >20 fracties/eenmansgroepen ook niet compleet te
// krijgen zonder er zelf een op te stellen; dit geeft in elk geval een
// stabiele, onderscheidende kleur per partij.
export function partyColorRgb(party: string): [number, number, number] {
	return CLUSTER_PALETTE[hashString(party) % CLUSTER_PALETTE.length];
}

// Eerst geprobeerd als doorlopende oud->nieuw-kleurovergang, maar dat gaf in
// de praktijk een vrijwel egale kleur (de data valt grotendeels in een smal
// deel van het aangenomen jaarbereik, dus bijna alles clampte naar hetzelfde
// eind van de gradient). Gewoon elk jaar zijn eigen, onderscheidende
// categorische kleur -- zelfde aanpak als cluster/partij.
export function yearColorRgb(year: number): [number, number, number] {
	return CLUSTER_PALETTE[hashInt(year) % CLUSTER_PALETTE.length];
}
