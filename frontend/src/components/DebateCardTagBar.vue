<script setup lang="ts">
// Tag-verdeling i.p.v. de standaard pro/contra-as op een debatkaart (issue
// #112-vervolg): gevuld via DebateCard.vue's "extra"-slot, alleen op de
// perspectiefpagina (zie PerspectiefView.vue). Eén horizontale balk,
// gesegmenteerd op tag-aandeel binnen dit debat. Top N expliciet, de rest
// samengevoegd tot "overig" -- een perspectief bevat al gauw 15-20 tags
// (data/tags.toml), te veel voor een leesbare balk op kaartbreedte.
import { computed } from "vue";
import { withAlpha } from "../lib/colorShades";
import type { DebateTagCount } from "../lib/groupByDebate";

const props = defineProps<{
	tagCounts: DebateTagCount[];
	color: string;
	density: "uitgelicht" | "uitgebreid" | "compact";
}>();

const TOP_N = 6;

const total = computed(() => props.tagCounts.reduce((sum, t) => sum + t.count, 0));

const segments = computed(() => {
	const top = props.tagCounts.slice(0, TOP_N);
	const rest = props.tagCounts.slice(TOP_N);
	const restCount = rest.reduce((sum, t) => sum + t.count, 0);

	const result = top.map((tag, i) => ({
		key: tag.sleutel,
		label: `${tag.sleutel}: ${tag.count}`,
		width: total.value ? `${(tag.count / total.value) * 100}%` : "0%",
		// Vaste rangorde-alpha (hoogste aandeel het meest gedekt) i.p.v. op een
		// los maximum geschaald -- zelfde soort dekking-draagt-de-waarde-keuze
		// als withAlpha's toepassing in PerspectiefTagHeatmap.vue, hier per
		// segment i.p.v. per tabelcel.
		background: withAlpha(props.color, 0.9 - i * (0.6 / Math.max(1, TOP_N - 1))),
	}));
	if (restCount > 0) {
		result.push({
			key: "__overig",
			label: `Overig: ${restCount}`,
			width: total.value ? `${(restCount / total.value) * 100}%` : "0%",
			background: "var(--color-border)",
		});
	}
	return result;
});
</script>

<template>
	<span class="tag-bar-wrap" :class="{ 'tag-bar-wrap--compact': density === 'compact' }">
		<span v-if="segments.length" class="tag-bar">
			<span
				v-for="segment in segments"
				:key="segment.key"
				class="tag-bar-segment"
				:style="{ width: segment.width, background: segment.background }"
				:title="segment.label"
			></span>
		</span>
		<span class="tag-bar-legend mono">
			<template v-if="tagCounts.length">{{ tagCounts.length }} tag{{ tagCounts.length === 1 ? "" : "s" }}, {{ total }} toekenning{{ total === 1 ? "" : "en" }}</template>
			<template v-else>geen tags</template>
		</span>
	</span>
</template>

<style scoped>
.tag-bar-wrap {
	display: block;
	margin-top: 0.75rem;
}

/* Vult, net als de default pro/contra-as, de 2e+3e kolom van de 3-koloms
   grid op een compacte kaart (zie .debate-card--compact in DebateCard.vue) --
   hier expliciet via grid-column i.p.v. de display:contents-truc, want deze
   balk is één aaneengesloten geheel, geen twee losse pro/contra-cellen. */
.tag-bar-wrap--compact {
	grid-column: 2 / span 2;
	display: flex;
	align-items: center;
	gap: 0.5rem;
	margin-top: 0;
}

.tag-bar {
	display: flex;
	flex: 1;
	height: 10px;
	border-radius: 2px;
	overflow: hidden;
	background: var(--color-bg);
}

.tag-bar-wrap--compact .tag-bar {
	height: 8px;
}

.tag-bar-segment {
	display: block;
	height: 100%;
}

.tag-bar-legend {
	display: block;
	margin-top: 0.4rem;
	font-size: var(--step--1);
	color: var(--color-muted);
	white-space: nowrap;
}

.tag-bar-wrap--compact .tag-bar-legend {
	margin-top: 0;
}
</style>
