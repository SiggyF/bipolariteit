<template>
	<div class="av">
		<div class="av-toggle" role="group" aria-label="Weergave van de argumentenboom">
			<button type="button" :aria-pressed="view === 'panes'" @click="view = 'panes'">Panelen</button>
			<button type="button" :aria-pressed="view === 'axis'" @click="view = 'axis'">Confrontatie-as</button>
		</div>
		<ArgumentPanes v-if="view === 'panes'" :tree="tree" />
		<ArgumentTree v-else :tree="tree" />
	</div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import ArgumentPanes from "./ArgumentPanes.vue";
import ArgumentTree from "./ArgumentTree.vue";
import type { ConfrontatieExport } from "../lib/argumentTree";

// Tijdelijke wissel tot ArgumentPanes de confrontatie-as in één keer
// vervangt (issue #251): tot die tijd blijft de bestaande weergave bereikbaar,
// o.a. voor de weerleggingslijnen en de twijfelachtige classificaties.
defineProps<{ tree: ConfrontatieExport }>();

const view = ref<"panes" | "axis">("panes");
</script>

<style scoped>
.av-toggle {
	display: inline-flex;
	margin-bottom: var(--space-2);
	border: 1px solid var(--lijn);
	border-radius: var(--hoek-rond);
	overflow: hidden;
	font-family: var(--font-kop);
	font-size: 0.9rem;
	font-weight: 600;
}

.av-toggle button {
	min-height: 2.75rem;
	padding: 0 1.25rem;
	font: inherit;
	background: transparent;
	border: 0;
	cursor: pointer;
	color: var(--galnoot-zacht);
}

.av-toggle button[aria-pressed="true"] {
	background: var(--galnoot);
	color: var(--op-inkt);
}

.av-toggle button:focus-visible {
	outline: 2px solid var(--galnoot);
	outline-offset: 2px;
}
</style>
