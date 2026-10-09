<script setup lang="ts">
// Persoons-/partijpagina's (issue #261): de kaart (pmtiles, MapLibre,
// deck.gl en tot ~7 MB contourdata) laadt pas na een klik, niet bij elk
// paginabezoek. TiledPlenairMap zit in een async component, zodat ook de
// kaartbibliotheken pas dan binnenkomen.
import { defineAsyncComponent, ref } from "vue";
import type { ContourKind } from "../lib/contours";

defineProps<{ tilesBaseUrl: string; kind: ContourKind; name: string }>();

const TiledPlenairMap = defineAsyncComponent(() => import("./TiledPlenairMap.vue"));
const shown = ref(false);
</script>

<template>
	<section class="contour-map-toggle" aria-label="Plek op de plenaire kaart">
		<h2>Plek op de plenaire kaart</h2>
		<button v-if="!shown" type="button" class="contour-map-button" @click="shown = true">Toon op de kaart</button>
		<TiledPlenairMap v-else :tiles-base-url="tilesBaseUrl" :focus="{ kind, name }" />
	</section>
</template>

<style scoped>
.contour-map-toggle {
	margin-top: var(--ruimte-6, 2rem);
}
.contour-map-button {
	font: inherit;
	padding: 0.5rem 1rem;
	color: inherit;
	background: transparent;
	border: 1px solid color-mix(in srgb, currentColor 30%, transparent);
	border-radius: 4px;
	cursor: pointer;
}
.contour-map-button:focus-visible {
	outline: 2px solid currentColor;
	outline-offset: 2px;
}
</style>
