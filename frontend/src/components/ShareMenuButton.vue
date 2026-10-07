<script setup lang="ts">
// Klein icoon-knopje in de videospeler-controlsrij (DebateVideoView.vue,
// issue #244) dat hetzelfde deelmenu opent als ShareMenu.astro in SiteNav --
// die zit op een Astro-element buiten de Vue-island en kan dus niet "even"
// in de controlsrij van de video staan. Hergebruikt dezelfde platformlijst/
// URL-opbouw (lib/shareMenu.ts) en dezelfde globale .share-menu-* CSS uit
// main.css, zodat het paneel er identiek uitziet.
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { buildEmbedSnippet, SHARE_PLATFORMS } from "../lib/shareMenu";

const props = defineProps<{
	// URL van de /embed/debatten/[id]/-tegenhanger. Alleen meegegeven vanaf
	// /debatten/[id]/ zelf -- niet vanaf de homepage-teaser en niet vanaf de
	// embed-pagina zelf (een insluitknop ín de embed zou naar zichzelf wijzen).
	embedUrl?: string | null;
}>();

const root = ref<HTMLElement | null>(null);
const triggerEl = ref<HTMLButtonElement | null>(null);
const open = ref(false);
const copyLabel = ref("Link kopiëren");
const embedLabel = ref("Insluitcode kopiëren");
const panelPos = ref({ top: 0, left: 0 });

// VideoPlayer.vue's .controls-row (de ouder van deze knop) heeft
// `overflow-x: auto` i.v.m. smalle schermen -- CSS dwingt dan óók
// overflow-y op auto af (één as non-visible maakt de andere niet langer
// visible), wat een position:absolute-paneel daarbinnen gewoon afsnijdt.
// Daarom hier getelepeerd naar <body> met position:fixed, positie berekend
// uit de knop zelf i.p.v. relatief aan een (geclipte) ouder.
const PANEL_WIDTH = 340;
const PANEL_MARGIN = 16;

function updatePosition() {
	if (!triggerEl.value) return;
	const rect = triggerEl.value.getBoundingClientRect();
	panelPos.value = {
		top: rect.bottom + 6,
		left: Math.min(rect.left, window.innerWidth - PANEL_WIDTH - PANEL_MARGIN),
	};
}

watch(open, (isOpen) => {
	if (isOpen) {
		updatePosition();
		window.addEventListener("scroll", updatePosition, true);
		window.addEventListener("resize", updatePosition);
	} else {
		window.removeEventListener("scroll", updatePosition, true);
		window.removeEventListener("resize", updatePosition);
	}
});

const isTouchPrimary = computed(() => typeof window !== "undefined" && window.matchMedia?.("(pointer: coarse)").matches);

function shareData() {
	return { title: document.title, url: location.href };
}

function onTriggerClick() {
	// navigator.share bestaat ook op desktop Safari/Chrome (macOS) -- puur op
	// de aanwezigheid van de API afgaan zou daar het systeemmenu tonen i.p.v.
	// de dropdown (zelfde afweging als ShareMenu.astro).
	if (navigator.share && isTouchPrimary.value) {
		navigator.share(shareData()).catch(() => {
			/* gebruiker annuleerde het systeemdeelvenster, geen actie nodig */
		});
		return;
	}
	open.value = !open.value;
}

function onPlatformClick(buildUrl: (title: string, url: string) => string) {
	const d = shareData();
	window.open(buildUrl(d.title, d.url), "_blank", "noopener,noreferrer,width=600,height=500");
	open.value = false;
}

async function copyLink() {
	await navigator.clipboard.writeText(location.href);
	copyLabel.value = "Gekopieerd";
	setTimeout(() => {
		copyLabel.value = "Link kopiëren";
		open.value = false;
	}, 2000);
}

async function copyEmbed() {
	if (!props.embedUrl) return;
	await navigator.clipboard.writeText(buildEmbedSnippet(props.embedUrl));
	embedLabel.value = "Gekopieerd";
	setTimeout(() => {
		embedLabel.value = "Insluitcode kopiëren";
		open.value = false;
	}, 2000);
}

function onKeydown(event: KeyboardEvent) {
	if (event.key === "Escape") open.value = false;
}

function onClickOutside(event: MouseEvent) {
	if (root.value && !root.value.contains(event.target as Node)) open.value = false;
}

onMounted(() => {
	document.addEventListener("keydown", onKeydown);
	document.addEventListener("click", onClickOutside);
});
onUnmounted(() => {
	document.removeEventListener("keydown", onKeydown);
	document.removeEventListener("click", onClickOutside);
	window.removeEventListener("scroll", updatePosition, true);
	window.removeEventListener("resize", updatePosition);
});
</script>

<template>
	<div ref="root" class="share-menu video-share-menu">
		<button
			ref="triggerEl"
			type="button"
			class="control-button argument-toggle-inline"
			:aria-expanded="open"
			aria-haspopup="menu"
			aria-label="Delen / insluiten"
			title="Delen / insluiten"
			@click="onTriggerClick"
		>
			<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
				<circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" />
				<line x1="8.6" y1="10.5" x2="15.4" y2="6.5" /><line x1="8.6" y1="13.5" x2="15.4" y2="17.5" />
			</svg>
		</button>
		<Teleport to="body">
		<div v-if="open" class="share-menu-panel" role="menu" :style="{ position: 'fixed', top: `${panelPos.top}px`, left: `${panelPos.left}px`, right: 'auto' }">
			<div class="share-menu-label">Deel deze pagina</div>
			<div class="share-menu-grid">
				<a
					v-for="platform in SHARE_PLATFORMS"
					:key="platform.key"
					href="#"
					class="share-menu-item"
					role="menuitem"
					@click.prevent="onPlatformClick(platform.buildUrl)"
				>
					<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="platform.icon" />
					<span>{{ platform.label }}</span>
				</a>
			</div>
			<div class="share-menu-divider"></div>
			<button type="button" class="share-menu-item share-menu-copy" role="menuitem" :class="{ 'is-copied': copyLabel !== 'Link kopiëren' }" @click="copyLink">
				<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
					<path d="M10 13.5a4 4 0 006 .5l2.5-2.5a4 4 0 00-5.7-5.7L11.5 7"/><path d="M14 10.5a4 4 0 00-6-.5L5.5 12.5a4 4 0 005.7 5.7L12.5 17"/>
				</svg>
				<span>{{ copyLabel }}</span>
			</button>
			<button
				v-if="props.embedUrl"
				type="button"
				class="share-menu-item share-menu-embed"
				role="menuitem"
				:class="{ 'is-copied': embedLabel !== 'Insluitcode kopiëren' }"
				@click="copyEmbed"
			>
				<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
					<polyline points="8 6 3 12 8 18"/><polyline points="16 6 21 12 16 18"/>
				</svg>
				<span>{{ embedLabel }}</span>
			</button>
		</div>
		</Teleport>
	</div>
</template>

<style scoped>
/* .share-menu/.share-menu-panel/.share-menu-item etc. komen uit main.css
   (global, gedeeld met ShareMenu.astro). Positie van het paneel zelf (fixed,
   links uitgelijnd onder de knop) komt uit panelPos/:style hierboven, niet
   uit CSS -- het paneel wordt naar <body> geteleporteerd (VideoPlayer.vue's
   .controls-row heeft overflow-x: auto, wat ook overflow-y impliciet clipt,
   dus een position:absolute-paneel daarbinnen was onzichtbaar).

   Vue's scoped CSS reikt alleen tot het root-element van een kindcomponent,
   niet dieper -- DebateVideoView.vue's eigen `.argument-toggle-inline`-regel
   (andere scope-attribute) bereikt de knop hieronder dus niet, net zoals die
   regel zelf al niet bij VideoPlayer.vue's `.control-button` kan. Zelfde
   vormgeving hier dus nogmaals herhaald, i.p.v. een derde keer. */
.video-share-menu .argument-toggle-inline {
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

.video-share-menu .argument-toggle-inline:hover,
.video-share-menu .argument-toggle-inline[aria-expanded="true"] {
	background: color-mix(in srgb, var(--galnoot) 7%, transparent);
}
</style>
