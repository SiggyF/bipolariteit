<script setup lang="ts">
import { computed } from "vue";
import { debateName } from "../lib/debateName";
import { formatDate } from "../lib/formatDate";
import { perspectiefWeergaveNaam, tagIconPath } from "../lib/tagIcon";
import { PERSPECTIEVEN } from "../lib/tagIcons.generated";
import { stanceLabel, typologyLabel, type Argument } from "../lib/types";
import { activeArguments, selectBadgeTags } from "../lib/videoLabels";
import { formatClock } from "../lib/videoTime";
import { displayPartyName } from "../lib/parties";
import PartyLogo from "./PartyLogo.vue";

// Overlay over de <video> heen: lower-third naamplaatje + tot 3 tag-badges
// per actief argument. Zie docs/design/videoplayer/README.md "Overgangen" en
// "Toegankelijkheid" -- icoon+tekst altijd samen, nooit kleur alleen, nooit
// tekst direct op beeld (vandaar de achtergrond per badge hieronder).

const props = defineProps<{ arguments: Argument[]; currentTime: number; off: Record<string, boolean> }>();
const emit = defineEmits<{ seek: [seconds: number] }>();

const colorByPerspective = new Map(PERSPECTIEVEN.map((p) => [p.naam, p.kleur]));

function isVisible(tag: { perspectief: string }) {
	return !props.off[tag.perspectief];
}

const active = computed(() => activeArguments(props.arguments, props.currentTime));

// Titelkaart bij het begin van de video: debat + datum, zodat je ook zonder
// de (soms lange) paginatitel erboven te lezen weet welk debat dit is --
// vooral relevant voor de compacte homepage-teaser (issue #110), waar die
// titel nu kort ("Laatste gelabelde debat") is i.p.v. de volledige debatnaam.
const debateTitle = computed(() => debateName(props.arguments[0]?.document.video_url ?? null));
const debateDate = computed(() => formatDate(props.arguments[0]?.document.published_at ?? null));
const showTitleCard = computed(() => props.currentTime < 4.5);

// Uit het ontwerpprototype (.dc.html): naast de naamplaat een klok die, als
// er nu geen gelabeld argument loopt, "volgend argument om ..." toont en
// aanklikbaar is -- anders staar je naar een gat in de tijdlijn zonder iets
// te kunnen doen.
const nextArgument = computed(() => {
	return props.arguments
		.filter((a) => a.start_seconds !== null && a.start_seconds > props.currentTime)
		.sort((a, b) => (a.start_seconds as number) - (b.start_seconds as number))[0] ?? null;
});

// De naamplaat blijft ook zichtbaar in een gat tussen twee gelabelde
// argumenten (anders verdwijnt-ie zodra "volgend argument" nog getoond moet
// worden): actieve spreker, anders de laatst gestarte, anders de eerstvolgende.
const nameplate = computed(() => {
	if (active.value[0]) return active.value[0].actor;
	const past = props.arguments
		.filter((a) => a.start_seconds !== null && a.start_seconds <= props.currentTime)
		.sort((a, b) => (b.start_seconds as number) - (a.start_seconds as number))[0];
	return past?.actor ?? nextArgument.value?.actor ?? null;
});

// Tijdrange van het lopende argument, los van de "volgend argument"-knop --
// die staat er nu altijd naast (i.p.v. alleen in een gat), maar compact
// (pijl-icoon) als er al een tijdrange getoond wordt, anders voluit in tekst.
const timeRangeText = computed(() => {
	const current = active.value[0];
	if (current?.start_seconds != null && current?.end_seconds != null) {
		return `${formatClock(current.start_seconds)}–${formatClock(current.end_seconds)}`;
	}
	return null;
});

// Kort, niet-prominent flitsje bij het begin van een spreekbeurt: type
// onderbouwing + pro/contra. Verdwijnt na 3s, blijft daarna alleen de
// tag-badges over -- geen constante ruis.
const introBadge = computed(() => {
	const argument = active.value[0];
	if (!argument || argument.start_seconds === null) return null;
	const sinceStart = props.currentTime - argument.start_seconds;
	if (sinceStart < 0 || sinceStart > 3) return null;
	return `${typologyLabel(argument.typology)} · ${stanceLabel(argument.stance)}`;
});

// Categorie + perspectief gaan niet meer altijd zichtbaar op de badge (te
// veel tekst over het beeld), maar in de title-tooltip bij hover.
const badges = computed(() =>
	active.value.flatMap((argument) =>
		selectBadgeTags(argument, props.arguments, isVisible).map((tag) => ({
			key: `${argument.id}-${tag.sleutel}`,
			label: tag.sleutel,
			iconPad: tagIconPath(tag.sleutel),
			color: colorByPerspective.get(tag.perspectief) ?? "var(--color-muted)",
			tooltip: tag.reden
				? `${tag.labelgroep} · ${perspectiefWeergaveNaam(tag.perspectief)}\n\n${tag.reden}`
				: `${tag.labelgroep} · ${perspectiefWeergaveNaam(tag.perspectief)}`,
		})),
	),
);
</script>

<template>
	<div class="video-overlay">
		<Transition name="badge">
			<div v-if="showTitleCard && debateTitle" class="title-card">
				<span class="title-card-name">{{ debateTitle }}</span>
				<span class="title-card-date">{{ debateDate }}</span>
			</div>
		</Transition>
		<Transition name="badge">
			<div v-if="introBadge" class="intro-badge">{{ introBadge }}</div>
		</Transition>
		<!-- Verticale rail rechts, los van het naamplaatje: houdt het midden
		     van het beeld (de spreker) vrij i.p.v. een brede balk onderin. -->
		<TransitionGroup tag="div" name="badge" class="badges">
			<div
				v-for="badge in badges"
				:key="badge.key"
				class="badge"
				:style="{ '--badge-color': badge.color }"
				:title="badge.tooltip"
			>
				<span class="badge-icon-circle">
					<svg v-if="badge.iconPad" viewBox="0 0 24 24" class="badge-icon" aria-hidden="true">
						<path :d="badge.iconPad" fill="none" stroke="currentColor" stroke-width="2" />
					</svg>
				</span>
				<span class="badge-label">{{ badge.label }}</span>
			</div>
		</TransitionGroup>
		<div v-if="nameplate" class="bottom-block">
			<div class="header-row">
				<span class="nameplate-name">{{ nameplate.name }}</span>
				<PartyLogo v-if="nameplate.party" :party="nameplate.party" class="nameplate-logo" />
				<span v-if="nameplate.party" class="nameplate-party">{{ displayPartyName(nameplate.party) }}</span>
				<div class="clock-group">
					<span v-if="timeRangeText" class="clock-indicator">{{ timeRangeText }}</span>
					<button
						v-if="nextArgument?.start_seconds != null"
						type="button"
						class="clock-indicator is-clickable"
						:class="{ 'is-compact': !!timeRangeText }"
						:aria-label="`Volgend argument om ${formatClock(nextArgument.start_seconds)}`"
						:title="timeRangeText ? `Volgend argument om ${formatClock(nextArgument.start_seconds)}` : undefined"
						@click="emit('seek', nextArgument.start_seconds as number)"
					>
						<span v-if="timeRangeText" aria-hidden="true">→ {{ formatClock(nextArgument.start_seconds) }}</span>
						<span v-else>volgend argument om {{ formatClock(nextArgument.start_seconds) }}</span>
					</button>
					<span v-else-if="!timeRangeText" class="clock-indicator">geen gelabelde argumenten meer</span>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.video-overlay {
	position: absolute;
	inset: 0;
	pointer-events: none;
	display: flex;
	flex-direction: column;
	justify-content: flex-end;
	padding: var(--space-2);
	background: linear-gradient(to top, rgba(0, 0, 0, 0.55) 0%, rgba(0, 0, 0, 0) 30%);
}

.title-card {
	position: absolute;
	top: var(--space-3);
	left: 50%;
	transform: translateX(-50%);
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 0.2em;
	max-width: 80%;
	background: rgba(0, 0, 0, 0.55);
	color: #fff;
	padding: 0.5em 1em;
	border-radius: 4px;
	text-align: center;
}

.title-card-name {
	font-family: var(--font-heading);
	font-size: var(--step-1);
}

.title-card-date {
	font-family: var(--font-mono);
	font-size: var(--step--1);
	color: rgba(255, 255, 255, 0.7);
}

.intro-badge {
	align-self: flex-start;
	background: rgba(0, 0, 0, 0.5);
	color: rgba(255, 255, 255, 0.85);
	padding: 0.3em 0.7em;
	border-radius: 3px;
	font-family: var(--font-mono);
	font-size: var(--step--1);
	letter-spacing: 0.02em;
}

.header-row {
	display: flex;
	align-items: baseline;
	gap: 0.5em;
	color: #fff;
}

.nameplate-name {
	font-family: var(--font-heading);
	font-style: italic;
	font-size: var(--step-1);
}

/* Gedesatureerd: een vol partijlogo naast de warme videobeelden trekt te
   veel aandacht en oogt los van de rest van de overlay-typografie. */
/* Desaturatie zit nu in de globale .party-logo-regel (main.css), hier alleen
   nog de verticale uitlijning. */
.nameplate-logo {
	align-self: center;
}

.nameplate-party {
	font-family: var(--font-mono);
	font-size: var(--step--1);
	letter-spacing: 0.08em;
	color: rgba(255, 255, 255, 0.7);
	text-transform: uppercase;
}

.clock-group {
	margin-left: auto;
	display: flex;
	align-items: baseline;
	gap: 0.6em;
}

.clock-indicator {
	font-family: var(--font-mono);
	font-size: var(--step--1);
	color: rgba(255, 255, 255, 0.55);
	background: none;
	border: none;
	padding: 0;
}

.clock-indicator.is-clickable {
	pointer-events: auto;
	cursor: pointer;
	text-decoration: underline dotted rgba(255, 255, 255, 0.5);
	text-underline-offset: 3px;
}

.clock-indicator.is-clickable:hover {
	color: rgba(255, 255, 255, 0.85);
}

/* Compact: er staat al een tijdrange, dus alleen een pijl + tijdstip i.p.v.
   de volledige "volgend argument om ..."-tekst. */
.clock-indicator.is-compact {
	font-size: 1em;
}

/* Verticale rail tegen de rechterrand, los van het naamplaatje onderin --
   houdt het midden van het beeld vrij. Categorie/perspectief staan niet meer
   op de badge zelf (te veel tekst over het beeld) maar in de title-tooltip. */
.badges {
	position: absolute;
	top: var(--space-2);
	right: var(--space-2);
	display: flex;
	flex-direction: column;
	align-items: flex-end;
	gap: 0.4em;
	pointer-events: auto;
}

.badge {
	display: flex;
	align-items: center;
	gap: 0.5em;
	background: rgba(20, 18, 15, 0.65);
	border-left: 2px solid var(--badge-color);
	color: #fff;
	padding: 0.3em 0.6em;
	border-radius: 3px;
	cursor: default;
}

.badge-icon-circle {
	flex-shrink: 0;
	width: 1.4em;
	height: 1.4em;
	border-radius: 50%;
	background: var(--badge-color);
	display: flex;
	align-items: center;
	justify-content: center;
}

.badge-icon {
	width: 0.9em;
	height: 0.9em;
	color: #fff;
}

.badge-label {
	font-family: var(--font-heading);
	font-size: var(--step--1);
	white-space: nowrap;
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
