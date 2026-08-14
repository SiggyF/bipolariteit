import { describe, expect, it } from "vitest";
import { formatClock } from "./videoTime";

describe("formatClock", () => {
	it("formatteert onder het uur als m:ss", () => {
		expect(formatClock(0)).toBe("0:00");
		expect(formatClock(65)).toBe("1:05");
	});

	it("formatteert vanaf een uur als h:mm:ss", () => {
		expect(formatClock(3661)).toBe("1:01:01");
	});

	it("klemt negatieve waarden op 0", () => {
		expect(formatClock(-5)).toBe("0:00");
	});
});
