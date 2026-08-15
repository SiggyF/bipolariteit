import type { Typology } from "./types";

// Gevalideerd 4-slot palet (validate_palette.js, licht + donker, alle zes
// checks PASS) plus --color-unclear als bewust neutrale "Overig"-kleur. De
// slotvolgorde is de CVD-garantie en ligt vast; wijzig hier niet de volgorde
// zonder opnieuw te valideren (zie het plan bij issue #54). Gedeeld tussen
// ArgumentTimeline.vue en about.astro zodat de typologiekleuren overal
// hetzelfde zijn.
export const TYPOLOGY_COLORS: Record<Typology, string> = {
	factual: "#6586c3",
	legal: "#804674",
	economic: "#5c884c",
	moral: "#067396",
	other: "var(--color-unclear)",
};
