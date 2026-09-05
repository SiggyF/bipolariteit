<script setup lang="ts">
import { reactive, ref } from "vue";
import VideoOverlay from "./VideoOverlay.vue";
import VideoOverlaySvg from "./VideoOverlaySvg.vue";
import type { Argument } from "../lib/types";

// Vergelijkingspagina (issue #179): de bestaande div-overlay naast de nieuwe
// SVG-drop-in-vervanger, over dezelfde statische achtergrond en dezelfde
// argumentdata, zodat het ontwerp visueel te toetsen is vóórdat
// VideoOverlaySvg.vue ooit VideoOverlay.vue in DebateVideoView.vue vervangt.
// Geen echte video (geen playback/CORS-afhankelijkheden nodig om alleen de
// overlay te beoordelen) -- een still als achtergrond volstaat.

function arg(overrides: Partial<Argument> & { id: number }): Argument {
	return {
		stance: "pro",
		typology: "factual",
		quote_text: "",
		quote_context: null,
		prompt_version: null,
		start_seconds: null,
		end_seconds: null,
		actor: { name: "Iemand", party: null, role_title: null },
		document: {
			id: 1,
			url: null,
			video_url: "https://debatdirect.tweedekamer.nl/2026-07-01/x/plenaire-zaal/samenhangende-aanpak-landbouw-natuur-en-stikstof-13-30/video",
			published_at: "2026-07-01T13:35:00",
			speaker_video_url: null,
			tweedekamer_activiteit_url: null,
			redactie_review: null,
			raw_video_url: null,
		},
		periode: { kamer: null, regering: null },
		claims: [],
		tags: [],
		oppositions: [],
		...overrides,
	};
}

function tag(sleutel: string, perspectief: string, labelgroep: string, reden: string | null = null) {
	return { sleutel, beschrijving: "", labelgroep, perspectief, created_by: "llm" as const, reden };
}

const fixtureArguments: Argument[] = [
	arg({
		id: 1,
		start_seconds: 0,
		end_seconds: 20,
		actor: { name: "Caroline van der Plas", party: "BBB", role_title: null },
		stance: "contra",
		typology: "moral",
		tags: [
			tag("Drogreden-Stroman", "Filosofisch & Argumentatietheoretisch", "Drogreden", "Zet de positie van de tegenstander overdreven zwart-wit neer."),
			tag("Stijlmiddel-Metafoor", "Communicatiewetenschappelijk & Media", "Stijlmiddel"),
		],
	}),
	arg({
		id: 2,
		start_seconds: 30,
		end_seconds: 60,
		actor: { name: "J. Jetten", party: "D66", role_title: null },
		stance: "pro",
		typology: "factual",
		tags: [tag("Actor-Politicus", "Sociologisch & Politicologisch", "Actor")],
	}),
	arg({
		id: 3,
		start_seconds: 70,
		end_seconds: 90,
		actor: { name: "Van Ooijen", party: null, role_title: "staatssecretaris van Volksgezondheid, Welzijn en Sport" },
		stance: "pro",
		typology: "legal",
		tags: [],
	}),
];

const currentTime = ref(5);
const off = reactive<Record<string, boolean>>({});
const maxTime = Math.max(...fixtureArguments.map((a) => a.end_seconds ?? 0)) + 10;

function handleSeek(seconds: number) {
	currentTime.value = seconds;
}
</script>

<template>
	<div class="compare">
		<p class="compare-controls">
			<label>
				t = {{ currentTime.toFixed(1) }}s
				<input v-model.number="currentTime" type="range" min="0" :max="maxTime" step="0.5" />
			</label>
		</p>
		<div class="stages">
			<div class="stage">
				<h2>Oud (div/CSS)</h2>
				<div class="video-stage">
					<div class="fake-video" />
					<VideoOverlay :arguments="fixtureArguments" :current-time="currentTime" :off="off" @seek="handleSeek" />
				</div>
			</div>
			<div class="stage">
				<h2>Nieuw (SVG-drop-in)</h2>
				<div class="video-stage">
					<div class="fake-video" />
					<VideoOverlaySvg :arguments="fixtureArguments" :current-time="currentTime" :off="off" @seek="handleSeek" />
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.compare {
	font-family: sans-serif;
	padding: 1rem;
}

.compare-controls {
	display: flex;
	gap: 1rem;
	align-items: center;
}

.compare-controls input[type="range"] {
	width: 400px;
	margin-left: 0.5rem;
}

.stages {
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: 1.5rem;
	margin-top: 1rem;
}

.video-stage {
	position: relative;
	aspect-ratio: 16 / 9;
	background: #333;
	container-type: inline-size;
	overflow: hidden;
	border-radius: 4px;
}

.fake-video {
	position: absolute;
	inset: 0;
	background: linear-gradient(135deg, #4a4a52 0%, #2a2a30 60%, #1a1a1e 100%);
}
</style>
