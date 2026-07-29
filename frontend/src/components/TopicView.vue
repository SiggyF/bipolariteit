<script setup lang="ts">
import { computed } from "vue";
import FilterBar from "./FilterBar.vue";
import StatsPanel from "./StatsPanel.vue";
import TagsPerParty from "./TagsPerParty.vue";
import TagCorrespondenceMap from "./TagCorrespondenceMap.vue";
import ArgumentColumn from "./ArgumentColumn.vue";
import { STANCES, stanceLabel, type Argument, type Correspondence } from "../lib/types";
import { filters, initFiltersFromUrl, matches } from "../lib/filters";

// Alles wat op het filter reageert zit bewust in dit ene island: de grafieken
// en de kolommen delen zo dezelfde argumentenlijst en dezelfde filterstore,
// waardoor ze niet uit elkaar kunnen lopen. Als extra: het corpus (~7 MB)
// wordt één keer geserialiseerd i.p.v. per island.
const props = defineProps<{
	argumentList: Argument[];
	topicSlug: string;
	correspondence: Correspondence | null;
}>();

initFiltersFromUrl(props.argumentList);

const filtered = computed(() => props.argumentList.filter(matches));

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

	<StatsPanel :argumentList="filtered" />
	<TagsPerParty :argumentList="filtered" />
	<TagCorrespondenceMap :correspondence="correspondence" :argumentList="filtered" />

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
