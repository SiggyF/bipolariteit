<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import ArgumentCard from "./ArgumentCard.vue";
import VideoOverlay from "./VideoOverlay.vue";
import VideoPlayer from "./VideoPlayer.vue";
import VideoTimeline from "./VideoTimeline.vue";
import { PERSPECTIEVEN } from "../lib/tagIcons.generated";
import { perspectiefWeergaveNaam } from "../lib/tagIcon";
import type { Argument } from "../lib/types";
import { activeArguments } from "../lib/videoLabels";
import { requestSeek, videoSeek } from "../lib/videoSeek";
import { notifyUserScroll } from "../lib/userScroll";

const props = withDefaults(
	defineProps<{
		arguments: Argument[];
		topicSlug: string;
		defaultExpanded?: boolean;
		initialMuted?: boolean;
		// Link naar de volledige /debat/[id]/-pagina; alleen zinvol op plekken
		// die zelf niet al die pagina zijn (bv. de homepage-teaser).
		debateHref?: string | null;
	}>(),
	// Expliciet via withDefaults, niet `props.defaultExpanded ?? true`: Vue
	// cast een afwezige Boolean-prop zelf al naar `false` (vóórdat `??` iets
	// ziet), dus `false ?? true` zou nog steeds `false` opleveren.
	{ defaultExpanded: true, initialMuted: false },
);

const rawVideoUrl = props.arguments[0]?.document.raw_video_url ?? null;

// Inklapbare argumentenlijst: elders (bv. de homepage-teaser van het laatste
// debat) moet dezelfde view compact passen zonder de hele lijst permanent te
// tonen. `defaultExpanded` ontbreekt op /debat/[id]/, dus die pagina's gedrag
// blijft ongewijzigd (altijd uitgeklapt).
const expanded = ref(props.defaultExpanded);

const currentTime = ref(0);
const duration = ref(0);

watch(
	() => videoSeek.token,
	() => {
		if (videoSeek.seconds !== null) currentTime.value = videoSeek.seconds;
	},
);

// Perspectief aan/uit-toggle: filtert welke tags meetellen voor de
// overlay-badges en de tijdlijn-segmenten (niet welke argumenten getoond
// worden -- dat blijft tijdgebonden). Gedeeld tussen VideoOverlay en
// VideoTimeline, dus hier op het gemeenschappelijke ouderniveau.
const off = reactive<Record<string, boolean>>({});
function togglePerspective(name: string) {
	off[name] = !off[name];
}

// Welk argument(en) nu spelen, om de bijbehorende kaart in de lijst rechts
// te benadrukken (zelfde idee als de overlay-badges: currentTime is leidend).
const activeArgumentIds = computed(() => new Set(activeArguments(props.arguments, currentTime.value).map((a) => a.id)));

// Op de compacte teaser (debateHref gezet, bv. de homepage) is er geen ruimte
// voor de volledige argumentenlijst -- maar wel voor één compacte kaart van
// het argument dat nu speelt (issue #135), met linkjes naar persoon/partij/
// tag zodat die vanaf de homepage al bereikbaar zijn zonder eerst naar de
// volledige debatpagina te hoeven.
const nowPlaying = computed(() => activeArguments(props.arguments, currentTime.value)[0] ?? null);

// Onderdrukt de auto-volg-scroll in ArgumentCard.vue zolang de gebruiker zelf
// aan het scrollen is (zie lib/userScroll.ts) -- window-niveau, want player-
// en argumentenkolom delen dezelfde paginascroll.
onMounted(() => {
	window.addEventListener("wheel", notifyUserScroll, { passive: true });
	window.addEventListener("touchmove", notifyUserScroll, { passive: true });
});
onUnmounted(() => {
	window.removeEventListener("wheel", notifyUserScroll);
	window.removeEventListener("touchmove", notifyUserScroll);
});
</script>

<template>
	<div class="debate-video-view" :class="{ 'is-compact': !expanded }">
		<div class="player-column">
			<div v-if="rawVideoUrl" class="player-stage">
				<VideoPlayer
					:src="rawVideoUrl"
					:seek-to="videoSeek.seconds"
					:seek-token="videoSeek.token"
					:initial-muted="props.initialMuted"
					:debate-href="props.debateHref"
					@timeupdate="(t) => (currentTime = t)"
					@loadedmetadata="(d) => (duration = d)"
					@seek="requestSeek"
				>
					<VideoOverlay :arguments="props.arguments" :current-time="currentTime" :off="off" @seek="requestSeek" />
				</VideoPlayer>
			</div>
			<p v-else class="no-video">Voor dit debat is geen video beschikbaar.</p>
			<VideoTimeline
				v-if="rawVideoUrl"
				:arguments="props.arguments"
				:current-time="currentTime"
				:duration="duration"
				:off="off"
			/>
			<div class="perspective-filters">
				<span class="perspective-filters-label">Perspectief</span>
				<button
					v-for="p in PERSPECTIEVEN"
					:key="p.naam"
					type="button"
					class="perspective-toggle"
					:class="{ 'is-off': off[p.naam] }"
					:style="{ '--perspective-color': p.kleur }"
					@click="togglePerspective(p.naam)"
				>
					<span class="perspective-dot"></span>{{ perspectiefWeergaveNaam(p.naam) }}
				</button>
			</div>
		</div>
		<div v-if="!props.debateHref" class="argument-column">
			<button type="button" class="argument-toggle" @click="expanded = !expanded">
				<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
					<path
						d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"
					/>
				</svg>
				{{ expanded ? "Argumenten verbergen" : "Argumenten tonen" }}
			</button>
			<ol v-if="expanded" class="argument-list">
				<li v-for="argument in props.arguments" :key="argument.id">
					<ArgumentCard
						:argument="argument"
						:topic-slug="props.topicSlug"
						video-context
						:playing="activeArgumentIds.has(argument.id)"
						@seek="requestSeek"
					/>
				</li>
			</ol>
		</div>
		<!-- Compacte plek (debateHref gezet, bv. de homepage-teaser): geen ruimte
		     voor de volledige lijst, wel voor één compacte "nu in beeld"-kaart
		     (issue #135). -->
		<div v-else-if="nowPlaying" class="now-playing">
			<ArgumentCard :argument="nowPlaying" :topic-slug="props.topicSlug" compact video-context :playing="true" @seek="requestSeek" />
		</div>
	</div>
</template>

<style scoped>
.debate-video-view {
	display: grid;
	grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
	gap: var(--space-4);
	align-items: start;
}

@media (max-width: 900px) {
	.debate-video-view {
		grid-template-columns: 1fr;
	}
}

/* Ingeklapte argumentenlijst: de player-kolom mag de volle breedte
   innemen i.p.v. naast een lege rechterkolom te blijven staan. De
   rij-afstand (anders 32px, bedoeld voor twee kolommen naast elkaar) is in
   deze ene kolom veel te veel lucht boven de link/toggle-rij. */
.debate-video-view.is-compact {
	grid-template-columns: 1fr;
	row-gap: var(--space-1);
}

/* Alleen bereikbaar door handmatig in te klappen op /debatten/[id]/ (de
   homepage-teaser rendert i.p.v. .argument-column de .now-playing-kaart
   hieronder, zie template): in ingeklapte stand staat er alleen de
   toggle-knop in deze kolom, die hoort dan bij de rand van de player. */
.debate-video-view.is-compact .argument-column {
	display: flex;
	justify-content: flex-end;
	gap: var(--space-2);
}

/* Perspectief-filters zijn een volledige-pagina-feature (filteren wat de
   tijdlijn/overlay tonen) -- op een compacte teaser kost die rij(en) knoppen
   meer ruimte dan ze daar opleveren. */
.debate-video-view.is-compact .perspective-filters {
	display: none;
}

.player-column {
	position: sticky;
	top: var(--space-2);
}

.no-video {
	color: var(--color-muted);
	padding: var(--space-3);
	background: var(--color-card-bg);
	border: 1px solid var(--color-border);
	border-radius: 4px;
}

.perspective-filters {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 8px;
	margin-top: var(--space-2);
}

.perspective-filters-label {
	font-size: var(--step--1);
	letter-spacing: 0.08em;
	text-transform: uppercase;
	color: var(--color-muted);
}

.perspective-toggle {
	display: flex;
	align-items: center;
	gap: 6px;
	padding: 5px 10px;
	border: 1px solid color-mix(in srgb, var(--perspective-color) 45%, var(--color-border));
	background: color-mix(in srgb, var(--perspective-color) 8%, var(--color-bg));
	border-radius: 3px;
	font-size: var(--step--1);
	color: var(--color-text);
	cursor: pointer;
}

.perspective-toggle.is-off {
	opacity: 0.45;
	border-color: var(--color-border);
	background: transparent;
}

.perspective-dot {
	width: 8px;
	height: 8px;
	border-radius: 50%;
	background: var(--perspective-color);
}

.argument-toggle {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	padding: 5px 10px;
	background: transparent;
	border: 1px solid var(--color-border);
	border-radius: 4px;
	color: var(--color-text);
	font-size: var(--step--1);
	text-decoration: none;
	cursor: pointer;
}

/* Buiten de compacte (ingeklapte) stand heeft de toggle wel ruimte nodig
   t.o.v. de argumentenlijst eronder. */
.debate-video-view:not(.is-compact) .argument-toggle {
	margin-bottom: var(--space-2);
}

.argument-list {
	list-style: none;
	margin: 0;
	padding: 0;
	display: flex;
	flex-direction: column;
	gap: var(--space-2);
}
</style>
