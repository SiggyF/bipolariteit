<script setup lang="ts">
import { computed } from "vue";
import DebateCard from "./DebateCard.vue";
import { debateId } from "../lib/debateId";
import { debateName } from "../lib/debateName";
import type { Argument } from "../lib/types";
import type { DebateSummary } from "../lib/groupByDebate";

// Lijst van debatten binnen dit topic die als video bekeken kunnen worden
// (issue #94) -- entry point vanaf de topicpagina naar /debat/[id]/. Alleen
// documenten met een gepersisteerde raw_video_url komen hierin voor.
// Groeperen op raw_video_url, niet op document.id: één debat bestaat uit veel
// document-rijen (één per spreekbeurt) die dezelfde raw_video_url delen.

const props = defineProps<{ argumentList: Argument[] }>();

const debates = computed<DebateSummary[]>(() => {
	const perDebate = new Map<string, DebateSummary & { speakers: Set<string> }>();
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
	}
	return [...perDebate.values()]
		.map(({ speakers, ...entry }) => ({ ...entry, speakerCount: speakers.size }))
		.sort((a, b) => (b.earliestPublishedAt ?? "").localeCompare(a.earliestPublishedAt ?? ""));
});

// Dichtheid (#112, zie ook debatten/index.astro): op een onderwerp-pagina is
// de lijst al gefilterd tot één topic, dus geen "uitgelicht"-tier met
// videostill nodig -- de eerste paar debatten uitgebreid, de rest compact.
const N_UITGEBREID = 2;
const maxArguments = computed(() => Math.max(1, ...debates.value.map((d) => d.argumentCount)));
const uitgebreid = computed(() => debates.value.slice(0, N_UITGEBREID));
const compact = computed(() => debates.value.slice(N_UITGEBREID));
</script>

<template>
	<section v-if="debates.length" class="debate-list">
		<h2>Bekijk de debatten</h2>
		<div class="debate-cards">
			<DebateCard v-for="debate in uitgebreid" :key="debate.id" :debate="debate" density="uitgebreid" :maxArguments="maxArguments" />
		</div>
		<div v-if="compact.length" class="debate-cards-compact">
			<DebateCard v-for="debate in compact" :key="debate.id" :debate="debate" density="compact" :maxArguments="maxArguments" />
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
