import { describe, expect, it } from "vitest";
import { buildOverlayState } from "./videoOverlayState";
import type { Argument, Tag } from "./types";

function tag(sleutel: string, perspectief = "Filosofisch & Argumentatietheoretisch"): Tag {
	return { sleutel, beschrijving: "", labelgroep: "groep", perspectief, created_by: "llm", reden: null };
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

const alwaysVisible = () => true;

describe("buildOverlayState", () => {
	it("toont het naamplaatje van het actieve argument", () => {
		const a = argument({ id: 1, start_seconds: 10, end_seconds: 20, actor: { name: "J. Jetten", party: "D66", role_title: null } });
		const state = buildOverlayState([a], 15, alwaysVisible);
		expect(state.nameplate).toEqual({ name: "J. Jetten", party: "D66", role_title: null });
	});

	it("valt terug op het laatst gestarte argument in een gat tussen twee argumenten", () => {
		const a = argument({ id: 1, start_seconds: 10, end_seconds: 20, actor: { name: "Eerst", party: null, role_title: null } });
		const b = argument({ id: 2, start_seconds: 30, end_seconds: 40, actor: { name: "Later", party: null, role_title: null } });
		const state = buildOverlayState([a, b], 25, alwaysVisible);
		expect(state.nameplate?.name).toBe("Eerst");
	});

	it("levert tot drie badges van het actieve argument", () => {
		const a = argument({
			id: 1,
			start_seconds: 10,
			end_seconds: 20,
			tags: [tag("A"), tag("B"), tag("C"), tag("D")],
		});
		const state = buildOverlayState([a], 15, alwaysVisible);
		expect(state.badges).toHaveLength(3);
	});

	it("respecteert de isVisible-filter (uitgezet perspectief)", () => {
		const a = argument({ id: 1, start_seconds: 10, end_seconds: 20, tags: [tag("A", "Filosofisch"), tag("B", "Juridisch")] });
		const state = buildOverlayState([a], 15, (t) => t.perspectief !== "Juridisch");
		expect(state.badges.map((b) => b.label)).toEqual(["A"]);
	});

	it("toont de titelkaart alleen in de eerste seconden", () => {
		const a = argument({ id: 1, document: { ...argument({ id: 1 }).document, video_url: "https://debatdirect.tweedekamer.nl/2026-01-01/x/plenaire-zaal/mijn-debat-10-00/video" } });
		expect(buildOverlayState([a], 0, alwaysVisible).showTitleCard).toBe(true);
		expect(buildOverlayState([a], 10, alwaysVisible).showTitleCard).toBe(false);
	});

	it("vindt vorig/volgend argument in een gat tussen twee argumenten", () => {
		const a = argument({ id: 1, start_seconds: 10, end_seconds: 20 });
		const b = argument({ id: 2, start_seconds: 30, end_seconds: 40 });
		const state = buildOverlayState([a, b], 25, alwaysVisible);
		expect(state.prevArgument?.id).toBe(1);
		expect(state.nextArgument?.id).toBe(2);
	});
});
