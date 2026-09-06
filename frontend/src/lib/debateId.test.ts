import { describe, expect, it } from "vitest";
import { debateId, groupByDebateId } from "./debateId";
import type { Argument } from "./types";

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
			raw_video_url: null,
		},
		periode: { kamer: null, regering: null },
		claims: [],
		tags: [],
		...overrides,
	};
}

describe("debateId", () => {
	it("is stabiel voor dezelfde url", () => {
		const url = "https://livestreaming.b67v2.tweedekamer.nl/2026-02-10/thorbeckezaal/index.m3u8?hd=1";
		expect(debateId(url)).toBe(debateId(url));
	});

	it("verschilt tussen verschillende urls", () => {
		const a = "https://livestreaming.b67v2.tweedekamer.nl/2026-02-10/thorbeckezaal/index.m3u8?hd=1";
		const b = "https://livestreaming.b67v2.tweedekamer.nl/2026-02-11/thorbeckezaal/index.m3u8?hd=1";
		expect(debateId(a)).not.toBe(debateId(b));
	});

	it("is url-veilig (alleen alfanumeriek)", () => {
		expect(debateId("https://x/y?z=1&start=2026-01-01T00%3A00%3A00")).toMatch(/^[a-z0-9]+$/);
	});
});

describe("groupByDebateId", () => {
	const urlA = "https://livestreaming.b67v2.tweedekamer.nl/2026-02-10/thorbeckezaal/index.m3u8?hd=1";
	const urlB = "https://livestreaming.b67v2.tweedekamer.nl/2026-02-11/thorbeckezaal/index.m3u8?hd=1";
	const idA = debateId(urlA);
	const idB = debateId(urlB);

	it("groepeert per debat", () => {
		const list = [
			argument({ id: 1, document: { ...argument({ id: 1 }).document, raw_video_url: urlA } }),
			argument({ id: 2, document: { ...argument({ id: 2 }).document, raw_video_url: urlB } }),
			argument({ id: 3, document: { ...argument({ id: 3 }).document, raw_video_url: urlA } }),
		];
		const groups = groupByDebateId(list);
		expect(groups.get(idA)?.map((a) => a.id)).toEqual([1, 3]);
		expect(groups.get(idB)?.map((a) => a.id)).toEqual([2]);
	});

	it("laat argumenten zonder raw_video_url weg", () => {
		const list = [argument({ id: 1 })];
		expect(groupByDebateId(list).size).toBe(0);
	});

	it("sorteert elke groep op start_seconds, argumenten zonder videospanne achteraan", () => {
		const doc = { ...argument({ id: 0 }).document, raw_video_url: urlA };
		const list = [
			argument({ id: 1, document: doc, start_seconds: 30 }),
			argument({ id: 2, document: doc, start_seconds: null }),
			argument({ id: 3, document: doc, start_seconds: 10 }),
		];
		expect(groupByDebateId(list).get(idA)?.map((a) => a.id)).toEqual([3, 1, 2]);
	});
});
