<script setup lang="ts">
import { computed } from "vue";
import { useTheme } from "../lib/useTheme";
import { displayPartyName } from "../lib/parties";
import { filters, toggleValue } from "../lib/filters";
import { NO_PARTY, type Argument, type Correspondence } from "../lib/types";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { ScatterChart } from "echarts/charts";
import { TooltipComponent, GridComponent, LegendComponent } from "echarts/components";

use([CanvasRenderer, ScatterChart, TooltipComponent, GridComponent, LegendComponent]);

// De kaart zelf is corpus-breed en wordt server-side berekend (prince). Bij een
// actief filter herberekenen we 'm dus niet, maar markeren we welke punten nog
// in de selectie voorkomen -- alles daarbuiten dimt. Client-side herberekenen
// (en daarmee een echt gefilterde analyse) staat in #3.
const props = defineProps<{ correspondence: Correspondence | null; argumentList: Argument[] }>();

const partiesInSelection = computed(() => new Set(props.argumentList.map((a) => a.actor.party ?? NO_PARTY)));
const tagsInSelection = computed(() => new Set(props.argumentList.flatMap((a) => a.tags.map((t) => t.sleutel))));

// Zonder filter zit elk punt in de selectie, dus dan dimt er vanzelf niets --
// geen aparte "is er gefilterd?"-vlag nodig.
const DIMMED_OPACITY = 0.15;

function partyOpacity(party: string): number {
	return partiesInSelection.value.has(party) ? 1 : DIMMED_OPACITY;
}

function tagOpacity(sleutel: string): number {
	return tagsInSelection.value.has(sleutel) ? 0.75 : DIMMED_OPACITY;
}

// Categorical identity colors (dataviz skill, slots 1 + 3) -- deliberately
// distinct from the pro/contra/onduidelijk diverging palette used elsewhere,
// since this map encodes "party vs. tag", not stance.
const COLORS = {
	light: { party: "#33456e", tag: "#a9822f" },
	dark: { party: "#7d97c4", tag: "#c9a54b" },
};

const isDark = useTheme();
const colors = computed(() => (isDark.value ? COLORS.dark : COLORS.light));
function onChartClick(p: any) {
	if (p.seriesName === "Tags") toggleValue("tag", p.data.name);
	else if (p.seriesName === "Partijen") toggleValue("partij", p.data.party);
}

const chartOption = computed(() => {
	const c = props.correspondence!;
	const axisLineStyle = { lineStyle: { color: isDark.value ? "#453f36" : "#ddd5c4" } };
	return {
		backgroundColor: "transparent",
		textStyle: { fontFamily: "inherit" },
		tooltip: {
			trigger: "item",
			extraCssText: "max-width: 220px; white-space: normal; line-height: 1.35;",
			formatter: (p: any) => {
				if (p.seriesName === "Partijen") return `<strong>${p.data.name}</strong><br/>${p.data.n} tags`;
				return `<strong>${p.data.name}</strong><br/><span style="opacity:0.7">${p.data.labelgroep}</span><br/>${p.data.beschrijving}<br/><span style="opacity:0.7">${p.data.n}x toegekend</span>`;
			},
		},
		legend: {
			data: ["Partijen", "Tags"],
			top: 0,
			textStyle: { color: isDark.value ? "#f2ede3" : "#221f1b" },
		},
		grid: { left: 40, right: 24, top: 40, bottom: 40 },
		xAxis: {
			type: "value",
			name: `dim 1 (${c.inertia_pct[0]}%)`,
			nameLocation: "middle",
			nameGap: 28,
			axisLine: { show: true, ...axisLineStyle },
			splitLine: axisLineStyle,
			axisLabel: { show: false },
			nameTextStyle: { color: isDark.value ? "#a89e8c" : "#6f6558" },
		},
		yAxis: {
			type: "value",
			name: `dim 2 (${c.inertia_pct[1]}%)`,
			axisLine: { show: true, ...axisLineStyle },
			splitLine: axisLineStyle,
			axisLabel: { show: false },
			nameTextStyle: { color: isDark.value ? "#a89e8c" : "#6f6558" },
		},
		series: [
			{
				name: "Partijen",
				type: "scatter",
				symbolSize: (val: number[]) => Math.max(14, Math.min(40, Math.sqrt(val[2]) * 6)),
				data: c.parties.map((p) => ({
					name: displayPartyName(p.party),
					party: p.party,
					value: [p.x, p.y, p.n],
					n: p.n,
					itemStyle: { color: colors.value.party, opacity: partyOpacity(p.party) },
				})),
				cursor: "pointer",
				label: {
					show: true,
					formatter: "{b}",
					position: "top",
					color: isDark.value ? "#f2ede3" : "#221f1b",
					fontSize: 11,
					fontWeight: 600,
				},
			},
			{
				name: "Tags",
				type: "scatter",
				symbolSize: (val: number[]) => Math.max(6, Math.min(20, Math.sqrt(val[2]) * 3)),
				data: c.tags.map((t) => ({
					name: t.sleutel,
					value: [t.x, t.y, t.n],
					n: t.n,
					beschrijving: t.beschrijving,
					labelgroep: t.labelgroep,
					itemStyle: { color: colors.value.tag, opacity: tagOpacity(t.sleutel) },
				})),
				cursor: "pointer",
				label: {
					show: true,
					formatter: "{b}",
					position: "top",
					color: isDark.value ? "#a89e8c" : "#6f6558",
					fontSize: 9,
				},
			},
		],
	};
});
</script>

<template>
	<section class="stats-panel">
		<h2>Partijen &amp; tags (correspondentieanalyse)</h2>
		<p class="panel-note">
			Partijen dicht bij elkaar gebruiken vergelijkbare soorten argumenten; een tag dicht bij een partij komt relatief vaak bij die
			partij voor. Gebaseerd op nog weinig getagde data -- wordt betrouwbaarder naarmate de taggingbatch vordert. Klik op een tag
			of partij om erop te filteren.
		</p>
		<p class="panel-note">
			Deze analyse is corpus-breed berekend en wordt <em>niet</em> herberekend op je selectie; punten die buiten de selectie
			vallen worden gedimd.
		</p>
		<VChart
			v-if="correspondence"
			class="party-chart correspondence-chart"
			:option="chartOption"
			autoresize
			@click="onChartClick"
		/>
		<p v-else class="panel-note">Nog te weinig getagde data voor een zinnige analyse (minimaal 3 partijen en 3 tags met genoeg volume nodig).</p>
	</section>
</template>
