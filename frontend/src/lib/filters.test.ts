import { afterEach, describe, expect, it } from "vitest";
import { currentKamerperiode, filters, matches } from "./filters";
import type { Argument } from "./types";
import topic from "../../../data/export/topics/stikstof.json";

const basis = (topic.arguments as unknown as Argument[])[0];

function argumentMetCitaat(quote_text: string): Argument {
	return { ...basis, quote_text };
}

function argumentMetPeriode(kamer: string | null, published_at: string | null): Argument {
	return {
		...basis,
		periode: { ...basis.periode, kamer },
		document: { ...basis.document, published_at },
	};
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

describe("currentKamerperiode()", () => {
	it("kiest de kamerperiode van het argument met de meest recente publicatiedatum", () => {
		const argumenten = [
			argumentMetPeriode("Tweede Kamer 2023-2025", "2024-05-01T10:00:00"),
			argumentMetPeriode("Tweede Kamer 2025-heden", "2025-12-01T10:00:00"),
			argumentMetPeriode("Tweede Kamer 2021-2023", "2022-01-01T10:00:00"),
		];
		expect(currentKamerperiode(argumenten)).toBe("Tweede Kamer 2025-heden");
	});

	it("negeert argumenten zonder periode of publicatiedatum", () => {
		const argumenten = [
			argumentMetPeriode(null, null),
			argumentMetPeriode("Tweede Kamer 2023-2025", "2024-05-01T10:00:00"),
		];
		expect(currentKamerperiode(argumenten)).toBe("Tweede Kamer 2023-2025");
	});

	it("levert null op zonder argumenten met periode", () => {
		expect(currentKamerperiode([argumentMetPeriode(null, null)])).toBeNull();
		expect(currentKamerperiode([])).toBeNull();
	});
});
