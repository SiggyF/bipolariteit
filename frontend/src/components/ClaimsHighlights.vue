<script setup lang="ts">
import { computed } from "vue";
import { displayPartyName } from "../lib/parties";
import { requestScrollTo } from "../lib/scrollTarget";
import type { Argument, Claim } from "../lib/types";

const TARGET_COUNT = 6;

const props = defineProps<{
	argumentList: Argument[];
	// Alleen zinvol op plekken die zelf niet de topic-pagina zijn (bv. de
	// homepage-teaser, zie DebateVideoView.vue's debateHref voor hetzelfde
	// idee): daar bestaat geen argumentenlijst op de pagina zelf om naartoe te
	// scrollen (requestScrollTo/scrollTarget werkt alleen binnen één pagina),
	// dus wordt elke kaart een link naar de topic-pagina i.p.v. een scrollknop.
	topicHref?: string;
}>();

interface Candidate {
	argument: Argument;
	claim: Claim;
	key: string;
}

// Elke claim krijgt bij eerste observatie een vaste willekeurige rank die
// blijft staan zolang de pagina leeft. Zo husselt filteren de zichtbare
// selectie niet steeds opnieuw -- alleen welke claims uit de al-gerandomiseerde
// volgorde toevallig (nog) matchen met het filter.
const randomRank = new Map<string, number>();
function rankOf(key: string): number {
	let r = randomRank.get(key);
	if (r === undefined) {
		r = Math.random();
		randomRank.set(key, r);
	}
	return r;
}

const candidates = computed<Candidate[]>(() => {
	const sourced: Candidate[] = [];
	const unsourced: Candidate[] = [];
	for (const argument of props.argumentList) {
		argument.claims.forEach((claim, i) => {
			const candidate: Candidate = { argument, claim, key: `${argument.id}:${i}` };
			(claim.attributed_source_text ? sourced : unsourced).push(candidate);
		});
	}
	sourced.sort((a, b) => rankOf(a.key) - rankOf(b.key));
	unsourced.sort((a, b) => rankOf(a.key) - rankOf(b.key));
	return [...sourced, ...unsourced].slice(0, TARGET_COUNT);
});

function onClaimClick(candidate: Candidate) {
	requestScrollTo(candidate.argument.id);
}

// Claims zijn uit een lopende zin geknipt en missen daardoor vaak een
// hoofdletter aan het begin en/of een punt aan het eind; "..." aan de
// ontbrekende kant(en) maakt dat leesbaar als fragment.
const STARTS_WITH_CAPITAL = /^[A-ZÀ-ÖØ-Þ]/;
const ENDS_WITH_SENTENCE_PUNCTUATION = /[.!?]["'”’)]?$/;
function displayClaimText(text: string): string {
	const withLeading = STARTS_WITH_CAPITAL.test(text) ? text : `... ${text}`;
	return ENDS_WITH_SENTENCE_PUNCTUATION.test(text) ? withLeading : `${withLeading} ...`;
}
</script>

<template>
	<section v-if="candidates.length" class="claims-highlights">
		<h2>Wat wordt er beweerd?</h2>
		<p class="panel-note">Een willekeurige greep uit de claims in deze selectie. Klik om het bijbehorende argument te bekijken.</p>
		<ul class="claims-highlights-grid">
			<li v-for="candidate in candidates" :key="candidate.key">
				<component
					:is="topicHref ? 'a' : 'button'"
					:type="topicHref ? undefined : 'button'"
					:href="topicHref"
					class="claim-highlight-card"
					@click="topicHref ? undefined : onClaimClick(candidate)"
				>
					<blockquote class="claim-highlight-text">{{ displayClaimText(candidate.claim.claim_text) }}</blockquote>
					<p v-if="candidate.claim.attributed_source_text" class="claim-highlight-source">
						bron: {{ candidate.claim.attributed_source_text }}
					</p>
					<p class="claim-highlight-meta">
						<span class="stance-dot" :class="`stance-${candidate.argument.stance}`"></span>
						{{ candidate.argument.actor.name }}<span v-if="candidate.argument.actor.party"> ({{ displayPartyName(candidate.argument.actor.party) }})</span>
					</p>
				</component>
			</li>
		</ul>
	</section>
</template>
