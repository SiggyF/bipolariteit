<script setup lang="ts">
import { computed, ref } from "vue";
import { debateId } from "../lib/debateId";
import { displayPartyName } from "../lib/parties";

// Issue #268: i.p.v. de volledige speler (DebateVideoView) toont de homepage
// hier een kort, vooraf gerenderd preview-fragment (scripts/build_shorts_sample.py)
// van het meest "emotionele" moment uit een steekproef debatten. Doorklikken
// gaat naar de échte, volledige debatpagina. Eén tegel voor nu -- een grid met
// meerdere tegels (play-on-hover) is een expliciet latere uitbreiding, zie de
// issue.
const props = defineProps<{
	dataBaseUrl: string;
}>();

interface ShortsManifestEntry {
	debatdirect_id: string;
	raw_video_url: string;
	topic_slug: string;
	topic_name: string;
	spreker: string;
	partij: string | null;
	citaat: string;
	score: number;
	clip_start_seconds: number;
	clip_duration_seconds: number;
	bestand: string;
}

type Status = "loading" | "error" | "ready" | "empty";

const status = ref<Status>("loading");
const entry = ref<ShortsManifestEntry | null>(null);

fetch(`${props.dataBaseUrl}/shorts/manifest.json`)
	.then((response) => {
		if (!response.ok) throw new Error(`HTTP ${response.status}`);
		return response.json() as Promise<ShortsManifestEntry[]>;
	})
	.then((manifest) => {
		if (manifest.length === 0) {
			status.value = "empty";
			return;
		}
		// Hoogst scorende clip (zelfde score als de selectie in
		// build_shorts_sample.py) -- geen aparte redactionele keuze nodig
		// bovenop wat de pipeline al rangschikt.
		entry.value = [...manifest].sort((a, b) => b.score - a.score)[0];
		status.value = "ready";
	})
	.catch(() => {
		status.value = "error";
	});

const clipUrl = computed(() => (entry.value ? `${props.dataBaseUrl}/shorts/${entry.value.bestand}` : null));
const debateHref = computed(() => (entry.value ? `/debatten/${debateId(entry.value.raw_video_url)}/` : null));

// Autoplay met geluid staat browsers niet toe -- de preview start dus muted
// (met loop, zoals een YouTube Shorts-tegel), met een losse knop om geluid
// aan te zetten. stopPropagation/preventDefault: de tegel zelf is de link
// naar de volledige debatpagina, deze knop mag daar niet doorheen navigeren.
const muted = ref(true);
function toggleMuted(event: MouseEvent) {
	event.preventDefault();
	event.stopPropagation();
	muted.value = !muted.value;
}
</script>

<template>
	<section v-if="status === 'ready' && entry" class="home-video-preview">
		<a :href="debateHref!" class="preview-tile" :aria-label="`Bekijk het volledige debat over ${entry.topic_name}`">
			<video
				:src="clipUrl!"
				:muted="muted"
				autoplay
				loop
				playsinline
				preload="auto"
			></video>
			<button
				type="button"
				class="preview-mute-toggle"
				:aria-label="muted ? 'Geluid aanzetten' : 'Geluid uitzetten'"
				:title="muted ? 'Geluid aanzetten' : 'Geluid uitzetten'"
				@click="toggleMuted"
			>
				<svg v-if="muted" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
					<path d="M11 5 6 9H2v6h4l5 4V5z" />
					<path d="M23 9l-6 6" />
					<path d="M17 9l6 6" />
				</svg>
				<svg v-else viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
					<path d="M11 5 6 9H2v6h4l5 4V5z" />
					<path d="M15.5 8.5a5 5 0 0 1 0 7" />
					<path d="M18.5 5.5a9 9 0 0 1 0 13" />
				</svg>
			</button>
			<div class="preview-caption">
				<p class="preview-quote">&ldquo;{{ entry.citaat }}&rdquo;</p>
				<p class="preview-meta">
					{{ entry.spreker }}<span v-if="entry.partij"> ({{ displayPartyName(entry.partij) }})</span> &middot; {{ entry.topic_name }}
				</p>
			</div>
		</a>
	</section>
</template>

<style scoped>
.home-video-preview {
	max-width: min(360px, 100%);
}

.preview-tile {
	position: relative;
	display: block;
	aspect-ratio: 16 / 9;
	border-radius: 6px;
	overflow: hidden;
	background: #000;
	color: inherit;
	text-decoration: none;
}

.preview-tile video {
	width: 100%;
	height: 100%;
	object-fit: cover;
	display: block;
}

.preview-mute-toggle {
	position: absolute;
	top: var(--space-1);
	right: var(--space-1);
	width: 36px;
	height: 36px;
	display: flex;
	align-items: center;
	justify-content: center;
	border: none;
	border-radius: 50%;
	background: rgba(0, 0, 0, 0.55);
	color: #fff;
	cursor: pointer;
}

.preview-mute-toggle:hover {
	background: rgba(0, 0, 0, 0.75);
}

/* Gradient onder de tekst i.p.v. een vlak vlak: houdt de ondertekst leesbaar
   ongeacht wat er in het videobeeld zelf gebeurt, zonder de hele tegel te
   verdonkeren (vergelijkbaar met YouTube Shorts' bijschrift-overlay). */
.preview-caption {
	position: absolute;
	left: 0;
	right: 0;
	bottom: 0;
	padding: var(--space-3) var(--space-2) var(--space-2);
	background: linear-gradient(to top, rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0));
	color: #fff;
}

.preview-quote {
	margin: 0 0 4px;
	font-size: var(--step--1);
	line-height: 1.3;
	display: -webkit-box;
	-webkit-line-clamp: 2;
	-webkit-box-orient: vertical;
	overflow: hidden;
}

.preview-meta {
	margin: 0;
	font-size: var(--step--1);
	opacity: 0.85;
}
</style>
