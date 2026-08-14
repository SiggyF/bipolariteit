<script setup lang="ts">
import { scaleLinear } from "d3-scale";
import { select } from "d3-selection";
import { zoom as d3zoom, zoomIdentity, type ZoomTransform } from "d3-zoom";
import { computed, onMounted, ref, useId, useTemplateRef } from "vue";
import { PERSPECTIEVEN } from "../lib/tagIcons.generated";
import type { Argument } from "../lib/types";
import { selectBadgeTags } from "../lib/videoLabels";
import { requestSeek } from "../lib/videoSeek";
import { formatClock } from "../lib/videoTime";

// SVG-tijdlijn: as met tijdstippen, per-spreekbeurt-markers (gegroepeerd op
// document.id) en per-argument segmenten, gekleurd op de zeldzaamste
// zichtbare tag. Rechtstreeks gemodelleerd naar het opgeleverde
// ontwerpprototype (docs/design/videoplayer/, .dc.html) i.p.v. losse
// HTML-knoppen -- dat oogde te "form-achtig" voor een scrubber.
//
// Toevoeging t.o.v. het prototype: een zoombaar venster via d3-zoom (wiel +
// slepen + pinch). Het prototype toont een vast venster van een paar
// minuten; sommige debatten hier beslaan 11+ uur manifest, dus zonder zoom
// zou alles tot een paar pixels samenpersen. d3-zoom levert alleen het
// gebaar/de transform -- Vue blijft alle SVG-content renderen, geen
// d3-DOM-manipulatie.

const props = defineProps<{
	arguments: Argument[];
	currentTime: number;
	duration: number;
	off: Record<string, boolean>;
}>();

const colorByPerspective = new Map(PERSPECTIEVEN.map((p) => [p.naam, p.kleur]));

function isVisible(tag: { perspectief: string }) {
	return !props.off[tag.perspectief];
}

const svgWidth = 900;
const height = 58;
const axisY = 34;

const svgEl = useTemplateRef<SVGSVGElement>("svgEl");
const transform = ref<ZoomTransform>(zoomIdentity);
const zoomBehavior = d3zoom<SVGSVGElement, unknown>()
	.scaleExtent([1, 2000])
	.translateExtent([[0, 0], [svgWidth, height]])
	.extent([[0, 0], [svgWidth, height]])
	.on("zoom", (event) => {
		transform.value = event.transform;
	});

onMounted(() => {
	if (svgEl.value) select(svgEl.value).call(zoomBehavior);
});

function zoomReset() {
	if (svgEl.value) select(svgEl.value).transition().duration(300).call(zoomBehavior.transform, zoomIdentity);
}

const isFullWindow = computed(() => transform.value.k === 1);

// Basisschaal over de volledige duur; de zoom-transform herschaalt 'm tot
// het huidige venster (d3's rescaleX-idioom).
const baseScale = computed(() => scaleLinear().domain([0, props.duration]).range([0, svgWidth]));
const scale = computed(() => transform.value.rescaleX(baseScale.value).clamp(true));
const windowStart = computed(() => scale.value.domain()[0]);
const windowEnd = computed(() => scale.value.domain()[1]);

function X(t: number): number {
	return scale.value(t);
}

const ticks = computed(() => {
	if (props.duration <= 0) return [];
	return scale.value.ticks(8).map((t) => ({ t, x: X(t) }));
});

interface Turn {
	documentId: number;
	start: number;
	actor: string;
	party: string | null;
	args: Argument[];
}

const turns = computed(() => {
	const perDocument = new Map<number, Turn>();
	for (const argument of props.arguments) {
		if (argument.start_seconds === null) continue;
		let turn = perDocument.get(argument.document.id);
		if (!turn) {
			turn = { documentId: argument.document.id, start: argument.start_seconds, actor: argument.actor.name, party: argument.actor.party, args: [] };
			perDocument.set(argument.document.id, turn);
		}
		turn.start = Math.min(turn.start, argument.start_seconds);
		turn.args.push(argument);
	}
	return [...perDocument.values()].sort((a, b) => a.start - b.start);
});

const turnMarkers = computed(() => {
	const visible = turns.value.filter((tn) => tn.start >= windowStart.value && tn.start <= windowEnd.value);
	const current = currentTurn.value;
	let lastLabelX = -999;
	return visible.map((tn) => {
		const x = X(tn.start);
		const showLabel = x - lastLabelX > 46;
		if (showLabel) lastLabelX = x;
		return { turn: tn, x, active: current?.documentId === tn.documentId, showLabel };
	});
});

const currentTurn = computed(() => {
	let current: Turn | null = null;
	for (const tn of turns.value) {
		if (tn.start <= props.currentTime) current = tn;
	}
	return current;
});

interface Segment {
	argument: Argument;
	x0: number;
	x1: number;
	color: string;
	active: boolean;
}

const segments = computed(() => {
	const result: Segment[] = [];
	for (const argument of props.arguments) {
		if (argument.start_seconds === null || argument.end_seconds === null) continue;
		if (argument.end_seconds < windowStart.value || argument.start_seconds > windowEnd.value) continue;
		const visibleTags = selectBadgeTags(argument, props.arguments, isVisible);
		if (!visibleTags.length) continue;
		const leading = visibleTags[0];
		const x0 = X(argument.start_seconds);
		const x1 = Math.max(X(argument.end_seconds), x0 + 2);
		result.push({
			argument,
			x0,
			x1,
			color: colorByPerspective.get(leading.perspectief) ?? "var(--color-muted)",
			active: props.currentTime >= argument.start_seconds && props.currentTime <= argument.end_seconds,
		});
	}
	return result;
});

const playheadX = computed(() => X(props.currentTime));
// Uniek per instance, anders botsen meerdere tijdlijnen op dezelfde pagina
// op hetzelfde filter-id.
const glowFilterId = `playhead-glow-${useId()}`;

// Klikken (geen sleep -- dat vangt d3-zoom als pan af) springt naar dat
// moment; de klik landt op viewBox-coördinaten via de bounding box, want de
// svg schaalt responsief (viewBox 0 0 svgWidth height, CSS-breedte 100%).
function onScrubberClick(event: MouseEvent) {
	const rect = (event.currentTarget as SVGSVGElement).getBoundingClientRect();
	const x = ((event.clientX - rect.left) / rect.width) * svgWidth;
	requestSeek(scale.value.invert(x));
}

function seekBy(deltaSeconds: number) {
	requestSeek(Math.max(0, props.currentTime + deltaSeconds));
}

function zoomKeyboard(factor: number) {
	if (svgEl.value) select(svgEl.value).transition().duration(150).call(zoomBehavior.scaleBy, factor);
}

function onKeydown(event: KeyboardEvent) {
	if (event.key === "ArrowRight") {
		seekBy(5);
		event.preventDefault();
	} else if (event.key === "ArrowLeft") {
		seekBy(-5);
		event.preventDefault();
	} else if (event.key === "+" || event.key === "=") {
		zoomKeyboard(2);
		event.preventDefault();
	} else if (event.key === "-") {
		zoomKeyboard(0.5);
		event.preventDefault();
	}
}
</script>

<template>
	<div class="video-timeline">
		<div class="zoom-controls">
			<span class="zoom-range">{{ formatClock(windowStart) }} – {{ formatClock(windowEnd) }} van {{ formatClock(duration) }}</span>
			<span class="zoom-hint">scroll om te zoomen, sleep om te pannen</span>
			<button type="button" :disabled="isFullWindow" @click="zoomReset">alles</button>
		</div>

		<svg
			ref="svgEl"
			:viewBox="`0 0 ${svgWidth} ${height}`"
			class="scrubber"
			role="slider"
			:aria-valuemin="windowStart"
			:aria-valuemax="windowEnd"
			:aria-valuenow="currentTime"
			:aria-valuetext="formatClock(currentTime)"
			tabindex="0"
			@keydown="onKeydown"
			@click="onScrubberClick"
		>
			<line :x1="0" :x2="svgWidth" :y1="axisY" :y2="axisY" class="axis" />
			<line :x1="0" :x2="playheadX" :y1="axisY" :y2="axisY" class="axis-progress" />

			<g v-for="tick in ticks" :key="tick.t">
				<line :x1="tick.x" :x2="tick.x" :y1="axisY" :y2="axisY + 5" class="tick" />
				<text :x="tick.x" :y="axisY + 17" text-anchor="middle" class="tick-label">{{ formatClock(tick.t) }}</text>
			</g>

			<template v-for="marker in turnMarkers" :key="marker.turn.documentId">
				<line
					:x1="marker.x"
					:x2="marker.x"
					:y1="axisY - 9"
					:y2="axisY + 9"
					:class="['turn-tick', { 'is-active': marker.active }]"
				/>
				<text
					v-if="marker.showLabel"
					:x="marker.x + 3"
					:y="10"
					:text-anchor="marker.x > svgWidth - 60 ? 'end' : 'start'"
					:class="['turn-label', { 'is-active': marker.active }]"
				>
					{{ marker.turn.actor.split(" ").at(-1) }}
				</text>
			</template>

			<rect
				v-for="segment in segments"
				:key="segment.argument.id"
				:x="segment.x0"
				:y="axisY - 5"
				:width="segment.x1 - segment.x0"
				:height="10"
				rx="2"
				:fill="segment.color"
				:opacity="segment.active ? 0.95 : 0.32"
				class="segment"
				@click.stop="requestSeek((segment.argument.start_seconds as number) + 0.4)"
			>
				<title>
					{{ formatClock(segment.argument.start_seconds ?? 0) }}–{{ formatClock(segment.argument.end_seconds ?? 0) }} ·
					{{ segment.argument.actor.name }}
				</title>
			</rect>

			<!-- Naald in de stijl van een jaren 60/70-radiotuner: een dun rood
			     lijntje met een zachte, vervagende "plastic" gloed erachter,
			     i.p.v. een harde lijn+cirkel. -->
			<defs>
				<filter :id="glowFilterId" x="-200%" y="-20%" width="400%" height="140%">
					<feGaussianBlur stdDeviation="3" />
				</filter>
			</defs>
			<rect
				:x="playheadX - 7"
				:y="0"
				width="14"
				:height="height"
				class="playhead-glow"
				:filter="`url(#${glowFilterId})`"
			/>
			<line :x1="playheadX" :x2="playheadX" :y1="1" :y2="height - 1" class="playhead" />
		</svg>
	</div>
</template>

<style scoped>
.video-timeline {
	display: flex;
	flex-direction: column;
	gap: 4px;
}

.zoom-controls {
	display: flex;
	align-items: center;
	gap: 6px;
	font-size: var(--step--1);
	color: var(--color-muted);
}

.zoom-controls button {
	background: none;
	border: none;
	color: var(--color-muted);
	cursor: pointer;
	font-size: 1em;
	padding: 2px 4px;
}

.zoom-controls button:hover:not(:disabled) {
	color: var(--color-accent);
}

.zoom-controls button:disabled {
	opacity: 0.4;
	cursor: default;
}

.zoom-range {
	margin-right: auto;
}

.zoom-hint {
	opacity: 0.6;
}

.scrubber {
	display: block;
	width: 100%;
	height: 58px;
	cursor: pointer;
	touch-action: none;
	border-top: 1px solid var(--color-border);
	border-bottom: 1px solid var(--color-border);
	/* Zonder dit geeft WebKit/Chrome een blauwe tik-flits bij elke klik --
	   niet de bedoelde focus-styling hieronder, gewoon de standaard
	   tap-highlight voor klikbare elementen. */
	-webkit-tap-highlight-color: transparent;
	outline: none;
}

.scrubber:focus-visible {
	outline: 2px solid var(--color-accent);
}

.axis {
	stroke: var(--color-border);
	stroke-width: 1;
}

.axis-progress {
	stroke: var(--color-accent);
	stroke-width: 1.5;
}

.tick {
	stroke: var(--color-border);
}

.tick-label {
	font-size: 9.5px;
	fill: var(--color-text);
	opacity: 0.45;
	font-family: var(--font-body);
}

.turn-tick {
	stroke: var(--color-border);
}

.turn-tick.is-active {
	stroke: var(--color-accent);
}

.turn-label {
	font-size: 9.5px;
	fill: var(--color-text);
	opacity: 0.4;
	font-family: var(--font-body);
}

.turn-label.is-active {
	opacity: 0.85;
}

.segment {
	cursor: pointer;
	stroke: none;
	-webkit-tap-highlight-color: transparent;
}

/* --color-contra (warm rood) puur om de kleur -- geen inhoudelijke link met
   "contra" hier, het is de enige rode tint in het palet en past bij het
   radiotuner-referentiebeeld. */
.playhead-glow {
	fill: var(--color-contra);
	opacity: 0.35;
}

.playhead {
	stroke: var(--color-contra);
	stroke-width: 1.25;
}
</style>
