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

export function notifyUserScroll() {
	userScroll.isScrolling = true;
	if (timer) clearTimeout(timer);
	timer = setTimeout(() => {
		userScroll.isScrolling = false;
	}, COOLDOWN_MS);
}
