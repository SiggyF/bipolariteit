<script setup lang="ts">
import { computed } from "vue";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { BarChart } from "echarts/charts";
import { TooltipComponent, GridComponent } from "echarts/components";
import { useTheme } from "../lib/useTheme";
import { displayPartyName } from "../lib/parties";
import { deriveTagsPerParty } from "../lib/aggregate";
import { toggleValue } from "../lib/filters";
import type { Argument } from "../lib/types";

use([CanvasRenderer, BarChart, TooltipComponent, GridComponent]);

const props = defineProps<{ argumentList: Argument[] }>();

const tagsPerParty = computed(() => deriveTagsPerParty(props.argumentList));

// Ascending so the biggest party lands nearest the top of ECharts' bottom-up axis.
const rows = computed(() => [...tagsPerParty.value].slice().reverse());

function onChartClick(p: any) {
	const party = rows.value[p.dataIndex]?.party;
	if (party) toggleValue("partij", party);
}

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
			cursor: "pointer",
		},
	],
}));

const chartHeight = computed(() => `${Math.max(160, rows.value.length * 34 + 24)}px`);
</script>

<template>
	<section class="stats-panel">
		<h2>Aantal tags per partij</h2>
		<p class="panel-note">
			Alleen LLM-toegekende tags (de 3 automatisch afgeleide labelgroepen tellen hier niet mee). Klik op een balk om op die
			partij te filteren.
		</p>
		<p v-if="!rows.length" class="panel-note">Geen getagde argumenten in deze selectie.</p>
		<VChart v-else class="party-chart" :option="chartOption" :style="{ height: chartHeight }" autoresize @click="onChartClick" />
	</section>
</template>
