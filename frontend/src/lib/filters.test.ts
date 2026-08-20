import { afterEach, describe, expect, it } from "vitest";
import { filters, matches } from "./filters";
import type { Argument } from "./types";
import topic from "../../../data/export/topics/stikstof.json";

const basis = (topic.arguments as unknown as Argument[])[0];

function argumentMetCitaat(quote_text: string): Argument {
	return { ...basis, quote_text };
}

afterEach(() => {
	filters.q = "";
});

describe("matches() met vrije tekstzoek", () => {
	it("een lege zoekopdracht filtert niets uit", () => {
		expect(matches(argumentMetCitaat("Stikstofcompensatie is nodig voor de natuur."))).toBe(true);
	});

	it("matcht hoofdletterongevoelig op een deelwoord", () => {
		filters.q = "STIKSTOFCOMPENSATIE";
		expect(matches(argumentMetCitaat("De stikstofcompensatie moet beter geregeld worden."))).toBe(true);
	});

	it("matcht accentongevoelig", () => {
		filters.q = "voor de boeren";
		expect(matches(argumentMetCitaat("Dit is vóór de boeren een goede zaak."))).toBe(true);
	});

	it("vereist alle woorden (AND), los van volgorde", () => {
		filters.q = "boeren stikstof";
		expect(matches(argumentMetCitaat("De stikstofregels raken de boeren hard."))).toBe(true);
		expect(matches(argumentMetCitaat("De regels raken de boeren hard.")))
			.toBe(false);
	});

	it("levert geen match op als het woord niet voorkomt", () => {
		filters.q = "asielbeleid";
		expect(matches(argumentMetCitaat("De stikstofcompensatie moet beter geregeld worden."))).toBe(false);
	});
});
