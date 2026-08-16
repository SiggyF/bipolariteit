<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { formatClock } from "../lib/videoTime";

// Kale <video>-wrapper rond het HLS-manifest uit document.raw_video_url. Geen
// ondertitel/textTracks-matching hier zoals in de PoC
// (docs/poc/video-eigen-player/poc_ownplayer.html) -- dat matchen gebeurt al
// in de backend (pipeline/match_argument_spans.py) en het resultaat staat al
// in start_seconds/end_seconds.
//
// Eigen play/pauze/geluid-knoppen i.p.v. de natieve <video controls>: die
// natieve balk verbergt zichzelf tot hover/pauze (zie ontwerpprototype,
// .dc.html, dat om dezelfde reden eigen bediening bouwt) en oogde daardoor
// "knullig" t.o.v. de rest van de site.

const props = defineProps<{
	src: string;
	seekTo: number | null;
	seekToken: number;
	initialMuted?: boolean;
	// Link naar de volledige /debat/[id]/-pagina; alleen gezet op plekken die
	// zelf niet al die pagina zijn (bv. de homepage-teaser).
	debateHref?: string | null;
}>();
const emit = defineEmits<{ timeupdate: [seconds: number]; loadedmetadata: [duration: number]; seek: [seconds: number] }>();

const videoEl = ref<HTMLVideoElement | null>(null);
const fatalError = ref(false);
const playing = ref(false);
// Geluid staat standaard aan (browsers laten ongedempte autoplay meestal
// alleen toe na een eerdere gebruikersinteractie op de pagina -- lukt de
// autoplay hieronder niet, dan staat het geluid alvast klaar voor de eerste
// keer dat de kijker zelf op play drukt). `initialMuted` laat een plek die
// een debat "koud" toont (zoals de homepage) hier bewust van afwijken.
const muted = ref(props.initialMuted ?? false);
const currentTime = ref(0);
const duration = ref(0);
let tickInterval: ReturnType<typeof setInterval> | null = null;
let hls: import("hls.js").default | null = null;

onMounted(async () => {
	const video = videoEl.value;
	if (!video) return;
	video.muted = muted.value;

	if (video.canPlayType("application/vnd.apple.mpegurl")) {
		// Safari: native HLS-ondersteuning, geen hls.js nodig.
		video.src = props.src;
	} else {
		const { default: Hls } = await import("hls.js");
		if (Hls.isSupported()) {
			hls = new Hls();
			hls.loadSource(props.src);
			hls.attachMedia(video);
			hls.on(Hls.Events.ERROR, (_evt, data) => {
				if (data.fatal) fatalError.value = true;
			});
		} else {
			fatalError.value = true;
			return;
		}
	}

	video.addEventListener("loadedmetadata", () => {
		duration.value = video.duration;
		emit("loadedmetadata", video.duration);
		// Autoplay-poging: browsers blokkeren dit doorgaans zonder eerdere
		// gebruikersinteractie op de pagina, dus dit lukt niet altijd -- geen
		// browser-issue om te "fixen", alleen best-effort.
		video.play().catch(() => {});
	});
	video.addEventListener("play", () => (playing.value = true));
	video.addEventListener("pause", () => (playing.value = false));
	video.addEventListener("volumechange", () => (muted.value = video.muted));
	// Een grote sprong (bv. naar een ander deel van een 11-uurs manifest)
	// bufferen kost tijd: de browser/hls.js kan onderweg meerdere
	// seeking/seeked-cyclussen afvuren terwijl currentTime nog heen en weer
	// schuift voor het echt stabiliseert. Op alleen het eerste "seeked"
	// wachten liet die tussentijdse schommeling al door -- de tijdlijn en de
	// overlay-badges knipperden mee. Elke "seeked" herstart daarom een korte
	// stilstandsperiode; pas als er even niets meer gebeurt, vertrouwen we
	// video.currentTime weer.
	video.addEventListener("seeked", () => {
		if (seekSettleTimer) clearTimeout(seekSettleTimer);
		seekSettleTimer = setTimeout(() => {
			seeking = false;
		}, 400);
	});

	// Vaste tick i.p.v. het losse timeupdate-event: die vuurt te grof (~250ms
	// browserafhankelijk) of te fijn, terwijl de overlay juist op ~250ms moet
	// draaien om korte quotes niet te missen (zie ontwerp "Overgangen").
	tickInterval = setInterval(() => {
		if (seeking) return;
		currentTime.value = video.currentTime;
		emit("timeupdate", video.currentTime);
	}, 250);
});

onBeforeUnmount(() => {
	if (tickInterval) clearInterval(tickInterval);
	if (seekSettleTimer) clearTimeout(seekSettleTimer);
	hls?.destroy();
});

let seeking = false;
let seekSettleTimer: ReturnType<typeof setTimeout> | null = null;

watch(
	() => props.seekToken,
	() => {
		const video = videoEl.value;
		if (!video || props.seekTo === null) return;
		seeking = true;
		if (seekSettleTimer) clearTimeout(seekSettleTimer);
		currentTime.value = props.seekTo;
		video.currentTime = props.seekTo;
		video.play().catch(() => {
			// Autoplay kan geweigerd worden vóór een gebruikersinteractie --
			// currentTime staat dan wel goed, de kijker moet zelf op play drukken.
		});
	},
);

function togglePlay() {
	const video = videoEl.value;
	if (!video) return;
	if (video.paused) video.play().catch(() => {});
	else video.pause();
}

function toggleMute() {
	const video = videoEl.value;
	if (!video) return;
	video.muted = !video.muted;
}

// Loopt via het "seek"-event (net als de tijdlijn/argumentenlijst) i.p.v.
// hier direct video.currentTime te zetten -- zo profiteert een relatieve
// sprong ook van de seeking/settle-onderdrukking hierboven, anders knippert
// de overlay/tijdlijn ook bij deze knoppen.
function skipBy(deltaSeconds: number) {
	emit("seek", Math.max(0, currentTime.value + deltaSeconds));
}

defineExpose({ fatalError });
</script>

<template>
	<div class="video-player">
		<div class="video-stage">
			<video v-show="!fatalError" ref="videoEl" playsinline></video>
			<p v-if="fatalError" class="video-fallback">
				De video kan nu niet worden afgespeeld (het onderliggende manifest is ongedocumenteerd en kan gemigreerd
				zijn). Probeer het later opnieuw, of bekijk het debat rechtstreeks bij de Tweede Kamer.
			</p>
			<!-- Overlay (badges/naamplaatje) moet precies over de video-pixels
			     vallen, niet over de controls-row eronder -- vandaar een eigen
			     positioneringscontext hier, i.p.v. de hele .video-player. -->
			<slot />
		</div>
		<div v-if="!fatalError" class="controls-row">
			<button type="button" class="control-button" title="30 seconden terug" aria-label="30 seconden terug" @click="skipBy(-30)">
				<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
					<path d="M11 19l-7-7 7-7" />
					<path d="M18 19l-7-7 7-7" />
				</svg>
				<span class="skip-label">30</span>
			</button>
			<button
				type="button"
				class="control-button is-primary"
				:title="playing ? 'Pauze' : 'Afspelen'"
				:aria-label="playing ? 'Pauze' : 'Afspelen'"
				@click="togglePlay"
			>
				<svg v-if="!playing" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
					<polygon points="7,4 20,12 7,20" fill="currentColor" />
				</svg>
				<svg v-else viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
					<rect x="7" y="4.5" width="3.5" height="15" fill="currentColor" />
					<rect x="14" y="4.5" width="3.5" height="15" fill="currentColor" />
				</svg>
			</button>
			<button type="button" class="control-button" title="10 seconden vooruit" aria-label="10 seconden vooruit" @click="skipBy(10)">
				<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
					<path d="M13 5l7 7-7 7" />
					<path d="M6 5l7 7-7 7" />
				</svg>
				<span class="skip-label">10</span>
			</button>
			<button
				type="button"
				class="control-button"
				:title="muted ? 'Geluid aan' : 'Geluid uit'"
				:aria-label="muted ? 'Geluid aan' : 'Geluid uit'"
				@click="toggleMute"
			>
				<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
					<path d="M4 9.5h3.5L12 5.5v13L7.5 14.5H4z" />
					<template v-if="!muted">
						<path d="M16 9a4 4 0 0 1 0 6" />
						<path d="M18.5 6.5a7.5 7.5 0 0 1 0 11" />
					</template>
					<template v-else>
						<line x1="16" y1="9.5" x2="21" y2="14.5" />
						<line x1="21" y1="9.5" x2="16" y2="14.5" />
					</template>
				</svg>
			</button>
			<span class="time-label">{{ formatClock(currentTime) }} / {{ formatClock(duration) }}</span>
			<a
				v-if="debateHref"
				:href="debateHref"
				class="control-button debate-link-button"
				title="Volledige debatpagina"
				aria-label="Volledige debatpagina"
			>
				<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
					<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
					<path d="M15 3h6v6" />
					<path d="M10 14 21 3" />
				</svg>
			</a>
			<!-- Ruimte voor een niet-generieke, per-plek control (bv. de
			     argumentenlijst-toggle op /debatten/[id]/ als die lijst is
			     ingeklapt): hoort qua herkomst niet in deze kale mediaplayer,
			     maar wel qua rij i.p.v. een aparte knoppenrij eronder. -->
			<slot name="controls-extra" />
		</div>
	</div>
</template>

<style scoped>
.video-stage {
	position: relative;
	background: #000;
	/* Op een brede/korte viewport (bv. een laptop met weinig hoogte) laat een
	   16:9-video die simpelweg 100% breedte volgt de speler + bedieningsrij +
	   tijdlijn + perspectief-filters eronder (allemaal in dezelfde sticky
	   player-column, zie DebateVideoView.vue) samen hoger uitvallen dan het
	   scherm, met de bedieningsrij dan buiten beeld. 220px is een grove
	   schatting van die rijen samen.
	   Native aspect-ratio+max-width+max-height (i.p.v. de breedte zelf via een
	   `calc((100vh - ...) * 16/9)` afleiden): dat eerdere `width`-calc maakte
	   de breedte ook afhankelijk van vh, dus herrekende bij ELKE resize (ook
	   een hoogteverandering, bv. bij het slepen aan een vensterhoek) de hele
	   breedte -- en daarmee de layout van alles eronder. Dit is het
	   standaardpatroon waarmee browsers "pas een blok met een vaste
	   verhouding binnen een begrensde ruimte" al goedkoop oplossen. */
	width: auto;
	max-width: 100%;
	max-height: calc(100vh - 220px);
	aspect-ratio: 16 / 9;
	margin: 0 auto;
}

video {
	display: block;
	width: 100%;
	height: 100%;
}

.video-fallback {
	padding: var(--space-3);
	color: var(--color-bg);
	text-align: center;
}

.controls-row {
	display: flex;
	align-items: center;
	gap: var(--space-2);
	padding: var(--space-1) 0;
}

/* Zelfde uitgangspunten als de .btn/.btn-icon-knoppen uit het
   ontwerpprototype: transparante, contourgetekende knop (geen gevulde
   cirkel), 4px hoeken, primary in de accentkleur, secondary neutraal. */
.control-button {
	width: 40px;
	height: 40px;
	min-width: 40px;
	min-height: 40px;
	display: flex;
	align-items: center;
	justify-content: center;
	background: transparent;
	border: 1px solid var(--color-border);
	border-radius: 4px;
	color: var(--color-text);
	cursor: pointer;
	padding: 0;
}

.control-button:hover {
	background: color-mix(in srgb, var(--color-text) 7%, transparent);
}

.control-button.is-primary {
	color: var(--color-accent);
	border-color: var(--color-accent);
}

.control-button.is-primary:hover {
	background: color-mix(in srgb, var(--color-accent) 12%, transparent);
}

/* De -30s/+10s-knoppen (vergelijkbaar met YouTube's skip-knoppen) hebben
   naast het pijl-icoon ook een secondenaantal nodig, dus breder dan de
   vierkante iconknoppen. */
.control-button:has(.skip-label) {
	width: auto;
	min-width: 40px;
	padding: 0 8px;
	gap: 3px;
}

.skip-label {
	font-family: var(--font-mono);
	font-size: 0.65rem;
}

.time-label {
	font-family: var(--font-mono);
	font-size: var(--step--1);
	color: var(--color-muted);
}

.debate-link-button {
	margin-left: auto;
}
</style>
