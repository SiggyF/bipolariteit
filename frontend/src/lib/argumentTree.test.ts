import { describe, expect, it } from "vitest";
import {
	bandSummaries,
	kidIdsOf,
	listGroups,
	looseCount,
	oppositionPartners,
	parentOf,
	scopeOf,
	sideTotals,
	typeNl,
	type ConfrontatieExport,
	type ExportArgument,
} from "./argumentTree";

function arg(id: number, stance: "pro" | "contra", gist = `gist ${id}`): ExportArgument {
	return {
		id,
		citaat: `citaat ${id}`,
		typologie: "factual",
		stance,
		spreker: "Spreker",
		partij: null,
		tags: [],
		claims: [],
		tweedekamer_activiteit_url: null,
		raw_video_url: null,
		start_seconds: null,
		gist,
		samenvatting: null,
	};
}

// Band 1: 1 pro (met 1 onderbouwing) tegenover 1 contra. Band 2: pro is een
// verwijzing naar #3, contra heeft geen onderbouwing. Daarnaast een losse
// pro-groep, een los pro-argument en een los contra-argument.
const tree: ConfrontatieExport = {
	slug: "test",
	name: "Test",
	topic_description: null,
	stats: { totaal_argumenten: 100, aantal_pro: 60, aantal_contra: 40, aantal_geselecteerd: 8 },
	arguments: Object.fromEntries(
		[
			arg(1, "pro"),
			arg(2, "pro"),
			arg(3, "contra"),
			arg(4, "contra"),
			arg(5, "pro"),
			arg(6, "pro"),
			arg(7, "pro"),
			arg(8, "contra"),
		].map((a) => [String(a.id), a]),
	),
	bands: [
		{
			nummer: 1,
			thema: "Eerste thema",
			pro: { type: "node", id: 1, kids: [{ id: 2, scheme: null, reden: "want" }] },
			contra: { type: "node", id: 3, kids: [] },
			oppositie: { argument_a_id: 1, argument_b_id: 3, scheme: null, reden: "" },
		},
		{
			nummer: 2,
			thema: "Tweede thema",
			pro: { type: "ref", ref_id: 2, band_nummer: 1 },
			contra: { type: "node", id: 4, kids: [] },
			oppositie: null,
		},
	],
	losse_groepen: [{ kind: "group", label: "Groep A", samenvatting: "Samen", member_ids: [5, 6] }],
	losse_argumenten: [7, 8],
	twijfelachtige_classificaties: [],
};

describe("typeNl", () => {
	it("vertaalt bekende typologieën en laat onbekende ongemoeid", () => {
		expect(typeNl("legal")).toBe("juridisch");
		expect(typeNl("onbekend")).toBe("onbekend");
	});
});

describe("bandSummaries", () => {
	it("telt hoofdknoop en onderbouwing mee, en een verwijskaart niet", () => {
		expect(bandSummaries(tree)).toEqual([
			{ nummer: 1, thema: "Eerste thema", proCount: 2, contraCount: 1 },
			{ nummer: 2, thema: "Tweede thema", proCount: 0, contraCount: 1 },
		]);
	});
});

describe("sideTotals", () => {
	it("telt de uitgelichte argumenten per kant, niet de corpus-stats", () => {
		expect(sideTotals(tree)).toEqual({ pro: 5, contra: 3 });
	});
});

describe("looseCount", () => {
	it("telt groepsleden en losse argumenten, per kant of samen", () => {
		expect(looseCount(tree, "pro")).toBe(3);
		expect(looseCount(tree, "contra")).toBe(1);
		expect(looseCount(tree)).toBe(4);
	});
});

describe("listGroups", () => {
	it("toont bij 'all' eerst de banden en dan de losse argumenten van die kant", () => {
		const groups = listGroups(tree, "pro", "all");

		expect(groups.map((g) => g.key)).toEqual(["band-1", "band-2", "groep-Groep A", "los"]);
		expect(groups[0].entries).toEqual([
			{ id: 1, kind: "node" },
			{ id: 2, kind: "kid" },
		]);
		expect(groups[1].entries).toEqual([{ id: 2, kind: "ref", refBand: 1 }]);
	});

	it("beperkt zich bij één band tot die band", () => {
		const groups = listGroups(tree, "contra", 2);

		expect(groups).toHaveLength(1);
		expect(groups[0].entries).toEqual([{ id: 4, kind: "node" }]);
	});

	it("geeft bij 'loose' alleen de losse argumenten van die kant", () => {
		const groups = listGroups(tree, "contra", "loose");

		expect(groups.map((g) => g.key)).toEqual(["los"]);
		expect(groups[0].entries).toEqual([{ id: 8, kind: "node" }]);
	});

	it("neemt de samenvatting van een coördinatieve groep mee", () => {
		const group = listGroups(tree, "pro", "loose")[0];

		expect(group.title).toBe("Groep A");
		expect(group.summary).toBe("Samen");
		expect(group.entries.map((e) => e.id)).toEqual([5, 6]);
	});
});

describe("scopeOf", () => {
	it("geeft het bandnummer voor hoofdknoop en onderbouwing, en 'loose' voor de rest", () => {
		expect(scopeOf(tree, 1)).toBe(1);
		expect(scopeOf(tree, 2)).toBe(1);
		expect(scopeOf(tree, 4)).toBe(2);
		expect(scopeOf(tree, 7)).toBe("loose");
	});
});

describe("oppositionPartners", () => {
	it("legt de tegenhanger in beide richtingen vast", () => {
		const partners = oppositionPartners(tree);

		expect(partners.get(1)).toEqual([3]);
		expect(partners.get(3)).toEqual([1]);
		expect(partners.has(4)).toBe(false);
	});
});

describe("parentOf / kidIdsOf", () => {
	it("koppelt onderbouwing aan het argument dat ze onderbouwt", () => {
		expect(parentOf(tree).get(2)).toBe(1);
		expect(parentOf(tree).has(1)).toBe(false);
		expect(kidIdsOf(tree, 1)).toEqual([2]);
		expect(kidIdsOf(tree, 3)).toEqual([]);
	});
});
