<script setup lang="ts">
import { computed, ref, onMounted, watch, nextTick } from "vue";
import { ISSUE_TYPES, type IssueKey, getFeedbackFor, submitFeedback } from "../lib/feedback";
import { debateId } from "../lib/debateId";
import { displayPartyName } from "../lib/parties";
import { filters, toggleValue } from "../lib/filters";
import { scrollTarget } from "../lib/scrollTarget";
import { userScroll } from "../lib/userScroll";
import { slugify } from "../lib/slug";
import { stanceLabel, typologyLabel, typologyDescription, type Argument, type Tag } from "../lib/types";
import { formatClock } from "../lib/videoTime";
import PartyLogo from "./PartyLogo.vue";

function tagTooltip(tag: Tag): string {
	const base = `${tag.labelgroep}: ${tag.beschrijving}`;
	return tag.reden ? `${base}\n\nReden: ${tag.reden}` : base;
}

// videoContext: true op de debat-videopagina (DebateVideoView.vue) -- daar
// moet klikken op een argument de speler laten springen (event "seek") i.p.v.
// naar /debatten/[id]/ te navigeren, want een paginaherlaad onderbreekt de
// afspelende video/het geluid. playing: dit argument is op dit moment aan de
// beurt in de video (currentTime binnen start_seconds/end_seconds).
const props = defineProps<{
	argument: Argument;
	topicSlug: string;
	videoContext?: boolean;
	playing?: boolean;
	// Compacte variant voor krappe plekken (bv. de "nu in beeld"-kaart op de
	// homepage, issue #135): alleen partijlogo + naam·partij + tijdcode + één
	// rij badges (stance/typologie/eerste tag), zonder citaat/claims/links/
	// feedback -- die passen niet naast/onder de speler.
	compact?: boolean;
}>();
const emit = defineEmits<{ seek: [seconds: number] }>();

const isSeekable = computed(() => !!props.videoContext && props.argument.start_seconds !== null);

function onCardClick(event: MouseEvent) {
	if (!isSeekable.value) return;
	// Klikken op een nested link/knop (tag, feedback, ...) moet zijn eigen
	// gedrag houden, niet ook nog seeken.
	if ((event.target as HTMLElement).closest("a, button, input, textarea, label")) return;
	emit("seek", props.argument.start_seconds as number);
}

// Toetsenbordequivalent van onCardClick: de kaart is in videoContext
// focusable (tabindex+role="button") maar zonder dit bleef Enter/Spatie
// zonder effect.
function onCardKeydown(event: KeyboardEvent) {
	if (!isSeekable.value) return;
	if ((event.target as HTMLElement).closest("a, button, input, textarea, label")) return;
	if (event.key !== "Enter" && event.key !== " ") return;
	event.preventDefault();
	emit("seek", props.argument.start_seconds as number);
}

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

// Scrollt de kaart in beeld zodra dit argument aan de beurt is in de video
// (playing-prop, alleen gezet op de debat-videopagina) -- anders moet je
// zelf blijven scrollen om bij te houden welk argument nu speelt. Niet als de
// gebruiker net zelf gescrolld heeft (userScroll.ts): anders wint deze
// auto-scroll het steeds van een handmatige scrollbeweging, omdat player- en
// argumentenkolom dezelfde paginascroll delen.
// Ook niet op een gestapelde mobiele layout (video-kolom boven, lijst
// eronder, ≤900px -- zelfde grens als `.player-column`'s sticky-positionering
// in DebateVideoView.vue, die daar om dezelfde reden ook uitstaat): daar
// scrollt dit de video net buiten beeld i.p.v. 'm zichtbaar te houden.
watch(
	() => props.playing,
	(isPlaying) => {
		if (isPlaying && !userScroll.isScrolling && window.matchMedia("(min-width: 901px)").matches) {
			cardEl.value?.scrollIntoView({ behavior: "smooth", block: "center" });
		}
	},
);
</script>

<template>
	<article
		ref="cardEl"
		class="argument-card"
		:class="[
			`stance-${argument.stance}`,
			{
				'is-highlighted': justHighlighted,
				'is-seekable': isSeekable,
				'is-playing': playing,
			},
		]"
		:tabindex="isSeekable ? 0 : undefined"
		:role="isSeekable ? 'button' : undefined"
		:aria-label="isSeekable ? `Spring naar dit moment (${formatClock(argument.start_seconds as number)})` : undefined"
		@click="onCardClick"
		@keydown="onCardKeydown"
	>
		<div class="argument-meta">
			<span v-if="compact" class="stance-dot" :class="`stance-${argument.stance}`" :title="stanceLabel(argument.stance)"></span>
			<span class="typology-badge" :title="typologyDescription(argument.typology)">{{ typologyLabel(argument.typology) }}</span>
			<span v-if="compact && argument.tags[0]" class="tag-badge">{{ argument.tags[0].sleutel }}</span>
			<span v-if="videoContext && argument.start_seconds !== null" class="argument-span" title="Videospanne van dit argument">
				{{ formatClock(argument.start_seconds) }}–{{ formatClock(argument.end_seconds ?? argument.start_seconds) }}
			</span>
		</div>
		<blockquote v-if="!compact" class="quote">"{{ argument.quote_text }}"</blockquote>
		<p v-if="!compact && argument.quote_context" class="quote-context">{{ argument.quote_context }}</p>
		<p class="attribution">
			<a v-if="argument.actor.party" :href="`/partijen/${slugify(argument.actor.party)}/`" :title="`Alle tags van ${argument.actor.party}`">
				<PartyLogo :party="argument.actor.party" />
			</a>
			Volgens <a :href="`/personen/${slugify(argument.actor.name)}/`" :title="`Alle tags van ${argument.actor.name}`"><strong>{{ argument.actor.name }}</strong></a><span v-if="argument.actor.party"> (<a :href="`/partijen/${slugify(argument.actor.party)}/`">{{ displayPartyName(argument.actor.party) }}</a>)</span><span v-if="argument.actor.role_title" class="role-title">, {{ argument.actor.role_title }}</span>
		</p>
		<ul v-if="!compact && argument.claims.length" class="claims">
			<li v-for="(claim, i) in argument.claims" :key="i">
				noemt: {{ claim.claim_text }}<span v-if="claim.attributed_source_text"> (bron: {{ claim.attributed_source_text }})</span>
			</li>
		</ul>
		<ul v-if="!compact && argument.tags.length" class="tags">
			<li v-for="tag in argument.tags" :key="tag.sleutel" class="tag-item">
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
				<a class="tag-link" :href="`/tags/${slugify(tag.sleutel)}/`" title="Bekijk tagpagina">↗</a>
			</li>
		</ul>

		<div v-if="!compact" class="argument-links">
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
			<button
				v-if="videoContext && argument.start_seconds !== null"
				type="button"
				class="link-button"
				title="Spring naar dit moment in de video"
				@click="emit('seek', argument.start_seconds as number)"
				>spring naar dit moment</button
			>
			<a
				v-else-if="argument.document.raw_video_url && argument.start_seconds !== null"
				:href="`/debatten/${debateId(argument.document.raw_video_url)}/`"
				title="Bekijk dit debat met argumentannotaties over de video"
				>bekijk in videospeler</a
			>
		</div>

		<div v-if="!compact" class="feedback">
			<button type="button" class="feedback-toggle" @click="open = !open">
				{{ saved ? "✓ feedback gegeven, aanpassen" : "feedback geven" }}
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

		<p v-if="!compact && argument.prompt_version" class="debug-version">prompt {{ argument.prompt_version }}</p>
	</article>
</template>
