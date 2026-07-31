<script setup lang="ts">
import { computed } from "vue";
import { displayPartyName } from "../lib/parties";
import { toggleValue } from "../lib/filters";
import { tagIconPath } from "../lib/tagIcon";
import { withAlpha } from "../lib/colorShades";
import type { PartyTagIndexEntry } from "../lib/aggregate";
import type { TagMeta } from "./TopPersonsPerTag.vue";

const props = defineProps<{
	tags: TagMeta[];
	partyIndex: Map<string, PartyTagIndexEntry>;
	color: string;
}>();

// Onder dit totaal is een percentage schijnnauwkeurig -- zelfde ondergrens als
// de top-5-per-tag-lijst eronder (DEFAULT_MIN_TOTAL in aggregate.ts), voor
// dezelfde reden: een partij met 5 argumenten waarvan 2 met deze tag zou 40%
// tonen alsof dat een gemeten aandeel is i.p.v. bijna toeval.
const MIN_TOTAL = 8;

const rows = computed(() =>
	[...props.partyIndex.values()].filter((e) => e.total >= MIN_TOTAL).sort((a, b) => b.total - a.total),
);

function pct(row: PartyTagIndexEntry, sleutel: string): number {
	return row.total ? ((row.tagCounts.get(sleutel) ?? 0) / row.total) * 100 : 0;
}

// Dekking i.p.v. tint schaalt op de hoogste waarde in de hele tabel, niet per
// rij/kolom -- anders zou de spaarzaamste combinatie er via zelfschaling
// even fel uitzien als de meest gebruikte, en dat is precies het contrast
// dat een heatmap moet laten zien.
const maxPct = computed(() => {
	let max = 0;
	for (const row of rows.value) for (const tag of props.tags) max = Math.max(max, pct(row, tag.sleutel));
	return max || 1;
});

function cellStyle(row: PartyTagIndexEntry, sleutel: string) {
	const value = pct(row, sleutel);
	if (value <= 0) return { background: "transparent" };
	const ratio = value / maxPct.value;
	return { background: withAlpha(props.color, 0.08 + ratio * 0.72) };
}

// Kolomgroepen voor de tweeledige tabelkop: `tags` staat al gesorteerd op
// labelgroep (zie PerspectiefView.vue), dus aaneengesloten reeksen met
// dezelfde labelgroep vormen de colspan-groepen -- geen aparte sortering nodig.
const groups = computed(() => {
	const result: { labelgroep: string; count: number }[] = [];
	for (const tag of props.tags) {
		const last = result[result.length - 1];
		if (last && last.labelgroep === tag.labelgroep) last.count += 1;
		else result.push({ labelgroep: tag.labelgroep, count: 1 });
	}
	return result;
});

function cellTitle(row: PartyTagIndexEntry, tag: TagMeta): string {
	const count = row.tagCounts.get(tag.sleutel) ?? 0;
	return `${tag.sleutel} — ${tag.beschrijving}\n${Math.round(pct(row, tag.sleutel))}% (${count} van ${row.total})`;
}
</script>

<template>
	<section class="stats-panel">
		<h2>Partij × tag</h2>
		<p class="panel-note">
			Percentage van de argumenten van een partij waarin deze tag voorkomt. Klik op een tagicoon of partijnaam om erop te
			filteren. Partijen met minder dan {{ MIN_TOTAL }} argumenten (over alle onderwerpen) blijven buiten de tabel -- bij
			minder is een percentage schijnnauwkeurig.
		</p>
		<p v-if="!rows.length || !tags.length" class="panel-note">Geen getagde argumenten in deze selectie.</p>
		<div v-else class="table-scroll">
			<table class="tag-heatmap">
				<thead>
					<tr>
						<th scope="col" rowspan="2"></th>
						<th
							v-for="group in groups"
							:key="group.labelgroep"
							:colspan="group.count"
							scope="colgroup"
							class="tag-heatmap-group"
						>
							{{ group.labelgroep }}
						</th>
					</tr>
					<tr>
						<th v-for="tag in tags" :key="tag.sleutel" scope="col" class="tag-heatmap-head">
							<button
								type="button"
								class="tag-heatmap-head-btn"
								:title="`${tag.sleutel} — ${tag.beschrijving}`"
								@click="toggleValue('tag', tag.sleutel)"
							>
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
								<span v-else class="tag-heatmap-head-fallback">{{ tag.sleutel }}</span>
							</button>
						</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="row in rows" :key="row.party">
						<th scope="row" class="tag-heatmap-party">
							<button type="button" class="tag-heatmap-party-btn" @click="toggleValue('partij', row.party)">
								{{ displayPartyName(row.party) }}
							</button>
						</th>
						<td
							v-for="tag in tags"
							:key="tag.sleutel"
							class="tag-heatmap-cell"
							:style="cellStyle(row, tag.sleutel)"
							:title="cellTitle(row, tag)"
						>
							{{ Math.round(pct(row, tag.sleutel)) }}%
						</td>
					</tr>
				</tbody>
			</table>
		</div>
	</section>
</template>
