import { onMounted, onUnmounted, ref } from "vue";

// Cross-island filter state (StatsPanel sets it on bar-click, ArgumentColumn
// reads it to filter its list) -- same CustomEvent pattern as useTagFilter.ts,
// necessary because Astro islands are separate Vue app instances.
export interface PartyFilter {
	// Raw `actor.party` value, or the "Onbekend" sentinel used for
	// arguments whose actor has no party (see build_stats in
	// pipeline/build_static_data.py).
	party: string;
}

const EVENT = "partyfilterchange";

export function setPartyFilter(filter: PartyFilter | null) {
	document.dispatchEvent(new CustomEvent<PartyFilter | null>(EVENT, { detail: filter }));
}

export function usePartyFilter() {
	const filter = ref<PartyFilter | null>(null);

	function update(e: Event) {
		filter.value = (e as CustomEvent<PartyFilter | null>).detail;
	}

	onMounted(() => {
		document.addEventListener(EVENT, update);
	});
	onUnmounted(() => {
		document.removeEventListener(EVENT, update);
	});

	return filter;
}
