import { describe, expect, it } from "vitest";
import { contourColor, contourNames, selectContours, type ContourCollection } from "./contours";

function feature(props: Record<string, unknown>) {
	return {
		type: "Feature" as const,
		properties: { n: 0, color: "#000", threshold: 1.5, ...props },
		geometry: { type: "Polygon" as const, coordinates: [] },
	};
}

const collection = {
	type: "FeatureCollection",
	features: [
		feature({ actor: "A", n: 100, threshold: 1.5 }),
		feature({ actor: "A", n: 100, threshold: 3 }),
		feature({ actor: "B", n: 500, threshold: 1.5 }),
	],
} as ContourCollection;

describe("contourNames", () => {
	it("geeft elke naam één keer, grootste eerst", () => {
		expect(contourNames(collection, "actor")).toEqual([
			{ name: "B", n: 500 },
			{ name: "A", n: 100 },
		]);
	});
});

describe("selectContours", () => {
	it("pakt alle drempels van de gekozen groep", () => {
		const result = selectContours([{ kind: "actor", collection, name: "A" }]);
		expect(result.features).toHaveLength(2);
	});

	it("negeert lege keuzes en nog niet geladen data", () => {
		const result = selectContours([
			{ kind: "actor", collection, name: null },
			{ kind: "party", collection: null, name: "VVD" },
		]);
		expect(result.features).toHaveLength(0);
	});
});

describe("contourColor", () => {
	it("gebruikt color_dark alleen op het donkere thema", () => {
		const props = { color: "#171c60", color_dark: "#ffd000" };
		expect(contourColor(props, true)).toBe("#ffd000");
		expect(contourColor(props, false)).toBe("#171c60");
	});

	it("valt terug op color als er geen donkere variant is", () => {
		expect(contourColor({ color: "#f47d20" }, true)).toBe("#f47d20");
	});
});
