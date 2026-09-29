<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from "vue";
import ArgumentCard from "./ArgumentCard.vue";
import { scrollTarget } from "../lib/scrollTarget";
import { standpuntModifier } from "../lib/standpunt";
import { stanceLabel, type Argument, type Stance } from "../lib/types";

const PAGE_SIZE = 50;

// Let op: de prop heet bewust NIET "arguments" -- die naam botst met het
// ingebouwde JS `arguments`-object van de (niet-arrow) render-functie die
// Vue's templatecompiler genereert. Vue laat zo'n botsende globale naam in
// de template ongemoeid (whitelist met Math/Date/arguments/etc.) i.p.v. 'm
// naar de prop te resolven, dus `{{ arguments.length }}` in een template
// gaf stilzwijgend de lengte van dat native object terug (altijd hetzelfde
// getal, ongeacht de echte data) i.p.v. een fout te gooien.
// Krijgt een al gefilterde lijst binnen: TopicView past het filter één keer
// toe voor de hele pagina, zodat kolommen en grafieken niet elk hun eigen
// interpretatie kunnen hebben.
// stance ontbreekt voor de samengevoegde mobiele lijst (issue #136): daar is
// er geen aparte kolomkop per stance meer, de stance staat per kaart zelf
// (ArgumentCard's StandpuntGlyph, glyph + woord, altijd zichtbaar) -- de kop
// valt dan terug op de neutrale .vl-vouw-kolom.is-los-stijl.
const props = defineProps<{ argumentList: Argument[]; topicSlug: string; label?: string; stance?: Stance }>();

const visibleCount = ref(Math.min(PAGE_SIZE, props.argumentList.length));
const visible = computed(() => props.argumentList.slice(0, visibleCount.value));
const hasMore = computed(() => visibleCount.value < props.argumentList.length);

watch(
	() => props.argumentList,
	(list) => {
		visibleCount.value = Math.min(PAGE_SIZE, list.length);
	},
);

// Haalt de infinite-scroll-paginering in als ClaimsHighlights vraagt om naar
// een argument te scrollen dat verderop in deze kolom staat dan wat al
// zichtbaar is.
watch(
	() => scrollTarget.token,
	() => {
		const id = scrollTarget.argumentId;
		if (id == null) return;
		const idx = props.argumentList.findIndex((a) => a.id === id);
		if (idx === -1) return;
		if (idx >= visibleCount.value) visibleCount.value = idx + 1;
	},
);

const sentinel = ref<HTMLElement | null>(null);
let observer: IntersectionObserver | null = null;

onMounted(() => {
	observer = new IntersectionObserver(
		(entries) => {
			if (entries[0].isIntersecting && hasMore.value) {
				visibleCount.value = Math.min(visibleCount.value + PAGE_SIZE, props.argumentList.length);
			}
		},
		{ rootMargin: "400px" },
	);
	if (sentinel.value) observer.observe(sentinel.value);
});

onBeforeUnmount(() => {
	observer?.disconnect();
});
</script>

<template>
	<section class="vl-vouw-kolom" :class="stance ? `is-${standpuntModifier(stance)}` : 'is-los'">
		<header v-if="stance || label">
			<span class="vl-vouw-kolom-titel">
				{{ stance ? stanceLabel(stance) : label }}
				<a href="/over/#argumenttypen" class="info-link" title="Wat betekenen stance en typologie?" aria-label="Uitleg: wat betekenen stance en typologie?">?</a>
			</span>
			<span class="vl-data">{{ argumentList.length }} {{ argumentList.length === 1 ? "argument" : "argumenten" }}</span>
		</header>
		<ArgumentCard v-for="argument in visible" :key="argument.id" :argument="argument" :topicSlug="topicSlug" />
		<div v-if="hasMore" ref="sentinel" class="column-load-more">
			<button type="button" @click="visibleCount = Math.min(visibleCount + PAGE_SIZE, argumentList.length)">
				meer laden ({{ argumentList.length - visibleCount }} resterend)
			</button>
		</div>
	</section>
</template>
