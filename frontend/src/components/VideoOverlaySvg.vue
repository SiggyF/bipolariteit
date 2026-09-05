<script setup lang="ts">
import { computed } from "vue";
import { partyLogoSimple } from "../lib/parties";
import { formatClock } from "../lib/videoTime";
import { buildOverlayState, displayPartyName } from "../lib/videoOverlayState";
import type { Argument } from "../lib/types";

// Drop-in SVG-vervanger voor VideoOverlay.vue (issue #179): zelfde props,
// zelfde emit, zelfde onderliggende toestand (videoOverlayState.ts, al
// gedeeld met beide varianten) -- alleen de renderlaag is SVG i.p.v.
// losse HTML/CSS-elementen. Bedoeld om naast VideoOverlay.vue te draaien op
// frontend/src/pages/dev/video-overlay-compare.astro, zodat de daadwerkelijke
// vormgeving (niet een losse export-only benadering) vergeleken en
// bijgeschaafd kan worden vóórdat 'm ooit VideoOverlay.vue vervangt.
//
// Bekende beperking t.o.v. de div-versie: geen container-query-gebaseerde
// compacte badge-labels (die query bestaat niet in kale SVG) -- hier altijd
// het volledige label. Prev/next-knoppen zijn `<g role="button" tabindex>`
// i.p.v. echte `<button>`s: klembaar en met aria-label, maar mist de
// browser-ingebouwde Enter/Spatie-activatie van een echt buttonelement (hier
// met de hand toegevoegd via @keydown).

const props = defineProps<{
	arguments: Argument[];
	currentTime: number;
	off: Record<string, boolean>;
	followPaused?: boolean;
	minimal?: boolean;
}>();
const emit = defineEmits<{ seek: [seconds: number] }>();

function isVisible(tag: { perspectief: string }) {
	return !props.off[tag.perspectief];
}

const state = computed(() => buildOverlayState(props.arguments, props.currentTime, isVisible));

function seekTo(seconds: number | null) {
	if (seconds !== null) emit("seek", seconds);
}

// SVG kent geen ctx.measureText -- zelfde per-karakter-heuristiek als
// svgOverlayRenderer.ts (export) om de badge-/naamplaatbreedte te schatten.
function badgeWidth(badge: { shortLabel: string }): number {
	return Math.min(360, badge.shortLabel.length * 6.6 + 34);
}

const nameplateSecondColumnX = computed(() => 12 + (state.value.nameplate?.name.length ?? 0) * 8 + 10);

// Rechts uitgelijnd blok (vorig-pijl · tijdrange · volgend-pijl), net als
// .clock-group's margin-left:auto in de div-versie -- hier met de hand
// berekend omdat SVG geen flexbox kent.
const ARROW_WIDTH = 10;
const GAP = 8;
const navLayout = computed(() => {
	const timeWidth = state.value.timeRangeText ? state.value.timeRangeText.length * 6.2 : 0;
	const nextX = 640 - 12 - ARROW_WIDTH;
	const timeX = state.value.timeRangeText ? nextX - GAP - timeWidth : nextX;
	const prevX = timeX - (state.value.timeRangeText ? GAP : GAP) - ARROW_WIDTH;
	return { prevX, timeX, nextX };
});
</script>

<template>
	<svg class="video-overlay-svg" viewBox="0 0 640 360" preserveAspectRatio="xMidYMid slice">
		<defs>
			<linearGradient id="video-overlay-scrim" x1="0" y1="1" x2="0" y2="0">
				<stop offset="0" stop-color="rgba(0,0,0,0.55)" />
				<stop offset="0.3" stop-color="rgba(0,0,0,0)" />
			</linearGradient>
		</defs>
		<rect x="0" y="0" width="640" height="360" fill="url(#video-overlay-scrim)" />

		<Transition name="badge">
			<g v-if="state.showTitleCard && state.debateTitle">
				<rect x="32" y="12" width="576" height="34" rx="4" fill="rgba(0,0,0,0.55)" />
				<text x="320" y="34" fill="#fff" font-family="'Libre Caslon Text', Georgia, serif" font-weight="bold" font-size="15" text-anchor="middle">
					{{ state.debateTitle }}
				</text>
			</g>
		</Transition>

		<Transition name="badge">
			<text v-if="state.introBadge" x="12" y="30" fill="rgba(255,255,255,0.85)" font-family="'IBM Plex Mono', monospace" font-size="11" letter-spacing="0.3">
				{{ state.introBadge }}
			</text>
		</Transition>

		<TransitionGroup tag="g" name="badge">
			<g v-for="(badge, i) in state.badges" :key="badge.key" :transform="`translate(0, ${12 + i * 26})`">
				<title>{{ badge.tooltip }}</title>
				<rect :x="640 - 12 - badgeWidth(badge)" y="0" :width="badgeWidth(badge)" height="22" rx="3" fill="rgba(20,18,15,0.65)" />
				<rect :x="640 - 12 - badgeWidth(badge)" y="0" width="2" height="22" :fill="badge.color" />
				<circle :cx="640 - 12 - badgeWidth(badge) + 15" cy="11" r="8" :fill="badge.color" />
				<svg v-if="badge.iconPad" :x="640 - 12 - badgeWidth(badge) + 9" y="5" width="12" height="12" viewBox="0 0 24 24">
					<path :d="badge.iconPad" fill="none" stroke="#fff" stroke-width="2" />
				</svg>
				<text :x="640 - 12 - badgeWidth(badge) + 26" y="15" fill="#fff" font-family="'Libre Caslon Text', Georgia, serif" font-size="11">
					{{ badge.shortLabel }}
				</text>
			</g>
		</TransitionGroup>

		<g v-if="state.nameplate">
			<text x="12" y="340" fill="#fff" font-family="'Libre Caslon Text', Georgia, serif" font-style="italic" font-size="15">
				{{ state.nameplate.name }}
			</text>
			<template v-if="state.nameplate.party">
				<image
					v-if="partyLogoSimple(state.nameplate.party)"
					:href="partyLogoSimple(state.nameplate.party) ?? undefined"
					:x="nameplateSecondColumnX"
					y="329"
					width="14"
					height="14"
					style="filter: saturate(0.6)"
				/>
				<text :x="nameplateSecondColumnX + (partyLogoSimple(state.nameplate.party) ? 18 : 0)" y="340" fill="rgba(255,255,255,0.7)" font-family="'IBM Plex Mono', monospace" font-size="11" letter-spacing="1">
					{{ displayPartyName(state.nameplate.party).toUpperCase() }}
				</text>
			</template>
			<text v-else-if="state.nameplate.role_title" :x="nameplateSecondColumnX" y="340" fill="rgba(255,255,255,0.7)" font-family="'IBM Plex Mono', monospace" font-size="11" letter-spacing="1">
				{{ state.nameplate.role_title.toUpperCase() }}
			</text>

			<g
				role="button"
				tabindex="0"
				class="nav-button"
				:class="{ 'is-disabled': !state.prevArgument }"
				:aria-label="state.prevArgument ? `Vorig argument om ${formatClock(state.prevArgument.start_seconds as number)}` : 'Geen vorig argument'"
				@click="state.prevArgument && seekTo(state.prevArgument.start_seconds)"
				@keydown.enter="state.prevArgument && seekTo(state.prevArgument.start_seconds)"
				@keydown.space.prevent="state.prevArgument && seekTo(state.prevArgument.start_seconds)"
			>
				<title>{{ state.prevArgument ? `Vorig argument om ${formatClock(state.prevArgument.start_seconds as number)}` : "Geen vorig argument" }}</title>
				<text :x="navLayout.prevX" y="340" fill="rgba(255,255,255,0.55)" font-family="'IBM Plex Mono', monospace" font-size="11">←</text>
			</g>
			<text v-if="state.timeRangeText" :x="navLayout.timeX" y="340" fill="rgba(255,255,255,0.55)" font-family="'IBM Plex Mono', monospace" font-size="11">
				{{ state.timeRangeText }}
			</text>
			<g
				role="button"
				tabindex="0"
				class="nav-button"
				:class="{ 'is-disabled': !state.nextArgument }"
				:aria-label="state.nextArgument ? `Volgend argument om ${formatClock(state.nextArgument.start_seconds as number)}` : 'Geen volgend argument'"
				@click="state.nextArgument && seekTo(state.nextArgument.start_seconds)"
				@keydown.enter="state.nextArgument && seekTo(state.nextArgument.start_seconds)"
				@keydown.space.prevent="state.nextArgument && seekTo(state.nextArgument.start_seconds)"
			>
				<title>{{ state.nextArgument ? `Volgend argument om ${formatClock(state.nextArgument.start_seconds as number)}` : "Geen volgend argument" }}</title>
				<text :x="navLayout.nextX" y="340" fill="rgba(255,255,255,0.55)" font-family="'IBM Plex Mono', monospace" font-size="11">→</text>
			</g>
		</g>
	</svg>
</template>

<style scoped>
.video-overlay-svg {
	position: absolute;
	inset: 0;
	width: 100%;
	height: 100%;
	pointer-events: none;
}

.nav-button {
	pointer-events: auto;
	cursor: pointer;
}

.nav-button.is-disabled {
	pointer-events: none;
	opacity: 0.35;
}

.badge-enter-active,
.badge-leave-active {
	transition: opacity 0.2s;
}

.badge-enter-from,
.badge-leave-to {
	opacity: 0;
}
</style>
