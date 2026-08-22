<script setup lang="ts">
import { computed } from "vue";
import { debateName } from "../lib/debateName";
import { formatDate } from "../lib/formatDate";
import { perspectiefWeergaveNaam, tagIconPath } from "../lib/tagIcon";
import { PERSPECTIEVEN } from "../lib/tagIcons.generated";
import { stanceLabel, typologyLabel, type Argument } from "../lib/types";
import { activeArguments, nextArgumentAfter, prevArgumentBefore, selectBadgeTags } from "../lib/videoLabels";
import { formatClock } from "../lib/videoTime";
import { displayPartyName } from "../lib/parties";
import PartyLogo from "./PartyLogo.vue";

// Overlay over de <video> heen: lower-third naamplaatje + tot 3 tag-badges
// per actief argument. Zie docs/design/videoplayer/README.md "Overgangen" en
// "Toegankelijkheid" -- icoon+tekst altijd samen, nooit kleur alleen, nooit
// tekst direct op beeld (vandaar de achtergrond per badge hieronder).

// followPaused: DebateVideoView.vue geeft dit door zolang userScroll.ts'
// cooldown actief is (de gebruiker heeft net zelf gescrolld) -- dan slaat
// ArgumentCard.vue's auto-scroll-naar-actief-argument (issue #147) even over.
// Zonder duidelijk signaal hier oogt dat als een bug ("waarom scrollt de
// lijst nu niet mee, en waarom een paar seconden later opeens wel"): dit
// badge maakt de (bestaande, tijdelijke) onderdrukking zichtbaar op de plek
// waar je 'm merkt -- naast de vorig/volgend-knoppen.
// minimal: zwevende mini-player (DebateVideoView.vue's isFloating, issue
// #173-vervolg). De vorig/volgend-argumentknoppen blijven bruikbaar (het
// seek-event werkt ongeacht of de speler zweeft), maar op de smalle 320px-
// breedte past niet de volle pijl+tijdstempel-vorm -- alleen de kale
// pijlknoppen, zonder tijdstempel/tussentekst.
const props = defineProps<{
	arguments: Argument[];
	currentTime: number;
	off: Record<string, boolean>;
	followPaused?: boolean;
	minimal?: boolean;
}>();
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
const nextArgument = computed(() => nextArgumentAfter(props.arguments, props.currentTime));

// Symmetrisch aan nextArgument, maar t.o.v. het huidige/eerstvolgende
// argument i.p.v. currentTime: anders is "vorig argument" tijdens het actieve
// argument zelf (start_seconds <= currentTime) hetzelfde argument als "nu".
const prevArgument = computed(() => prevArgumentBefore(props.arguments, active.value[0]?.start_seconds ?? props.currentTime));

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
//
// sleutel is opgebouwd als "Categorie-Subtype" (bv. "Drogreden-Ad-Hominem");
// op mobiel is er geen ruimte voor het volledige label, dus valt de
// categorie daar weg ("Ad Hominem") -- de volledige tekst blijft wel in de
// title-tooltip en op desktop (zie de mobiele media query hieronder).
function shortTagLabel(sleutel: string): string {
	const parts = sleutel.split("-");
	return parts.length > 1 ? parts.slice(1).join(" ") : sleutel;
}

const badges = computed(() =>
	active.value.flatMap((argument) =>
		selectBadgeTags(argument, props.arguments, isVisible).map((tag) => ({
			key: `${argument.id}-${tag.sleutel}`,
			label: tag.sleutel,
			shortLabel: shortTagLabel(tag.sleutel),
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
				<span class="badge-label">
					<span class="badge-label-full">{{ badge.label }}</span>
					<span class="badge-label-short">{{ badge.shortLabel }}</span>
				</span>
			</div>
		</TransitionGroup>
		<div v-if="nameplate" class="bottom-block">
			<div class="header-row">
				<span class="nameplate-name">{{ nameplate.name }}</span>
				<PartyLogo v-if="nameplate.party" :party="nameplate.party" class="nameplate-logo" />
				<span v-if="nameplate.party" class="nameplate-party">{{ displayPartyName(nameplate.party) }}</span>
				<!-- Bewindspersonen (bv. een staatssecretaris) spreken op dat moment
				     niet namens een fractie, dus actors.party is voor hen vaak NULL
				     totdat scripts/backfill_minister_info.py 'm (waar traceerbaar via
				     de TK Persoon-API/rijksoverheid.nl/Wikidata) alsnog vult -- zie
				     pipeline/db/schema.sql (speaker_role_title). Zolang dat nog niet
				     gebeurd is voor deze spreker, role_title als vangnet i.p.v. een
				     kaal naamplaatje -- zelfde patroon als ArgumentCard.vue al doet
				     ("Volgens X, staatssecretaris van ..."). -->
				<span v-else-if="nameplate.role_title" class="nameplate-party">{{ nameplate.role_title }}</span>
				<div class="clock-group" :class="{ 'is-minimal': minimal }">
					<!-- Altijd zichtbaar, disabled i.p.v. verborgen bij het eerste/
					     laatste argument (issue #134): een verdwijnende knop springt de
					     layout en de disabled-state is dan niet te onderscheiden van
					     "bestaat niet". Altijd het compacte pijl+tijd-formaat, ook
					     zonder timeRangeText (in een gat tussen twee argumenten): de
					     volledige zin ("vorig/volgend argument om ...") paste daar niet
					     meer op één regel zodra prev/next tegelijk zichtbaar zijn -- die
					     staat nog wel in aria-label/title. In de mini-player (minimal)
					     blijven de knoppen zelf staan -- ze werken daar (seeken doet de
					     video gewoon door) -- maar zonder de tijdstempel/tussentekst,
					     die past niet meer op de smalle 320px-breedte. -->
					<button
						type="button"
						class="clock-indicator is-clickable"
						:disabled="!prevArgument"
						:aria-label="prevArgument ? `Vorig argument om ${formatClock(prevArgument.start_seconds as number)}` : 'Geen vorig argument'"
						:title="prevArgument ? `Vorig argument om ${formatClock(prevArgument.start_seconds as number)}` : 'Geen vorig argument'"
						@click="prevArgument && emit('seek', prevArgument.start_seconds as number)"
					>
						← <span v-if="prevArgument && !minimal">{{ formatClock(prevArgument.start_seconds as number) }}</span>
					</button>
					<span v-if="timeRangeText && !minimal" class="clock-indicator">{{ timeRangeText }}</span>
					<button
						type="button"
						class="clock-indicator is-clickable"
						:disabled="!nextArgument"
						:aria-label="nextArgument ? `Volgend argument om ${formatClock(nextArgument.start_seconds as number)}` : 'Geen volgend argument'"
						:title="nextArgument ? `Volgend argument om ${formatClock(nextArgument.start_seconds as number)}` : 'Geen volgend argument'"
						@click="nextArgument && emit('seek', nextArgument.start_seconds as number)"
					>
						→ <span v-if="nextArgument && !minimal">{{ formatClock(nextArgument.start_seconds as number) }}</span>
					</button>
				</div>
			</div>
			<!-- Eigen regel onder de klok-knoppenrij i.p.v. ernaast in .clock-group:
			     dat liet de knoppen (margin-left: auto, dus rechts uitgelijnd binnen
			     .header-row) bij elke verschijning/verdwijning van breedte
			     veranderen, waardoor ze zichtbaar heen en weer sprongen. Altijd
			     gerenderd (geen v-if) en alleen opacity togglend i.p.v. verwijderd
			     uit de DOM: anders reserveert deze regel geen ruimte zolang 'm
			     onzichtbaar is, en schuift .bottom-block (flex-end in
			     .video-overlay) bij elke verschijning/verdwijning alsnog verticaal
			     op/neer. -->
			<p
				class="follow-paused-hint"
				:class="{ 'is-visible': followPaused }"
				:title="followPaused ? 'Je scrollt zelf in de argumentenlijst -- die volgt de video hierdoor even niet automatisch mee' : undefined"
				aria-hidden="true"
			>
				lijst volgt niet mee
			</p>
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
	max-width: min(80%, 28rem);
	background: rgba(0, 0, 0, 0.55);
	color: #fff;
	padding: 0.5em 1em;
	border-radius: 4px;
	text-align: center;
}

/* clamp() i.p.v. de vaste --step-*-tokens: schaalt continu, zodat een lange
   debattitel niet buiten de kaart uitsteekt (voorheen: één vaste stap bij
   900px, die op bv. 360px-schermen alsnog kon overlopen). cqw (containerbreedte
   van .video-stage in VideoPlayer.vue) i.p.v. vw: vw schaalt op de hele
   viewport, dus bleef in de zwevende mini-player (DebateVideoView.vue's
   isFloating, vast op min(320px, 100vw-...)) even groot als op een brede
   desktop-viewport en liep daar ver over -- cqw volgt de werkelijke breedte
   van het videovak zelf, ongeacht of dat de volle speler of de mini-player is. */
.title-card-name {
	font-family: var(--font-heading);
	font-size: clamp(0.6rem, 3.2cqw, var(--step-1));
	overflow-wrap: break-word;
	/* Harde ondergrens naast het schalende lettertype: een lange
	   Kamerstuktitel (bv. "Initiatiefnota van het lid ... voor Iedereen") kan
	   ook op het kleinste lettertype nog te veel regels vullen in de smalle
	   mini-player en zo over het naamplaatje onderin heen groeien -- knip 'm
	   daarom hard af na 3 regels i.p.v. de kaart open te laten groeien. */
	display: -webkit-box;
	-webkit-box-orient: vertical;
	-webkit-line-clamp: 3;
	overflow: hidden;
}

.title-card-date {
	font-family: var(--font-mono);
	font-size: clamp(0.6rem, 3cqw, var(--step--1));
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

/* Zelfde cqw-redenering als .title-card-name hierboven: schaalt op de
   werkelijke breedte van het videovak, dus ook correct in de zwevende
   mini-player (vast 320px) op een brede desktop-viewport, waar dit voorheen
   (vaste --step-1) net zo groot bleef als op de volle speler en over de
   rand van de kaart heen liep. */
.nameplate-name {
	font-family: var(--font-heading);
	font-style: italic;
	font-size: clamp(0.65rem, 4.5cqw, var(--step-1));
}

/* Gedesatureerd: een vol partijlogo naast de warme videobeelden trekt te
   veel aandacht en oogt los van de rest van de overlay-typografie. */
/* Desaturatie zit nu in de globale .party-logo-regel (main.css); breedte/
   hoogte hier overschreven (i.p.v. de vaste 18px uit .party-logo) zodat het
   logo meeschaalt met de rest van de naamplaat i.p.v. verhoudingsgewijs
   groot te blijven in de mini-player. */
.nameplate-logo {
	align-self: center;
	width: clamp(12px, 4cqw, 18px);
	height: clamp(12px, 4cqw, 18px);
}

.nameplate-party {
	font-family: var(--font-mono);
	font-size: clamp(0.55rem, 2.8cqw, var(--step--1));
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

/* Mini-player (issue #173-vervolg): alleen de kale pijlen, geen tijdstempel
   ernaast -- krapper gaatje ertussen past bij die kortere knopinhoud. */
.clock-group.is-minimal {
	gap: 0.4em;
}

.clock-indicator {
	font-family: var(--font-mono);
	font-size: clamp(0.55rem, 2.8cqw, var(--step--1));
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

/* Subtiel bedoeld: geen achtergrond/kader, gewoon een kleine, gedempte regel
   onder de klok-knoppen -- opvallen is niet het doel, alleen even duidelijk
   maken waarom de argumentenlijst nu niet meebeweegt. Rechts uitgelijnd,
   onder .clock-group (die zelf ook rechts uitgelijnd staat via
   margin-left: auto). Altijd gerenderd (zie template) en hier alleen via
   opacity in-/uitgeschakeld -- nooit `display: none`, anders reserveert deze
   regel geen hoogte terwijl 'm uit staat en schuift .bottom-block (flex-end
   in .video-overlay) bij elke toggle een regel op/neer. */
.follow-paused-hint {
	margin: 0.2em 0 0;
	font-family: var(--font-mono);
	font-size: 0.65rem;
	color: rgba(255, 255, 255, 0.4);
	text-align: right;
	opacity: 0;
	transition: opacity 0.4s ease;
}

.follow-paused-hint.is-visible {
	opacity: 1;
}

/* Eerste/laatste argument: knop blijft staan (geen layout-sprong) maar is
   disabled i.p.v. verborgen, zie issue #134. */
.clock-indicator.is-clickable:disabled {
	pointer-events: none;
	cursor: default;
	opacity: 0.35;
	text-decoration: none;
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

/* font-size hier (i.p.v. alleen op .badge-label) zodat het icoon en de
   padding -- allebei in em, dus relatief aan dit lettertype -- in dezelfde
   verhouding meeschalen als de tekst i.p.v. los van elkaar te bewegen. */
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
	font-size: clamp(0.55rem, 2.8cqw, var(--step--1));
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
	white-space: nowrap;
}

.badge-label-short {
	display: none;
}

.badge-enter-active {
	transition: opacity 0.2s;
}

/* Kort en uit de flex-flow (position:absolute): zonder dit bleef een
   vertrekkende badge tijdens de fade-out nog meetellen in de
   kolomstapeling, waardoor een binnenkomende badge tijdelijk lager
   (halverwege het beeld) verscheen en pas na het verdwijnen van de oude naar
   boven sprong. */
.badge-leave-active {
	transition: opacity 0.06s;
	position: absolute;
}

.badge-enter-from,
.badge-leave-to {
	opacity: 0;
}

/* @container i.p.v. @media (issue #173-vervolg): de tekst zelf schaalt al
   continu mee via cqw/clamp() hierboven, dus dat hoeft hier niet meer
   herhaald. Wat overblijft is een knik in de vormgeving (kortere labels,
   krappere padding) die moet reageren op de werkelijke breedte van het
   videovak -- ook de zwevende mini-player (DebateVideoView.vue's
   isFloating, vast op min(320px, 100vw-...)) op een brede desktop-viewport,
   waar een @media-breakpoint op viewportbreedte nooit zou triggeren. */
@container (max-width: 900px) {
	.badge,
	.intro-badge {
		padding: 0.2em 0.45em;
	}

	.badge-icon-circle {
		width: 1.1em;
		height: 1.1em;
	}

	/* Geen ruimte voor "Drogreden Ad Hominem" -- toon alleen "Ad Hominem"
	   (de volledige tekst blijft beschikbaar via de title-tooltip en op
	   desktop, en staat er sowieso bij in de "nu in beeld"-kaart onder de
	   video, zie ArgumentCard.vue). */
	.badge-label-full {
		display: none;
	}

	.badge-label-short {
		display: inline;
	}

	.badges {
		gap: 0.3em;
	}
}
</style>
