<script setup lang="ts">
// Tag-verdeling i.p.v. de standaard pro/contra-as op een debatkaart (issue
// #112-vervolg): gevuld via DebateCard.vue's "extra"-slot, alleen op de
// perspectiefpagina (zie PerspectiefView.vue). Eén balk, gesegmenteerd op
// tag-aandeel binnen dit debat, met het tagicoon (tagIcon.ts, dezelfde
// iconen als PerspectiefTagHeatmap.vue) IN elk segment i.p.v. in een aparte
// legenda -- identiteit mag nooit alleen op kleur/hover leunen (dataviz-
// skill: "identity is never color-alone"), en een icoon binnen het segment
// zelf koppelt identiteit direct aan het aandeel, zonder extra vloeroppervlak
// onder de balk. TOP_N=4 (dataviz-skill: "<=4 direct-labeled"), de rest
// samengevoegd tot "overig" -- een perspectief bevat al gauw 15-20 tags
// (config/tags.toml), te veel voor een leesbare balk op kaartbreedte.
//
// Vlakke, uniforme segmentkleur (i.p.v. rangorde-alpha zoals de vorige
// versie): het icoon draagt nu de identiteit, dus kleur hoeft geen rangorde
// meer te coderen -- en een vaste, voldoende donkere tint geeft het
// icoonstroke-wit betrouwbaar contrast op elk segment.
//
// mixWithBase (ondoorzichtig) i.p.v. withAlpha (rgba-transparantie): een
// compacte kaartrij heeft geen eigen kaartachtergrond (staat direct op
// --color-bg), een uitgelichte/uitgebreide kaart wél (--color-card-bg,
// een net iets andere tint) -- dezelfde rgba() zou dus per kaarttype een
// andere kleur opleveren. --color-bg als vaste mengbasis houdt 'm overal
// gelijk.
import { computed } from "vue";
import { mixWithBase } from "../lib/colorShades";

const PAGE_BG = "#f2efe7";
import { tagIconPath } from "../lib/tagIcon";
import type { DebateTagCount } from "../lib/groupByDebate";

const props = defineProps<{
	tagCounts: DebateTagCount[];
	color: string;
	density: "uitgelicht" | "uitgebreid" | "compact";
}>();

const TOP_N = 4;
// Onder deze aandeel-fractie past een 14px-icoon niet meer fatsoenlijk in het
// segment -- dan geen icoon tonen (blijft wel een gekleurd segment + hover).
const MIN_ICON_FRACTIE = 0.08;

const total = computed(() => props.tagCounts.reduce((sum, t) => sum + t.count, 0));

const segments = computed(() => {
	const top = props.tagCounts.slice(0, TOP_N);
	const rest = props.tagCounts.slice(TOP_N);
	const restCount = rest.reduce((sum, t) => sum + t.count, 0);

	const result = top.map((tag) => {
		const fractie = total.value ? tag.count / total.value : 0;
		return {
			key: tag.sleutel,
			label: `${tag.sleutel}: ${tag.count}`,
			width: `${fractie * 100}%`,
			icon: fractie >= MIN_ICON_FRACTIE ? tagIconPath(tag.sleutel) : null,
			background: mixWithBase(props.color, PAGE_BG, 0.15),
			border: mixWithBase(props.color, PAGE_BG, 0.5),
			iconStroke: props.color,
		};
	});
	if (restCount > 0) {
		result.push({
			key: "__overig",
			label: `Overig: ${restCount}`,
			width: total.value ? `${(restCount / total.value) * 100}%` : "0%",
			icon: null,
			// Zelfde lichte-vulling-principe als de tag-segmenten -- anders oogt
			// "overig" bij een groot aandeel als een lege ruimte i.p.v. een segment.
			background: mixWithBase("#6f6558", PAGE_BG, 0.2),
			border: "var(--color-border)",
			iconStroke: props.color,
		});
	}
	return result;
});
</script>

<template>
	<span class="tag-bar-wrap" :class="{ 'tag-bar-wrap--compact': density === 'compact' }">
		<span v-if="segments.length" class="tag-bar" :class="{ 'tag-bar--compact': density === 'compact' }">
			<span
				v-for="segment in segments"
				:key="segment.key"
				class="tag-bar-segment"
				:style="{ width: segment.width, background: segment.background, borderColor: segment.border }"
				:title="segment.label"
			>
				<svg
					v-if="segment.icon"
					class="tag-bar-icon"
					viewBox="0 0 24 24"
					width="14"
					height="14"
					fill="none"
					:stroke="segment.iconStroke"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
				>
					<path :d="segment.icon" />
				</svg>
			</span>
		</span>
		<span v-else class="tag-bar-legend mono">geen tags</span>
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
	margin-top: 0;
}

.tag-bar {
	display: flex;
	height: 22px;
	gap: 2px;
	width: 100%;
}

.tag-bar--compact {
	height: 16px;
}

/* Elk segment een eigen afgeronde vorm + subtiele rand in de
   perspectiefkleur (borderColor komt uit segment.border, inline) -- geen
   vaste kleur hier. */
.tag-bar-segment {
	display: flex;
	align-items: center;
	justify-content: center;
	height: 100%;
	border-radius: 3px;
	border-width: 1px;
	border-style: solid;
	box-sizing: border-box;
	overflow: hidden;
}

.tag-bar-icon {
	flex-shrink: 0;
}

.tag-bar--compact .tag-bar-icon {
	width: 11px;
	height: 11px;
}

.tag-bar-legend {
	display: block;
	font-size: var(--step--1);
	color: var(--color-muted);
}
</style>
