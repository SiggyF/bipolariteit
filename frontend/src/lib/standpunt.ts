import type { Stance } from "./types";

// De Vloei-CSS-modifiers zijn Dutch (is-pro/is-contra/is-onduidelijk, zie
// main.css), de Stance-waarde is Engels op één uitzondering na (schema.sql:
// 'unclear'). Gedeeld door StandpuntGlyph.vue en ArgumentCard.vue (de
// inkttab), zodat die twee niet uit de pas kunnen lopen.
export function standpuntModifier(stance: Stance): "pro" | "contra" | "onduidelijk" {
	return stance === "unclear" ? "onduidelijk" : stance;
}
