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

const props = defineProps<{ src: string; seekTo: number | null; seekToken: number }>();
const emit = defineEmits<{ timeupdate: [seconds: number]; loadedmetadata: [duration: number] }>();

const videoEl = ref<HTMLVideoElement | null>(null);
const fatalError = ref(false);
const playing = ref(false);
const muted = ref(true);
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
		</div>
	</div>
</template>

<style scoped>
.video-stage {
	position: relative;
	background: #000;
}

video {
	display: block;
	width: 100%;
	aspect-ratio: 16 / 9;
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

.time-label {
	font-family: var(--font-mono);
	font-size: var(--step--1);
	color: var(--color-muted);
}
</style>
