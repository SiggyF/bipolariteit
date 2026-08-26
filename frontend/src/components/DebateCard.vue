<script setup lang="ts">
// Eén kaartcomponent, drie dichtheden -- ontwerp uit
// docs/design/debattenlijst/Debattenkaarten.dc.html (issue #112).
// "uitgelicht" (met videostill) en "uitgebreid" (kaart zonder beeld) delen
// dezelfde pro/contra/onduidelijk-as; "compact" is een dichte rij met alleen
// een kleine as. Balklengte via scaleWidth() (wortelschaal, zie
// debateCardScale.ts) i.p.v. lineair, zodat een klein debat niet wegvalt
// naast een debat met honderden argumenten.
import { computed } from "vue";
import { formatDate } from "../lib/formatDate";
import { formatDateShort } from "../lib/formatDateShort";
import { scaleWidth } from "../lib/debateCardScale";
import type { DebateSummary } from "../lib/groupByDebate";

const props = defineProps<{
	debate: DebateSummary;
	density: "uitgelicht" | "uitgebreid" | "compact";
	maxArguments: number;
	topicName?: string | null;
	thumbnailUrl?: string | null;
}>();

const proWidth = computed(() => scaleWidth(props.debate.stance.pro, props.maxArguments));
const contraWidth = computed(() => scaleWidth(props.debate.stance.contra, props.maxArguments));
const unclearWidth = computed(() => scaleWidth(props.debate.stance.unclear, props.maxArguments));
</script>

<template>
	<a :href="`/debatten/${debate.id}/`" class="debate-card" :class="`debate-card--${density}`">
		<span v-if="density === 'uitgelicht'" class="debate-card-thumb" aria-hidden="true">
			<img v-if="thumbnailUrl" :src="thumbnailUrl" alt="" loading="lazy" />
		</span>

		<span class="debate-card-body">
			<span class="debate-card-headline">
				<span class="debate-card-title">{{ debate.name ?? "Debat" }}</span>
				<span class="debate-card-date mono">{{
					density === "compact" ? formatDateShort(debate.earliestPublishedAt) : formatDate(debate.earliestPublishedAt)
				}}</span>
			</span>

			<span v-if="density !== 'compact'" class="debate-card-meta mono">
				<span>{{ debate.argumentCount }} argument{{ debate.argumentCount === 1 ? "" : "en" }}</span>
				<span aria-hidden="true">·</span>
				<span>{{ debate.speakerCount }} spreker{{ debate.speakerCount === 1 ? "" : "s" }}</span>
				<template v-if="topicName">
					<span aria-hidden="true">·</span>
					<span>{{ topicName }}</span>
				</template>
			</span>

			<span class="debate-card-axis" :class="{ 'debate-card-axis--compact': density === 'compact' }">
				<span class="debate-card-axis-pro">
					<span v-if="density !== 'compact'" class="mono debate-card-axis-count">{{ debate.stance.pro }}</span>
					<span class="debate-card-axis-bar debate-card-axis-bar--pro" :style="{ width: proWidth }"></span>
				</span>
				<span class="debate-card-axis-contra">
					<span class="debate-card-axis-bar debate-card-axis-bar--contra" :style="{ width: contraWidth }"></span>
					<span class="debate-card-axis-bar debate-card-axis-bar--unclear" :style="{ width: unclearWidth }"></span>
					<span v-if="density !== 'compact'" class="mono debate-card-axis-count">{{ debate.stance.contra }}</span>
				</span>
			</span>

			<span v-if="density !== 'compact'" class="debate-card-unclear mono">{{ debate.stance.unclear }} onduidelijk</span>
		</span>
	</a>
</template>

<style scoped>
.debate-card {
	display: block;
	text-decoration: none;
	color: inherit;
	border: 1px solid var(--color-border);
	background: var(--color-card-bg);
	border-radius: 4px;
}

.debate-card--uitgelicht,
.debate-card--uitgebreid {
	padding: var(--space-2);
}

.debate-card--uitgelicht {
	display: grid;
	/* Vaste vierkante maat i.p.v. "auto" + stretch: die combinatie gaf een
	   circulaire grid-berekening (de kolombreedte hangt af van de
	   thumb-hoogte via aspect-ratio, de thumb-hoogte hangt af van de
	   rijhoogte, de rijhoogte hangt af van de kolombreedte...) waardoor de
	   thumb ongecontroleerd groeide. 200px is ruim hoger dan de vorige
	   140x87.5px-versie en dekt in de praktijk de hoogte van de tekstkolom
	   ernaast (titel t/m onduidelijk-regel) redelijk goed. */
	grid-template-columns: 200px 1fr;
	gap: var(--space-2);
}

.debate-card-thumb {
	display: block;
	width: 200px;
	aspect-ratio: 1;
	border: 1px solid var(--color-border);
	border-radius: 2px;
	background: var(--color-bg);
	overflow: hidden;
}

.debate-card-thumb img {
	width: 100%;
	height: 100%;
	object-fit: cover;
	object-position: center;
	display: block;
}

.debate-card-body {
	display: block;
	min-width: 0;
}

.debate-card-headline {
	display: flex;
	align-items: baseline;
	justify-content: space-between;
	gap: var(--space-2);
}

.debate-card--uitgelicht .debate-card-title {
	font: 400 19px/1.25 var(--font-heading);
}

.debate-card--uitgebreid .debate-card-title {
	font: 400 17px/1.25 var(--font-heading);
}

.debate-card--compact .debate-card-title {
	font: 400 15px/1.35 var(--font-heading);
}

.debate-card-date {
	font-size: var(--step--1);
	font-weight: 500;
	color: var(--color-muted);
	white-space: nowrap;
}

.debate-card-meta {
	display: flex;
	align-items: center;
	gap: 0.6rem;
	margin-top: 0.4rem;
	font-size: var(--step--1);
	font-weight: 500;
	color: var(--color-muted);
	flex-wrap: wrap;
}

.debate-card-axis {
	display: grid;
	grid-template-columns: 1fr 1fr;
	align-items: center;
	margin-top: 0.75rem;
}

.debate-card-axis-pro {
	display: flex;
	justify-content: flex-end;
	align-items: center;
	gap: 0.4rem;
	border-right: 1px solid var(--color-text);
	padding-right: 0.5rem;
}

.debate-card-axis-contra {
	display: flex;
	align-items: center;
	gap: 0.4rem;
	padding-left: 0.5rem;
}

.debate-card-axis-bar {
	display: inline-block;
	height: 10px;
}

.debate-card--uitgelicht .debate-card-axis-bar {
	height: 12px;
}

.debate-card-axis--compact .debate-card-axis-bar {
	height: 8px;
}

.debate-card-axis-bar--pro {
	background: var(--color-pro);
}

.debate-card-axis-bar--contra {
	background: var(--color-contra);
}

.debate-card-axis-bar--unclear {
	background: var(--color-unclear);
}

.debate-card-axis-count {
	font-size: 10px;
	font-weight: 500;
}

.debate-card-axis-pro .debate-card-axis-count {
	color: var(--color-pro);
}

.debate-card-axis-contra .debate-card-axis-count {
	color: var(--color-contra);
}

.debate-card-unclear {
	display: block;
	margin-top: 0.6rem;
	font-size: var(--step--1);
	color: var(--color-muted);
}

/* Compacte rij: geen kaartrand, gewoon een regel met titel + as. */
.debate-card--compact {
	border: none;
	background: none;
	border-radius: 0;
	border-bottom: 1px solid var(--color-border);
	display: grid;
	grid-template-columns: 1fr 96px 96px;
	gap: 0.6rem;
	align-items: center;
	padding: 0.55rem 0;
}

/* .debate-card-body zit tussen de grid-root en headline/axis in -- moet zelf
   ook display:contents zijn, anders reikt de contents-truc op .debate-card-axis
   niet door tot de 3-koloms grid van .debate-card--compact (contents werkt
   niet door een niet-contents tussenlaag heen). */
.debate-card--compact .debate-card-body {
	display: contents;
}

.debate-card--compact .debate-card-headline {
	display: inline;
}

.debate-card--compact .debate-card-date {
	margin-left: 0.4rem;
}

.debate-card--compact .debate-card-axis {
	display: contents;
}
</style>
