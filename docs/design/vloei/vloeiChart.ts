// Vloei-grafiekthema voor ECharts (docs/design/vloei/grafiek.md).
//
// ECharts tekent op canvas en kan geen CSS custom properties lezen. Daarom
// staan de waarden hier als spiegel van tokens.json / main.css. Pas ze alleen
// samen aan: een kleur die hier afwijkt van main.css is een bug.
//
// Gebruik:
//   import * as echarts from "echarts/core";
//   import { registreerVloei, themaNaam, lettertypenKlaar } from "../lib/vloeiChart";
//   registreerVloei(echarts);              // één keer, bv. in lib/echartsSetup.ts
//   await lettertypenKlaar();              // vóór de eerste render (canvas tekent niet opnieuw als een font later binnenkomt)
//   <v-chart :theme="themaNaam(isDark)" :option="..." />

export type Modus = "light" | "dark";

/** Spiegel van de Vloei-kleurtokens die grafieken nodig hebben. */
export const VLOEI = {
	light: {
		vloei: "#eceef0",
		blad: "#fbfbfc",
		was: "#dde1e8",
		lijn: "#c3c8d2",
		rand: "#737b8e",
		galnoot: "#1a2031",
		galnootZacht: "#4b5366",
		pro: "#1f6f66",
		contra: "#9c3b32",
		onduidelijk: "#5d6475", // tekst en glyph
		onduidelijkVlak: "#aab0bd", // vlak in grafieken (gearceerd, zie grafiek.md)
	},
	dark: {
		vloei: "#121622",
		blad: "#1a1f2d",
		was: "#262c3c",
		lijn: "#353c4e",
		rand: "#727c96",
		galnoot: "#e6e8ee",
		galnootZacht: "#a9b0c0",
		pro: "#6fc2b4",
		contra: "#ec9387",
		onduidelijk: "#a3a9b8",
		onduidelijkVlak: "#525869",
	},
} as const;

/**
 * Categorisch: vier slots in vaste volgorde, nooit gecycled. Gevalideerd
 * all-pairs (dus ook voor scatter) in beide modi. Een vijfde reeks wordt
 * "Overig" in `rand`, of small multiples; nooit een gegenereerde kleur.
 * Geen van de slots ligt op pro (groen) of contra (rood): standpuntkleuren
 * blijven voorbehouden aan standpunten.
 */
export const CATEGORISCH = {
	//        indigo     oker       pruim      hemel
	light: ["#434baa", "#b97515", "#ab437b", "#2692ba"],
	dark: ["#5763c4", "#986116", "#b94f87", "#379fc7"],
} as const;

/** Sequentieel (hoeveelheid): één hue (indigo), licht → donker. In donker omgekeerd verankerd. */
export const SEQUENTIEEL = {
	light: ["#a2ade4", "#8592dc", "#6b78cd", "#515bb5", "#393f9d", "#262a71"],
	dark: ["#4a5498", "#606cc0", "#7786e3", "#95a4f6", "#b8c4fc", "#d9e0ff"],
} as const;

/** Divergerend (polariteit): contra ← neutraal grijs → pro. Gelijke stappen per arm. */
export const DIVERGEREND = {
	light: ["#9c3b32", "#c87a6f", "#eabfb8", "#e3e5ea", "#afd4cd", "#53a298", "#1f6f66"],
	dark: ["#ec9387", "#9f5c53", "#5a3833", "#2a2f3b", "#294944", "#308175", "#6fc2b4"],
} as const;

/** Vaste slot per tagperspectief (vervangt de kleuren uit tag-styles.json in grafieken). */
export const PERSPECTIEF_SLOT: Record<string, number> = {
	"Methodologisch & Contextueel": 0,
	"Filosofisch & Argumentatietheoretisch": 1,
	"Politicologisch & Sociaal-Psychologisch": 2,
	"Communicatiewetenschappelijk & Media": 3,
};

export function perspectiefKleur(perspectief: string, modus: Modus): string {
	const slot = PERSPECTIEF_SLOT[perspectief];
	return slot === undefined ? VLOEI[modus].rand : CATEGORISCH[modus][slot];
}

/** Lettertypen. "Archivo Smal" is een vaste wdth-85-instantie: canvas kan geen font-variation-settings. */
export const LETTER = {
	smal: '"Archivo Smal", Archivo, "Arial Narrow", system-ui, sans-serif',
	tekst: 'Literata, Georgia, serif',
} as const;

export async function lettertypenKlaar(): Promise<void> {
	if (typeof document === "undefined" || !document.fonts) return;
	await Promise.all([
		document.fonts.load(`500 12px "Archivo Smal"`),
		document.fonts.load(`600 13px "Archivo Smal"`),
	]).catch(() => undefined);
}

/** Arcering voor onduidelijk: diagonale lijnen in de oppervlaktekleur. Tweede drager naast de positie in de vouw. */
export function onduidelijkArcering(modus: Modus) {
	return {
		symbol: "rect",
		symbolSize: 1,
		color: VLOEI[modus].blad,
		dashArrayX: [1, 0],
		dashArrayY: [2, 3],
		rotation: -Math.PI / 4,
	};
}

export function vloeiThema(modus: Modus) {
	const t = VLOEI[modus];
	const asLabel = { color: t.galnootZacht, fontFamily: LETTER.smal, fontSize: 12, fontWeight: 500 };
	const categorieLabel = { color: t.galnoot, fontFamily: LETTER.smal, fontSize: 13, fontWeight: 600 };
	return {
		color: [...CATEGORISCH[modus]],
		backgroundColor: "transparent",
		textStyle: { fontFamily: LETTER.smal, color: t.galnoot, fontSize: 12 },
		title: { show: false }, // titels staan in HTML (kop-2), niet in de canvas
		grid: { left: 8, right: 16, top: 8, bottom: 8, containLabel: true },
		categoryAxis: {
			axisLine: { show: false },
			axisTick: { show: false },
			axisLabel: categorieLabel,
			splitLine: { show: false },
		},
		valueAxis: {
			axisLine: { show: false },
			axisTick: { show: false },
			axisLabel: asLabel,
			splitLine: { lineStyle: { color: t.lijn, width: 1 } },
			nameTextStyle: asLabel,
		},
		bar: {
			barMaxWidth: 18,
			itemStyle: { borderRadius: [0, 4, 4, 0] },
		},
		line: { lineStyle: { width: 2 }, symbol: "circle", symbolSize: 8, showSymbol: false },
		scatter: {
			symbolSize: 8,
			itemStyle: { opacity: 0.85, borderColor: t.blad, borderWidth: 1 },
		},
		legend: {
			// Voorkeur: HTML-legenda (.vl-legenda). Deze stijl is alleen voor de ECharts-legenda (bv. scroll).
			icon: "roundRect",
			itemWidth: 10,
			itemHeight: 10,
			itemGap: 16,
			textStyle: categorieLabel,
			inactiveColor: t.rand,
			pageIconColor: t.galnoot,
			pageIconInactiveColor: t.rand,
			pageTextStyle: asLabel,
		},
		tooltip: {
			className: "vl-tooltip",
			backgroundColor: t.blad,
			borderWidth: 0,
			padding: 0,
			textStyle: { color: t.galnoot },
			extraCssText: "", // stijl volledig in .vl-tooltip (main.css)
			axisPointer: {
				type: "shadow",
				z: 0, // achter de balken, niet eroverheen
				shadowStyle: { color: t.was, opacity: 0.6 },
				lineStyle: { color: t.rand, width: 1 },
			},
		},
		visualMap: {
			inRange: { color: [...SEQUENTIEEL[modus]] },
			textStyle: asLabel,
		},
	};
}

export function registreerVloei(echarts: { registerTheme: (naam: string, thema: object) => void }): void {
	echarts.registerTheme("vloei", vloeiThema("light"));
	echarts.registerTheme("vloei-donker", vloeiThema("dark"));
}

export const themaNaam = (isDark: boolean): string => (isDark ? "vloei-donker" : "vloei");

// ---------------------------------------------------------------------------
// Gespiegelde standpuntbalk ("de vouw" als grafiek)
// ---------------------------------------------------------------------------

export interface StandpuntRij {
	naam: string;
	pro: number;
	contra: number;
	onduidelijk: number;
}

export interface GespiegeldOpties {
	modus: Modus;
	/** "aantal" (TypologyStanceBars, TagsPerParty-achtig) of "procent" van het rijtotaal (StatsPanel). */
	eenheid?: "aantal" | "procent";
	/** Totaal per rij achter de naam tonen ("n=37"), nuttig bij eenheid "procent". */
	toonN?: boolean;
}

const GLYPH =
	'<svg viewBox="0 0 32 20" aria-hidden="true"><ellipse class="l" cx="11" cy="10" rx="9" ry="5.5" transform="rotate(-15 11 10)"/>' +
	'<ellipse class="r" cx="21" cy="10" rx="9" ry="5.5" transform="rotate(15 21 10)"/><circle cx="16" cy="10" r="2.2"/></svg>';

const escapeHtml = (s: string) =>
	s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);

function nice(max: number): number {
	if (max <= 0) return 1;
	const p = Math.pow(10, Math.floor(Math.log10(max)));
	const f = max / p;
	return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * p;
}

/**
 * Bouwt xAxis, yAxis, series en tooltip voor een gespiegelde standpuntbalk.
 * Pro loopt vanaf de middenas naar links, contra naar rechts, en onduidelijk
 * ligt gearceerd over de as (half links, half rechts): de vouw.
 * Merge het resultaat in je eigen option; `grid` en kleuren komen uit het thema.
 */
export function gespiegeldeStandpuntBalk(rijen: StandpuntRij[], opties: GespiegeldOpties) {
	const { modus, eenheid = "aantal", toonN = eenheid === "procent" } = opties;
	const t = VLOEI[modus];
	const pct = eenheid === "procent";
	const waarden = rijen.map((r) => {
		const n = r.pro + r.contra + r.onduidelijk;
		const f = pct && n ? 100 / n : 1;
		return { n, pro: r.pro * f, contra: r.contra * f, ond: r.onduidelijk * f };
	});
	const grens = pct
		? 100
		: nice(Math.max(1, ...waarden.map((w) => Math.max(w.pro, w.contra) + w.ond / 2)));
	const fmt = (v: number) => (pct ? `${Math.round(Math.abs(v))}%` : `${Math.round(Math.abs(v))}`);
	const rand = { borderColor: t.blad, borderWidth: 1 }; // 2px oppervlaktegat tussen segmenten

	const label = (positie: "left" | "right") => ({
		show: true,
		position: positie,
		distance: 6,
		color: t.galnootZacht,
		fontFamily: LETTER.smal,
		fontSize: 12,
		fontWeight: 500,
		formatter: (p: { value: number }) => (Math.abs(p.value) > 0 ? fmt(p.value) : ""),
	});

	const ondStijl = { color: t.onduidelijkVlak, decal: onduidelijkArcering(modus), ...rand };
	const series = [
		{
			name: "onduidelijk",
			id: "onduidelijk-links",
			type: "bar",
			stack: "vouw",
			barWidth: 16,
			itemStyle: { ...ondStijl, borderRadius: 0 },
			data: waarden.map((w) => -w.ond / 2),
			// Middenas: 1.5px galnoot, getekend als markLine op x = 0.
			markLine: {
				silent: true,
				symbol: "none",
				label: { show: false },
				lineStyle: { color: t.galnoot, width: 1.5, type: "solid" },
				data: [{ xAxis: 0 }],
			},
		},
		{
			name: "pro",
			id: "pro",
			type: "bar",
			stack: "vouw",
			barWidth: 16,
			itemStyle: { color: t.pro, borderRadius: [4, 0, 0, 4], ...rand },
			label: label("left"),
			data: waarden.map((w) => -w.pro),
		},
		{
			name: "onduidelijk",
			id: "onduidelijk-rechts",
			type: "bar",
			stack: "vouw",
			barWidth: 16,
			itemStyle: { ...ondStijl, borderRadius: 0 },
			data: waarden.map((w) => w.ond / 2),
		},
		{
			name: "contra",
			id: "contra",
			type: "bar",
			stack: "vouw",
			barWidth: 16,
			itemStyle: { color: t.contra, borderRadius: [0, 4, 4, 0], ...rand },
			label: label("right"),
			data: waarden.map((w) => w.contra),
		},
	];

	const rijHtml = (klasse: string, woord: string, waarde: number, ruw: number) =>
		`<div class="vl-tooltip-rij"><span class="vl-standpunt is-${klasse}">${GLYPH}${woord}</span>` +
		`<span class="vl-tooltip-waarde">${pct ? `${Math.round(waarde)}%` : ruw}</span>` +
		(pct ? `<span class="vl-tooltip-extra">${ruw}</span>` : "") +
		`</div>`;

	return {
		xAxis: {
			type: "value",
			min: -grens,
			max: grens,
			splitNumber: 4,
			axisLabel: { formatter: fmt },
		},
		yAxis: {
			type: "category",
			inverse: true, // eerste rij bovenaan; geen .reverse() meer nodig
			data: rijen.map((r, i) => (toonN ? `${r.naam}  {n|n=${waarden[i].n}}` : r.naam)),
			axisLabel: {
				rich: { n: { color: t.galnootZacht, fontFamily: LETTER.smal, fontSize: 12, fontWeight: 500 } },
			},
		},
		tooltip: {
			trigger: "axis",
			formatter: (params: Array<{ dataIndex: number }>) => {
				const i = params[0]?.dataIndex ?? 0;
				const r = rijen[i];
				const w = waarden[i];
				return (
					`<div class="vl-tooltip-kop">${escapeHtml(r.naam)}<span class="vl-tooltip-extra">${w.n} argumenten</span></div>` +
					rijHtml("pro", "pro", w.pro, r.pro) +
					rijHtml("onduidelijk", "onduidelijk", w.ond, r.onduidelijk) +
					rijHtml("contra", "contra", w.contra, r.contra)
				);
			},
		},
		series,
	};
}
