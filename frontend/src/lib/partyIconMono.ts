import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { partyLogoSimple } from "./parties";

// frontend/src/lib -> frontend/public. Losstaand van parties.ts omdat dat
// bestand ook client-side geïmporteerd wordt (bv. ActorTagUsage.vue) --
// node:fs zou daar niet bundelen.
const PUBLIC_DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), "../../public");

const cache = new Map<string, string | null>();

/** Ruwe, kleurloze SVG-markup van een partijlogo (geen `fill` gezet), voor
 * gebruik als klein zwart-wit icoon op de persoonspagina (naast het
 * partijgenoten-mediaan op de taghistogram, zie ActorTagUsage.vue). Alleen
 * server-side aanroepbaar (leest het bronbestand van schijf) -- de
 * aanroepende .astro-pagina geeft de string door als prop, de kleur (afhankelijk
 * van het thema) wordt pas client-side toegevoegd.
 *
 * De bronbestanden (public/party-logos/simplified/*.svg) hebben geen
 * `fill`-attribuut op hun `<path>`-elementen, alleen `class="cls-N"` die naar
 * een `<defs><style>`-blok met de merkkleur wijst -- die strippen we, waarna
 * de paden terugvallen op overerving van het `fill`-attribuut dat de
 * aanroeper straks op de buitenste `<svg>` zet. */
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
	const mono = svg.replace(/<\?xml[^>]*\?>\s*/, "").replace(/<defs>[\s\S]*?<\/defs>/, "");
	cache.set(party, mono);
	return mono;
}
