<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import ArgumentCard from "./ArgumentCard.vue";
import VideoOverlay from "./VideoOverlay.vue";
import VideoPlayer from "./VideoPlayer.vue";
import VideoTimeline from "./VideoTimeline.vue";
import { PERSPECTIEVEN } from "../lib/tagIcons.generated";
import { perspectiefWeergaveNaam } from "../lib/tagIcon";
import type { Argument } from "../lib/types";
import { activeArguments } from "../lib/videoLabels";
import { requestSeek, videoSeek } from "../lib/videoSeek";

const props = defineProps<{ arguments: Argument[]; topicSlug: string }>();

const rawVideoUrl = props.arguments[0]?.document.raw_video_url ?? null;

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
</script>

<template>
	<div class="debate-video-view">
		<div class="player-column">
			<div v-if="rawVideoUrl" class="player-stage">
				<VideoPlayer
					:src="rawVideoUrl"
					:seek-to="videoSeek.seconds"
					:seek-token="videoSeek.token"
					@timeupdate="(t) => (currentTime = t)"
					@loadedmetadata="(d) => (duration = d)"
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
		<ol class="argument-list">
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

.argument-list {
	list-style: none;
	margin: 0;
	padding: 0;
	display: flex;
	flex-direction: column;
	gap: var(--space-2);
}
</style>
