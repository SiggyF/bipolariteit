<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from "vue";
import { ISSUE_TYPES, type IssueKey, getFeedbackFor, submitFeedback } from "../lib/feedback";
import { displayPartyName } from "../lib/parties";
import { filters, toggleValue } from "../lib/filters";
import { scrollTarget } from "../lib/scrollTarget";
import { slugify } from "../lib/slug";
import type { Argument, Tag } from "../lib/types";
import PartyLogo from "./PartyLogo.vue";

function tagTooltip(tag: Tag): string {
	const base = `${tag.labelgroep}: ${tag.beschrijving}`;
	return tag.reden ? `${base}\n\nReden: ${tag.reden}` : base;
}

const props = defineProps<{ argument: Argument; topicSlug: string }>();

const open = ref(false);
const selectedIssues = ref<IssueKey[]>([]);
const note = ref("");
const saved = ref(false);

onMounted(() => {
	const existing = getFeedbackFor(props.argument.id);
	if (existing) {
		selectedIssues.value = existing.issues;
		note.value = existing.note ?? "";
		saved.value = true;
	}
});

function toggleIssue(key: IssueKey) {
	const i = selectedIssues.value.indexOf(key);
	if (i === -1) selectedIssues.value.push(key);
	else selectedIssues.value.splice(i, 1);
	saved.value = false;
}

function submit() {
	submitFeedback({
		argument_id: props.argument.id,
		topic_slug: props.topicSlug,
		issues: selectedIssues.value,
		note: note.value || null,
	});
	saved.value = true;
	open.value = false;
}

// Reageert op een "ga naar dit argument"-aanvraag vanuit ClaimsHighlights.vue.
// immediate: true, zodat een kaart die pas na de aanvraag gemount wordt
// (omdat ArgumentColumn zijn visibleCount ophoogt) de aanvraag alsnog oppikt.
const cardEl = ref<HTMLElement | null>(null);
const justHighlighted = ref(false);
let highlightTimer: ReturnType<typeof setTimeout> | null = null;

watch(
	() => scrollTarget.token,
	async () => {
		if (scrollTarget.argumentId !== props.argument.id) return;
		await nextTick();
		cardEl.value?.scrollIntoView({ behavior: "smooth", block: "center" });
		justHighlighted.value = true;
		if (highlightTimer) clearTimeout(highlightTimer);
		highlightTimer = setTimeout(() => {
			justHighlighted.value = false;
		}, 2200);
	},
	{ immediate: true },
);
</script>

<template>
	<article ref="cardEl" class="argument-card" :class="[`stance-${argument.stance}`, { 'is-highlighted': justHighlighted }]">
		<div class="argument-meta">
			<span class="typology-badge">{{ argument.typology }}</span>
		</div>
		<blockquote class="quote">"{{ argument.quote_text }}"</blockquote>
		<p v-if="argument.quote_context" class="quote-context">{{ argument.quote_context }}</p>
		<p class="attribution">
			<a v-if="argument.actor.party" :href="`/partij/${slugify(argument.actor.party)}/`" :title="`Alle tags van ${argument.actor.party}`">
				<PartyLogo :party="argument.actor.party" />
			</a>
			Volgens <a :href="`/persoon/${slugify(argument.actor.name)}/`" :title="`Alle tags van ${argument.actor.name}`"><strong>{{ argument.actor.name }}</strong></a><span v-if="argument.actor.party"> (<a :href="`/partij/${slugify(argument.actor.party)}/`">{{ displayPartyName(argument.actor.party) }}</a>)</span><span v-if="argument.actor.role_title" class="role-title"> — {{ argument.actor.role_title }}</span>
		</p>
		<ul v-if="argument.claims.length" class="claims">
			<li v-for="(claim, i) in argument.claims" :key="i">
				noemt: {{ claim.claim_text }}<span v-if="claim.attributed_source_text"> (bron: {{ claim.attributed_source_text }})</span>
			</li>
		</ul>
		<ul v-if="argument.tags.length" class="tags">
			<li v-for="tag in argument.tags" :key="tag.sleutel">
				<button
					type="button"
					class="tag-badge"
					:class="{ 'is-active': filters.values.tag.includes(tag.sleutel) }"
					:title="tagTooltip(tag)"
					:aria-pressed="filters.values.tag.includes(tag.sleutel)"
					@click="toggleValue('tag', tag.sleutel)"
				>
					{{ tag.sleutel }}
				</button>
			</li>
		</ul>

		<div class="argument-links">
			<a
				v-if="argument.document.tweedekamer_activiteit_url"
				:href="argument.document.tweedekamer_activiteit_url"
				target="_blank"
				rel="noopener"
				title="Officiële tweedekamer.nl-pagina van dit debat (Verslag/Handelingen + video)"
				>bekijk in de Tweede Kamer</a
			>
			<a
				v-if="argument.document.url"
				:href="argument.document.url"
				target="_blank"
				rel="noopener"
				title="Ruwe brondata (XML) van de Tweede Kamer -- machine-leesbaar, geen leesbare pagina"
				>ruwe brondata (XML)</a
			>
			<a
				v-if="argument.document.speaker_video_url"
				:href="argument.document.speaker_video_url"
				target="_blank"
				rel="noopener"
				title="Springt naar het moment dat deze spreker begint in het debat"
				>video (dit moment)</a
			>
			<a
				v-else-if="argument.document.video_url"
				:href="argument.document.video_url"
				target="_blank"
				rel="noopener"
				>video (hele debat)</a
			>
		</div>

		<div class="feedback">
			<button type="button" class="feedback-toggle" @click="open = !open">
				{{ saved ? "✓ feedback gegeven — aanpassen" : "feedback geven" }}
			</button>
			<div v-if="open" class="feedback-panel">
				<label v-for="issue in ISSUE_TYPES" :key="issue.key" class="feedback-option">
					<input
						type="checkbox"
						:checked="selectedIssues.includes(issue.key)"
						@change="toggleIssue(issue.key)"
					/>
					{{ issue.label }}
				</label>
				<textarea v-model="note" placeholder="Toelichting (optioneel)" rows="2"></textarea>
				<button type="button" class="feedback-submit" @click="submit" :disabled="!selectedIssues.length">
					Versturen
				</button>
			</div>
		</div>

		<p v-if="argument.prompt_version" class="debug-version">prompt {{ argument.prompt_version }}</p>
	</article>
</template>
