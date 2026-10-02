<script setup lang="ts">
import { computed } from "vue";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import "../lib/echartsSetup";
import { CanvasRenderer } from "echarts/renderers";
import { BarChart } from "echarts/charts";
import { TooltipComponent, GridComponent } from "echarts/components";
import { useTheme } from "../lib/useTheme";
import { displayPartyName } from "../lib/parties";
import { deriveTagsPerParty } from "../lib/aggregate";
import { toggleValue } from "../lib/filters";
import { themaNaam } from "../lib/vloeiChart";
import type { Argument } from "../lib/types";

use([CanvasRenderer, BarChart, TooltipComponent, GridComponent]);

const props = defineProps<{ argumentList: Argument[] }>();

const tagsPerParty = computed(() => deriveTagsPerParty(props.argumentList));

const rows = computed(() => [...tagsPerParty.value]);

function onChartClick(p: any) {
	const party = rows.value[p.dataIndex]?.party;
	if (party) toggleValue("partij", party);
}

const isDark = useTheme();

const chartOption = computed(() => ({
	grid: { left: 110, right: 40, top: 8, bottom: 16 },
	xAxis: { type: "value" },
	yAxis: {
		type: "category",
		inverse: true,
		data: rows.value.map((r) => displayPartyName(r.party)),
	},
	series: [
		{
			type: "bar",
			data: rows.value.map((r) => r.tag_count),
			label: { show: true, position: "right" },
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
		<div v-else class="vl-grafiek">
			<VChart
				class="party-chart"
				:option="chartOption"
				:theme="themaNaam(isDark)"
				:style="{ height: chartHeight }"
				autoresize
				@click="onChartClick"
			/>
		</div>
	</section>
</template>
