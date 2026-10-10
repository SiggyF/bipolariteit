// Puntgrootte en kleursterkte van de tiled plenaire kaart per zoomniveau
// (TiledPlenairMap.vue, issue #390).
//
// De punten staan in een multiply-blend ("inkt"): wat het oog ziet is het
// aantal overlappende schijven per pixel. Hoeveel punten er per px² staan hangt
// af van het zoomniveau (uitdunning, zie pipeline/tiling/ink.py), dus een vaste
// of lineair meegroeiende straal geeft per zoom een heel andere inktdichtheid.
// Met de gemeten dichtheid kiezen we de straal zo dat de verwachte overlap op
// een druk punt (p90) op elk niveau gelijk is; de kleursterkte kan dan
// constant blijven.

import type { InkTable } from "./tiledMapTransform";

/** Blend-modus licht thema: "multiply" (inkt, verdonkert) of "mix" (gewone alpha-over). */
export type LightBlend = "multiply" | "mix";
/** Blend-modus donker thema: "max" (lichtste punt wint) of "screen" (1 - (1-src)(1-dst), gloei zonder af te kappen). */
export type DarkBlend = "max" | "screen";

export type PointStyle = {
	/** Gewenste verwachte overlap (schijven per pixel) op een druk punt (p90), licht thema. */
	targetOverlap: number;
	/** Idem voor het donkere thema: licht telt bij screen sneller op, dus daar past een lagere overlap. */
	darkTargetOverlap: number;
	/** Ondergrens van de straal in px. */
	radiusMin: number;
	/** Bovengrens van de straal in px (op het fijnste niveau zou de gemeten dichtheid anders reuzenpunten geven). */
	radiusMax: number;
	/** Kleursterkte (0 = wit, 1 = vol verzadigd), licht thema. Bij "mix" is dit de dekking per punt. */
	strength: number;
	/** Helderheid van een punt (0 = zwart, 1 = vol), donker thema. */
	darkStrength: number;
	blendLight: LightBlend;
	blendDark: DarkBlend;
};

export const DEFAULT_POINT_STYLE: PointStyle = {
	targetOverlap: 1.2,
	darkTargetOverlap: 0.85,
	radiusMin: 0.6,
	radiusMax: 4,
	strength: 0.37,
	darkStrength: 0.43,
	blendLight: "multiply",
	blendDark: "screen",
};

// Passende sterkte per blend-modus: multiply mengt richting wit (0,37), mix is
// de dekking per punt en moet lager om de wolk doorzichtig te houden (0,26),
// max/screen dempen de helderheid richting zwart. Wordt gebruikt als de
// benchmarkpagina van blend-modus wisselt, zodat een andere modus niet met de
// sterkte van de vorige begint.
export const BLEND_DEFAULT_STRENGTH: Record<LightBlend | DarkBlend, number> = {
	multiply: 0.37,
	mix: 0.26,
	max: 1,
	screen: 0.43,
};

// Terugval als grid.json (nog) geen `ink`-blok heeft: de meting van de
// pyramide die op 2026-10-10 live stond (plenair-map-full.pmtiles, globaal
// budget van 3000 punten per bevolkte tegel), met `python -m pipeline.tiling.ink`.
// Zodra `make tiles-full` het blok in grid.json zet, wint dat; deze tabel is
// dan ongebruikt. Na een nieuwe pyramide met andere uitdunning is hij verouderd.
export const MEASURED_INK_FALLBACK: InkTable = {
	render_tile_px: 512,
	cell_px: 16,
	zooms: [
		{ zoom: 0, tiles: 1, points: 3000, per_px2_p50: 0.2734, per_px2_p90: 0.7797, per_px2_p99: 0.9408 },
		{ zoom: 1, tiles: 4, points: 12000, per_px2_p50: 0.416, per_px2_p90: 0.8625, per_px2_p99: 1.0799 },
		{ zoom: 2, tiles: 4, points: 12000, per_px2_p50: 0.1289, per_px2_p90: 0.2379, per_px2_p99: 0.3203 },
		{ zoom: 3, tiles: 9, points: 27000, per_px2_p50: 0.0781, per_px2_p90: 0.1523, per_px2_p99: 0.207 },
		{ zoom: 4, tiles: 18, points: 54000, per_px2_p50: 0.0391, per_px2_p90: 0.0859, per_px2_p99: 0.125 },
		{ zoom: 5, tiles: 40, points: 120000, per_px2_p50: 0.0234, per_px2_p90: 0.0508, per_px2_p99: 0.082 },
		{ zoom: 6, tiles: 118, points: 354000, per_px2_p50: 0.0195, per_px2_p90: 0.043, per_px2_p99: 0.0728 },
		{ zoom: 7, tiles: 391, points: 731985, per_px2_p50: 0.0117, per_px2_p90: 0.0273, per_px2_p99: 0.0508 },
		{ zoom: 8, tiles: 1372, points: 731985, per_px2_p50: 0.0039, per_px2_p90: 0.0117, per_px2_p99: 0.0195 },
	],
};

export type ResolvedPointStyle = { radius: number; strength: number; blend: LightBlend | DarkBlend };

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

/** Zoomfractie: 0 op het grofste tegelniveau, 1 op het fijnste. */
export function zoomFraction(zoom: number, minzoom: number, maxzoom: number): number {
	if (maxzoom <= minzoom) return 0;
	return clamp((zoom - minzoom) / (maxzoom - minzoom), 0, 1);
}

/** Gemeten p90-dichtheid (punten per px²) voor een zoomniveau; valt terug op het dichtstbijzijnde lagere niveau. */
export function inkDensity(ink: InkTable | undefined, zoom: number): number | null {
	if (!ink || ink.zooms.length === 0) return null;
	let best: InkTable["zooms"][number] | null = null;
	for (const row of ink.zooms) {
		if (row.zoom <= zoom && (best === null || row.zoom > best.zoom)) best = row;
	}
	const row = best ?? ink.zooms.reduce((a, b) => (a.zoom < b.zoom ? a : b));
	return row.per_px2_p90 > 0 ? row.per_px2_p90 : null;
}

/**
 * Straal en kleursterkte voor een tegelniveau. Met een ink-tabel volgt de
 * straal uit de doeloverlap (`n = dichtheid * pi * r^2`); zonder tabel (oudere
 * grid.json) groeit de straal lineair met het zoomniveau. De betekenis van
 * `strength` hangt van de blend af: wit-menging (multiply), dekking (mix) of
 * helderheid (max/screen).
 */
export function resolvePointStyle(
	ink: InkTable | undefined,
	zoom: number,
	minzoom: number,
	maxzoom: number,
	style: PointStyle,
	dark: boolean,
): ResolvedPointStyle {
	const density = inkDensity(ink, zoom);
	const radius =
		density === null
			? style.radiusMin + zoomFraction(zoom, minzoom, maxzoom) * (style.radiusMax - style.radiusMin)
			: clamp(Math.sqrt((dark ? style.darkTargetOverlap : style.targetOverlap) / (Math.PI * density)), style.radiusMin, style.radiusMax);
	return dark
		? { radius, strength: style.darkStrength, blend: style.blendDark }
		: { radius, strength: style.strength, blend: style.blendLight };
}

/**
 * Zet "neutrale" punten (geen cluster/partij/jaar/topic, of gedempt door een
 * filter) vóór de gekleurde, zodat de gekleurde bovenop liggen: deck.gl tekent
 * een laag in datavolgorde. Stabiel binnen beide groepen. Alleen zichtbaar bij
 * alpha-over ("mix"); multiply, max en screen zijn volgorde-onafhankelijk.
 */
export function neutralFirst<T>(points: readonly T[], isNeutral: (point: T) => boolean): T[] {
	const neutral: T[] = [];
	const colored: T[] = [];
	for (const point of points) (isNeutral(point) ? neutral : colored).push(point);
	return neutral.concat(colored);
}

/**
 * Aantal zoomniveaus waarmee de kaart voorbij het diepste tegelniveau mag
 * inzoomen. Daar blijven de tegels van het diepste niveau staan (uitvergroot)
 * en schalen de punten met de kaart mee.
 */
export const OVERZOOM_LEVELS = 3;

/** Bovengrens van de puntstraal in px bij overzoom, zodat punten geen reuzenschijven worden. */
export const OVERZOOM_RADIUS_MAX_PX = 24;
