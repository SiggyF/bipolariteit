/** Seconden -> "m:ss" of "h:mm:ss", gedeeld door VideoPlayer/VideoTimeline/
 * VideoOverlay zodat tijdweergave overal hetzelfde format heeft. */
export function formatClock(seconds: number): string {
	const total = Math.max(0, Math.round(seconds));
	const h = Math.floor(total / 3600);
	const m = Math.floor((total % 3600) / 60);
	const sec = total % 60;
	return h > 0
		? `${h}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`
		: `${m}:${String(sec).padStart(2, "0")}`;
}
