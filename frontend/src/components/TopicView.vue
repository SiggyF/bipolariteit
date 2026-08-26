<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import FilterBar from "./FilterBar.vue";
import DebateList from "./DebateList.vue";
import ClaimsHighlights from "./ClaimsHighlights.vue";
import StatsPanel from "./StatsPanel.vue";
import TypologyStanceBars from "./TypologyStanceBars.vue";
import TagsPerParty from "./TagsPerParty.vue";
import TagCorrespondenceMap from "./TagCorrespondenceMap.vue";
import ArgumentColumn from "./ArgumentColumn.vue";
import { STANCES, stanceLabel, type Argument } from "../lib/types";
import { filters, initFiltersFromUrl, matches } from "../lib/filters";

// Alles wat op het filter reageert zit bewust in dit ene island: de grafieken
// en de kolommen delen zo dezelfde argumentenlijst en dezelfde filterstore,
// waardoor ze niet uit elkaar kunnen lopen.
const props = defineProps<{
	topicSlug: string;
	dataBaseUrl: string;
}>();

// Het corpus per onderwerp (~7-11 MB) werd voorheen als Astro-prop in de HTML
// gebakken; dat duwde de grotere onderwerpen over de Cloudflare Workers-
// assetlimiet van 25 MiB (issue #163). Nu client-side gefetcht, net als
// PerspectiefView.vue.
type FetchStatus = "loading" | "ready" | "error";
const status = ref<FetchStatus>("loading");
const argumentList = ref<Argument[]>([]);

onMounted(async () => {
	try {
		const response = await fetch(`${props.dataBaseUrl}/onderwerpen/${props.topicSlug}.json`);
		if (!response.ok) throw new Error(`onverwachte statuscode ${response.status}`);
		argumentList.value = await response.json();
		initFiltersFromUrl(argumentList.value);
		status.value = "ready";
	} catch {
		status.value = "error";
	}
});

const filtered = computed(() => argumentList.value.filter(matches));

// Kolommen tonen alleen de posities die het filter overlaat; filter je op
// Pro, dan verdwijnen de andere twee kolommen in plaats van leeg te blijven.
const columns = computed(() =>
	STANCES.filter((stance) => !filters.values.stance.length || filters.values.stance.includes(stance)).map((stance) => ({
		stance,
		label: stanceLabel(stance),
		argumentList: filtered.value.filter((a) => a.stance === stance),
	})),
);

// Onder 900px vervangt één samengevoegde lijst (natuurlijke volgorde, niet
// per stance gegroepeerd) de drie kolommen (issue #136) -- pro/contra/
// onduidelijk staan daar door elkaar, met een stance-badge per kaart
// (ArgumentCard.vue) i.p.v. de kolomkop als enige indicatie. Zelfde
// breakpoint als ArgumentCard's eigen matchMedia-check en de rest van de
// site (main.css).
const MOBILE_QUERY = "(max-width: 900px)";
const mobileQuery = window.matchMedia(MOBILE_QUERY);
const isMobile = ref(mobileQuery.matches);
function onMobileQueryChange(e: MediaQueryListEvent) {
	isMobile.value = e.matches;
}
onMounted(() => mobileQuery.addEventListener("change", onMobileQueryChange));
onBeforeUnmount(() => mobileQuery.removeEventListener("change", onMobileQueryChange));
</script>

<template>
	<p v-if="status === 'error'" class="no-results">Kon de argumentdata niet laden. Probeer de pagina te verversen.</p>
	<p v-else-if="status === 'loading'" class="no-results">Bezig met laden&hellip;</p>
	<template v-else>
		<FilterBar :argumentList="argumentList" :matchCount="filtered.length" />

		<TypologyStanceBars :argumentList="filtered" />

		<TagCorrespondenceMap :argumentList="argumentList" />

		<DebateList :argumentList="filtered" />

		<ClaimsHighlights :argumentList="filtered" />

		<StatsPanel :argumentList="filtered" />
		<TagsPerParty :argumentList="filtered" />

		<p v-if="!filtered.length" class="no-results">
			Geen argumenten voldoen aan dit filter. Verwijder een filter hierboven om er meer te zien.
		</p>

		<ArgumentColumn v-else-if="isMobile" :argumentList="filtered" :topicSlug="topicSlug" label="Argumenten" stanceClass="column-single" />

		<div v-else class="columns">
			<ArgumentColumn
				v-for="column in columns"
				:key="column.stance"
				:argumentList="column.argumentList"
				:topicSlug="topicSlug"
				:label="column.label"
				:stanceClass="`column-${column.stance}`"
			/>
		</div>
	</template>
</template>
