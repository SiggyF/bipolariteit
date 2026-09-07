<template>
	<div
		v-if="variant !== 'ref'"
		ref="rootEl"
		class="ack"
		:class="[`ack-${variant}`, `ack-${side}`, { 'ack-selected': selected, 'ack-linked': linked }]"
		:data-arg="argument.id"
		@click="$emit('select', argument.id)"
		@mouseenter="$emit('hover', argument.id)"
		@mouseleave="$emit('unhover')"
	>
		<div class="ack-kicker">
			<span>{{ typeNl }}</span><span class="ack-id">#{{ argument.id }}</span>
		</div>
		<div class="ack-gist">{{ argument.gist }}</div>
		<div v-if="argument.samenvatting" class="ack-samenvatting">{{ argument.samenvatting }}</div>
		<div class="ack-speaker">{{ argument.spreker }}<template v-if="argument.partij"> ({{ argument.partij }})</template></div>
		<div v-if="showCitaat" class="ack-quote">&ldquo;{{ quoteShort }}&rdquo;</div>
		<div v-if="oppGist" class="ack-opp">↔ weerlegt {{ oppGist }}</div>
	</div>
	<div v-else class="ack ack-ref" :class="`ack-${side}`" @click="$emit('select', refId)">
		Zie #{{ refId }}: hangt als onderbouwing onder een ander thema (band {{ refBandNummer }}).
	</div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";

interface CardArgument {
	id: number;
	gist: string;
	samenvatting: string | null;
	spreker: string;
	partij: string | null;
	typologie: string;
	citaat: string;
}

const props = defineProps<{
	variant: "hoofd" | "kid" | "los" | "ref";
	side: "pro" | "contra";
	argument?: CardArgument;
	refId?: number;
	refBandNummer?: number;
	selected?: boolean;
	linked?: boolean;
	showCitaat?: boolean;
	oppGist?: string | null;
}>();

defineEmits<{ select: [id: number]; hover: [id: number]; unhover: [] }>();

const TYPE_NL: Record<string, string> = {
	factual: "feitelijk",
	moral: "moreel",
	legal: "juridisch",
	economic: "economisch",
	other: "overig",
};

const typeNl = computed(() => (props.argument ? (TYPE_NL[props.argument.typologie] ?? props.argument.typologie) : ""));

const QUOTE_SHORT_LEN = 162;
const quoteShort = computed(() => {
	const q = props.argument?.citaat ?? "";
	return q.length > QUOTE_SHORT_LEN + 3 ? `${q.slice(0, QUOTE_SHORT_LEN).trimEnd()}…` : q;
});

const rootEl = ref<HTMLElement | null>(null);
defineExpose({ rootEl });
</script>

<style scoped>
.ack {
	position: relative;
	border: 1px solid var(--confrontatie-divider);
	background: transparent;
	cursor: pointer;
	padding: 0.7rem 0.8rem;
}

.ack:hover {
	border-color: var(--confrontatie-accent);
}

.ack-selected {
	outline: 2px solid var(--confrontatie-accent);
	outline-offset: -1px;
}

.ack-linked:not(.ack-selected) {
	outline: 1px solid var(--confrontatie-accent);
	outline-offset: -1px;
}

.ack-hoofd {
	width: 336px;
	max-width: 100%;
	padding: 0.8rem 0.9rem 0.85rem;
	border-top-width: 2px;
}

.ack-hoofd.ack-pro {
	border-top-color: var(--color-pro);
}

.ack-hoofd.ack-contra {
	border-top-color: var(--color-contra);
}

.ack-kid {
	width: 288px;
	max-width: 100%;
}

.ack-los {
	width: 328px;
	max-width: 100%;
}

.ack-kicker {
	position: relative;
	display: flex;
	gap: 0.6rem;
	font-size: 0.65rem;
	letter-spacing: 0.1em;
	text-transform: uppercase;
	color: var(--confrontatie-muted);
	font-feature-settings: "tnum";
	margin-bottom: 0.35rem;
}

/* Verbindingsstreepje van een onderbouwing-kaart naar de gestippelde rail
   (zie .confrontatie-kids-pro/-contra in ArgumentTree.vue). Op de KAART
   zelf (`.ack-kid`, met `position:relative` via .ack) i.p.v. op de kicker-
   tekst erin: zo is de lengte gewoon de rail-gap (3rem = 336px hoofdkaart -
   288px kid-kaart, zie .confrontatie-kids in ArgumentTree.vue) vanaf de
   buitenrand van de kaart, zonder ook nog de kaartpadding/-rand tot de
   kicker-tekst te moeten meerekenen -- die zat er eerder verkeerd in en gaf
   een net-niet-sluitend streepje. `top` is het verticale midden van de
   kicker-regel (padding-top 0.7rem + halve regelhoogte 0.65rem*1.6/2),
   zodat het op dezelfde hoogte als het medaillon op de weerleggingslijn
   uitkomt. */
.ack-kid.ack-pro::after,
.ack-kid.ack-contra::after {
	content: "";
	position: absolute;
	top: 1.22rem;
	width: 3rem;
	border-top: 1px dashed var(--confrontatie-muted-2);
}

.ack-kid.ack-pro::after {
	right: -3rem;
}

.ack-kid.ack-contra::after {
	left: -3rem;
}

.ack-pro .ack-kicker,
.ack-pro .ack-gist,
.ack-pro .ack-samenvatting,
.ack-pro .ack-speaker,
.ack-pro .ack-quote {
	text-align: right;
}

.ack-pro .ack-kicker {
	justify-content: flex-end;
}

.ack-id {
	color: var(--confrontatie-muted-2);
}

.ack-gist {
	font-family: var(--confrontatie-font-heading);
	font-size: 1.2rem;
	line-height: 1.25;
}

/* Vangnet voor gists die (nog) met een kleine letter uit de LLM komen --
   de prompt (pipeline/prompts/argument_tree_gemini.md) vraagt inmiddels
   om een hoofdletter, maar al gegenereerde data hoeft niet meteen opnieuw
   te draaien om er correct uit te zien. */
.ack-gist::first-letter {
	text-transform: uppercase;
}

.ack-kid .ack-gist {
	font-size: 1.02rem;
}

.ack-samenvatting {
	font-size: 0.8rem;
	line-height: 1.5;
	color: var(--confrontatie-text-soft);
	margin-top: 0.3rem;
}

.ack-speaker {
	font-size: 0.7rem;
	color: var(--confrontatie-muted);
	margin-top: 0.4rem;
}

.ack-quote {
	font-size: 0.78rem;
	line-height: 1.5;
	color: var(--confrontatie-text-soft);
	margin-top: 0.55rem;
	padding-top: 0.55rem;
	border-top: 1px solid var(--confrontatie-divider);
	font-style: italic;
}

.ack-opp {
	font-size: 0.68rem;
	color: var(--confrontatie-accent-text);
	margin-top: 0.5rem;
	font-feature-settings: "tnum";
}

.ack-ref {
	width: 336px;
	max-width: 100%;
	padding: 0.75rem 0.9rem;
	border-style: dashed;
	border-color: var(--confrontatie-accent);
	font-size: 0.75rem;
	line-height: 1.5;
	color: var(--confrontatie-muted);
}

.ack-ref.ack-pro {
	text-align: right;
}
</style>
