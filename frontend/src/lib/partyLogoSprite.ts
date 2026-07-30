// Partijlogo's als ECharts-symbool. Een logo op de kaart is niet hetzelfde als
// een logo in een tabel: ECharts tekent een `image://`-symbool in een vak dat
// jij opgeeft, dus zonder de echte verhouding wordt een breed wordmerk (PVV is
// 13:1) in een vierkant geperst. Daarom lezen we de SVG zelf en halen we de
// verhouding uit de viewBox.
//
// Diezelfde binnengehaalde SVG-tekst laat een tweede ding toe: hem
// hertekenen. CSS kan dat niet -- het logo belandt op een canvas, buiten het
// bereik van stylesheets -- maar de opmaak aanpassen en als data-URI
// terugserveren kan wel.

import { ref } from "vue";
import { partyLogo } from "./parties";

export interface LogoSprite {
	/** Bron voor het ECharts-symbool, dus inclusief het `image://`-voorvoegsel. */
	symbool: string;
	/** breedte / hoogte. 1 als de SVG niets bruikbaars meldt. */
	verhouding: number;
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

/** breedte/hoogte uit viewBox, anders uit width/height, anders 1. */
function verhoudingVan(svg: string): number {
	const viewBox = svg.match(/viewBox\s*=\s*"([^"]+)"/);
	if (viewBox) {
		const [, , b, h] = viewBox[1].trim().split(/[\s,]+/).map(Number);
		if (b > 0 && h > 0) return b / h;
	}
	const breedte = Number.parseFloat(svg.match(/\swidth\s*=\s*"([\d.]+)/)?.[1] ?? "");
	const hoogte = Number.parseFloat(svg.match(/\sheight\s*=\s*"([\d.]+)/)?.[1] ?? "");
	if (breedte > 0 && hoogte > 0) return breedte / hoogte;
	return 1;
}

/** Alle kleur eruit, alles als lijntekening in één inkt terug. Bewust outline
 * en geen silhouet: een gevuld silhouet maakt van elk meerlaags logo (CDA, PRO)
 * één zwarte klodder, terwijl de contour de vorm nog laat zien. */
function naarOutline(svg: string, inkt: string, verhouding: number): string {
	const viewBox = svg.match(/viewBox\s*=\s*"([^"]+)"/);
	const eenheden = viewBox ? Number(viewBox[1].trim().split(/[\s,]+/)[2]) : 100;
	// Lijndikte in gebruikerseenheden, zodat hij na schaling overal even zwaar
	// oogt -- Volt tekent op 2047 eenheden, VVD op 80.
	const dikte = (Number.isFinite(eenheden) && eenheden > 0 ? eenheden : 100) / 90;
	return svg
		.replace(/<style[\s\S]*?<\/style>/g, "")
		.replace(/\s(fill|stroke)\s*=\s*"(?!none")[^"]*"/g, "")
		.replace(/\sstyle\s*=\s*"[^"]*"/g, "")
		.replace(
			/<svg\b/,
			`<svg fill="none" stroke="${inkt}" stroke-width="${dikte}" stroke-linejoin="round" ` +
				// Sommige bestanden hebben geen viewBox; zonder afmeting rendert een
				// data-URI als niets.
				(viewBox ? "" : `viewBox="0 0 100 ${Math.round(100 / verhouding)}" `),
		);
}

/**
 * @param partij  fractienaam zoals in de data
 * @param inkt    hex-kleur voor de outline-variant, of null voor het originele logo
 */
export function logoSprite(partij: string, inkt: string | null): LogoSprite | null {
	const pad = partyLogo(partij);
	if (!pad) return null;
	// De originele variant hoeft de SVG-tekst alleen voor de verhouding, maar
	// zonder die tekst is er ook geen verhouding, dus in beide gevallen wachten
	// we tot hij binnen is.
	const tekst = svgTekst(pad);
	if (!tekst) return null;
	const verhouding = verhoudingVan(tekst);
	if (!inkt) return { symbool: `image://${pad}`, verhouding };
	const uri = `data:image/svg+xml,${encodeURIComponent(naarOutline(tekst, inkt, verhouding))}`;
	return { symbool: `image://${uri}`, verhouding };
}
