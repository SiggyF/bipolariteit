import { describe, expect, it } from "vitest";
import { debateThumbnailUrl } from "./debateThumbnail";

const VIDEO_URL = "https://debatdirect.tweedekamer.nl/2025-06-26/overig/plenaire-zaal/asielnoodmaatregelenwet-13-45/video";

describe("debateThumbnailUrl", () => {
	it("bouwt een zomertijd-URL (+0200) op het gegeven moment", () => {
		expect(debateThumbnailUrl(VIDEO_URL, "2025-06-26T13:05:08", 0)).toBe(
			"https://livestreaming-thumb.b67buv2.tweedekamer.nl/plenaire-zaal/1080/2025-06-26/13:05:08+0200.jpg",
		);
	});

	it("bouwt een wintertijd-URL (+0100)", () => {
		const winterVideoUrl = "https://debatdirect.tweedekamer.nl/2025-02-20/huisvesting/plenaire-zaal/stikstofontwikkelingen-15-00/video";
		expect(debateThumbnailUrl(winterVideoUrl, "2025-02-20T16:04:53", 0)).toBe(
			"https://livestreaming-thumb.b67buv2.tweedekamer.nl/plenaire-zaal/1080/2025-02-20/16:04:53+0100.jpg",
		);
	});

	it("telt start_seconds op en rolt over naar de volgende dag", () => {
		expect(debateThumbnailUrl(VIDEO_URL, "2025-06-26T23:30:00", 3600)).toBe(
			"https://livestreaming-thumb.b67buv2.tweedekamer.nl/plenaire-zaal/1080/2025-06-27/00:30:00+0200.jpg",
		);
	});

	it("geeft null zonder video_url", () => {
		expect(debateThumbnailUrl(null, "2025-06-26T13:05:08", 0)).toBeNull();
	});

	it("geeft null zonder published_at", () => {
		expect(debateThumbnailUrl(VIDEO_URL, null, 0)).toBeNull();
	});

	it("geeft null zonder start_seconds", () => {
		expect(debateThumbnailUrl(VIDEO_URL, "2025-06-26T13:05:08", null)).toBeNull();
	});
});
