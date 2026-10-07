<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import ArgumentCard from "./ArgumentCard.vue";
import ShareMenuButton from "./ShareMenuButton.vue";
import VideoOverlay from "./VideoOverlay.vue";
import VideoPlayer from "./VideoPlayer.vue";
import VideoTimeline from "./VideoTimeline.vue";
import { useDebateArguments } from "../lib/debateArguments";
import { PERSPECTIEVEN } from "../lib/tagIcons.generated";
import { perspectiefKleurVar, perspectiefWeergaveNaam } from "../lib/tagIcon";
import { activeArguments } from "../lib/videoLabels";
import { requestSeek, videoSeek } from "../lib/videoSeek";
import { notifyUserScroll, userScroll } from "../lib/userScroll";
import { downloadClip, recordClip } from "../lib/clipExport";

const props = withDefaults(
	defineProps<{
		debateId: string;
		topicSlug: string;
		dataBaseUrl: string;
		// Direct meegegeven i.p.v. afgeleid uit de gefetchte argumentenlijst
		// (zie `entry`/`arguments` hieronder): de video moet meteen kunnen
		// laden, zonder te wachten op de onderwerp-JSON (issue #119).
		rawVideoUrl: string | null;
		posterUrl: string | null;
		defaultExpanded?: boolean;
		initialMuted?: boolean;
		// Link naar de volledige /debat/[id]/-pagina; alleen zinvol op plekken
		// die zelf niet al die pagina zijn (bv. de homepage-teaser).
		debateHref?: string | null;
		// URL van de /embed/debatten/[id]/-tegenhanger (issue #244). Alleen
		// meegegeven vanaf /debatten/[id]/ zelf -- niet vanaf de
		// homepage-teaser (debateHref is daar al gezet) en niet vanaf de
		// embed-pagina zelf (een insluitknop ín de embed zou rechtstreeks naar
		// zichzelf verwijzen).
		embedUrl?: string | null;
	}>(),
	// Expliciet via withDefaults, niet `props.defaultExpanded ?? true`: Vue
	// cast een afwezige Boolean-prop zelf al naar `false` (vóórdat `??` iets
	// ziet), dus `false ?? true` zou nog steeds `false` opleveren.
	{ defaultExpanded: true, initialMuted: false },
);

// Gedeelde store (issue #119): meerdere islands op dezelfde pagina (deze
// component en ClaimsHighlights.vue op de homepage) delen dezelfde fetch van
// het per-debat gepubliceerde bestand i.p.v. elk apart de volledige lijst als
// Astro-prop te krijgen. `arguments` blijft leeg tot `entry.status ===
// "ready"`.
const entry = useDebateArguments(props.debateId, props.dataBaseUrl);
const argumentList = computed(() => entry.arguments);

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
// Lokale clip-export (issue #180): geen server, dus canvas.captureStream()
// van de echte VideoOverlay.vue-DOM op de videoframes (via <foreignObject>,
// zie clipExport.ts) -- geen aparte SVG-herbouw van de overlay, één
// implementatie voor live scherm én export. Op zowel de volledige
// debatpagina als de homepage-teaser (zelfde knop overal, issue over
// video-component-uniformiteit).
const videoPlayerRef = ref<InstanceType<typeof VideoPlayer> | null>(null);
const videoOverlayRef = ref<InstanceType<typeof VideoOverlay> | null>(null);
const exporting = ref(false);
const exportProgress = ref(0);
const exportError = ref<string | null>(null);

// Fallback-lengte als er geen actief argument is (bv. een gat in de
// tijdlijn) -- de meeste geldige argumentspannes vallen ruim onder de 60s,
// die bovengrens is puur om een uitschieter (foutief lange spanne) niet een
// enorme clip te laten opnemen.
const DEFAULT_CLIP_SECONDS = 10;
const MAX_CLIP_SECONDS = 60;

async function exportClip() {
	const video = videoPlayerRef.value?.videoEl;
	const overlayEl = videoOverlayRef.value?.rootEl;
	if (!video || !overlayEl || exporting.value) return;
	exporting.value = true;
	exportProgress.value = 0;
	exportError.value = null;
	try {
		// Standaard het hele huidige fragment (het actieve argument), niet een
		// vast aantal seconden vanaf waar de video toevallig staat -- dat is
		// wat "dit fragment downloaden" betekent voor de kijker. Vereist eerst
		// terugspoelen naar het begin van dat argument.
		const argument = nowPlaying.value;
		let clipSeconds = DEFAULT_CLIP_SECONDS;
		if (argument?.start_seconds != null && argument?.end_seconds != null) {
			clipSeconds = Math.min(MAX_CLIP_SECONDS, Math.max(1, argument.end_seconds - argument.start_seconds));
			video.currentTime = argument.start_seconds;
			await new Promise<void>((resolve) => {
				video.addEventListener("seeked", () => resolve(), { once: true });
			});
		}
		const result = await recordClip(video, overlayEl, clipSeconds, {
			onProgress: (fraction) => {
				exportProgress.value = fraction;
			},
			hls: videoPlayerRef.value?.getHlsInstance(),
		});
		downloadClip(result, `${props.debateId}-clip.webm`);
	} catch (e) {
		exportError.value = e instanceof Error ? e.message : "onbekende fout";
		console.error("clip-export mislukt:", e);
	} finally {
		exporting.value = false;
	}
}

// Welk argument(en) nu spelen, om de bijbehorende kaart in de lijst rechts
// te benadrukken (zelfde idee als de overlay-badges: currentTime is leidend).
const activeArgumentsList = computed(() => activeArguments(argumentList.value, currentTime.value));
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
const visibleArgumentCount = ref(Math.min(PAGE_SIZE, argumentList.value.length));
// De lijst is bij mount nog leeg (fetch loopt) -- zodra 'm gevuld raakt moet
// de eerste pagina alsnog ingesteld worden, anders blijft visibleArgumentCount
// op de 0 waarmee 'm hierboven initieel is berekend (issue #119: arguments
// komt nu async binnen i.p.v. synchroon als prop).
watch(
	() => argumentList.value.length,
	(length) => {
		if (visibleArgumentCount.value === 0 && length > 0) visibleArgumentCount.value = Math.min(PAGE_SIZE, length);
	},
);
// Watcht op een stabiele string-sleutel i.p.v. rechtstreeks op
// activeArgumentIds: dat Set-object wordt bij elke currentTime-tick (~4x/s)
// opnieuw aangemaakt, dus zonder dit vuurt de watcher ook wanneer de actieve
// argumenten niet echt gewijzigd zijn en doet dan alsnog een O(n) findIndex.
const activeArgumentKey = computed(() => activeArgumentsList.value.map((a) => a.id).join(","));
watch(activeArgumentKey, () => {
	const ids = activeArgumentIds.value;
	if (ids.size === 0) return;
	const activeIndex = argumentList.value.findIndex((a) => ids.has(a.id));
	if (activeIndex >= 0 && activeIndex + 1 > visibleArgumentCount.value) {
		visibleArgumentCount.value = Math.min(activeIndex + 1 + PAGE_SIZE, argumentList.value.length);
	}
});
const visibleArguments = computed(() => argumentList.value.slice(0, visibleArgumentCount.value));
// Alleen relevant op de volle pagina (niet de compacte teaser, die heeft geen
// scrollende argumentenlijst) -- gaat naar VideoOverlay.vue zodat de "lijst
// volgt niet mee"-hint naast de vorig/volgend-knoppen verschijnt zolang
// userScroll.ts' cooldown actief is (issue #147-vervolg).
const followPaused = computed(() => !props.debateHref && userScroll.isScrolling);
const hasMoreArguments = computed(() => visibleArgumentCount.value < argumentList.value.length);
function loadMoreArguments() {
	visibleArgumentCount.value = Math.min(visibleArgumentCount.value + PAGE_SIZE, argumentList.value.length);
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
const nowPlaying = computed(() => activeArguments(argumentList.value, currentTime.value)[0] ?? null);

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
	playerColumnResizeObserver?.disconnect();
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
// Ankerpunt krijgt de hoogte van .player-column zelf (i.p.v. 0px) zodat zijn
// ONDERrand overeenkomt met de onderkant van de video -- issue #188: met een
// 0px-ankerpunt trad de mini-player al aan zodra je een klein stukje voorbij
// de BOVENkant van de video scrolde, i.p.v. pas als de video daadwerkelijk
// volledig uit beeld is.
const playerColumnHeight = ref(0);
let playerColumnResizeObserver: ResizeObserver | null = null;
watch(playerColumnEl, (el) => {
	playerColumnResizeObserver?.disconnect();
	playerColumnResizeObserver = null;
	if (!el) return;
	playerColumnResizeObserver = new ResizeObserver(([entry]) => {
		playerColumnHeight.value = entry.contentRect.height;
	});
	playerColumnResizeObserver.observe(el);
});
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
			// boundingClientRect.bottom < 0 (i.p.v. top < 0): het ankerpunt heeft
			// nu dezelfde hoogte als .player-column (zie playerColumnHeight
			// hierboven), dus de ONDERrand van het ankerpunt valt samen met de
			// onderkant van de video. Pas als díe onderrand boven de viewport zit,
			// is de video daadwerkelijk volledig uit beeld -- top < 0 gaf al
			// isFloating zodra je een klein stukje voorbij de bovenkant scrolde
			// (issue #188).
			if (!entry.isIntersecting && entry.boundingClientRect.bottom < 0 && !stickyHandlesVisibility()) {
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
		<div ref="floatAnchorEl" class="float-anchor" :style="{ height: `${playerColumnHeight}px` }" aria-hidden="true"></div>
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
			<div v-if="props.rawVideoUrl" class="player-stage">
				<VideoPlayer
					ref="videoPlayerRef"
					:src="props.rawVideoUrl"
					:poster="props.posterUrl"
					:seek-to="videoSeek.seconds"
					:seek-token="videoSeek.token"
					:initial-muted="props.initialMuted"
					:debate-href="props.debateHref"
					:minimal="isFloating"
					@timeupdate="(t) => (currentTime = t)"
					@loadedmetadata="(d) => (duration = d)"
					@seek="requestSeek"
				>
					<VideoOverlay
						ref="videoOverlayRef"
						:arguments="argumentList"
						:current-time="currentTime"
						:off="off"
						:follow-paused="followPaused"
						:minimal="isFloating"
						@seek="requestSeek"
					/>
					<!-- Altijd dezelfde plek (dezelfde rij als play/pause, vergelijk
					     YouTube's chat-knop) i.p.v. mee te verhuizen tussen boven de
					     lijst en onder de video -- dat verspringen maakte de knop
					     moeilijker terug te vinden. Beide knoppen in één
					     .controls-extra-group i.p.v. allebei hun eigen
					     margin-left:auto: flexbox verdeelt de vrije ruimte dan over
					     élke auto-margin apart, wat de knoppen ver uit elkaar duwde
					     i.p.v. als groep rechts te houden. -->
					<template #controls-extra>
						<div class="controls-extra-group">
							<!-- Uniform op zowel de volledige debatpagina als de
							     homepage-teaser (geen v-if op debateHref hier). Links
							     van de argumenten-toggle: die laatste hoort qua
							     associatie bij het paneel rechts ernaast, dus moet
							     zelf uiterst rechts blijven staan. -->
							<button
								type="button"
								class="control-button argument-toggle-inline"
								:disabled="exporting"
								:aria-label="exporting ? `Fragment wordt gedownload... ${Math.round(exportProgress * 100)}%` : 'Huidige fragment downloaden (WebM)'"
								:title="exportError ? `Mislukt: ${exportError}` : exporting ? `Bezig met downloaden... ${Math.round(exportProgress * 100)}%` : 'Huidige fragment downloaden (WebM)'"
								@click="exportClip"
							>
								<svg v-if="!exporting" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
									<path d="M12 3v11" />
									<path d="M7 10l5 5 5-5" />
									<path d="M5 20h14" />
								</svg>
								<svg v-else viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
									<circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="2" opacity="0.25" />
									<circle
										cx="12"
										cy="12"
										r="9"
										fill="none"
										stroke="currentColor"
										stroke-width="2"
										stroke-linecap="round"
										:stroke-dasharray="2 * Math.PI * 9"
										:stroke-dashoffset="2 * Math.PI * 9 * (1 - exportProgress)"
										transform="rotate(-90 12 12)"
									/>
								</svg>
							</button>
							<ShareMenuButton v-if="!props.debateHref" :embed-url="props.embedUrl" />
							<button
								v-if="!props.debateHref"
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
						</div>
					</template>
				</VideoPlayer>
			</div>
			<p v-else class="no-video">Voor dit debat is geen video beschikbaar.</p>
			<Transition v-if="props.rawVideoUrl && !isFloating" name="fade" mode="out-in">
				<div v-if="entry.status === 'loading'" key="loading" class="timeline-skeleton" aria-hidden="true"></div>
				<p v-else-if="entry.status === 'error'" key="error" class="status-hint">Kon de argumentdata niet laden. Probeer de pagina te verversen.</p>
				<VideoTimeline v-else key="ready" :arguments="argumentList" :current-time="currentTime" :duration="duration" :off="off" />
			</Transition>
			<div v-if="!isFloating" class="perspective-filters" title="Verbergt of toont dit perspectief in de tag-badges op de video en in de tijdlijn hieronder">
				<span class="perspective-filters-label">Filter op perspectief</span>
				<button
					v-for="p in PERSPECTIEVEN"
					:key="p.naam"
					type="button"
					class="perspective-toggle"
					:class="{ 'is-off': off[p.naam] }"
					:style="{ '--perspective-color': perspectiefKleurVar(p.naam) }"
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
			<Transition v-if="expanded" name="fade" mode="out-in">
				<div v-if="entry.status === 'loading'" key="loading" class="argument-list-skeleton" aria-hidden="true">
					<p class="status-hint">Argumenten laden&hellip;</p>
				</div>
				<p v-else-if="entry.status === 'error'" key="error" class="status-hint">Kon de argumentdata niet laden. Probeer de pagina te verversen.</p>
				<ol v-else key="ready" class="argument-list">
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
							meer laden ({{ argumentList.length - visibleArgumentCount }} resterend)
						</button>
					</li>
				</ol>
			</Transition>
		</div>
		<!-- Compacte plek (debateHref gezet, bv. de homepage-teaser): geen ruimte
		     voor de volledige lijst, wel voor één compacte "nu in beeld"-kaart
		     (issue #135). -->
		<div v-else class="now-playing">
			<Transition name="fade" mode="out-in">
				<p v-if="entry.status === 'loading'" key="loading" class="status-hint">Argumenten laden&hellip;</p>
				<p v-else-if="entry.status === 'error'" key="error" class="status-hint">Kon de argumentdata niet laden.</p>
				<ArgumentCard
					v-else-if="nowPlaying"
					key="ready"
					:argument="nowPlaying"
					:topic-slug="props.topicSlug"
					compact
					video-context
					:playing="true"
					:arguments-in-debate="argumentList"
					:off="off"
					@seek="requestSeek"
				/>
			</Transition>
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
	background: var(--vloei);
	border: 1px solid var(--lijn);
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
   waar .player-column staat -- zonder in de flex-berekening mee te tellen.
   Hoogte komt inline uit playerColumnHeight (script-sectie): matcht de
   hoogte van .player-column, zodat de onderrand van dit ankerpunt samenvalt
   met de onderkant van de video (zie floatObserver hierboven, issue #188). */
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
	color: var(--galnoot-zacht);
	padding: var(--space-3);
	background: var(--blad);
	border: 1px solid var(--lijn);
	border-radius: 4px;
}

/* Zelfde fade-idioom als VideoOverlay.vue's badge-transities
   (.badge-enter-active e.a.): alleen opacity, geen beweging -- houdt de
   overgang tussen skeleton en echte inhoud (issue #119: arguments komt async
   binnen) rustig i.p.v. een layout-sprong of harde flits. */
.fade-enter-active,
.fade-leave-active {
	transition: opacity 0.2s;
}

.fade-enter-from,
.fade-leave-to {
	opacity: 0;
}

.status-hint {
	color: var(--galnoot-zacht);
	padding: var(--space-2) 0;
	margin: 0;
}

/* Plaatshouders op de plek van de tijdlijn/argumentkaarten zolang de
   onderwerp-JSON nog niet binnen is -- voorkomt dat de pagina springt zodra
   de echte inhoud verschijnt. */
.timeline-skeleton {
	height: 28px;
	border-radius: 4px;
	background: var(--blad);
	margin-top: var(--space-2);
}

.argument-list-skeleton {
	padding: var(--space-2) 0;
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
	color: var(--galnoot-zacht);
}

.perspective-toggle {
	display: flex;
	align-items: center;
	gap: 6px;
	padding: 5px 10px;
	border: 1px solid color-mix(in srgb, var(--perspective-color) 45%, var(--lijn));
	background: color-mix(in srgb, var(--perspective-color) 8%, var(--vloei));
	border-radius: 3px;
	font-size: var(--step--1);
	color: var(--galnoot);
	cursor: pointer;
}

.perspective-toggle.is-off {
	opacity: 0.45;
	border-color: var(--lijn);
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
.controls-extra-group {
	display: flex;
	align-items: center;
	gap: 0.4rem;
	margin-left: auto;
}

.argument-toggle-inline {
	width: 40px;
	height: 40px;
	min-width: 40px;
	min-height: 40px;
	display: flex;
	align-items: center;
	justify-content: center;
	background: transparent;
	border: 1px solid var(--lijn);
	border-radius: 4px;
	color: var(--galnoot);
	cursor: pointer;
	padding: 0;
}

.argument-toggle-inline:hover {
	background: color-mix(in srgb, var(--galnoot) 7%, transparent);
}

.argument-toggle-inline[aria-pressed="true"] {
	color: var(--galnoot);
	border-color: var(--galnoot);
}

.argument-toggle-inline:disabled {
	opacity: 0.5;
	cursor: default;
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
