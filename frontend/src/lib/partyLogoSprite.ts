// Partijlogo's als ECharts-symbool. De vereenvoudigde iconenset in
// public/party-logos/simplified/ is één vast vierkant kavas (160x160) per
// partij, dus in tegenstelling tot de officiële wordmarks (PVV is 13:1) is er
// hier geen verhouding om rekening mee te houden.
//
// De ingehaalde SVG-tekst laat een tweede ding toe: hem hertekenen. CSS kan
// dat niet -- het logo belandt op een canvas, buiten het bereik van
// stylesheets -- maar de opmaak aanpassen en als data-URI terugserveren wel.

import { ref } from "vue";
import { partyLogoSimple } from "./parties";

export interface LogoSprite {
	/** Bron voor het ECharts-symbool, dus inclusief het `image://`-voorvoegsel. */
	symbool: string;
}

// Reactief: de fetches komen na de eerste render binnen, en de kaart moet zich
// dan opnieuw opbouwen. Een nieuw object i.p.v. muteren, zodat Vue het ziet.
const ruweSvg = ref<Record<string, string>>({});
const opgevraagd = new Set<string>();

/** Haalt de SVG-tekst op (eenmalig per pad) en geeft hem terug zodra hij er is. */
function svgTekst(pad: string): string | null {
	if (ruweSvg.value[pad] !== undefined) return ruweSvg.value[pad];
	if (!opgevraagd.has(pad) && typeof fetch !== "undefined") {
		opgevraagd.add(pad);
		fetch(pad)
			.then((r) => (r.ok ? r.text() : Promise.reject(new Error(String(r.status)))))
			.then((tekst) => {
				ruweSvg.value = { ...ruweSvg.value, [pad]: tekst };
			})
			// Stil falen is hier het juiste gedrag: zonder logo valt de kaart terug
			// op de stip, en dat is een werkende kaart.
			.catch(() => opgevraagd.delete(pad));
	}
	return null;
}

function hexNaarRgb(hex: string): [number, number, number] | null {
	const m = hex.replace("#", "");
	const acht = m.length === 3 ? [...m].map((c) => c + c).join("") : m;
	if (acht.length !== 6) return null;
	return [0, 2, 4].map((i) => Number.parseInt(acht.slice(i, i + 2), 16)) as [number, number, number];
}

function rgbNaarHex([r, g, b]: [number, number, number]): string {
	return `#${[r, g, b].map((c) => Math.round(Math.max(0, Math.min(255, c))).toString(16).padStart(2, "0")).join("")}`;
}

/** Verzadiging schalen zonder de tint te verliezen: mengen naar het grijs op
 * dezelfde helderheid (luminantie-gewogen, geen HSL-omweg nodig voor dit
 * doel). Factor 1 = ongewijzigd, 0 = grijstinten. */
function verzadig([r, g, b]: [number, number, number], factor: number): [number, number, number] {
	const grijs = 0.299 * r + 0.587 * g + 0.114 * b;
	return [r, g, b].map((c) => grijs + (c - grijs) * factor) as [number, number, number];
}

/** Elke `fill: #hex` in het `<style>`-blok vervangen -- alle vlakken in deze
 * set zitten daar (zie `.cls-N { fill: #... }`), dus dit ene patroon volstaat. */
function herkleur(svg: string, bewerk: (rgb: [number, number, number]) => [number, number, number]): string {
	return svg.replace(/fill:\s*#([0-9a-fA-F]{3,6})/g, (heel, hex) => {
		const rgb = hexNaarRgb(hex);
		return rgb ? `fill: ${rgbNaarHex(bewerk(rgb))}` : heel;
	});
}

/**
 * @param partij  fractienaam zoals in de data
 * @param verzadiging  1 = ongewijzigde merkkleuren, lager mengt naar grijs --
 *   het ontwerp vraagt 10% als gedempte, onderling consistente variant.
 */
export function logoSprite(partij: string, verzadiging: number): LogoSprite | null {
	const pad = partyLogoSimple(partij);
	if (!pad) return null;
	const tekst = svgTekst(pad);
	if (!tekst) return null;
	const bewerkt = verzadiging >= 1 ? tekst : herkleur(tekst, (rgb) => verzadig(rgb, verzadiging));
	return { symbool: `image://data:image/svg+xml,${encodeURIComponent(bewerkt)}` };
}
