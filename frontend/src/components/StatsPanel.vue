<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from "vue";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { CustomChart } from "echarts/charts";
import { TooltipComponent, GridComponent } from "echarts/components";
import { partyLogo } from "../lib/parties";

use([CanvasRenderer, CustomChart, TooltipComponent, GridComponent]);

interface StanceCounts {
	total: number;
	pro: number;
	contra: number;
	unclear: number;
	pro_pct: number;
	contra_pct: number;
	unclear_pct: number;
}

interface PartyStats extends StanceCounts {
	party: string;
}

interface Stats {
	overall: StanceCounts;
	by_party: PartyStats[];
}

const props = defineProps<{ stats: Stats }>();

// Diverging pair (dataviz skill: polarity = two hues + neutral midpoint).
// pro = blue, contra = red, unclear = neutral gray -- light/dark validated steps.
const COLORS = {
	light: { pro: "#2a78d6", contra: "#e34948", unclear: "#a8a29e" },
	dark: { pro: "#3987e5", contra: "#e66767", unclear: "#78716c" },
};

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
onUnmounted(() => {
	mql?.removeEventListener("change", updateDark);
});

const colors = computed(() => (isDark.value ? COLORS.dark : COLORS.light));

// Sorted ascending so the biggest party ends up nearest the top in ECharts'
// bottom-up category axis.
const parties = computed(() => [...props.stats.by_party].slice().reverse());

// Bar thickness reflects how many arguments a party has -- sqrt scale so a
// party with 10x the arguments doesn't get a 10x-thick bar, just visibly
// more. Ratio 0..1, applied against the category band height at render time
// so bars always stay centered on their axis tick (see renderItem below) --
// a plain per-series barWidth broke that centering, hence the custom series.
const thicknessRatios = computed(() => {
	const totals = parties.value.map((p) => p.total);
	const minTotal = Math.min(...totals);
	const maxTotal = Math.max(...totals);
	if (minTotal === maxTotal) return totals.map(() => 0.6);
	const sqrtMin = Math.sqrt(minTotal);
	const sqrtMax = Math.sqrt(maxTotal);
	return totals.map((t) => {
		const ratio = (Math.sqrt(t) - sqrtMin) / (sqrtMax - sqrtMin);
		return 0.25 + ratio * 0.55; // keep a visible minimum, cap below the full band
	});
});

// Shared per-row data so each of the three segment-series can compute its
// own slice's pixel boundaries independent of the others.
const rowData = computed(() =>
	parties.value.map((p, i) => [i, p.pro_pct, p.contra_pct, p.unclear_pct, thicknessRatios.value[i], p.pro, p.contra, p.unclear]),
);

function makeSegmentSeries(segment: "pro" | "contra" | "unclear", color: string, label: string) {
	return {
		type: "custom",
		data: rowData.value,
		encode: { x: [1, 2, 3], y: 0 },
		renderItem(_params: any, api: any) {
			const idx = api.value(0) as number;
			const proPct = api.value(1) as number;
			const contraPct = api.value(2) as number;
			const unclearPct = api.value(3) as number;
			const thicknessRatio = api.value(4) as number;

			const start = segment === "pro" ? 0 : segment === "contra" ? proPct : proPct + contraPct;
			const value = segment === "pro" ? proPct : segment === "contra" ? contraPct : unclearPct;
			if (!value) return undefined;
			const end = start + value;

			const y = api.coord([0, idx])[1];
			const bandHeight = api.size!([0, 1])[1] as number;
			const barHeight = Math.max(6, bandHeight * thicknessRatio);
			const x0 = api.coord([start, idx])[0];
			const x1 = api.coord([end, idx])[0];

			return {
				type: "rect",
				shape: { x: x0, y: y - barHeight / 2, width: x1 - x0, height: barHeight },
				style: { fill: color },
			};
		},
		tooltip: {
			formatter: (p: any) => {
				const [, , , , , pro, contra, unclear] = p.value as number[];
				const raw = { pro, contra, unclear }[segment];
				const pct = { pro: p.value[1], contra: p.value[2], unclear: p.value[3] }[segment];
				return `${label}: ${pct}% (${raw})`;
			},
		},
	};
}

const chartOption = computed(() => ({
	backgroundColor: "transparent",
	textStyle: { fontFamily: "inherit" },
	tooltip: { trigger: "item" },
	grid: { left: 110, right: 24, top: 16, bottom: 16 },
	xAxis: {
		type: "value",
		max: 100,
		axisLabel: { formatter: "{value}%", color: isDark.value ? "#a8a29e" : "#78716c" },
		splitLine: { lineStyle: { color: isDark.value ? "#44403c" : "#e7e5e4" } },
	},
	yAxis: {
		type: "category",
		data: parties.value.map((p) => p.party),
		axisLabel: { color: isDark.value ? "#f5f5f4" : "#1c1917" },
	},
	series: [
		makeSegmentSeries("pro", colors.value.pro, "Pro"),
		makeSegmentSeries("contra", colors.value.contra, "Contra"),
		makeSegmentSeries("unclear", colors.value.unclear, "Onduidelijk"),
	],
}));

const chartHeight = computed(() => `${Math.max(200, parties.value.length * 42 + 32)}px`);
</script>

<template>
	<section class="stats-panel">
		<h2>Statistieken per partij</h2>

		<ul class="chart-legend">
			<li><span class="legend-swatch" :style="{ background: colors.pro }"></span>Pro</li>
			<li><span class="legend-swatch" :style="{ background: colors.contra }"></span>Contra</li>
			<li><span class="legend-swatch" :style="{ background: colors.unclear }"></span>Onduidelijk</li>
		</ul>

		<VChart class="party-chart" :option="chartOption" :style="{ height: chartHeight }" autoresize />

		<table class="party-table">
			<caption class="visually-hidden">Argumenten per partij, met aantallen naast de percentages uit de grafiek</caption>
			<thead>
				<tr>
					<th>Partij</th>
					<th>Argumenten</th>
					<th>Pro</th>
					<th>Contra</th>
					<th>Onduidelijk</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="party in stats.by_party" :key="party.party">
					<td class="party-cell">
						<img v-if="partyLogo(party.party)" :src="partyLogo(party.party)!" :alt="party.party" class="party-logo" />
						{{ party.party }}
					</td>
					<td>{{ party.total }}</td>
					<td>{{ party.pro_pct }}% ({{ party.pro }})</td>
					<td>{{ party.contra_pct }}% ({{ party.contra }})</td>
					<td>{{ party.unclear_pct }}% ({{ party.unclear }})</td>
				</tr>
			</tbody>
		</table>
	</section>
</template>
