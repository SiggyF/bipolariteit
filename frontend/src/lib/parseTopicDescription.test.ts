import { describe, expect, it } from "vitest";
import { parseTopicDescription } from "./parseTopicDescription";
import stikstof from "../../../data/export/topics/stikstof.json";
import abortus from "../../../data/export/topics/abortus.json";

describe("parseTopicDescription", () => {
	it("splitst stikstof (intro + pro + contra + disclaimer)", () => {
		const parsed = parseTopicDescription(stikstof.description as string);
		expect(parsed.intro).toHaveLength(1);
		expect(parsed.intro[0]).toMatch(/^Dit debat gaat over het Nederlandse stikstofbeleid/);
		expect(parsed.pro).toMatch(/^voorstander van verplichtende, stevige stikstofreductie/);
		expect(parsed.contra).toMatch(/^voorstander van afzwakking, uitstel/);
		expect(parsed.note).toMatch(/^Let op: dit is puur een classificatie-hulpmiddel/);
	});

	it("splitst abortus (intro + pro + contra, geen disclaimer)", () => {
		const parsed = parseTopicDescription(abortus.description as string);
		expect(parsed.pro).toMatch(/^pleit voor het schrappen van abortus/);
		expect(parsed.contra).toMatch(/^pleit voor behoud van abortus/);
		expect(parsed.note).toBeNull();
	});

	it("normaliseert word-wrap-newlines binnen een alinea naar spaties", () => {
		const parsed = parseTopicDescription("Regel een.\nRegel twee.\n\nPRO = a.\n\nCONTRA = b.");
		expect(parsed.intro).toEqual(["Regel een. Regel twee."]);
	});

	it("valt terug op alleen intro als PRO/CONTRA ontbreekt", () => {
		const parsed = parseTopicDescription("Gewone beschrijving zonder pro/contra-structuur.");
		expect(parsed.pro).toBeNull();
		expect(parsed.contra).toBeNull();
		expect(parsed.intro).toEqual(["Gewone beschrijving zonder pro/contra-structuur."]);
	});
});
