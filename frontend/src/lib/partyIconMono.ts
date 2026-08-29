import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { partyLogoSimple } from "./parties";

// frontend/src/lib -> frontend/public. Losstaand van parties.ts omdat dat
// bestand ook client-side geïmporteerd wordt (bv. ActorTagUsage.vue) --
// node:fs zou daar niet bundelen.
const PUBLIC_DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), "../../public");

const cache = new Map<string, string | null>();

// Relatieve luminantie (ITU-R BT.709), niet een kaal RGB-gemiddelde: anders
// verdwijnt bv. het contrast tussen een felgeel en een donkerblauw merkvlak
// bijna helemaal bij het ompoetsen naar grijs.
function naarGrijs(hex: string): string {
	const n = parseInt(hex.slice(1), 16);
	const r = (n >> 16) & 255;
	const g = (n >> 8) & 255;
	const b = n & 255;
	const l = Math.round(0.2126 * r + 0.7152 * g + 0.0722 * b);
	const h = l.toString(16).padStart(2, "0");
	return `#${h}${h}${h}`;
}

/** Ruwe SVG-markup van een partijlogo, omgezet naar grijstinten, voor gebruik
 * als klein icoon op de persoonspagina (naast het partijgenoten-mediaan op de
 * taghistogram, zie ActorTagUsage.vue). Alleen server-side aanroepbaar (leest
 * het bronbestand van schijf) -- de aanroepende .astro-pagina geeft de string
 * door als prop.
 *
 * De bronbestanden (public/party-logos/simplified/*.svg) coderen twee
 * merkkleuren via `<defs><style>.cls-1{fill:#...}.cls-2{fill:#...}</style>
 * </defs>` en `class="cls-N"` op de paden. Elke kleur plat naar één vaste
 * grijstint zetten liet het contrast tussen de twee vlakken verdwijnen --
 * overlappende vormen (bv. VVD se twee letter-lagen) versmolten dan tot een
 * onleesbare klodder. Vandaar: per merkkleur een eigen grijswaarde op
 * luminantie, zodat het silhouet net zo herkenbaar blijft als in kleur. */
export function partyIconMonoSvgRaw(party: string): string | null {
	if (cache.has(party)) return cache.get(party)!;
	const logo = partyLogoSimple(party);
	if (!logo) {
		cache.set(party, null);
		return null;
	}
	let svg: string;
	try {
		svg = readFileSync(path.join(PUBLIC_DIR, logo), "utf-8");
	} catch {
		cache.set(party, null);
		return null;
	}
	const mono = svg
		.replace(/<\?xml[^>]*\?>\s*/, "")
		.replace(/fill:\s*(#[0-9a-fA-F]{6})/g, (_match, hex) => `fill: ${naarGrijs(hex)}`);
	cache.set(party, mono);
	return mono;
}
