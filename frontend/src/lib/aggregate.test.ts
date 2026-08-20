import { describe, expect, it } from "vitest";
import { countByTypologyAndStance } from "./aggregate";
import type { Argument, Stance, Typology } from "./types";

function argument(typology: Typology, stance: Stance): Argument {
	return {
		stance,
		typology,
		quote_text: "",
		quote_context: null,
		prompt_version: null,
		start_seconds: null,
		end_seconds: null,
		actor: { name: "Iemand", party: null, role_title: null },
		document: {
			id: 1,
			url: null,
			video_url: null,
			published_at: null,
			speaker_video_url: null,
			tweedekamer_activiteit_url: null,
			redactie_review: null,
			raw_video_url: null,
		},
		periode: { kamer: null, regering: null },
		claims: [],
		tags: [],
		oppositions: [],
	};
}

describe("countByTypologyAndStance", () => {
	it("telt per typologie de stances en het totaal, gesorteerd op totaal", () => {
		const rows = countByTypologyAndStance([
			argument("factual", "pro"),
			argument("factual", "pro"),
			argument("factual", "contra"),
			argument("moral", "pro"),
		]);

		const factual = rows.find((r) => r.typology === "factual");
		expect(factual).toEqual({ typology: "factual", pro: 2, contra: 1, unclear: 0, total: 3 });

		const moral = rows.find((r) => r.typology === "moral");
		expect(moral).toEqual({ typology: "moral", pro: 1, contra: 0, unclear: 0, total: 1 });

		expect(rows[0].typology).toBe("factual");
	});

	it("geeft alle typologieën terug, ook zonder argumenten in de selectie", () => {
		const rows = countByTypologyAndStance([]);
		expect(rows).toHaveLength(5);
		expect(rows.every((r) => r.total === 0)).toBe(true);
	});
});
