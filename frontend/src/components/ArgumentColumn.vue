<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import ArgumentCard from "./ArgumentCard.vue";

const PAGE_SIZE = 50;

// Let op: de prop heet bewust NIET "arguments" -- die naam botst met het
// ingebouwde JS `arguments`-object van de (niet-arrow) render-functie die
// Vue's templatecompiler genereert. Vue laat zo'n botsende globale naam in
// de template ongemoeid (whitelist met Math/Date/arguments/etc.) i.p.v. 'm
// naar de prop te resolven, dus `{{ arguments.length }}` in een template
// gaf stilzwijgend de lengte van dat native object terug (altijd hetzelfde
// getal, ongeacht de echte data) i.p.v. een fout te gooien.
const props = defineProps<{ argumentList: any[]; topicSlug: string; label: string; stanceClass: string }>();

const visibleCount = ref(Math.min(PAGE_SIZE, props.argumentList.length));
const visible = computed(() => props.argumentList.slice(0, visibleCount.value));
const hasMore = computed(() => visibleCount.value < props.argumentList.length);

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
	<section class="column" :class="stanceClass">
		<h2>{{ label }} ({{ argumentList.length }})</h2>
		<ArgumentCard v-for="argument in visible" :key="argument.id" :argument="argument" :topicSlug="topicSlug" />
		<div v-if="hasMore" ref="sentinel" class="column-load-more">
			<button type="button" @click="visibleCount = Math.min(visibleCount + PAGE_SIZE, argumentList.length)">
				meer laden ({{ argumentList.length - visibleCount }} resterend)
			</button>
		</div>
	</section>
</template>
