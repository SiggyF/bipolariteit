// Genereert src/lib/tagIcons.generated.ts uit het ontwerpsysteem in
// docs/design/tag-iconografie/tag-styles.json plus de Lucide-iconen.
//
//   node scripts/build_tag_icons.mjs
//
// Waarom een generatiestap en niet gewoon de SVG's importeren:
//
// 1. ECharts wil één padstring (`path://d`), maar een Lucide-icoon is een mix
//    van <path>, <circle>, <line>, <polyline> en <rect>. Die moeten samen tot
//    één `d` gesmolten worden.
// 2. Lucide-iconen zijn lijntekeningen (fill: none, stroke-width 2). Op de
//    kaart tekenen we ze dus met itemStyle.borderColor i.p.v. .color -- zie
//    TagCorrespondenceMap.vue.
// 3. Het resultaat staat in de repo, dus lucide-static is alleen bij het
//    genereren nodig en belandt niet in de bundel.

import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const hier = dirname(fileURLToPath(import.meta.url));
const stijlen = JSON.parse(readFileSync(resolve(hier, "../../docs/design/tag-iconografie/tag-styles.json"), "utf8"));
const iconenMap = resolve(hier, "../node_modules/lucide-static/icons");
const doel = resolve(hier, "../src/lib/tagIcons.generated.ts");

const getal = (el, naam, standaard = 0) => {
	const m = el.match(new RegExp(`\\b${naam}\\s*=\\s*"([^"]*)"`));
	return m ? Number.parseFloat(m[1]) : standaard;
};

/** Eén boog van 180 graden, twee keer, is een hele ellips. */
function ellipsPad(cx, cy, rx, ry) {
	return `M${cx - rx} ${cy}a${rx} ${ry} 0 1 0 ${2 * rx} 0a${rx} ${ry} 0 1 0 ${-2 * rx} 0`;
}

function rechthoekPad(x, y, b, h, rx, ry) {
	if (!rx && !ry) return `M${x} ${y}h${b}v${h}h${-b}Z`;
	const a = rx || ry;
	const o = ry || rx;
	return (
		`M${x + a} ${y}h${b - 2 * a}a${a} ${o} 0 0 1 ${a} ${o}` +
		`v${h - 2 * o}a${a} ${o} 0 0 1 ${-a} ${o}` +
		`h${-(b - 2 * a)}a${a} ${o} 0 0 1 ${-a} ${-o}` +
		`v${-(h - 2 * o)}a${a} ${o} 0 0 1 ${a} ${-o}Z`
	);
}

function puntenPad(el, sluiten) {
	const punten = (el.match(/points\s*=\s*"([^"]*)"/)?.[1] ?? "").trim().split(/[\s,]+/).map(Number);
	if (punten.length < 4) return "";
	const stukken = [];
	for (let i = 0; i < punten.length; i += 2) stukken.push(`${i === 0 ? "M" : "L"}${punten[i]} ${punten[i + 1]}`);
	return stukken.join("") + (sluiten ? "Z" : "");
}

function naarPad(svg) {
	const delen = [];
	for (const [el] of svg.matchAll(/<(path|circle|ellipse|line|polyline|polygon|rect)\b[^>]*>/g)) {
		if (el.startsWith("<path")) delen.push(el.match(/\sd\s*=\s*"([^"]*)"/)?.[1] ?? "");
		else if (el.startsWith("<circle")) {
			const r = getal(el, "r");
			delen.push(ellipsPad(getal(el, "cx"), getal(el, "cy"), r, r));
		} else if (el.startsWith("<ellipse")) delen.push(ellipsPad(getal(el, "cx"), getal(el, "cy"), getal(el, "rx"), getal(el, "ry")));
		else if (el.startsWith("<line")) delen.push(`M${getal(el, "x1")} ${getal(el, "y1")}L${getal(el, "x2")} ${getal(el, "y2")}`);
		else if (el.startsWith("<polyline")) delen.push(puntenPad(el, false));
		else if (el.startsWith("<polygon")) delen.push(puntenPad(el, true));
		else if (el.startsWith("<rect"))
			delen.push(
				rechthoekPad(getal(el, "x"), getal(el, "y"), getal(el, "width"), getal(el, "height"), getal(el, "rx"), getal(el, "ry")),
			);
	}
	// De twee lege sprongen zetten de bounding box op het volle 24x24-raster.
	// Zonder dat perst ECharts elk icoon afzonderlijk tot het opgegeven vak en
	// zijn een breed en een smal icoon niet meer even zwaar.
	return `M0 0 M24 24 ${delen.filter(Boolean).join("")}`;
}

// Zeven iconen uit het ontwerpsysteem bestaan niet in Lucide -- deels Nederlandse
// namen, deels bedachte. Hier staat wat we in de plaats gebruiken, expliciet en
// niet stilzwijgend, zodat de afwijking van het ontwerp zichtbaar blijft.
const VERVANGERS = {
	"person-lectern": "presentation", // Actor-Politicus: spreker achter een katheder
	cheque: "hand-heart", // Actor-NGO: maatschappelijke organisatie
	"person-cap": "user-round", // Actor-Burger
	"resize-figure": "scaling", // Moraliteit-Proportionaliteit
	"round-table": "users-round", // Context-Commissie
	voorzittershamer: "gavel", // Context-Plenair
	paper: "file-text", // Context-Tweeminutendebat
};

const namen = new Set();
for (const p of stijlen.perspectives) {
	namen.add(p.icon);
	for (const g of p.groepen) for (const t of g.tags) namen.add(t.icon);
}

const paden = {};
const ontbreekt = [];
for (const naam of [...namen].sort()) {
	try {
		const bestand = VERVANGERS[naam] ?? naam;
		paden[naam] = naarPad(readFileSync(resolve(iconenMap, `${bestand}.svg`), "utf8"));
	} catch {
		ontbreekt.push(naam);
	}
}

const perspectieven = stijlen.perspectives.map((p) => ({
	key: p.key,
	naam: p.naam,
	kleur: p.color,
	icoon: p.icon,
	tags: Object.fromEntries(p.groepen.flatMap((g) => g.tags.map((t) => [t.sleutel, t.icon]))),
}));

const uit = `// GEGENEREERD -- niet met de hand aanpassen.
// Bron: docs/design/tag-iconografie/tag-styles.json + lucide-static.
// Opnieuw maken: cd frontend && node scripts/build_tag_icons.mjs

/** Lucide-iconen als ECharts-padstring. Lijntekeningen: teken ze met
 *  itemStyle.borderColor en een doorzichtige vulling, niet met .color. */
export const ICOON_PAD: Record<string, string> = ${JSON.stringify(paden, null, "\t")};

export interface PerspectiefStijl {
	key: string;
	naam: string;
	kleur: string;
	icoon: string;
	/** tagsleutel -> icoonnaam */
	tags: Record<string, string>;
}

export const PERSPECTIEVEN: PerspectiefStijl[] = ${JSON.stringify(perspectieven, null, "\t")};

/** Icoonnaam voor een tagsleutel, over alle perspectieven heen. */
export const TAG_ICOON: Record<string, string> = ${JSON.stringify(
	Object.fromEntries(perspectieven.flatMap((p) => Object.entries(p.tags))),
	null,
	"\t",
)};
`;

writeFileSync(doel, uit);
console.log(`${Object.keys(paden).length} iconen weggeschreven naar ${doel}`);
if (ontbreekt.length) console.warn(`niet gevonden in lucide-static: ${ontbreekt.join(", ")}`);
