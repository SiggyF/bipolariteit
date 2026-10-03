import type { Typology } from "./types";

// Gevalideerd 4-slot palet (validate_palette.js, licht + donker, alle zes
// checks PASS) plus --onduidelijk als bewust neutrale "Overig"-kleur. De
// slotvolgorde is de CVD-garantie en ligt vast; wijzig hier niet de volgorde
// zonder opnieuw te valideren (zie het plan bij issue #54). Gebruikt door
// over.astro; los definiëren i.p.v. hardcoden zodat de typologiekleuren
// overal hetzelfde blijven zodra dit elders ook nodig is.
export const TYPOLOGY_COLORS: Record<Typology, string> = {
	factual: "#6586c3",
	legal: "#804674",
	economic: "#5c884c",
	moral: "#067396",
	other: "var(--onduidelijk)",
};
