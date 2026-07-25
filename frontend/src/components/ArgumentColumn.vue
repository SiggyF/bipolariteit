<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import ArgumentCard from "./ArgumentCard.vue";

const PAGE_SIZE = 50;

const props = defineProps<{ arguments: any[]; topicSlug: string; label: string; stanceClass: string }>();

const visibleCount = ref(Math.min(PAGE_SIZE, props.arguments.length));
const visible = computed(() => props.arguments.slice(0, visibleCount.value));
const hasMore = computed(() => visibleCount.value < props.arguments.length);

const sentinel = ref<HTMLElement | null>(null);
let observer: IntersectionObserver | null = null;

onMounted(() => {
	observer = new IntersectionObserver(
		(entries) => {
			if (entries[0].isIntersecting && hasMore.value) {
				visibleCount.value = Math.min(visibleCount.value + PAGE_SIZE, props.arguments.length);
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
		<h2>{{ label }} ({{ arguments.length }})</h2>
		<ArgumentCard v-for="argument in visible" :key="argument.id" :argument="argument" :topicSlug="topicSlug" />
		<div v-if="hasMore" ref="sentinel" class="column-load-more">
			<button type="button" @click="visibleCount = Math.min(visibleCount + PAGE_SIZE, arguments.length)">
				meer laden ({{ arguments.length - visibleCount }} resterend)
			</button>
		</div>
	</section>
</template>
