<script setup lang="ts">
import { computed } from "vue";
import ArgumentTimeline from "./ArgumentTimeline.vue";
import TagCorrespondenceMap from "./TagCorrespondenceMap.vue";
import PerspectiefTagHeatmap from "./PerspectiefTagHeatmap.vue";
import TopPersonsPerTag, { type TagMeta } from "./TopPersonsPerTag.vue";
import { PERSPECTIEVEN } from "../lib/tagIcons.generated";
import { filterTagsByPerspectief, derivePartyTagIndex, derivePersonTagIndex } from "../lib/aggregate";
import type { Argument } from "../lib/types";

const props = defineProps<{ perspectief: string; argumentList: Argument[] }>();

const kleur = computed(() => PERSPECTIEVEN.find((p) => p.naam === props.perspectief)?.kleur ?? "#6f6558");

// Correspondentiekaart schaalt op de perspectief-gefilterde lijst; de
// heatmap en de top-5-per-tag rekenen op het volledige corpus, want hun
// noemer (partij-/persoonstotaal) moet alles omvatten, niet alleen dit
// perspectief (zie derivePartyTagIndex/derivePersonTagIndex).
const scopedList = computed(() => filterTagsByPerspectief(props.argumentList, props.perspectief));

const totalToekenningen = computed(() => scopedList.value.reduce((sum, a) => sum + a.tags.length, 0));

// Tags van dit perspectief, gegroepeerd op labelgroep -- bepaalt zowel de
// kolomvolgorde van de heatmap als de volgorde van de top-5-lijsten eronder.
const tagMeta = computed(() => {
	const meta = new Map<string, TagMeta>();
	for (const argument of scopedList.value) {
		for (const tag of argument.tags) {
			if (!meta.has(tag.sleutel)) meta.set(tag.sleutel, { sleutel: tag.sleutel, beschrijving: tag.beschrijving, labelgroep: tag.labelgroep });
		}
	}
	return meta;
});

const orderedTags = computed(() =>
	[...tagMeta.value.values()].sort((a, b) => a.labelgroep.localeCompare(b.labelgroep, "nl") || a.sleutel.localeCompare(b.sleutel, "nl")),
);

const partyIndex = computed(() => derivePartyTagIndex(props.argumentList));
const personIndex = computed(() => derivePersonTagIndex(props.argumentList));
</script>

<template>
	<section class="perspectief-view">
		<header class="actor-header">
			<span class="perspectief-swatch" :style="{ background: kleur }"></span>
			<h1>{{ perspectief }}</h1>
		</header>
		<p class="panel-note">{{ totalToekenningen }} tagtoekenningen in dit perspectief, over alle onderwerpen heen.</p>

		<ArgumentTimeline :argumentList="scopedList" :interactive="false" />

		<TagCorrespondenceMap :argument-list="scopedList" />

		<PerspectiefTagHeatmap :tags="orderedTags" :party-index="partyIndex" :color="kleur" />

		<TopPersonsPerTag :tags="orderedTags" :person-index="personIndex" :color="kleur" />
	</section>
</template>
