<script setup lang="ts">
import { computed } from "vue";
import { useTheme } from "../lib/useTheme";
import { displayPartyName } from "../lib/parties";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { ScatterChart } from "echarts/charts";
import { TooltipComponent, GridComponent, LegendComponent } from "echarts/components";

use([CanvasRenderer, ScatterChart, TooltipComponent, GridComponent, LegendComponent]);

interface PartyPoint {
	party: string;
	x: number;
	y: number;
	n: number;
}

interface TagPoint {
	sleutel: string;
	beschrijving: string;
	labelgroep: string;
	x: number;
	y: number;
	n: number;
}

interface Correspondence {
	inertia_pct: number[];
	parties: PartyPoint[];
	tags: TagPoint[];
}

const props = defineProps<{ correspondence: Correspondence | null }>();

// Categorical identity colors (dataviz skill, slots 1 + 3) -- deliberately
// distinct from the pro/contra/onduidelijk diverging palette used elsewhere,
// since this map encodes "party vs. tag", not stance.
const COLORS = {
	light: { party: "#33456e", tag: "#a9822f" },
	dark: { party: "#7d97c4", tag: "#c9a54b" },
};

const isDark = useTheme();
const colors = computed(() => (isDark.value ? COLORS.dark : COLORS.light));

const chartOption = computed(() => {
	const c = props.correspondence!;
	const axisLineStyle = { lineStyle: { color: isDark.value ? "#453f36" : "#ddd5c4" } };
	return {
		backgroundColor: "transparent",
		textStyle: { fontFamily: "inherit" },
		tooltip: {
			trigger: "item",
			formatter: (p: any) => {
				if (p.seriesName === "Partijen") return `<strong>${p.data.name}</strong><br/>${p.data.n} tags`;
				return `<strong>${p.data.name}</strong><br/>${p.data.labelgroep}<br/>${p.data.beschrijving}<br/>${p.data.n}x toegekend`;
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
				data: c.parties.map((p) => ({ name: displayPartyName(p.party), value: [p.x, p.y, p.n], n: p.n })),
				itemStyle: { color: colors.value.party },
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
				})),
				itemStyle: { color: colors.value.tag, opacity: 0.75 },
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
			partij voor. Gebaseerd op nog weinig getagde data -- wordt betrouwbaarder naarmate de taggingbatch vordert.
		</p>
		<VChart v-if="correspondence" class="party-chart correspondence-chart" :option="chartOption" autoresize />
		<p v-else class="panel-note">Nog te weinig getagde data voor een zinnige analyse (minimaal 3 partijen en 3 tags met genoeg volume nodig).</p>
	</section>
</template>
