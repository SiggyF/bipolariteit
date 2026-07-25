<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from "vue";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { BarChart } from "echarts/charts";
import { TooltipComponent, GridComponent } from "echarts/components";
import { partyLogo } from "../lib/parties";

use([CanvasRenderer, BarChart, TooltipComponent, GridComponent]);

interface PartyTagCount {
	party: string;
	tag_count: number;
}

const props = defineProps<{ tagsPerParty: PartyTagCount[] }>();

const isDark = ref(false);
let mql: MediaQueryList | undefined;
const updateDark = () => {
	isDark.value = document.documentElement.getAttribute("data-theme") === "dark" || (mql?.matches ?? false);
};
onMounted(() => {
	mql = window.matchMedia("(prefers-color-scheme: dark)");
	mql.addEventListener("change", updateDark);
	updateDark();
});
onUnmounted(() => mql?.removeEventListener("change", updateDark));

// Ascending so the biggest party lands nearest the top of ECharts' bottom-up axis.
const rows = computed(() => [...props.tagsPerParty].slice().reverse());

const barColor = computed(() => (isDark.value ? "#3987e5" : "#2a78d6"));

const chartOption = computed(() => ({
	backgroundColor: "transparent",
	textStyle: { fontFamily: "inherit" },
	tooltip: { trigger: "item" },
	grid: { left: 110, right: 24, top: 8, bottom: 16 },
	xAxis: {
		type: "value",
		axisLabel: { color: isDark.value ? "#a8a29e" : "#78716c" },
		splitLine: { lineStyle: { color: isDark.value ? "#44403c" : "#e7e5e4" } },
	},
	yAxis: {
		type: "category",
		data: rows.value.map((r) => r.party),
		axisLabel: { color: isDark.value ? "#f5f5f4" : "#1c1917" },
	},
	series: [
		{
			type: "bar",
			data: rows.value.map((r) => r.tag_count),
			itemStyle: { color: barColor.value, borderRadius: [0, 3, 3, 0] },
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
