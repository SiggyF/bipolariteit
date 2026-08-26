<script setup lang="ts">
// Tag-verdeling i.p.v. de standaard pro/contra-as op een debatkaart (issue
// #112-vervolg): gevuld via DebateCard.vue's "extra"-slot, alleen op de
// perspectiefpagina (zie PerspectiefView.vue). Eén horizontale balk,
// gesegmenteerd op tag-aandeel binnen dit debat, plus een legenda eronder --
// identiteit mag nooit alleen op kleur/hover leunen (dataviz-skill: "identity
// is never color-alone"), dus icoon+naam per getoonde tag, niet enkel een
// hover-title. TOP_N=4 (dataviz-skill: "<=4 direct-labeled"), de rest
// samengevoegd tot "overig" -- een perspectief bevat al gauw 15-20 tags
// (data/tags.toml), te veel voor een leesbare balk op kaartbreedte.
//
// Kleur blijft alpha-tinten van de perspectiefkleur (geen los categorisch
// palet per tag) -- zelfde principe als PerspectiefTagHeatmap.vue/
// TagCorrespondenceMap.vue: de perspectiefkleur is de enige betekenisdrager,
// tagidentiteit komt uit het icoon+de naam, niet uit een tweede kleurenset.
import { computed } from "vue";
import { withAlpha } from "../lib/colorShades";
import { tagIconPath } from "../lib/tagIcon";
import type { DebateTagCount } from "../lib/groupByDebate";

const props = defineProps<{
	tagCounts: DebateTagCount[];
	color: string;
	density: "uitgelicht" | "uitgebreid" | "compact";
}>();

const TOP_N = 4;

const total = computed(() => props.tagCounts.reduce((sum, t) => sum + t.count, 0));

const segments = computed(() => {
	const top = props.tagCounts.slice(0, TOP_N);
	const rest = props.tagCounts.slice(TOP_N);
	const restCount = rest.reduce((sum, t) => sum + t.count, 0);

	const result = top.map((tag, i) => ({
		key: tag.sleutel,
		sleutel: tag.sleutel,
		count: tag.count,
		icon: tagIconPath(tag.sleutel),
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
			sleutel: "Overig",
			count: restCount,
			icon: null,
			width: total.value ? `${(restCount / total.value) * 100}%` : "0%",
			background: "var(--color-border)",
		});
	}
	return result;
});
</script>

<template>
	<span class="tag-bar-wrap" :class="{ 'tag-bar-wrap--compact': density === 'compact' }">
		<span v-if="segments.length" class="tag-bar" :title="segments.map((s) => `${s.sleutel}: ${s.count}`).join(', ')">
			<span
				v-for="segment in segments"
				:key="segment.key"
				class="tag-bar-segment"
				:style="{ width: segment.width, background: segment.background }"
			></span>
		</span>

		<span v-if="density !== 'compact' && segments.length" class="tag-bar-legend">
			<span v-for="segment in segments" :key="segment.key" class="tag-bar-legend-item">
				<svg
					v-if="segment.icon"
					class="tag-bar-legend-icon"
					viewBox="0 0 24 24"
					width="14"
					height="14"
					fill="none"
					:stroke="color"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
				>
					<path :d="segment.icon" />
				</svg>
				<span class="mono">{{ segment.sleutel }} ({{ segment.count }})</span>
			</span>
		</span>
		<span v-else-if="density !== 'compact'" class="tag-bar-legend mono">geen tags</span>
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
	height: 10px;
	border-radius: 2px;
	overflow: hidden;
	background: var(--color-bg);
}

.tag-bar-wrap--compact .tag-bar {
	flex: 1;
	height: 8px;
}

.tag-bar-segment {
	display: block;
	height: 100%;
}

/* 2px-tussenruimte tussen segmenten (dataviz-skill: "surface gap between
   stacked segments") -- via een rand i.p.v. gap, zodat de balk zelf één
   aaneengesloten breedte blijft (100% van de container). */
.tag-bar-segment + .tag-bar-segment {
	border-left: 2px solid var(--color-bg);
}

.tag-bar-legend {
	display: flex;
	flex-wrap: wrap;
	gap: 0.5rem 0.9rem;
	margin-top: 0.5rem;
	font-size: var(--step--1);
	color: var(--color-muted);
}

.tag-bar-legend-item {
	display: inline-flex;
	align-items: center;
	gap: 0.3rem;
	white-space: nowrap;
}

.tag-bar-legend-icon {
	flex-shrink: 0;
}
</style>
