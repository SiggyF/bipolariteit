import { describe, expect, it } from "vitest";
import { activeArguments, nextArgumentAfter, prevArgumentBefore, selectBadgeTags } from "./videoLabels";
import type { Argument, Tag } from "./types";

function tag(sleutel: string, perspectief = "Filosofisch & Argumentatietheoretisch"): Tag {
	return { sleutel, beschrijving: "", labelgroep: "", perspectief, created_by: "llm", reden: null };
}

function argument(overrides: Partial<Argument> & { id: number }): Argument {
	return {
		stance: "pro",
		typology: "factual",
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
		...overrides,
	};
}

describe("activeArguments", () => {
	const a = argument({ id: 1, start_seconds: 10, end_seconds: 20 });
	const b = argument({ id: 2, start_seconds: 15, end_seconds: 30 });
	const withoutSpan = argument({ id: 3 });
	const args = [a, b, withoutSpan];

	it("bevat argumenten waarvan t binnen de spanne valt, grenzen inclusief", () => {
		expect(activeArguments(args, 10).map((x) => x.id)).toEqual([1]);
		expect(activeArguments(args, 20).map((x) => x.id)).toEqual([1, 2]);
	});

	it("kan meerdere overlappende argumenten tegelijk actief hebben", () => {
		expect(activeArguments(args, 17).map((x) => x.id)).toEqual([1, 2]);
	});

	it("negeert argumenten zonder spanne", () => {
		expect(activeArguments(args, 0).map((x) => x.id)).toEqual([]);
	});

	it("levert niets buiten elke spanne", () => {
		expect(activeArguments(args, 100)).toEqual([]);
	});
});

describe("nextArgumentAfter", () => {
	const a = argument({ id: 1, start_seconds: 10, end_seconds: 20 });
	const b = argument({ id: 2, start_seconds: 30, end_seconds: 40 });
	const withoutSpan = argument({ id: 3 });
	const args = [b, withoutSpan, a]; // bewust niet al gesorteerd

	it("vindt het eerstvolgende argument na de gegeven tijd", () => {
		expect(nextArgumentAfter(args, 5)?.id).toBe(1);
		expect(nextArgumentAfter(args, 10)?.id).toBe(2);
	});

	it("negeert argumenten zonder spanne", () => {
		expect(nextArgumentAfter(args, 25)?.id).toBe(2);
	});

	it("levert null als er niets meer na deze tijd komt", () => {
		expect(nextArgumentAfter(args, 100)).toBeNull();
	});
});

describe("prevArgumentBefore", () => {
	const a = argument({ id: 1, start_seconds: 10, end_seconds: 20 });
	const b = argument({ id: 2, start_seconds: 30, end_seconds: 40 });
	const withoutSpan = argument({ id: 3 });
	const args = [b, withoutSpan, a];

	it("vindt het laatste argument vóór de gegeven tijd", () => {
		expect(prevArgumentBefore(args, 35)?.id).toBe(2);
		expect(prevArgumentBefore(args, 30)?.id).toBe(1);
	});

	it("negeert argumenten zonder spanne", () => {
		expect(prevArgumentBefore(args, 15)?.id).toBe(1);
	});

	it("levert null als er niets vóór deze tijd is", () => {
		expect(prevArgumentBefore(args, 0)).toBeNull();
	});
});

describe("selectBadgeTags", () => {
	it("sorteert op zeldzaamheid binnen het debat en capt op 3", () => {
		const common = tag("Actor-Politicus");
		const rare = tag("Ad-Hominem");
		const medium = tag("Framing");
		const extra = tag("Nog-Een-Tag");

		const target = argument({ id: 1, tags: [common, rare, medium, extra] });
		const debate = [
			target,
			argument({ id: 2, tags: [common, medium] }),
			argument({ id: 3, tags: [common] }),
		];

		const result = selectBadgeTags(target, debate).map((t) => t.sleutel);
		expect(result).toEqual(["Ad-Hominem", "Nog-Een-Tag", "Framing"]);
	});

	it("gebruikt perspectief als tie-break bij gelijke frequentie", () => {
		const x = tag("X", "Zoveelste");
		const y = tag("Y", "Alfabetisch-eerste");
		const target = argument({ id: 1, tags: [x, y] });

		const result = selectBadgeTags(target, [target]).map((t) => t.sleutel);
		expect(result).toEqual(["Y", "X"]);
	});
});
