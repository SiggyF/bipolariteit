<script setup lang="ts">
import { computed } from "vue";
import FilterBar from "./FilterBar.vue";
import ArgumentTimeline from "./ArgumentTimeline.vue";
import DebateList from "./DebateList.vue";
import ClaimsHighlights from "./ClaimsHighlights.vue";
import StatsPanel from "./StatsPanel.vue";
import TagsPerParty from "./TagsPerParty.vue";
import TagCorrespondenceMap from "./TagCorrespondenceMap.vue";
import ArgumentColumn from "./ArgumentColumn.vue";
import { STANCES, stanceLabel, type Argument } from "../lib/types";
import { DATE_FROM, DATE_TO, filters, initFiltersFromUrl, matches, matchesExcept } from "../lib/filters";

// Alles wat op het filter reageert zit bewust in dit ene island: de grafieken
// en de kolommen delen zo dezelfde argumentenlijst en dezelfde filterstore,
// waardoor ze niet uit elkaar kunnen lopen. Als extra: het corpus (~7 MB)
// wordt één keer geserialiseerd i.p.v. per island.
const props = defineProps<{
	argumentList: Argument[];
	topicSlug: string;
}>();

initFiltersFromUrl(props.argumentList);

const filtered = computed(() => props.argumentList.filter(matches));

// De tijdlijn slaat het datumbereik zelf over: klikken op een staaf zet het
// datumfilter, maar de tijdlijn moet daarna alle debatdagen blijven tonen om
// te laten zien wélke dag je selecteerde -- anders klapt de as in tot één
// staaf na de eerste klik. Andere dimensies (partij, tag, ...) werken wel
// gewoon door, net als bij de correspondentiekaart.
const timelineList = computed(() => props.argumentList.filter((a) => matchesExcept(a, [DATE_FROM, DATE_TO])));

// Kolommen tonen alleen de posities die het filter overlaat; filter je op
// Pro, dan verdwijnen de andere twee kolommen in plaats van leeg te blijven.
const columns = computed(() =>
	STANCES.filter((stance) => !filters.values.stance.length || filters.values.stance.includes(stance)).map((stance) => ({
		stance,
		label: stanceLabel(stance),
		argumentList: filtered.value.filter((a) => a.stance === stance),
	})),
);
</script>

<template>
	<FilterBar :argumentList="argumentList" :matchCount="filtered.length" />

	<TagCorrespondenceMap :argumentList="argumentList" />

	<ArgumentTimeline :argumentList="timelineList" />

	<DebateList :argumentList="filtered" />

	<ClaimsHighlights :argumentList="filtered" />

	<StatsPanel :argumentList="filtered" />
	<TagsPerParty :argumentList="filtered" />

	<p v-if="!filtered.length" class="no-results">
		Geen argumenten voldoen aan dit filter. Verwijder een filter hierboven om er meer te zien.
	</p>

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
