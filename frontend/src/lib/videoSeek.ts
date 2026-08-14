import { reactive } from "vue";

// Kleine gedeelde store waarmee de rechterlijst (ArgumentCard/DebateVideoView)
// en de tijdlijn (VideoTimeline) de player laten springen zonder dat die
// componenten via props/events aan elkaar gekoppeld hoeven te zijn. Zelfde
// idee als scrollTarget.ts: module-scope reactive singleton, geen Pinia.

export interface VideoSeekTarget {
	seconds: number | null;
	/** Verhoogt bij elke aanvraag, ook als seconds ongewijzigd blijft, zodat
	 * nogmaals klikken op dezelfde marker opnieuw seekt/afspeelt. */
	token: number;
}

export const videoSeek = reactive<VideoSeekTarget>({ seconds: null, token: 0 });

export function requestSeek(seconds: number) {
	videoSeek.seconds = seconds;
	videoSeek.token++;
}
