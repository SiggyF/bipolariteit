import { describe, expect, it } from "vitest";
import { requestSeek, videoSeek } from "./videoSeek";

describe("requestSeek", () => {
	it("zet seconds en verhoogt token", () => {
		const startToken = videoSeek.token;
		requestSeek(42);
		expect(videoSeek.seconds).toBe(42);
		expect(videoSeek.token).toBe(startToken + 1);
	});

	it("verhoogt token ook als seconds ongewijzigd blijft", () => {
		requestSeek(42);
		const token = videoSeek.token;
		requestSeek(42);
		expect(videoSeek.token).toBe(token + 1);
	});
});
