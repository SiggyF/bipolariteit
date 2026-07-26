<script setup lang="ts">
import { computed } from "vue";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { BarChart } from "echarts/charts";
import { TooltipComponent, GridComponent } from "echarts/components";
import { useTheme } from "../lib/useTheme";
import { displayPartyName } from "../lib/parties";

use([CanvasRenderer, BarChart, TooltipComponent, GridComponent]);

interface PartyTagCount {
	party: string;
	tag_count: number;
}

const props = defineProps<{ tagsPerParty: PartyTagCount[] }>();

// Ascending so the biggest party lands nearest the top of ECharts' bottom-up axis.
const rows = computed(() => [...props.tagsPerParty].slice().reverse());

const isDark = useTheme();
const barColor = computed(() => (isDark.value ? "#7d97c4" : "#33456e"));

const chartOption = computed(() => ({
	backgroundColor: "transparent",
	textStyle: { fontFamily: "inherit" },
	tooltip: { trigger: "item" },
	grid: { left: 110, right: 24, top: 8, bottom: 16 },
	xAxis: {
		type: "value",
		axisLabel: { color: isDark.value ? "#a89e8c" : "#6f6558" },
		splitLine: { lineStyle: { color: isDark.value ? "#453f36" : "#ddd5c4" } },
	},
	yAxis: {
		type: "category",
		data: rows.value.map((r) => displayPartyName(r.party)),
		axisLabel: { color: isDark.value ? "#f2ede3" : "#221f1b" },
	},
	series: [
		{
			type: "bar",
			data: rows.value.map((r) => r.tag_count),
			itemStyle: { color: barColor.value },
			barMaxWidth: 22,
		},
	],
}));

const chartHeight = computed(() => `${Math.max(160, rows.value.length * 34 + 24)}px`);
</script>

<template>
	<section class="stats-panel">
		<h2>Aantal tags per partij</h2>
		<p class="panel-note">Alleen LLM-toegekende tags (de 3 automatisch afgeleide labelgroepen tellen hier niet mee).</p>
		<VChart class="party-chart" :option="chartOption" :style="{ height: chartHeight }" autoresize />
	</section>
</template>
