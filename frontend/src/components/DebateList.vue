<script setup lang="ts">
import { computed, useSlots } from "vue";
import DebateCard from "./DebateCard.vue";
import { debateId } from "../lib/debateId";
import { debateName } from "../lib/debateName";
import { debateThumbnailUrl } from "../lib/debateThumbnail";
import type { Argument } from "../lib/types";
import type { DebateSummary, DebateTagCount } from "../lib/groupByDebate";

// Lijst van debatten binnen dit topic die als video bekeken kunnen worden
// (issue #94) -- entry point vanaf de topicpagina naar /debat/[id]/. Alleen
// documenten met een gepersisteerde raw_video_url komen hierin voor.
// Groeperen op raw_video_url, niet op document.id: één debat bestaat uit veel
// document-rijen (één per spreekbeurt) die dezelfde raw_video_url delen.

const props = defineProps<{
	argumentList: Argument[];
	/** Toon alleen de meest recente N debatten i.p.v. alles (bv. de
	 * perspectiefpagina spant alle topics/jaren, dat kunnen tientallen
	 * debatten zijn -- ongelimiteerd op een topic-pagina, waar het bereik
	 * toch al beperkt is). */
	limit?: number;
	/** Alleen debatten met minstens 1 tag-toekenning (binnen de meegegeven
	 * argumentList) opnemen. Voorkomt dat een debat dat de tag-pipeline nog
	 * niet heeft bereikt (arguments.tagged_at IS NULL, dus altijd 0 tags, niet
	 * "dit perspectief was hier niet van toepassing") als misleidend "geen
	 * tags" verschijnt -- en, erger, vóór de limit een wél-getagd ouder debat
	 * verdringt. Alleen relevant in combinatie met de "extra"-slot die
	 * tagCounts toont (zie PerspectiefView, issue #112-vervolg); topic-
	 * pagina's laten dit op false (stance is altijd gevuld, ongeacht tagging). */
	hideUntagged?: boolean;
}>();

const thumbnailsByDebateId = new Map<string, string>();

// tagCounts wordt altijd meegehouden (goedkoop -- argumentList is toch al in
// memory), maar alleen gebruikt door een consument die de "extra"-scoped-slot
// invult (zie PerspectiefView, issue #112-vervolg: tag-verdeling i.p.v.
// pro/contra op de perspectiefpagina). Op scopedList van een perspectief
// bevat argument.tags al alleen de tags van dát perspectief
// (filterTagsByPerspectief in export_public_data.ts), dus hier is geen
// perspectief-filter nodig.
const debates = computed<(DebateSummary & { tagCounts: DebateTagCount[] })[]>(() => {
	const perDebate = new Map<string, DebateSummary & { speakers: Set<string>; tagCounts: Map<string, DebateTagCount> }>();
	thumbnailsByDebateId.clear();
	for (const argument of props.argumentList) {
		if (!argument.document.raw_video_url) continue;
		const id = debateId(argument.document.raw_video_url);
		let entry = perDebate.get(id);
		if (!entry) {
			entry = {
				id,
				topicSlug: "",
				name: debateName(argument.document.video_url),
				earliestPublishedAt: argument.document.published_at,
				speakerCount: 0,
				argumentCount: 0,
				stance: { pro: 0, contra: 0, unclear: 0 },
				speakers: new Set(),
				tagCounts: new Map(),
			};
			perDebate.set(id, entry);
		}
		if (
			argument.document.published_at &&
			(!entry.earliestPublishedAt || argument.document.published_at < entry.earliestPublishedAt)
		) {
			entry.earliestPublishedAt = argument.document.published_at;
		}
		entry.speakers.add(argument.actor.name);
		entry.argumentCount++;
		if (argument.stance === "pro" || argument.stance === "contra" || argument.stance === "unclear") {
			entry.stance[argument.stance]++;
		}
		for (const tag of argument.tags) {
			const existing = entry.tagCounts.get(tag.sleutel);
			if (existing) existing.count++;
			else entry.tagCounts.set(tag.sleutel, { sleutel: tag.sleutel, beschrijving: tag.beschrijving, labelgroep: tag.labelgroep, count: 1 });
		}
		if (!thumbnailsByDebateId.has(id)) {
			const url = debateThumbnailUrl(argument.document.video_url, argument.document.published_at, argument.start_seconds);
			if (url) thumbnailsByDebateId.set(id, url);
		}
	}
	return [...perDebate.values()]
		.map(({ speakers, tagCounts, ...entry }) => ({
			...entry,
			speakerCount: speakers.size,
			tagCounts: [...tagCounts.values()].sort((a, b) => b.count - a.count),
		}))
		.filter((entry) => !props.hideUntagged || entry.tagCounts.length > 0)
		.sort((a, b) => (b.earliestPublishedAt ?? "").localeCompare(a.earliestPublishedAt ?? ""));
});

const limitedDebates = computed(() => (props.limit ? debates.value.slice(0, props.limit) : debates.value));

// Dichtheid (#112, zie ook debatten/index.astro): 1 uitgelicht met
// videostill, dan een paar uitgebreid, de rest compact.
const N_UITGELICHT = 1;
const N_UITGEBREID = 2;
const maxArguments = computed(() => Math.max(1, ...limitedDebates.value.map((d) => d.argumentCount)));
const uitgelicht = computed(() => limitedDebates.value.slice(0, N_UITGELICHT));
const uitgebreid = computed(() => limitedDebates.value.slice(N_UITGELICHT, N_UITGELICHT + N_UITGEBREID));
const compact = computed(() => limitedDebates.value.slice(N_UITGELICHT + N_UITGEBREID));

// Doorgeven i.p.v. hier al invullen: de "extra"-slot (default = pro/contra-as,
// zie DebateCard.vue) laat een consument als PerspectiefView 'm overschrijven
// met iets anders (tag-verdeling). Alleen doorgeven als er ook echt content
// voor is -- anders overschrijft een lege <template #extra> per ongeluk de
// eigen default-fallback van DebateCard bij bestaand gebruik (topic-pagina's).
const slots = useSlots();
const hasExtraSlot = computed(() => Boolean(slots.extra));
</script>

<template>
	<section v-if="debates.length" class="debate-list">
		<h2>Bekijk de debatten</h2>
		<div class="debate-cards">
			<DebateCard
				v-for="debate in uitgelicht"
				:key="debate.id"
				:debate="debate"
				density="uitgelicht"
				:maxArguments="maxArguments"
				:thumbnailUrl="thumbnailsByDebateId.get(debate.id) ?? null"
			>
				<template v-if="hasExtraSlot" #extra="slotProps"><slot name="extra" v-bind="slotProps" /></template>
			</DebateCard>
			<DebateCard v-for="debate in uitgebreid" :key="debate.id" :debate="debate" density="uitgebreid" :maxArguments="maxArguments">
				<template v-if="hasExtraSlot" #extra="slotProps"><slot name="extra" v-bind="slotProps" /></template>
			</DebateCard>
		</div>
		<div v-if="compact.length" class="debate-cards-compact">
			<DebateCard v-for="debate in compact" :key="debate.id" :debate="debate" density="compact" :maxArguments="maxArguments">
				<template v-if="hasExtraSlot" #extra="slotProps"><slot name="extra" v-bind="slotProps" /></template>
			</DebateCard>
		</div>
	</section>
</template>

<style scoped>
.debate-list {
	margin: var(--space-4) 0;
}

.debate-cards {
	display: flex;
	flex-direction: column;
	gap: var(--space-1);
}

.debate-cards-compact {
	margin-top: var(--space-2);
}
</style>
