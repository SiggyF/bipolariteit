// Topic-kleuren voor de plenaire/debattenkaart. Losgetrokken uit
// PlenairMap.vue (die zelf ongewijzigd blijft, zie issue #215) zodat
// TiledPlenairMap.vue dezelfde kleuren gebruikt zonder ze te dupliceren.
export const TOPIC_COLOR: Record<string, string> = {
	stikstof: "#4a7a4a",
	abortus: "#a64d5f",
	asiel: "#c07a2e",
	energietransitie: "#3d6e8f",
	plenair: "#a89e8c",
};

export const DEFAULT_TOPIC_COLOR = "#a89e8c";
