<script setup lang="ts">
import { reactive, ref } from "vue";
import { debateId } from "../lib/debateId";
import { debateName } from "../lib/debateName";
import { displayPartyName } from "../lib/parties";
import { formatDate } from "../lib/formatDate";
import { tagIconPath, tagKleur } from "../lib/tagIcon";
import { formatClock } from "../lib/videoTime";
import PartyLogo from "./PartyLogo.vue";

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
	video_url: string | null;
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
// ?t=<seconden>: zelfde patroon als VideoPlayer.vue's debateHrefWithTime --
// een teaser die doorlinkt naar de volledige debatpagina neemt de
// afspeelpositie mee, zodat je daar niet weer bij 0:00 begint maar bij het
// getoonde fragment.
function debateHref(entry: ShortsManifestEntry): string {
	return `/debatten/${debateId(entry.raw_video_url)}/?t=${Math.floor(entry.clip_start_seconds)}`;
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
						<!-- Icoon-only, thematisch gekleurd (zelfde bron als
						     DebateVideoView.vue's perspective-toggles: PERSPECTIEVEN,
						     via tagKleur()/tagIconPath() in lib/tagIcon.ts), overlay
						     rechtsboven op de video (consistent met tagbadges elders
						     op de site), geen tekstlabel en geen eigen link (zou een a
						     in een a zijn, ongeldige HTML binnen de tegel-link). -->
						<span v-if="entry.tags.length" class="fragment-tag-icons">
							<span
								v-for="tagSleutel in entry.tags"
								:key="tagSleutel"
								class="fragment-tag-icon"
								:title="tagSleutel"
								:style="{ '--tag-color': tagKleur(tagSleutel) ?? 'var(--galnoot-zacht)' }"
							>
								<svg v-if="tagIconPath(tagSleutel)" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
									<path :d="tagIconPath(tagSleutel)!" />
								</svg>
							</span>
						</span>
						<!-- Tijdstip van het fragment IN het debat (niet de clipduur) --
						     zelfde plek/stijl als YouTube's duurbadge, maar hier het
						     startpunt: geeft aan waar in het debat dit moment zit, en
						     komt overeen met de ?t= in debateHref() hierboven. -->
						<span class="fragment-time-pointer">{{ formatClock(entry.clip_start_seconds) }}</span>
						<div class="preview-caption">
							<p class="preview-quote">&ldquo;{{ entry.citaat }}&rdquo;</p>
						</div>
					</span>
					<span class="card-tile-name">
						<PartyLogo v-if="entry.partij" :party="entry.partij" :title="displayPartyName(entry.partij)" />
						{{ entry.spreker }}
					</span>
					<span v-if="debateName(entry.video_url)" class="fragment-debate-title">{{ debateName(entry.video_url) }}</span>
					<span class="card-tile-subtitle">{{ entry.topic_name }}</span>
					<span class="card-tile-count">{{ formatDate(entry.published_at) }} &middot; {{ formatClock(entry.clip_start_seconds) }}</span>
				</a>
			</li>
		</ul>
	</section>
</template>

<style scoped>
/* Bredere kolommen dan .card-grid's 140px-default (main.css): een 16:9-video
   heeft meer ruimte nodig dan een topic-still om herkenbaar te blijven --
   zelfde minmax als index.astro's .highlighted-debates .card-grid, zodat
   beide secties op dezelfde tegelbreedte uitkomen. auto-fit i.p.v. auto-fill:
   met minder tegels dan er kolommen passen, laat auto-fill de resterende
   (lege) kolombanen toch meetellen voor de 1fr-verdeling -- de tegels worden
   dan smaller dan in de sectie eronder, die toevallig wél evenveel kolommen
   als tegels heeft. auto-fit laat lege banen instorten, dus de tegels
   vullen altijd de volle rijbreedte, ongeacht het aantal. */
.card-grid--fragmenten {
	grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
}

/* Overlay rechtsboven op de video (mute-knop staat linksboven, zie
   .preview-mute-toggle) -- zelfde plek als tagbadges/-iconen elders op de
   site (bv. ArgumentCard.vue), icoon-only, cirkelvormig zoals de mute-knop. */
.fragment-tag-icons {
	position: absolute;
	top: var(--space-1);
	right: var(--space-1);
	display: flex;
	gap: 4px;
	z-index: 1;
}

/* Thematische kleur + icoon per tag (zelfde bron als DebateVideoView.vue's
   perspective-toggles/ActorTagUsage.vue: PERSPECTIEVEN, via tagKleur()/
   tagIconPath() in lib/tagIcon.ts) -- het icoon draagt de identiteit
   (dataviz-skill: "identity is never color-alone"), de kleur versterkt 'm. */
.fragment-tag-icon {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 32px;
	height: 32px;
	border-radius: 50%;
	background: rgba(0, 0, 0, 0.55);
	color: var(--tag-color);
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
	/* Zelfde desaturatie als .card-tile-image img elders (main.css), voor een
	   consistente stijl tussen deze sectie en "Uitgelichte debatten" -- alleen
	   tijdens het afspelen (hover/focus, zie .fragment-tile:hover/:focus-within
	   hieronder) weer volle kleur, zodat het fragment dan juist wél levendig
	   oogt. */
	filter: saturate(0.6);
	transition: filter 0.15s ease;
}

.fragment-tile:hover video,
.fragment-tile:focus-within video {
	filter: none;
}

.preview-mute-toggle {
	position: absolute;
	top: var(--space-1);
	left: var(--space-1);
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

/* Zelfde plek/stijl als YouTube's duurbadge (rechtsonder op de thumbnail),
   maar hier het startpunt van het fragment ín het debat i.p.v. de clipduur
   -- zie de template-comment bij .fragment-time-pointer. */
.fragment-time-pointer {
	position: absolute;
	bottom: var(--space-1);
	right: var(--space-1);
	z-index: 1;
	padding: 1px 5px;
	border-radius: 3px;
	background: rgba(0, 0, 0, 0.7);
	color: #fff;
	font-family: var(--font-kop);
	font-size: var(--step--1);
	font-variant-numeric: tabular-nums;
}

.fragment-debate-title {
	font-size: var(--step--1);
	line-height: 1.3;
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
	font-style: italic;
	font-size: var(--step--1);
	line-height: 1.3;
	display: -webkit-box;
	-webkit-line-clamp: 2;
	-webkit-box-orient: vertical;
	overflow: hidden;
}
</style>
