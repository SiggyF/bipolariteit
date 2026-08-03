<script setup lang="ts">
import { computed } from "vue";
import { displayPartyName } from "../lib/parties";
import { slugify } from "../lib/slug";
import { tagIconPath } from "../lib/tagIcon";
import {
	derivePartyTagIndex,
	derivePersonTagIndex,
	deriveTopPersonsForTag,
	filterArgumentsByTag,
} from "../lib/aggregate";
import ArgumentCard from "./ArgumentCard.vue";
import type { Argument } from "../lib/types";

export interface TopicTaggedArgument extends Argument {
	topicSlug: string;
	topicName: string;
}

const props = defineProps<{
	sleutel: string;
	beschrijving: string;
	labelgroep: string;
	perspectief: string;
	deterministic: boolean;
	argumentList: TopicTaggedArgument[];
}>();

// Zelfde ondergrens als PerspectiefTagHeatmap.vue/aggregate.ts: onder dit
// partijtotaal is een percentage schijnnauwkeurig.
const MIN_PARTY_TOTAL = 8;

const taggedArguments = computed(() => filterArgumentsByTag(props.argumentList, props.sleutel));

const partyRows = computed(() => {
	if (props.deterministic) return [];
	const index = derivePartyTagIndex(props.argumentList);
	const rows: { party: string; count: number; total: number; pct: number }[] = [];
	for (const entry of index.values()) {
		if (entry.total < MIN_PARTY_TOTAL) continue;
		const count = entry.tagCounts.get(props.sleutel) ?? 0;
		if (!count) continue;
		rows.push({ party: entry.party, count, total: entry.total, pct: (count / entry.total) * 100 });
	}
	rows.sort((a, b) => b.pct - a.pct);
	return rows;
});

const topPersons = computed(() => {
	if (props.deterministic) return [];
	return deriveTopPersonsForTag(derivePersonTagIndex(props.argumentList), props.sleutel);
});

const perTopic = computed(() => {
	const byTopic = new Map<string, { topicSlug: string; topicName: string; count: number }>();
	for (const argument of taggedArguments.value) {
		const existing = byTopic.get(argument.topicSlug);
		if (existing) existing.count += 1;
		else byTopic.set(argument.topicSlug, { topicSlug: argument.topicSlug, topicName: argument.topicName, count: 1 });
	}
	return [...byTopic.values()].sort((a, b) => b.count - a.count);
});

const exampleArguments = computed(() =>
	[...taggedArguments.value]
		.sort((a, b) => (b.document.published_at ?? "").localeCompare(a.document.published_at ?? ""))
		.slice(0, 5),
);

function topicLink(topicSlug: string): string {
	return `/topics/${topicSlug}/?tag=${encodeURIComponent(props.sleutel)}`;
}

function verhouding(row: { tagCount: number; total: number }): string {
	return `1 op de ${Math.round(row.total / row.tagCount)}`;
}
</script>

<template>
	<section class="tag-detail">
		<header class="actor-header">
			<svg
				v-if="tagIconPath(sleutel)"
				viewBox="0 0 24 24"
				width="28"
				height="28"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round"
			>
				<path :d="tagIconPath(sleutel)!" />
			</svg>
			<h1>{{ sleutel }}</h1>
		</header>
		<p class="panel-note">{{ beschrijving }}</p>
		<p class="panel-note">
			{{ labelgroep }} &middot;
			<a :href="`/perspectief/${slugify(perspectief)}/`">{{ perspectief }}</a>
		</p>
		<p v-if="deterministic" class="panel-note">
			Deze tag wordt automatisch (deterministisch) toegekend, niet door het LLM. Bij TK-data is dat vrijwel altijd
			hetzelfde voor elk argument binnen een onderwerp, dus draagt de tag geen onderscheidend signaal tussen
			partijen of personen -- daarom geen partij-/persoonranglijst hieronder.
		</p>

		<p v-if="!taggedArguments.length" class="no-results">Nog geen argumenten met deze tag.</p>

		<template v-else>
			<p class="panel-note">{{ taggedArguments.length }} toekenningen, over {{ perTopic.length }} onderwerp(en).</p>

			<section v-if="!deterministic" class="stats-panel">
				<h2>Per partij</h2>
				<p class="panel-note">
					Percentage van de argumenten van een partij waarin deze tag voorkomt. Partijen met minder dan
					{{ MIN_PARTY_TOTAL }} argumenten (over alle onderwerpen) blijven buiten de lijst.
				</p>
				<p v-if="!partyRows.length" class="panel-note">Te weinig volume voor een zinnige uitsplitsing per partij.</p>
				<ul v-else class="topic-breakdown">
					<li v-for="row in partyRows" :key="row.party">
						<a :href="`/partij/${slugify(row.party)}/`">{{ displayPartyName(row.party) }}</a>
						<span class="topic-count">{{ Math.round(row.pct) }}% ({{ row.count }} van {{ row.total }})</span>
					</li>
				</ul>
			</section>

			<section v-if="!deterministic" class="stats-panel">
				<h2>Per persoon</h2>
				<p class="panel-note">
					Gerangschikt op aandeel van iemands eigen argumenten (over alle onderwerpen), niet op absoluut aantal.
					Personen met te weinig argumenten of te weinig toekenningen van deze tag blijven buiten de lijst.
				</p>
				<ol v-if="topPersons.length" class="top-persons-list">
					<li v-for="row in topPersons" :key="row.person">
						<a :href="`/persoon/${slugify(row.person)}/`">{{ row.person }}</a>
						<span v-if="row.party" class="topic-count">({{ displayPartyName(row.party) }})</span>
						<span class="topic-count">{{ verhouding(row) }} argumenten ({{ row.tagCount }} van {{ row.total }})</span>
					</li>
				</ol>
				<p v-else class="panel-note">Te weinig volume voor een zinnige ranglijst.</p>
			</section>

			<section class="stats-panel">
				<h2>Per onderwerp</h2>
				<ul class="card-grid">
					<li v-for="topic in perTopic" :key="topic.topicSlug">
						<a :href="topicLink(topic.topicSlug)" class="card-tile">
							<span class="card-tile-name">{{ topic.topicName }}</span>
							<span class="card-tile-count">{{ topic.count }} argumenten</span>
						</a>
					</li>
				</ul>
			</section>

			<section class="stats-panel">
				<h2>Voorbeeldargumenten</h2>
				<ArgumentCard
					v-for="argument in exampleArguments"
					:key="argument.id"
					:argument="argument"
					:topic-slug="argument.topicSlug"
				/>
			</section>
		</template>
	</section>
</template>
