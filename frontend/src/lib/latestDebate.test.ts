import { describe, expect, it } from "vitest";
import { findLatestDebate } from "./latestDebate";
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

// De HLS-manifest-URL van het stikstofdebat van 2026-07-01 (issue #152) --
// hasht naar debateId "yn3moz", de uitgesloten id in latestDebate.ts.
const BROKEN_RAW_VIDEO_URL =
	"https://livestreaming.b67v2.tweedekamer.nl/2026-07-01/plenairezaal/index.m3u8?hd=1&subtitles=vod&keyframes=1&start=2026-07-01T13%3A35%3A26%2B0200&end=2026-07-02T01%3A14%3A54%2B0200";

describe("findLatestDebate", () => {
	it("slaat een bekend-kapot debat over en pakt het eerstvolgende meest recente", () => {
		const broken = argument({
			id: 1,
			document: { ...argument({ id: 1 }).document, raw_video_url: BROKEN_RAW_VIDEO_URL, published_at: "2026-07-01T13:35:26" },
		});
		const working = argument({
			id: 2,
			document: { ...argument({ id: 2 }).document, raw_video_url: "https://example.com/werkend.m3u8", published_at: "2026-06-01T10:00:00" },
		});
		const result = findLatestDebate([{ slug: "stikstof", arguments: [broken, working] }]);
		expect(result?.id).not.toBe("yn3moz");
		expect(result?.earliestPublishedAt).toBe("2026-06-01T10:00:00");
	});

	it("geeft null als het enige debat het bekend-kapotte is", () => {
		const broken = argument({
			id: 1,
			document: { ...argument({ id: 1 }).document, raw_video_url: BROKEN_RAW_VIDEO_URL, published_at: "2026-07-01T13:35:26" },
		});
		expect(findLatestDebate([{ slug: "stikstof", arguments: [broken] }])).toBeNull();
	});
});
