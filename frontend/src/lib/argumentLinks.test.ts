import { describe, expect, it } from "vitest";
import { externalArgumentLinks, internalVideoLink } from "./argumentLinks";

describe("externalArgumentLinks", () => {
	it("levert niets op zonder brondatavelden", () => {
		expect(
			externalArgumentLinks({
				tweedekamer_activiteit_url: null,
				document_url: null,
				speaker_video_url: null,
				video_url: null,
			}),
		).toEqual([]);
	});

	it("zet Tweede Kamer, XML en video (dit moment) in vaste volgorde", () => {
		const links = externalArgumentLinks({
			tweedekamer_activiteit_url: "https://tweedekamer.nl/activiteit",
			document_url: "https://tweedekamer.nl/document.xml",
			speaker_video_url: "https://tweedekamer.nl/video?t=123",
			video_url: "https://tweedekamer.nl/video",
		});
		expect(links.map((l) => l.key)).toEqual(["tweedekamer", "xml", "video-extern"]);
		expect(links.every((l) => l.external)).toBe(true);
		expect(links[2].href).toBe("https://tweedekamer.nl/video?t=123");
		expect(links[2].label).toBe("video op tweedekamer.nl (dit moment)");
	});

	it("valt terug op video_url (heel debat) zonder speaker_video_url", () => {
		const links = externalArgumentLinks({
			tweedekamer_activiteit_url: null,
			document_url: null,
			speaker_video_url: null,
			video_url: "https://tweedekamer.nl/video",
		});
		expect(links).toEqual([
			{
				key: "video-extern",
				href: "https://tweedekamer.nl/video",
				label: "video op tweedekamer.nl (heel debat)",
				title: undefined,
				external: true,
			},
		]);
	});

	it("toont nooit beide video-varianten tegelijk", () => {
		const links = externalArgumentLinks({
			tweedekamer_activiteit_url: null,
			document_url: null,
			speaker_video_url: "https://tweedekamer.nl/video?t=1",
			video_url: "https://tweedekamer.nl/video",
		});
		expect(links.filter((l) => l.key === "video-extern")).toHaveLength(1);
	});
});

describe("internalVideoLink", () => {
	it("is null zonder raw_video_url", () => {
		expect(internalVideoLink(null, 42)).toBeNull();
	});

	it("linkt met tijdstempel als start_seconds bekend is", () => {
		const link = internalVideoLink("https://example.org/hls/manifest.m3u8", 42.9);
		expect(link?.href).toMatch(/^\/debatten\/[a-z0-9]+\/\?t=42$/);
		expect(link?.external).toBe(false);
		expect(link?.label).toBe("bekijk dit moment in videospeler");
	});

	it("linkt zonder tijdstempel als start_seconds ontbreekt", () => {
		const link = internalVideoLink("https://example.org/hls/manifest.m3u8", null);
		expect(link?.href).toMatch(/^\/debatten\/[a-z0-9]+\/$/);
		expect(link?.label).toBe("bekijk in videospeler");
	});

	it("gebruikt dezelfde debateId voor dezelfde raw_video_url", () => {
		const url = "https://example.org/hls/manifest.m3u8";
		expect(internalVideoLink(url, 10)?.href.split("?")[0]).toBe(internalVideoLink(url, null)?.href);
	});
});
