import { describe, expect, it } from "vitest";
import { renderOverlaySvg, svgToDataUrl } from "./svgOverlayRenderer";
import type { OverlayState } from "./videoOverlayState";

function baseState(overrides: Partial<OverlayState> = {}): OverlayState {
	return {
		debateTitle: null,
		debateDate: null,
		showTitleCard: false,
		introBadge: null,
		badges: [],
		nameplate: null,
		prevArgument: null,
		nextArgument: null,
		timeRangeText: null,
		...overrides,
	};
}

describe("renderOverlaySvg", () => {
	it("levert geldige SVG-opmaak op met de opgegeven afmetingen", () => {
		const svg = renderOverlaySvg(baseState(), 640, 360);
		expect(svg).toMatch(/^<svg xmlns="http:\/\/www\.w3\.org\/2000\/svg" width="640" height="360"/);
		expect(svg).toContain("</svg>");
	});

	it("tekent de titelkaart alleen als showTitleCard aan staat", () => {
		const met = renderOverlaySvg(baseState({ showTitleCard: true, debateTitle: "Stikstofdebat" }), 640, 360);
		expect(met).toContain("Stikstofdebat");
		const zonder = renderOverlaySvg(baseState({ showTitleCard: false, debateTitle: "Stikstofdebat" }), 640, 360);
		expect(zonder).not.toContain("Stikstofdebat");
	});

	it("escaped tekst tegen XML-injectie vanuit argumentdata", () => {
		const svg = renderOverlaySvg(
			baseState({ showTitleCard: true, debateTitle: `<script>alert("x")</script> & vrienden` }),
			640,
			360,
		);
		expect(svg).not.toContain("<script>");
		expect(svg).toContain("&lt;script&gt;");
		expect(svg).toContain("&amp;");
	});

	it("tekent het naamplaatje met partij", () => {
		const svg = renderOverlaySvg(baseState({ nameplate: { name: "J. Jetten", party: "D66", role_title: null } }), 640, 360);
		expect(svg).toContain("J. Jetten");
	});

	it("tekent maximaal drie badges", () => {
		const badges = ["A", "B", "C", "D"].map((label) => ({
			key: label,
			label,
			shortLabel: label,
			iconPad: null,
			color: "#888",
			tooltip: label,
		}));
		const svg = renderOverlaySvg(baseState({ badges }), 640, 360);
		expect(svg).toContain(">A<");
		expect(svg).toContain(">B<");
		expect(svg).toContain(">C<");
		expect(svg).not.toContain(">D<");
	});
});

describe("svgToDataUrl", () => {
	it("levert een decodeerbare data-URL op", () => {
		const svg = "<svg xmlns=\"http://www.w3.org/2000/svg\"></svg>";
		const url = svgToDataUrl(svg);
		expect(url.startsWith("data:image/svg+xml;charset=utf-8,")).toBe(true);
		expect(decodeURIComponent(url.split(",")[1])).toBe(svg);
	});
});
