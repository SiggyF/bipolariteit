import { reactive } from "vue";

// Kleine gedeelde store waarmee een claim in ClaimsHighlights.vue een
// "ga naar argument X"-aanvraag doet aan ArgumentColumn/ArgumentCard, zonder
// dat die componenten via props/events aan elkaar gekoppeld hoeven te zijn.
// Zelfde idee als filters.ts: module-scope reactive singleton, geen Pinia.

export interface ScrollTarget {
	argumentId: number | null;
	/** Verhoogt bij elke aanvraag, ook als argumentId ongewijzigd blijft, zodat
	 * een tweede klik op dezelfde claim opnieuw scrollt/highlight. */
	token: number;
}

export const scrollTarget = reactive<ScrollTarget>({ argumentId: null, token: 0 });

export function requestScrollTo(argumentId: number) {
	scrollTarget.argumentId = argumentId;
	scrollTarget.token++;
}
