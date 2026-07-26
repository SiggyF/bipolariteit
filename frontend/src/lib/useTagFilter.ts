import { onMounted, onUnmounted, ref } from "vue";

// Cross-island filter state (TagCorrespondenceMap sets it on tag-click,
// ArgumentColumn reads it to filter its list) -- Astro islands are separate
// Vue app instances, so a plain module-scope ref can't be trusted to stay
// in sync across them. Same DOM CustomEvent pattern as useTheme.ts.
export interface TagFilter {
	sleutel: string;
	beschrijving: string;
}

const EVENT = "tagfilterchange";

export function setTagFilter(filter: TagFilter | null) {
	document.dispatchEvent(new CustomEvent<TagFilter | null>(EVENT, { detail: filter }));
}

export function useTagFilter() {
	const filter = ref<TagFilter | null>(null);

	function update(e: Event) {
		filter.value = (e as CustomEvent<TagFilter | null>).detail;
	}

	onMounted(() => {
		document.addEventListener(EVENT, update);
	});
	onUnmounted(() => {
		document.removeEventListener(EVENT, update);
	});

	return filter;
}
