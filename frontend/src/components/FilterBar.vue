<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import type { Argument } from "../lib/types";
import {
	DIMENSIONS,
	clearAll,
	facetOptions,
	filters,
	formatValue,
	isActive,
	labelFor,
	removeValue,
	setDateRange,
	toggleValue,
} from "../lib/filters";

const props = defineProps<{ argumentList: Argument[]; matchCount: number }>();

// Facetten over de hele topic, niet over de selectie -- anders verdwijnen de
// opties waarmee je je eigen filter weer zou kunnen verbreden.
const facets = computed(() => facetOptions(props.argumentList));

const openFacet = ref<string | null>(null);
const search = ref("");

function toggleFacet(key: string) {
	openFacet.value = openFacet.value === key ? null : key;
	search.value = "";
}

const visibleOptions = computed(() => {
	const facet = facets.value.find((f) => f.key === openFacet.value);
	if (!facet) return [];
	const needle = search.value.trim().toLowerCase();
	if (!needle) return facet.options;
	return facet.options.filter((o) => o.label.toLowerCase().includes(needle));
});

// Actieve filters als platte lijst chips, in dezelfde volgorde als DIMENSIONS.
const chips = computed(() =>
	DIMENSIONS.flatMap((dimension) =>
		filters.values[dimension.key].map((value) => ({
			dimension: dimension.key,
			dimensionLabel: dimension.label,
			value,
			label: formatValue(dimension.key, value),
		})),
	),
);

function isSelected(key: string, value: string) {
	return filters.values[key].includes(value);
}

// Klik buiten de balk (of Escape) klapt het open paneel weer dicht. Het paneel
// is hoog en de argumenten staan eronder, dus wegklikken is de natuurlijke
// manier om verder te lezen.
const bar = ref<HTMLElement | null>(null);

function onDocumentPointerDown(e: PointerEvent) {
	if (!openFacet.value) return;
	if (bar.value?.contains(e.target as Node)) return;
	openFacet.value = null;
}

function onKeydown(e: KeyboardEvent) {
	if (e.key === "Escape") openFacet.value = null;
}

onMounted(() => {
	document.addEventListener("pointerdown", onDocumentPointerDown);
	document.addEventListener("keydown", onKeydown);
});

onBeforeUnmount(() => {
	document.removeEventListener("pointerdown", onDocumentPointerDown);
	document.removeEventListener("keydown", onKeydown);
});
</script>

<template>
	<div ref="bar" class="filter-bar" :class="{ 'is-active': isActive() }">
		<div class="filter-bar-row">
			<span class="filter-count">
				<strong>{{ matchCount }}</strong> van {{ argumentList.length }} argumenten
			</span>

			<div class="filter-facets">
				<button
					v-for="facet in facets"
					:key="facet.key"
					type="button"
					class="facet-button"
					:class="{ 'is-open': openFacet === facet.key, 'has-selection': filters.values[facet.key].length > 0 }"
					:aria-expanded="openFacet === facet.key"
					@click="toggleFacet(facet.key)"
				>
					{{ facet.label }}
					<span v-if="filters.values[facet.key].length" class="facet-badge">{{ filters.values[facet.key].length }}</span>
				</button>
				<button
					type="button"
					class="facet-button"
					:class="{ 'is-open': openFacet === 'datum', 'has-selection': !!filters.van || !!filters.tot }"
					:aria-expanded="openFacet === 'datum'"
					@click="toggleFacet('datum')"
				>
					Datum
				</button>
			</div>

			<button v-if="isActive()" type="button" class="filter-clear" @click="clearAll()">alles wissen</button>
		</div>

		<ul v-if="chips.length || filters.van || filters.tot" class="filter-chips">
			<li v-for="chip in chips" :key="`${chip.dimension}:${chip.value}`" class="filter-chip">
				<span class="chip-dimension">{{ chip.dimensionLabel }}</span>
				{{ chip.label }}
				<button
					type="button"
					:aria-label="`filter ${chip.dimensionLabel} ${chip.label} verwijderen`"
					@click="removeValue(chip.dimension, chip.value)"
				>
					×
				</button>
			</li>
			<li v-if="filters.van || filters.tot" class="filter-chip">
				<span class="chip-dimension">Datum</span>
				{{ filters.van || "begin" }} t/m {{ filters.tot || "eind" }}
				<button type="button" aria-label="datumfilter verwijderen" @click="setDateRange(null, null)">×</button>
			</li>
		</ul>

		<div v-if="openFacet === 'datum'" class="facet-panel">
			<label>
				van
				<input type="date" :value="filters.van" @change="setDateRange(($event.target as HTMLInputElement).value, filters.tot)" />
			</label>
			<label>
				t/m
				<input type="date" :value="filters.tot" @change="setDateRange(filters.van, ($event.target as HTMLInputElement).value)" />
			</label>
		</div>

		<div v-else-if="openFacet" class="facet-panel">
			<p class="facet-hint">
				Meerdere waarden binnen <strong>{{ labelFor(openFacet) }}</strong> gelden als &ldquo;of&rdquo;; verschillende
				filtersoorten gelden samen als &ldquo;en&rdquo;.
			</p>
			<input v-model="search" type="search" class="facet-search" :placeholder="`zoek in ${labelFor(openFacet).toLowerCase()}…`" />
			<ul class="facet-options">
				<li v-for="option in visibleOptions" :key="option.value">
					<label>
						<input
							type="checkbox"
							:checked="isSelected(openFacet, option.value)"
							@change="toggleValue(openFacet, option.value)"
						/>
						<span class="facet-option-label">{{ option.label }}</span>
						<span class="facet-option-count">{{ option.count }}</span>
					</label>
				</li>
				<li v-if="!visibleOptions.length" class="facet-empty">geen resultaten</li>
			</ul>
		</div>
	</div>
</template>
