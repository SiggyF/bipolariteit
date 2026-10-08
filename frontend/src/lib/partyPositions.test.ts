import { describe, expect, it } from "vitest";
import { groupPartyPositions, type TopicPartyCount } from "./partyPositions";

function count(party: string, pro: number, contra: number, unclear = 0): TopicPartyCount {
	return { party, pro, contra, unclear };
}

describe("groupPartyPositions", () => {
	it("sorteert partijen naar hun dominante stance-kolom, op dominante telling aflopend", () => {
		const result = groupPartyPositions([count("BBB", 10, 90), count("D66", 80, 5), count("SP", 20, 30)]);

		expect(result.pro.map((p) => p.party)).toEqual(["D66"]);
		expect(result.contra.map((p) => p.party)).toEqual(["BBB", "SP"]);
	});

	it("laat partijen met dominante 'unclear'-stance buiten beide kolommen", () => {
		const result = groupPartyPositions([count("DENK", 2, 1, 9)]);

		expect(result.pro).toEqual([]);
		expect(result.contra).toEqual([]);
	});

	it("knipt elke kolom af op de top 4 en telt de rest", () => {
		const parties = ["A", "B", "C", "D", "E", "F"].map((party, i) => count(party, 100 - i, 0));
		const result = groupPartyPositions(parties);

		expect(result.pro).toHaveLength(4);
		expect(result.pro.map((p) => p.party)).toEqual(["A", "B", "C", "D"]);
		expect(result.proRest).toBe(2);
		expect(result.contraRest).toBe(0);
	});

	it("gebruikt de telling van de dominante stance, niet het totaal", () => {
		const result = groupPartyPositions([count("VVD", 5, 20)]);

		expect(result.contra).toEqual([{ party: "VVD", count: 20 }]);
	});
});
