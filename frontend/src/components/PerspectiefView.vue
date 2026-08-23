<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import ArgumentTimeline from "./ArgumentTimeline.vue";
import TagCorrespondenceMap from "./TagCorrespondenceMap.vue";
import PerspectiefTagHeatmap from "./PerspectiefTagHeatmap.vue";
import TopPersonsPerTag, { type TagMeta } from "./TopPersonsPerTag.vue";
import { PERSPECTIEVEN } from "../lib/tagIcons.generated";
import {
	deserializePartyTagIndex,
	deserializePersonTagIndex,
	type SerializedPartyTagIndexEntry,
	type SerializedPersonTagIndexEntry,
} from "../lib/aggregate";
import { perspectiefWeergaveNaam } from "../lib/tagIcon";
import { slugify } from "../lib/slug";
import type { Argument } from "../lib/types";

// De partij-/persoonindex wordt build-time over het volledige corpus
// uitgerekend (Astro-pagina, zie [naam].astro) -- hun noemer moet alle
// onderwerpen omvatten, niet alleen dit perspectief. Alleen de perspectief-
// gefilterde, lean argumentenlijst voor de tijdlijn/correspondentiekaart
// wordt hier client-side gefetcht in plaats van als prop meegebakken (issue
// #163: die lijst was het gros van de 18-21 MB per perspectiefpagina).
const props = defineProps<{
	perspectief: string;
	partyIndex: SerializedPartyTagIndexEntry[];
	personIndex: SerializedPersonTagIndexEntry[];
	dataBaseUrl: string;
}>();

const kleur = computed(() => PERSPECTIEVEN.find((p) => p.naam === props.perspectief)?.kleur ?? "#6f6558");

type FetchStatus = "loading" | "ready" | "error";
const status = ref<FetchStatus>("loading");
const scopedList = ref<Argument[]>([]);

onMounted(async () => {
	try {
		const response = await fetch(`${props.dataBaseUrl}/perspectieven/${slugify(props.perspectief)}.json`);
		if (!response.ok) throw new Error(`onverwachte statuscode ${response.status}`);
		scopedList.value = await response.json();
		status.value = "ready";
	} catch {
		status.value = "error";
	}
});

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

const partyIndex = computed(() => deserializePartyTagIndex(props.partyIndex));
const personIndex = computed(() => deserializePersonTagIndex(props.personIndex));
</script>

<template>
	<section class="perspectief-view">
		<header class="actor-header">
			<span class="perspectief-swatch" :style="{ background: kleur }"></span>
			<h1>{{ perspectiefWeergaveNaam(perspectief) }}</h1>
		</header>

		<p v-if="status === 'error'" class="panel-note panel-error">
			Kon de argumentdata niet laden. Probeer de pagina te verversen.
		</p>
		<p v-else-if="status === 'loading'" class="panel-note">Bezig met laden&hellip;</p>
		<template v-else>
			<p class="panel-note">{{ totalToekenningen }} tagtoekenningen in dit perspectief, over alle onderwerpen heen.</p>

			<ArgumentTimeline :argumentList="scopedList" :interactive="false" />

			<TagCorrespondenceMap :argument-list="scopedList" />
		</template>

		<PerspectiefTagHeatmap :tags="orderedTags" :party-index="partyIndex" :color="kleur" />

		<TopPersonsPerTag :tags="orderedTags" :person-index="personIndex" :color="kleur" />
	</section>
</template>

<style scoped>
.panel-error {
	color: var(--kleur-fout, #b3261e);
}
</style>
