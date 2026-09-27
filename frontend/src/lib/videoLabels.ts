import type { Argument, Tag } from "./types";

// Overlay-logica voor de debat-videospeler (issue #94), losstaand van de
// componenten zodat ze zonder jsdom/hls.js unit-testbaar zijn. Zie
// docs/design/videoplayer/README.md, secties "Overgangen" en "Labelselectie".

/** Argumenten waarvan de videospanne de gegeven tijd t (seconden) bevat. Kan
 * er meerdere zijn (interrupties) -- behandel als verzameling, niet als één
 * argument. Argumenten zonder spanne doen nooit mee. */
export function activeArguments(args: Argument[], t: number): Argument[] {
	return args.filter(
		(a) => a.start_seconds !== null && a.end_seconds !== null && t >= a.start_seconds && t <= a.end_seconds,
	);
}

/** Eerstvolgende argument met `start_seconds` na `afterSeconds` (exclusief),
 * of null. Eén lineaire pass i.p.v. filteren+sorteren op de hele lijst -- dit
 * draait bij elke currentTime-update (~4x/s) in VideoOverlay.vue, en een
 * lange debat kan honderden argumenten hebben. */
export function nextArgumentAfter(args: Argument[], afterSeconds: number): Argument | null {
	let result: Argument | null = null;
	for (const a of args) {
		if (a.start_seconds === null || a.start_seconds <= afterSeconds) continue;
		if (result === null || a.start_seconds < (result.start_seconds as number)) result = a;
	}
	return result;
}

/** Symmetrisch aan nextArgumentAfter: laatste argument met `start_seconds`
 * vóór `beforeSeconds` (exclusief). */
export function prevArgumentBefore(args: Argument[], beforeSeconds: number): Argument | null {
	let result: Argument | null = null;
	for (const a of args) {
		if (a.start_seconds === null || a.start_seconds >= beforeSeconds) continue;
		if (result === null || a.start_seconds > (result.start_seconds as number)) result = a;
	}
	return result;
}

/** Tot drie tags van dit argument, gesorteerd op zeldzaamheid binnen dit
 * debat (documentfrequentie, niet globaal) zodat generieke tags als
 * Actor-Politicus wegvallen en wat afwijkt -- meestal de drogreden --
 * bovenaan komt. Tie-break op perspectief (alfabetisch, voor een stabiele
 * volgorde). `isVisible` filtert kandidaten (bv. een uitgezet perspectief
 * in de tijdlijn-legenda) zonder de frequentietelling zelf te beïnvloeden --
 * die blijft over alle tags van het debat gaan, ook verborgen tags.
 *
 * Bewust geen categorie-voorrang (bv. drogredenen/stijlmiddelen altijd
 * eerst): dat zou de selectie laten oordelen over wat "belangrijker" is
 * i.p.v. gewoon te laten zien wat opvalt binnen dit specifieke debat. */
export function selectBadgeTags(
	argument: Argument,
	argsInThisDebate: Argument[],
	isVisible: (tag: Tag) => boolean = () => true,
): Tag[] {
	const frequency = new Map<string, number>();
	for (const a of argsInThisDebate) {
		for (const tag of a.tags) {
			frequency.set(tag.sleutel, (frequency.get(tag.sleutel) ?? 0) + 1);
		}
	}
	return argument.tags
		.filter(isVisible)
		.sort((a, b) => {
			const freqDiff = (frequency.get(a.sleutel) ?? 0) - (frequency.get(b.sleutel) ?? 0);
			if (freqDiff !== 0) return freqDiff;
			return a.perspectief.localeCompare(b.perspectief);
		})
		.slice(0, 3);
}
