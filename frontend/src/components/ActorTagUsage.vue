<script setup lang="ts">
import { computed } from "vue";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { BarChart } from "echarts/charts";
import { TooltipComponent, GridComponent } from "echarts/components";
import { useTheme } from "../lib/useTheme";
import { displayPartyName } from "../lib/parties";
import { deriveTagUsage, bucketSmallCounts } from "../lib/aggregate";
import PartyLogo from "./PartyLogo.vue";
import ArgumentCard from "./ArgumentCard.vue";
import type { Argument } from "../lib/types";

use([CanvasRenderer, BarChart, TooltipComponent, GridComponent]);

export interface TopicTaggedArgument extends Argument {
	topicSlug: string;
	topicName: string;
}

const props = defineProps<{
	name: string;
	mode: "partij" | "persoon";
	argumentList: TopicTaggedArgument[];
}>();

// Zie issue #5: bij deze taggingvolumes heeft een individuele spreker vaak
// maar 1-3 toekenningen van een tag. Op persoonsniveau vouwen we die samen
// i.p.v. ze als ranglijst te tonen -- op partijniveau is het volume hoog
// genoeg dat dat niet nodig is.
const PERSON_TAG_THRESHOLD = 3;

const tagRows = computed(() => {
	const rows = deriveTagUsage(props.argumentList);
	return props.mode === "persoon" ? bucketSmallCounts(rows, PERSON_TAG_THRESHOLD) : rows;
});

// Ascending so the biggest bar lands nearest the top of ECharts' bottom-up axis.
const chartRows = computed(() => [...tagRows.value].reverse());

const isDark = useTheme();
const barColor = computed(() => (isDark.value ? "#7d97c4" : "#33456e"));

const chartOption = computed(() => ({
	backgroundColor: "transparent",
	textStyle: { fontFamily: "inherit" },
	tooltip: { trigger: "item" },
	grid: { left: 90, right: 24, top: 8, bottom: 16 },
	xAxis: {
		type: "value",
		axisLabel: { color: isDark.value ? "#a89e8c" : "#6f6558" },
		splitLine: { lineStyle: { color: isDark.value ? "#453f36" : "#ddd5c4" } },
	},
	yAxis: {
		type: "category",
		data: chartRows.value.map((r) => r.sleutel),
		axisLabel: { color: isDark.value ? "#f2ede3" : "#221f1b" },
	},
	series: [
		{
			type: "bar",
			data: chartRows.value.map((r) => r.count),
			itemStyle: { color: barColor.value },
			barMaxWidth: 22,
		},
	],
}));

const chartHeight = computed(() => `${Math.max(160, chartRows.value.length * 28 + 24)}px`);

const totalArguments = computed(() => props.argumentList.length);

const perTopic = computed(() => {
	const byTopic = new Map<string, { topicSlug: string; topicName: string; count: number }>();
	for (const argument of props.argumentList) {
		const existing = byTopic.get(argument.topicSlug);
		if (existing) existing.count += 1;
		else byTopic.set(argument.topicSlug, { topicSlug: argument.topicSlug, topicName: argument.topicName, count: 1 });
	}
	return [...byTopic.values()].sort((a, b) => b.count - a.count);
});

function topicLink(topicSlug: string): string {
	const param = props.mode === "partij" ? "partij" : "persoon";
	return `/topics/${topicSlug}/?${param}=${encodeURIComponent(props.name)}`;
}

const exampleArguments = computed(() =>
	[...props.argumentList]
		.sort((a, b) => (b.document.published_at ?? "").localeCompare(a.document.published_at ?? ""))
		.slice(0, 5),
);
</script>

<template>
	<section class="actor-tag-usage">
		<header class="actor-header">
			<PartyLogo v-if="mode === 'partij'" :party="name" />
			<h1>{{ mode === "partij" ? displayPartyName(name) : name }}</h1>
		</header>
		<p class="panel-note">{{ totalArguments }} argumenten in totaal, over {{ perTopic.length }} onderwerp(en).</p>

		<section class="stats-panel">
			<h2>Tags</h2>
			<p class="panel-note">
				Alleen LLM-toegekende tags.
				<template v-if="mode === 'persoon'">
					Tags met minder dan {{ PERSON_TAG_THRESHOLD }} toekenningen zijn samengevoegd tot "overig" -- bij deze
					volumes zegt een enkele toekenning weinig.
				</template>
			</p>
			<p v-if="!tagRows.length" class="panel-note">Geen getagde argumenten.</p>
			<VChart v-else class="tag-usage-chart" :option="chartOption" :style="{ height: chartHeight }" autoresize />
		</section>

		<section class="stats-panel">
			<h2>Per onderwerp</h2>
			<ul class="topic-breakdown">
				<li v-for="topic in perTopic" :key="topic.topicSlug">
					<a :href="topicLink(topic.topicSlug)">{{ topic.topicName }}</a>
					<span class="topic-count">{{ topic.count }} argumenten</span>
				</li>
			</ul>
		</section>

		<section class="stats-panel">
			<h2>Voorbeeldargumenten</h2>
			<ArgumentCard v-for="argument in exampleArguments" :key="argument.id" :argument="argument" :topic-slug="argument.topicSlug" />
		</section>
	</section>
</template>
