<script setup lang="ts">
import { computed } from "vue";
import { displayPartyName } from "../lib/parties";
import { slugify } from "../lib/slug";
import { tagIconPath } from "../lib/tagIcon";
import { deriveTopPersonsForTag, type PersonTagIndexEntry } from "../lib/aggregate";

export interface TagMeta {
	sleutel: string;
	beschrijving: string;
	labelgroep: string;
}

const props = defineProps<{
	tags: TagMeta[];
	personIndex: Map<string, PersonTagIndexEntry>;
	color: string;
}>();

const rowsPerTag = computed(() =>
	props.tags.map((tag) => ({
		tag,
		personen: deriveTopPersonsForTag(props.personIndex, tag.sleutel),
	})),
);

function verhouding(row: { tagCount: number; total: number }): string {
	return `1 op de ${Math.round(row.total / row.tagCount)}`;
}
</script>

<template>
	<section class="stats-panel">
		<h2>Top 5 personen per tag</h2>
		<p class="panel-note">
			Gerangschikt op aandeel van iemands eigen argumenten (over alle onderwerpen), niet op absoluut aantal -- zo wint niet
			automatisch de meest actieve spreker. Personen met te weinig argumenten of te weinig toekenningen van deze tag blijven
			buiten de lijst; bij die volumes zegt een enkele toekenning te weinig.
		</p>
		<div v-for="{ tag, personen } in rowsPerTag" :key="tag.sleutel" class="tag-persons-block">
			<h3 class="tag-persons-heading">
				<svg
					v-if="tagIconPath(tag.sleutel)"
					viewBox="0 0 24 24"
					width="18"
					height="18"
					fill="none"
					:stroke="color"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
				>
					<path :d="tagIconPath(tag.sleutel)!" />
				</svg>
				{{ tag.sleutel }}
			</h3>
			<p class="panel-note">{{ tag.beschrijving }}</p>
			<ol v-if="personen.length" class="top-persons-list">
				<li v-for="row in personen" :key="row.person">
					<a :href="`/persoon/${slugify(row.person)}/`">{{ row.person }}</a>
					<span v-if="row.party" class="topic-count">({{ displayPartyName(row.party) }})</span>
					<span class="topic-count">{{ verhouding(row) }} argumenten ({{ row.tagCount }} van {{ row.total }})</span>
				</li>
			</ol>
			<p v-else class="panel-note">Te weinig volume voor een zinnige ranglijst.</p>
		</div>
	</section>
</template>
