<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import ArgumentCard from "./ArgumentCard.vue";
import VideoOverlay from "./VideoOverlay.vue";
import VideoPlayer from "./VideoPlayer.vue";
import VideoTimeline from "./VideoTimeline.vue";
import { debateThumbnailUrl } from "../lib/debateThumbnail";
import { PERSPECTIEVEN } from "../lib/tagIcons.generated";
import { perspectiefWeergaveNaam } from "../lib/tagIcon";
import type { Argument } from "../lib/types";
import { activeArguments } from "../lib/videoLabels";
import { requestSeek, videoSeek } from "../lib/videoSeek";
import { notifyUserScroll, userScroll } from "../lib/userScroll";

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

// Still voor het <video>-element z'n `poster` (issue: zwart vlak vóórdat
// hls.js het manifest geladen heeft) -- eerste argument in dit debat met een
// gematchte videospanne, zelfde aanpak als de homepage-kaarten
// (frontend/src/pages/index.astro) en Python's _topic_image_url.
const posterUrl = computed(() => {
	for (const argument of props.arguments) {
		const url = debateThumbnailUrl(argument.document.video_url, argument.document.published_at, argument.start_seconds);
		if (url) return url;
	}
	return null;
});

// Inklapbare argumentenlijst: elders (bv. de homepage-teaser van het laatste
// debat) moet dezelfde view compact passen zonder de hele lijst permanent te
// tonen. `defaultExpanded` ontbreekt op /debat/[id]/, dus die pagina blijft op
// de `true`-default zitten -- maar op een klein scherm is een direct
// volledig uitgeklapte lijst onder de video niet fijn (veel scrollen voor je
// bij de bediening bent), dus dan begint 'ie toch ingeklapt. `&&` i.p.v. een
// aparte "was defaultExpanded expliciet gezet"-check: de homepage-teaser zet
// defaultExpanded altijd expliciet op false, dus `false && ...` blijft daar
// gewoon `false` ongeacht schermbreedte; alleen de `true`-default (dus
// /debatten/[id]/) is schermbreedte-gevoelig. Veilig om hier synchroon
// `window` te lezen: dit component rendert alleen via `client:only="vue"`,
// dus zonder SSR-hydratatie om mismatch mee te krijgen.
const expanded = ref(props.defaultExpanded && (typeof window === "undefined" || window.innerWidth > 900));

// De breedte-transitie (zie .is-animating hieronder) mag alleen lopen bij
// deze bewuste toggle, niet bij elke herberekening van de (procentuele)
// breedte -- anders krijgt ook het slepen aan de vensterrand een trage,
// inhalende animatie i.p.v. direct mee te schalen.
const animating = ref(false);
let animatingTimer: ReturnType<typeof setTimeout> | null = null;
function toggleExpanded() {
	expanded.value = !expanded.value;
	animating.value = true;
	if (animatingTimer) clearTimeout(animatingTimer);
	animatingTimer = setTimeout(() => {
		animating.value = false;
		animatingTimer = null;
	}, 320);
}

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
const activeArgumentsList = computed(() => activeArguments(props.arguments, currentTime.value));
const activeArgumentIds = computed(() => new Set(activeArgumentsList.value.map((a) => a.id)));

// Bij een lang debat (honderden argumenten) is de hele lijst in één keer
// renderen de grootste kostenpost op de pagina (gemeten: >34.000 DOM-nodes
// voor één debat), en dat maakt ook ongerelateerde layoutwijzigingen elders
// (bv. de video die van breedte verandert) traag. Zelfde infinite-scroll-
// patroon (PAGE_SIZE, IntersectionObserver+sentinel, "meer laden"-knop) als
// ArgumentColumn.vue op de topic-pagina, hier lokaal i.p.v. hergebruikt: die
// component is voor de naast-elkaar pro/contra-kolommen daar, deze lijst is
// één chronologische kolom. Extra t.o.v. dat patroon: altijd minstens tot het
// actieve argument, zodat de kaart bestaat om naartoe te scrollen (zie
// ArgumentCard.vue's scrollIntoView-op-playing), en de sentinel-observer
// wordt hier opnieuw gekoppeld telkens als de lijst in-/uitklapt (bij
// ArgumentColumn.vue bestaat de lijst altijd, hier niet: `expanded` toggelt 'm
// helemaal uit de DOM).
const PAGE_SIZE = 50;
const visibleArgumentCount = ref(Math.min(PAGE_SIZE, props.arguments.length));
// Watcht op een stabiele string-sleutel i.p.v. rechtstreeks op
// activeArgumentIds: dat Set-object wordt bij elke currentTime-tick (~4x/s)
// opnieuw aangemaakt, dus zonder dit vuurt de watcher ook wanneer de actieve
// argumenten niet echt gewijzigd zijn en doet dan alsnog een O(n) findIndex.
const activeArgumentKey = computed(() => activeArgumentsList.value.map((a) => a.id).join(","));
watch(activeArgumentKey, () => {
	const ids = activeArgumentIds.value;
	if (ids.size === 0) return;
	const activeIndex = props.arguments.findIndex((a) => ids.has(a.id));
	if (activeIndex >= 0 && activeIndex + 1 > visibleArgumentCount.value) {
		visibleArgumentCount.value = Math.min(activeIndex + 1 + PAGE_SIZE, props.arguments.length);
	}
});
const visibleArguments = computed(() => props.arguments.slice(0, visibleArgumentCount.value));
// Alleen relevant op de volle pagina (niet de compacte teaser, die heeft geen
// scrollende argumentenlijst) -- gaat naar VideoOverlay.vue zodat de "lijst
// volgt niet mee"-hint naast de vorig/volgend-knoppen verschijnt zolang
// userScroll.ts' cooldown actief is (issue #147-vervolg).
const followPaused = computed(() => !props.debateHref && userScroll.isScrolling);
const hasMoreArguments = computed(() => visibleArgumentCount.value < props.arguments.length);
function loadMoreArguments() {
	visibleArgumentCount.value = Math.min(visibleArgumentCount.value + PAGE_SIZE, props.arguments.length);
}

// IntersectionObserver i.p.v. een scroll-listener: observeert alleen de
// sentinel onderaan i.p.v. bij elke scroll-tick te rekenen. `rootMargin` laadt
// de volgende batch al ruim voordat de sentinel zelf in beeld komt, zodat het
// aanvullen niet als een merkbare hapering aanvoelt.
const sentinelEl = ref<HTMLElement | null>(null);
let sentinelObserver: IntersectionObserver | null = null;
watch(sentinelEl, (el) => {
	sentinelObserver?.disconnect();
	sentinelObserver = null;
	if (!el) return;
	sentinelObserver = new IntersectionObserver(
		(entries) => {
			if (entries[0]?.isIntersecting && hasMoreArguments.value) loadMoreArguments();
		},
		{ rootMargin: "600px 0px" },
	);
	sentinelObserver.observe(el);
});

// Op de compacte teaser (debateHref gezet, bv. de homepage) is er geen ruimte
// voor de volledige argumentenlijst -- maar wel voor één compacte kaart van
// het argument dat nu speelt (issue #135), met linkjes naar persoon/partij/
// tag zodat die vanaf de homepage al bereikbaar zijn zonder eerst naar de
// volledige debatpagina te hoeven.
const nowPlaying = computed(() => activeArguments(props.arguments, currentTime.value)[0] ?? null);

// Onderdrukt de auto-volg-scroll in ArgumentCard.vue zolang de gebruiker zelf
// aan het scrollen is (zie lib/userScroll.ts) -- window-niveau, want player-
// en argumentenkolom delen dezelfde paginascroll. Het generieke "scroll"-
// event i.p.v. losse wheel-/touchmove-listeners: die missen toetsenbord-
// scrollen (Page Down/spatie/pijltjes) en het slepen aan de scrollbar-
// duimschijf, waarbij geen van beide events afgaat.
onMounted(() => {
	window.addEventListener("scroll", notifyUserScroll, { passive: true });

	// Vervolg op VideoPlayer.vue's debateHrefWithTime: de "volledige
	// debatpagina"-link vanaf een teaser (bv. de homepage) neemt de
	// afspeelpositie mee als ?t=<seconden>, zodat je hier niet weer bij 0:00
	// begint. Alleen op de eigen /debatten/[id]/-pagina zinvol (!debateHref) --
	// een teaser heeft zelf geen ?t= in zijn URL.
	if (!props.debateHref) {
		const seconds = Number(new URLSearchParams(window.location.search).get("t"));
		if (Number.isFinite(seconds) && seconds > 0) requestSeek(seconds);
	}
});
onUnmounted(() => {
	window.removeEventListener("scroll", notifyUserScroll);
	sentinelObserver?.disconnect();
	if (animatingTimer) clearTimeout(animatingTimer);
	floatObserver?.disconnect();
});

// Mini-player (YouTube/nieuwssites): overal waar sticky niet al voor "video
// blijft in beeld" zorgt -- de compacte teaser (debateHref gezet, geen
// argumentenkolom ernaast) én de gestapelde mobiele /debatten/[id]/-layout
// (≤900px, of handmatig ingeklapt via de argumentenlijst-toggle, zie de
// :not(.is-compact)/min-width:901px-voorwaarden bij de sticky-regel
// hierboven) -- blijft de video zichtbaar in een klein blokje rechtsonder
// zodra je 'm voorbij scrolt, i.p.v. gewoon te verdwijnen. Geen
// position:sticky op .player-column zelf voor dit geval: dat legde 'm eerder
// op volle breedte over .now-playing/de rest van de pagina heen (zie
// #143-vervolg).
const playerColumnEl = ref<HTMLElement | null>(null);
// Los "ankerpunt" vóór .player-column i.p.v. .player-column zelf observeren:
// zodra isFloating aanstaat wordt .player-column position:fixed (dus altijd
// "in beeld", ongeacht scrollpositie) -- observeer je .player-column zelf,
// dan meldt de observer meteen weer isIntersecting:true zodra 'm float, wat
// isFloating direct weer uitzet en oneindig oscilleert. Dit ankerpunt blijft
// altijd op zijn oorspronkelijke plek in de document-flow staan.
const floatAnchorEl = ref<HTMLElement | null>(null);
const isFloating = ref(false);
const floatingDismissed = ref(false);
const floatingPlaceholderHeight = ref(0);
let floatObserver: IntersectionObserver | null = null;

// Zelfde voorwaarde als de sticky-CSS hieronder, maar omgekeerd: sticky is
// alleen actief bij :not(.is-compact) op min-width:901px, dus mini-player
// juist overal daarbuiten.
function stickyHandlesVisibility(): boolean {
	return expanded.value && window.innerWidth > 900;
}

watch(floatAnchorEl, (el) => {
	floatObserver?.disconnect();
	floatObserver = null;
	if (!el) return;
	floatObserver = new IntersectionObserver(
		([entry]) => {
			// boundingClientRect.top < 0 onderscheidt "voorbij de bovenkant
			// gescrolld" van "nog niet in beeld gekomen" (bv. bij het eerste
			// meten) -- beide geven isIntersecting: false.
			if (!entry.isIntersecting && entry.boundingClientRect.top < 0 && !stickyHandlesVisibility()) {
				if (floatingDismissed.value) return;
				if (playerColumnEl.value) floatingPlaceholderHeight.value = playerColumnEl.value.getBoundingClientRect().height;
				isFloating.value = true;
			} else {
				isFloating.value = false;
				floatingDismissed.value = false;
			}
		},
		{ threshold: 0 },
	);
	floatObserver.observe(el);
});

function dismissFloating() {
	isFloating.value = false;
	floatingDismissed.value = true;
}
</script>

<template>
	<div class="debate-video-view" :class="{ 'is-compact': !expanded, 'is-animating': animating, 'is-floating': isFloating }">
		<div ref="floatAnchorEl" class="float-anchor" aria-hidden="true"></div>
		<div ref="playerColumnEl" class="player-column">
			<button
				v-if="isFloating"
				type="button"
				class="floating-close"
				aria-label="Zwevende video sluiten"
				title="Zwevende video sluiten"
				@click="dismissFloating"
			>
				×
			</button>
			<div v-if="rawVideoUrl" class="player-stage">
				<VideoPlayer
					:src="rawVideoUrl"
					:poster="posterUrl"
					:seek-to="videoSeek.seconds"
					:seek-token="videoSeek.token"
					:initial-muted="props.initialMuted"
					:debate-href="props.debateHref"
					@timeupdate="(t) => (currentTime = t)"
					@loadedmetadata="(d) => (duration = d)"
					@seek="requestSeek"
				>
					<VideoOverlay :arguments="props.arguments" :current-time="currentTime" :off="off" :follow-paused="followPaused" @seek="requestSeek" />
					<!-- Altijd dezelfde plek (dezelfde rij als play/pause, vergelijk
					     YouTube's chat-knop) i.p.v. mee te verhuizen tussen boven de
					     lijst en onder de video -- dat verspringen maakte de knop
					     moeilijker terug te vinden. -->
					<template v-if="!props.debateHref" #controls-extra>
						<button
							type="button"
							class="control-button argument-toggle-inline"
							:aria-pressed="expanded"
							:aria-label="expanded ? 'Argumenten verbergen' : 'Argumenten tonen'"
							:title="expanded ? 'Argumenten verbergen' : 'Argumenten tonen'"
							@click="toggleExpanded"
						>
							<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
								<path
									d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"
								/>
							</svg>
						</button>
					</template>
				</VideoPlayer>
			</div>
			<p v-else class="no-video">Voor dit debat is geen video beschikbaar.</p>
			<VideoTimeline
				v-if="rawVideoUrl && !isFloating"
				:arguments="props.arguments"
				:current-time="currentTime"
				:duration="duration"
				:off="off"
			/>
			<div v-if="!isFloating" class="perspective-filters" title="Verbergt of toont dit perspectief in de tag-badges op de video en in de tijdlijn hieronder">
				<span class="perspective-filters-label">Filter op perspectief</span>
				<button
					v-for="p in PERSPECTIEVEN"
					:key="p.naam"
					type="button"
					class="perspective-toggle"
					:class="{ 'is-off': off[p.naam] }"
					:style="{ '--perspective-color': p.kleur }"
					:aria-pressed="!off[p.naam]"
					:title="off[p.naam] ? `${perspectiefWeergaveNaam(p.naam)} weer tonen in badges en tijdlijn` : `${perspectiefWeergaveNaam(p.naam)} verbergen uit badges en tijdlijn`"
					@click="togglePerspective(p.naam)"
				>
					<span class="perspective-dot"></span>{{ perspectiefWeergaveNaam(p.naam) }}
				</button>
			</div>
		</div>
		<!-- Neemt de rij in die .player-column normaal vult zolang die zweeft
		     (position: fixed, dus buiten de flow) -- anders springt .now-playing
		     omhoog naar waar de video ooit stond. -->
		<div v-if="isFloating" class="player-column-spacer" :style="{ height: `${floatingPlaceholderHeight}px` }" aria-hidden="true"></div>
		<div v-if="!props.debateHref" class="argument-column">
			<ol v-if="expanded" class="argument-list">
				<li v-for="argument in visibleArguments" :key="argument.id">
					<ArgumentCard
						:argument="argument"
						:topic-slug="props.topicSlug"
						video-context
						:playing="activeArgumentIds.has(argument.id)"
						@seek="requestSeek"
					/>
				</li>
				<li v-if="hasMoreArguments" ref="sentinelEl" class="column-load-more">
					<button type="button" @click="loadMoreArguments">
						meer laden ({{ props.arguments.length - visibleArgumentCount }} resterend)
					</button>
				</li>
			</ol>
		</div>
		<!-- Compacte plek (debateHref gezet, bv. de homepage-teaser): geen ruimte
		     voor de volledige lijst, wel voor één compacte "nu in beeld"-kaart
		     (issue #135). -->
		<div v-else-if="nowPlaying" class="now-playing">
			<ArgumentCard
				:argument="nowPlaying"
				:topic-slug="props.topicSlug"
				compact
				video-context
				:playing="true"
				:arguments-in-debate="props.arguments"
				:off="off"
				@seek="requestSeek"
			/>
		</div>
	</div>
</template>

<style scoped>
/* Flex i.p.v. grid, met expliciete breedte-percentages: grid-template-columns
   is met een wisselend aantal tracks (2 uitgeklapt, 1 ingeklapt) niet
   animeerbaar, dus sprong de video-breedte (en daarmee -- 16:9 -- de hoogte)
   bij het in-/uitklappen van de argumentenlijst instant naar een heel andere
   grootte. `width` in procenten is wel een animeerbare eigenschap. */
.debate-video-view {
	position: relative;
	display: flex;
	flex-wrap: wrap;
	gap: var(--space-4);
	align-items: start;
}

.player-column {
	width: 60%;
	/* Flex-items krijgen standaard min-width: auto (= min-content van hun
	   inhoud) -- zonder dit duwt een niet-wrappende rij knoppen
	   (.controls-row in VideoPlayer.vue) deze kolom, en daarmee de hele
	   pagina, breder dan de viewport (zichtbaar als een ontbrekende
	   rechtermarge op mobiel). */
	min-width: 0;
}

.argument-column {
	width: calc(40% - var(--space-4));
	overflow: hidden;
}

@media (max-width: 900px) {
	.player-column,
	.argument-column {
		width: 100%;
	}
}

/* Alleen tijdens de bewuste toggle (zie toggleExpanded() in de script-sectie)
   animeert de breedte -- deze transitie permanent op .player-column/
   .argument-column zetten liet ook doodgewone vensterresizes trage,
   inhalende breedteveranderingen geven, want elke herberekening van de
   procentuele breedte (dus ook slepen aan de vensterrand) triggert een CSS-
   transition net zo goed als een class-toggle. */
.debate-video-view.is-animating .player-column,
.debate-video-view.is-animating .argument-column {
	transition: width 0.3s ease, opacity 0.2s ease;
}

/* Ingeklapte argumentenlijst: de player-kolom mag de volle breedte
   innemen i.p.v. naast een lege rechterkolom te blijven staan. */
.debate-video-view.is-compact .player-column {
	width: 100%;
}

.debate-video-view.is-compact .argument-column {
	width: 0%;
	opacity: 0;
}

/* Compacte teaser (debateHref gezet): geen argument-column-buur om ruimte
   mee te delen, dus altijd de volle breedte. */
.now-playing {
	width: 100%;
}

/* Perspectief-filters zijn een volledige-pagina-feature (filteren wat de
   tijdlijn/overlay tonen) -- op een compacte teaser kost die rij(en) knoppen
   meer ruimte dan ze daar opleveren. */
.debate-video-view.is-compact .perspective-filters {
	display: none;
}

/* Sticky is alleen zinvol naast een langere, gelijktijdig zichtbare
   argumentenkolom (desktop, 2 kolommen): dan blijft de video in beeld terwijl
   je door de langere lijst ernaast scrolt. Op een gestapelde mobiele layout
   (≤900px, zie hierboven) staat de argumentenlijst ONDER de video in
   dezelfde kolom -- sticky zou de video dan over die lijst heen laten
   plakken terwijl je erdoorheen scrolt. Dezelfde stapeling geldt op een brede
   viewport voor de compacte teaser (.is-compact, bv. de homepage): daar staat
   geen argumentenkolom náást de video maar hooguit .now-playing eronder, dus
   :not(.is-compact) hier -- zonder die uitsluiting bleef de video ook daar
   aan de bovenkant plakken terwijl de rest van de pagina eronderdoor
   scrolde. */
@media (min-width: 901px) {
	.debate-video-view:not(.is-compact) .player-column {
		position: sticky;
		top: var(--space-2);
	}
}

/* Mini-player (YouTube/nieuwssites): zodra je de teaser voorbij scrolt,
   blijft de video zichtbaar in een klein blokje rechtsonder i.p.v. gewoon te
   verdwijnen. position: fixed i.p.v. sticky (zie hierboven): fixed haalt
   .player-column volledig uit de flow en legt 'm nooit over volgende inhoud
   heen op volle breedte, wat sticky hier eerder wel deed. */
.debate-video-view.is-floating .player-column {
	position: fixed;
	bottom: var(--space-3);
	right: var(--space-3);
	width: min(320px, calc(100vw - 2 * var(--space-3)));
	z-index: 40;
	background: var(--color-bg);
	border: 1px solid var(--color-border);
	border-radius: 6px;
	box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
	overflow: hidden;
}

.player-column-spacer {
	width: 100%;
}

/* position: absolute i.p.v. gewoon flex-item: als (0x0-)flex-item telde dit
   toch nog mee voor de gap tussen flex-items (zie .debate-video-view), en op
   de volle /debatten/[id]/-pagina is de 60/40-verdeling al exact sluitend
   (.argument-column trekt de gap er al vanaf) -- die extra gap-breedte was
   precies genoeg om de argumentenkolom naar een nieuwe rij te laten
   wrappen, met de sticky video er nog steeds overheen (issue: video-column
   bleef zichtbaar, argumentenlijst scrolde eronderdoor). Absoluut
   gepositioneerd t.o.v. .debate-video-view (position: relative, zie
   hierboven) blijft dit ankerpunt op dezelfde documentplek -- vlak boven
   waar .player-column staat -- zonder in de flex-berekening mee te tellen. */
.float-anchor {
	position: absolute;
	top: 0;
	left: 0;
	width: 0;
	height: 0;
}

.floating-close {
	position: absolute;
	top: 6px;
	right: 6px;
	z-index: 2;
	width: 26px;
	height: 26px;
	display: flex;
	align-items: center;
	justify-content: center;
	border: none;
	border-radius: 50%;
	background: rgba(0, 0, 0, 0.55);
	color: #fff;
	font-size: 1rem;
	line-height: 1;
	cursor: pointer;
}

.floating-close:hover {
	background: rgba(0, 0, 0, 0.75);
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

/* Zit in VideoPlayer's controls-row (via de controls-extra-slot), dus in
   DebateVideoView's eigen scoped stylesheet -- VideoPlayer's `.control-button`
   -regel (andere scope-attribute) bereikt deze knop niet, vandaar hier
   dezelfde vormgeving herhaald. Icoon-only zoals de andere controlsrij-
   knoppen (play/pauze/mute): geen tekstlabel meer, dat maakte "vorig/volgend
   argument" ernaast al krap; aria-label/title dragen de betekenis. */
.argument-toggle-inline {
	width: 40px;
	height: 40px;
	min-width: 40px;
	min-height: 40px;
	display: flex;
	align-items: center;
	justify-content: center;
	background: transparent;
	border: 1px solid var(--color-border);
	border-radius: 4px;
	color: var(--color-text);
	cursor: pointer;
	padding: 0;
	margin-left: auto;
}

.argument-toggle-inline:hover {
	background: color-mix(in srgb, var(--color-text) 7%, transparent);
}

.argument-toggle-inline[aria-pressed="true"] {
	color: var(--color-accent);
	border-color: var(--color-accent);
}

.argument-list {
	list-style: none;
	margin: 0;
	padding: 0;
	display: flex;
	flex-direction: column;
	gap: var(--space-2);
}

/* Bij een lang debat (honderden argumenten) draagt deze lijst het gros van
   de paginagrootte -- gemeten op één debat: >34.000 DOM-nodes, bijna alle
   nodes op de hele pagina. Zonder dit moet de browser bij ELKE
   layoutverandering elders op de pagina (bv. de video die van breedte
   verandert tijdens het slepen aan de vensterrand) ook deze hele lijst
   herberekenen, wat het slepen zichtbaar traag maakt. `content-visibility`
   laat de browser layout/paint overslaan voor kaarten buiten beeld;
   `contain-intrinsic-size` is een plaatshouder-hoogte zodat de scrollbar
   niet springt zolang een kaart nog niet gemeten is. */
.argument-list li {
	content-visibility: auto;
	contain-intrinsic-size: 0 220px;
}
</style>
