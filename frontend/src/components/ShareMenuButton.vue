<script setup lang="ts">
// Klein icoon-knopje in de videospeler-controlsrij (DebateVideoView.vue,
// issue #244) dat hetzelfde deelmenu opent als ShareMenu.astro in SiteNav --
// die zit op een Astro-element buiten de Vue-island en kan dus niet "even"
// in de controlsrij van de video staan. Hergebruikt dezelfde platformlijst/
// URL-opbouw (lib/shareMenu.ts) en dezelfde globale .share-menu-* CSS uit
// main.css, zodat het paneel er identiek uitziet.
import { computed, onMounted, onUnmounted, ref } from "vue";
import { buildEmbedSnippet, SHARE_PLATFORMS } from "../lib/shareMenu";

const props = defineProps<{
	// URL van de /embed/debatten/[id]/-tegenhanger. Alleen meegegeven vanaf
	// /debatten/[id]/ zelf -- niet vanaf de homepage-teaser en niet vanaf de
	// embed-pagina zelf (een insluitknop ín de embed zou naar zichzelf wijzen).
	embedUrl?: string | null;
}>();

const root = ref<HTMLElement | null>(null);
const open = ref(false);
const copyLabel = ref("Link kopiëren");
const embedLabel = ref("Insluitcode kopiëren");

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
});
</script>

<template>
	<div ref="root" class="share-menu video-share-menu">
		<button
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
		<div v-if="open" class="share-menu-panel" role="menu">
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
	</div>
</template>

<style scoped>
/* .share-menu (incl. position: relative)/.share-menu-panel/.share-menu-item
   etc. komen uit main.css (global, gedeeld met ShareMenu.astro) -- hier
   alleen de afwijkende uitlijning t.o.v. SiteNav's rechts-uitgelijnde
   trigger: deze knop zit standaard ergens midden in de controlsrij, dus het
   paneel moet links uitlijnen i.p.v. rechts om niet buiten de videobreedte
   te vallen. */
.video-share-menu .share-menu-panel {
	left: 0;
	right: auto;
}

/* Vue's scoped CSS reikt alleen tot het root-element van een kindcomponent,
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
