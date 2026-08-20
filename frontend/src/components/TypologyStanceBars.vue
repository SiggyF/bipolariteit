<script setup lang="ts">
import { computed } from "vue";
import { countByTypologyAndStance } from "../lib/aggregate";
import { typologyLabel } from "../lib/types";
import type { Argument } from "../lib/types";

// Platte HTML/CSS, bewust geen ECharts-island (issue #137): werkt zonder JS
// en schaalt van 320px tot desktop zonder een aparte mobiele variant nodig te
// hebben.
const props = defineProps<{ argumentList: Argument[] }>();

const rows = computed(() => countByTypologyAndStance(props.argumentList));

// Eén gedeelde schaal voor alle rijen (niet per rij op het eigen totaal), zodat
// de balklengte tussen typologieën onderling vergelijkbaar blijft -- een
// typologie met weinig argumenten moet ook zichtbaar korte balken krijgen,
// niet een balk die tot de rand van zijn eigen rij is opgerekt.
const maxCount = computed(() => Math.max(1, ...rows.value.map((r) => Math.max(r.pro, r.contra))));

// Tot 92% i.p.v. 100%: het aantal staat vlak na de balk, in dezelfde
// flex-rij (zie template) -- bij de langste balk moet daar nog ruimte voor
// overblijven, anders duwt de tekst zichzelf de kolom uit.
function widthPct(n: number): number {
	return (n / maxCount.value) * 92;
}
</script>

<template>
	<section class="stats-panel">
		<h2>Argumenttypes <span class="panel-scope">(pro/contra per typologie)</span></h2>

		<ul class="chart-legend">
			<li><span class="legend-swatch" style="background: var(--color-pro)"></span>Pro</li>
			<li><span class="legend-swatch" style="background: var(--color-contra)"></span>Contra</li>
		</ul>

		<ul class="typology-bars">
			<li v-for="row in rows" :key="row.typology" class="typology-bar-row">
				<div class="typology-bar-track typology-bar-track-contra">
					<span class="typology-bar-value">{{ row.contra }}</span>
					<div class="typology-bar-fill typology-bar-fill-contra" :style="{ width: `${widthPct(row.contra)}%` }"></div>
				</div>

				<span class="typology-bar-name">
					{{ typologyLabel(row.typology) }}
					<span class="typology-bar-total">{{ row.total }}</span>
				</span>

				<div class="typology-bar-track typology-bar-track-pro">
					<div class="typology-bar-fill typology-bar-fill-pro" :style="{ width: `${widthPct(row.pro)}%` }"></div>
					<span class="typology-bar-value">{{ row.pro }}</span>
				</div>
			</li>
		</ul>
	</section>
</template>
