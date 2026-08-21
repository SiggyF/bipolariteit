import { reactive } from "vue";

// Onderdrukt de auto-volg-scroll in ArgumentCard.vue (springt naar het
// actieve argument tijdens afspelen, zie de `playing`-watcher daar) zolang de
// gebruiker zelf recent gescrolld heeft. Zonder dit wint de auto-scroll het
// telkens van een handmatige scrollbeweging, want de video-kolom en de
// argumentenlijst delen dezelfde (enige) pagina-scroll -- naar boven scrollen
// terwijl de video doorspeelt werd zo meteen weer teruggetrokken naar het
// actieve argument. Zelfde idee als scrollTarget.ts/videoSeek.ts:
// module-scope reactive singleton, geen Pinia.

const COOLDOWN_MS = 4000;

export const userScroll = reactive({ isScrolling: false });

let timer: ReturnType<typeof setTimeout> | null = null;

// Tot voor kort werd dit alleen aangeroepen vanuit wheel-/touchmove-listeners
// (zie DebateVideoView.vue) -- dat mist toetsenbordscrollen (Page Down/
// spatie/pijltjes) en het slepen aan de eigen scrollbar-duimschijf, die geen
// van beide een wheel-/touchmove-event geven. Nu gekoppeld aan het generieke
// window "scroll"-event (vangt elke oorzaak), met markProgrammaticScroll()
// hieronder om te voorkomen dat de eigen auto-scroll (ArgumentCard.vue's
// scrollIntoView) zichzelf als "gebruiker scrolt" aanmerkt -- dat zou anders
// de cooldown telkens zelf blijven verlengen.
export function notifyUserScroll() {
	if (Date.now() < programmaticUntil) return;
	userScroll.isScrolling = true;
	if (timer) clearTimeout(timer);
	timer = setTimeout(() => {
		userScroll.isScrolling = false;
	}, COOLDOWN_MS);
}

let programmaticUntil = 0;

// Aanroepen vlak vóór een programmatische scroll (scrollIntoView), zodat de
// scroll-events die dat zelf veroorzaakt niet alsnog notifyUserScroll
// triggeren. durationMs ruim boven een smooth-scrollanimatie (~1s) houden.
export function markProgrammaticScroll(durationMs = 1200) {
	programmaticUntil = Date.now() + durationMs;
}
