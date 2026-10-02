<script setup lang="ts">
import { computed } from "vue";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import "../lib/echartsSetup";
import { SVGRenderer } from "echarts/renderers";
import { BarChart } from "echarts/charts";
import { TooltipComponent, GridComponent, MarkLineComponent } from "echarts/components";
import PartyLogo from "./PartyLogo.vue";
import StandpuntGlyph from "./StandpuntGlyph.vue";
import { useTheme } from "../lib/useTheme";
import { displayPartyName } from "../lib/parties";
import { deriveStats } from "../lib/aggregate";
import { toggleValue } from "../lib/filters";
import { gespiegeldeStandpuntBalk, themaNaam } from "../lib/vloeiChart";
import type { Argument } from "../lib/types";

use([SVGRenderer, BarChart, TooltipComponent, GridComponent, MarkLineComponent]);

// Rekent op de al gefilterde lijst: filter je op één partij, dan gaat deze
// grafiek daarin mee in plaats van corpus-brede cijfers te blijven tonen naast
// een gefilterde kolom.
const props = defineProps<{ argumentList: Argument[] }>();

const stats = computed(() => deriveStats(props.argumentList));

const isDark = useTheme();

// stats.by_party staat al aflopend op pro_pct, en met inverse: true op de
// categorie-as (gespiegeldeStandpuntBalk) komt de eerste rij bovenaan -- geen
// .reverse() meer nodig.
const parties = computed(() => stats.value.by_party);

const chartOption = computed(() =>
	gespiegeldeStandpuntBalk(
		parties.value.map((p) => ({ naam: displayPartyName(p.party), pro: p.pro, contra: p.contra, onduidelijk: p.unclear })),
		{ modus: isDark.value ? "dark" : "light", eenheid: "procent", toonN: true },
	),
);

// Klik op een balksegment: dataIndex komt overeen met de rij-volgorde in
// parties.value (elke reeks van gespiegeldeStandpuntBalk deelt die volgorde).
function onChartClick(p: any) {
	const idx = p.dataIndex as number | undefined;
	if (idx === undefined) return;
	const party = parties.value[idx]?.party;
	if (!party) return;
	toggleValue("partij", party);
}

// Partijnaam op de as-labels: ECharts' `axisLabel.triggerEvent` vuurt geen
// klik voor categorie-as-labels onder de SVG-renderer (bevestigd op een
// minimale, niet-custom-series repro op echarts 6.1.0 -- een echarts-
// beperking, niet iets specifieks voor deze grafiek). SVGRenderer geeft wel
// echte <text>-DOM-nodes, dus die matchen we rechtstreeks i.p.v. via
// ECharts' eigen event-systeem. Het label bevat nu ook "n=…" (rich text),
// dus startsWith i.p.v. een exacte match.
function onChartWrapperClick(e: MouseEvent) {
	const target = e.target as Element;
	if (!(target instanceof SVGTextElement)) return;
	const text = target.textContent?.trim();
	if (!text) return;
	const match = parties.value.find((p) => text.startsWith(displayPartyName(p.party)));
	if (match) toggleValue("partij", match.party);
}

const chartHeight = computed(() => `${Math.max(200, parties.value.length * 42 + 32)}px`);
</script>

<template>
	<section class="stats-panel">
		<h2>Statistieken per partij <span class="panel-scope">({{ stats.overall.total }} argumenten in selectie)</span></h2>

		<div class="vl-grafiek">
			<ul class="vl-legenda is-gespiegeld">
				<li><StandpuntGlyph stance="pro" /><span class="aantal">{{ stats.overall.pro }}</span></li>
				<li><StandpuntGlyph stance="unclear" /><span class="aantal">{{ stats.overall.unclear }}</span></li>
				<li><span class="aantal">{{ stats.overall.contra }}</span><StandpuntGlyph stance="contra" /></li>
			</ul>

			<p class="panel-note">Klik op een balk of partijnaam om op die partij te filteren.</p>

			<div class="clickable-chart" @click="onChartWrapperClick">
				<VChart
					class="party-chart"
					:option="chartOption"
					:theme="themaNaam(isDark)"
					:init-options="{ renderer: 'svg' }"
					:style="{ height: chartHeight }"
					autoresize
					@click="onChartClick"
				/>
			</div>
		</div>

		<div class="table-scroll">
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
							<PartyLogo :party="party.party" />
							{{ displayPartyName(party.party) }}
						</td>
						<td>{{ party.total }}</td>
						<td>{{ party.pro_pct }}% ({{ party.pro }})</td>
						<td>{{ party.contra_pct }}% ({{ party.contra }})</td>
						<td>{{ party.unclear_pct }}% ({{ party.unclear }})</td>
					</tr>
				</tbody>
			</table>
		</div>
	</section>
</template>
