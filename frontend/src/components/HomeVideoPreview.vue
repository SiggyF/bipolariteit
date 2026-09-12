<script setup lang="ts">
import { reactive, ref } from "vue";
import { debateId } from "../lib/debateId";
import { displayPartyName } from "../lib/parties";
import { formatDate } from "../lib/formatDate";
import { slugify } from "../lib/slug";

// Issue #268: i.p.v. de volledige speler (DebateVideoView) toont de homepage
// hier een paar korte, vooraf gerenderde preview-fragmenten
// (scripts/build_shorts_sample.py) van de meest "emotionele" momenten uit een
// steekproef debatten -- zelfde kaart-idioom (.card-grid/.card-tile, main.css)
// als de "Uitgelicht"-sectie hieronder, maar dan één tegel per fragment i.p.v.
// per onderwerp/debat-zonder-video. Doorklikken op een tegel gaat naar de
// échte, volledige debatpagina.
const props = defineProps<{
	dataBaseUrl: string;
}>();

const TILE_COUNT = 4;

interface ShortsManifestEntry {
	debatdirect_id: string;
	raw_video_url: string;
	published_at: string | null;
	topic_slug: string;
	topic_name: string;
	spreker: string;
	partij: string | null;
	citaat: string;
	tags: string[];
	score: number;
	clip_start_seconds: number;
	clip_duration_seconds: number;
	bestand: string;
}

type Status = "loading" | "error" | "ready" | "empty";

const status = ref<Status>("loading");
const entries = ref<ShortsManifestEntry[]>([]);

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
		// Hoogst scorende clips eerst (zelfde score als de selectie in
		// build_shorts_sample.py) -- geen aparte redactionele keuze nodig
		// bovenop wat de pipeline al rangschikt.
		entries.value = [...manifest].sort((a, b) => b.score - a.score).slice(0, TILE_COUNT);
		status.value = "ready";
	})
	.catch(() => {
		status.value = "error";
	});

function clipUrl(entry: ShortsManifestEntry): string {
	return `${props.dataBaseUrl}/shorts/${entry.bestand}`;
}
function debateHref(entry: ShortsManifestEntry): string {
	return `/debatten/${debateId(entry.raw_video_url)}/`;
}

// Play-on-hover (zoals YouTube's hover-preview op een thumbnail), i.p.v.
// permanent autoplay: staat stil op het eerste frame tot de kijker er met de
// muis overheen gaat (of, voor toetsenbordgebruik, de tegel focust) en pauzeert
// weer zodra de muis/focus weggaat -- terug naar het begin, zodat een volgende
// hover weer bij het begin van het fragment start i.p.v. halverwege.
const videoEls = new Map<string, HTMLVideoElement>();
function setVideoEl(debatdirectId: string, el: Element | null) {
	if (el instanceof HTMLVideoElement) videoEls.set(debatdirectId, el);
	else videoEls.delete(debatdirectId);
}
function startPreview(entry: ShortsManifestEntry) {
	videoEls.get(entry.debatdirect_id)?.play().catch(() => {});
}
function stopPreview(entry: ShortsManifestEntry) {
	const video = videoEls.get(entry.debatdirect_id);
	if (!video) return;
	video.pause();
	video.currentTime = 0;
}

// Autoplay-met-geluid staat browsers niet toe -- elk fragment start dus muted,
// met een eigen knop om geluid aan te zetten. Per debatdirect_id i.p.v. één
// gedeelde ref: elke tegel heeft zijn eigen mute-status.
// stopPropagation/preventDefault: de tegel zelf is de link naar de volledige
// debatpagina, deze knop mag daar niet doorheen navigeren.
const mutedByDebate = reactive<Record<string, boolean>>({});
function isMuted(entry: ShortsManifestEntry): boolean {
	return mutedByDebate[entry.debatdirect_id] ?? true;
}
function toggleMuted(entry: ShortsManifestEntry, event: MouseEvent) {
	event.preventDefault();
	event.stopPropagation();
	mutedByDebate[entry.debatdirect_id] = !isMuted(entry);
}
</script>

<template>
	<section v-if="status === 'ready' && entries.length" class="home-video-preview">
		<ul class="card-grid card-grid--fragmenten">
			<li v-for="entry in entries" :key="entry.debatdirect_id">
				<a
					:href="debateHref(entry)"
					class="card-tile fragment-tile"
					:aria-label="`Bekijk het volledige debat over ${entry.topic_name}`"
					@mouseenter="startPreview(entry)"
					@mouseleave="stopPreview(entry)"
					@focus="startPreview(entry)"
					@blur="stopPreview(entry)"
				>
					<span class="card-tile-image fragment-video-wrap">
						<video
							:ref="(el) => setVideoEl(entry.debatdirect_id, el as Element | null)"
							:src="clipUrl(entry)"
							:muted="isMuted(entry)"
							loop
							playsinline
							preload="metadata"
						></video>
						<button
							type="button"
							class="preview-mute-toggle"
							:aria-label="isMuted(entry) ? 'Geluid aanzetten' : 'Geluid uitzetten'"
							:title="isMuted(entry) ? 'Geluid aanzetten' : 'Geluid uitzetten'"
							@click="toggleMuted(entry, $event)"
						>
							<svg v-if="isMuted(entry)" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
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
						</div>
					</span>
					<span class="card-tile-name">
						{{ entry.spreker }}<span v-if="entry.partij"> ({{ displayPartyName(entry.partij) }})</span>
					</span>
					<span class="card-tile-subtitle">{{ entry.topic_name }}</span>
					<span class="card-tile-count">{{ formatDate(entry.published_at) }}</span>
				</a>
				<!-- Buiten de tegel-link (nesten van <a> in <a> is ongeldige HTML):
				     de tagbadges linken zelf naar hun tagpagina, dus staan als
				     los rijtje onder de tegel, niet in de tegel-link zelf. -->
				<ul v-if="entry.tags.length" class="tags fragment-tags">
					<li v-for="tagSleutel in entry.tags" :key="tagSleutel" class="tag-item">
						<a class="tag-badge" :href="`/tags/${slugify(tagSleutel)}/`" :title="`Bekijk tagpagina: ${tagSleutel}`">{{ tagSleutel }}</a>
					</li>
				</ul>
			</li>
		</ul>
	</section>
</template>

<style scoped>
/* Bredere kolommen dan .card-grid's 140px-default (main.css): een 16:9-video
   heeft meer ruimte nodig dan een topic-still om herkenbaar te blijven --
   zelfde aanpak als index.astro's .highlighted-debates .card-grid. */
.card-grid--fragmenten {
	grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
}

/* .card-grid > li is standaard een rij-flexcontainer (main.css) -- prima
   zolang de tegel zijn enige kind is, maar met de tagbadges als losse buur
   ernaast (zie template: buiten de tegel-link, want <a> in <a> is ongeldig)
   moet die buur ONDER de tegel komen, niet ernaast. */
.card-grid--fragmenten > li {
	flex-direction: column;
}

.fragment-tile {
	padding: 0;
	overflow: hidden;
}

.fragment-tile .card-tile-name,
.fragment-tile .card-tile-subtitle,
.fragment-tile .card-tile-count {
	padding: 0 var(--space-2);
}

.fragment-tile .card-tile-name {
	margin-top: var(--space-1);
}

.fragment-tile .card-tile-count {
	margin-bottom: var(--space-2);
}

.fragment-tags {
	margin: var(--space-1) 0 0;
}

/* Gecombineerde selector (i.p.v. alleen .fragment-video-wrap) om zeker te
   winnen van .card-tile-image's vaste height:110px (main.css) ongeacht
   stylesheet-volgorde -- dezelfde specificiteit (één class) zou anders van
   laadvolgorde afhangen. */
.card-tile-image.fragment-video-wrap {
	position: relative;
	height: auto;
	aspect-ratio: 16 / 9;
	background: #000;
}

.fragment-video-wrap video {
	width: 100%;
	height: 100%;
	object-fit: cover;
	display: block;
	/* Geen desaturatie zoals .card-tile-image img elders: dit is een levend
	   fragment, geen still-thumbnail, dus moet er niet gedempt uitzien. */
	filter: none;
}

.preview-mute-toggle {
	position: absolute;
	top: var(--space-1);
	right: var(--space-1);
	width: 32px;
	height: 32px;
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

/* Gradient onder de tekst i.p.v. een vlak vlak: houdt het citaat leesbaar
   ongeacht wat er in het videobeeld zelf gebeurt, zonder het hele frame te
   verdonkeren (vergelijkbaar met YouTube Shorts' bijschrift-overlay). Alleen
   het citaat hier -- spreker/onderwerp/datum staan als gewone tekst onder de
   video, zie card-tile-name/-subtitle/-count hierboven. */
.preview-caption {
	position: absolute;
	left: 0;
	right: 0;
	bottom: 0;
	padding: var(--space-3) var(--space-2) var(--space-1);
	background: linear-gradient(to top, rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0));
	color: #fff;
}

.preview-quote {
	margin: 0;
	font-size: var(--step--1);
	line-height: 1.3;
	display: -webkit-box;
	-webkit-line-clamp: 2;
	-webkit-box-orient: vertical;
	overflow: hidden;
}
</style>
