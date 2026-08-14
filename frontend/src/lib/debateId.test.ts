import { describe, expect, it } from "vitest";
import { debateId } from "./debateId";

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
