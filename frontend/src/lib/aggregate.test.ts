import { describe, expect, it } from "vitest";
import { countByTypologyAndStance, deriveVerbositeitStats } from "./aggregate";
import type { Argument, Sprekerbeurt, Stance, Typology } from "./types";

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

function sprekerbeurt(overrides: Partial<Sprekerbeurt> = {}): Sprekerbeurt {
	return {
		id: 1,
		actor: { name: "Iemand", party: null },
		char_count: 100,
		word_count: 20,
		sentence_count: 2,
		syllable_count: 30,
		long_word_count: 4,
		unique_word_count: 15,
		token_count: 25,
		...overrides,
	};
}

describe("deriveVerbositeitStats", () => {
	it("telt sprekerbeurten mee die geen argument opleverden, als volume-noemer", () => {
		const stats = deriveVerbositeitStats([sprekerbeurt({ char_count: 1000 }), sprekerbeurt({ char_count: 1000 })], [
			argument("factual", "pro"),
		]);
		expect(stats.nSprekerbeurten).toBe(2);
		expect(stats.nArgumenten).toBe(1);
		expect(stats.argumentenPer1000Tekens).toBeCloseTo(0.5, 5);
	});

	it("berekent claims/argument en gem. quote-lengte uit de argumentenlijst", () => {
		const arg1 = argument("factual", "pro");
		arg1.quote_text = "een citaat van tien.";
		arg1.claims = [{ claim_text: "x", attributed_source_text: null }];
		const arg2 = argument("factual", "contra");
		arg2.quote_text = "kort";

		const stats = deriveVerbositeitStats([sprekerbeurt()], [arg1, arg2]);
		expect(stats.claimsPerArgument).toBeCloseTo(0.5, 5);
		expect(stats.gemQuoteLengte).toBeCloseTo((arg1.quote_text.length + arg2.quote_text.length) / 2, 5);
	});

	it("geeft nullen terug zonder sprekerbeurten of argumenten, i.p.v. NaN/Infinity", () => {
		const stats = deriveVerbositeitStats([], []);
		expect(Object.values(stats).every((v) => Number.isFinite(v))).toBe(true);
	});

	it("msttr = totaal unieke woorden / totaal woorden, gewogen naar sprekerbeurtlengte", () => {
		const stats = deriveVerbositeitStats(
			[sprekerbeurt({ word_count: 10, unique_word_count: 8 }), sprekerbeurt({ word_count: 90, unique_word_count: 27 })],
			[],
		);
		expect(stats.msttr).toBeCloseTo((8 + 27) / (10 + 90), 5);
	});
});
