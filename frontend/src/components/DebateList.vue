<script setup lang="ts">
import { computed } from "vue";
import { debateId } from "../lib/debateId";
import { debateName } from "../lib/debateName";
import type { Argument } from "../lib/types";

// Lijst van debatten binnen dit topic die als video bekeken kunnen worden
// (issue #94) -- entry point vanaf de topicpagina naar /debat/[id]/. Alleen
// documenten met een gepersisteerde raw_video_url komen hierin voor.
// Groeperen op raw_video_url, niet op document.id: één debat bestaat uit veel
// document-rijen (één per spreekbeurt) die dezelfde raw_video_url delen.

const props = defineProps<{ argumentList: Argument[] }>();

interface DebateEntry {
	id: string;
	name: string | null;
	earliestPublishedAt: string | null;
	speakers: Set<string>;
	argumentCount: number;
}

const debates = computed(() => {
	const perDebate = new Map<string, DebateEntry>();
	for (const argument of props.argumentList) {
		if (!argument.document.raw_video_url) continue;
		const id = debateId(argument.document.raw_video_url);
		let entry = perDebate.get(id);
		if (!entry) {
			entry = {
				id,
				name: debateName(argument.document.video_url),
				earliestPublishedAt: argument.document.published_at,
				speakers: new Set(),
				argumentCount: 0,
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
	}
	return [...perDebate.values()].sort((a, b) => (b.earliestPublishedAt ?? "").localeCompare(a.earliestPublishedAt ?? ""));
});

function formatDate(iso: string | null): string {
	if (!iso) return "datum onbekend";
	return new Date(iso).toLocaleDateString("nl-NL", { day: "numeric", month: "long", year: "numeric" });
}
</script>

<template>
	<section v-if="debates.length" class="debate-list">
		<h2>Bekijk de debatten</h2>
		<ul>
			<li v-for="debate in debates" :key="debate.id">
				<a :href="`/debat/${debate.id}/`">
					<span class="debate-title">
						<strong>{{ debate.name ?? "Debat" }}</strong>
						<span class="debate-date">{{ formatDate(debate.earliestPublishedAt) }}</span>
					</span>
					<span class="debate-meta">
						{{ debate.argumentCount }} argument{{ debate.argumentCount === 1 ? "" : "en" }}, {{ debate.speakers.size }}
						spreker{{ debate.speakers.size === 1 ? "" : "s" }}
					</span>
				</a>
			</li>
		</ul>
	</section>
</template>

<style scoped>
.debate-list {
	margin: var(--space-4) 0;
}

.debate-list ul {
	list-style: none;
	margin: 0;
	padding: 0;
	display: flex;
	flex-direction: column;
	gap: var(--space-1);
}

.debate-list a {
	display: flex;
	justify-content: space-between;
	align-items: baseline;
	gap: var(--space-2);
	padding: var(--space-1) var(--space-2);
	background: var(--color-card-bg);
	border: 1px solid var(--color-border);
	border-radius: 4px;
	text-decoration: none;
	color: var(--color-text);
}

.debate-title {
	display: flex;
	align-items: baseline;
	gap: 0.6em;
}

.debate-date {
	color: var(--color-muted);
	font-size: var(--step--1);
	white-space: nowrap;
}

.debate-meta {
	color: var(--color-muted);
	font-family: var(--font-mono);
	font-size: var(--step--1);
	white-space: nowrap;
}
</style>
