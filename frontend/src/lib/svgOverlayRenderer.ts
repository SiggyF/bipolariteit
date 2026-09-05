import type { OverlayState } from "./videoOverlayState";
import { displayPartyName } from "./videoOverlayState";

// Eén schaalbare SVG-eenheid voor de video-export (issue #179/#180): i.p.v.
// losse HTML/CSS-elementen met individueel afgestemde clamp()-waarden, hier
// één viewBox="0 0 W H" die op elke canvasgrootte proportioneel meeschaalt.
// Dit is bewust een vereenvoudigde, exportgerichte weergave -- niet
// pixel-identiek aan VideoOverlay.vue's live CSS/transities -- want die
// bestaan puur voor het live scherm (container queries, badge-animaties);
// een 10s-clip heeft daar niets aan en pixel-parity zou een veel grotere
// herbouw vergen dan issue #180 vraagt.

function escapeXml(text: string): string {
	return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

export function renderOverlaySvg(state: OverlayState, width: number, height: number): string {
	const parts: string[] = [];
	parts.push(`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`);

	const pad = Math.round(width * 0.02);
	const fontTitle = Math.round(width * 0.032);
	const fontName = Math.round(width * 0.026);
	const fontSmall = Math.round(width * 0.02);

	if (state.showTitleCard && state.debateTitle) {
		const cardWidth = Math.round(width * 0.9);
		const cardHeight = Math.round(fontTitle * 1.8);
		const cardX = Math.round((width - cardWidth) / 2);
		parts.push(
			`<rect x="${cardX}" y="${pad}" width="${cardWidth}" height="${cardHeight}" rx="6" fill="rgba(0,0,0,0.6)"/>`,
			`<text x="${width / 2}" y="${pad + cardHeight / 2 + fontTitle * 0.35}" fill="#fff" font-family="sans-serif" font-weight="bold" font-size="${fontTitle}" text-anchor="middle">${escapeXml(state.debateTitle)}</text>`,
		);
	}

	if (state.nameplate) {
		const plateY = height - pad - fontName * 1.8;
		const label = state.nameplate.party
			? `${state.nameplate.name} (${displayPartyName(state.nameplate.party)})`
			: state.nameplate.role_title
				? `${state.nameplate.name} · ${state.nameplate.role_title}`
				: state.nameplate.name;
		const plateWidth = Math.min(width * 0.8, label.length * fontName * 0.62 + pad * 2);
		parts.push(
			`<rect x="${pad}" y="${plateY}" width="${plateWidth}" height="${fontName * 1.6}" rx="4" fill="#1a73e8"/>`,
			`<text x="${pad * 1.5}" y="${plateY + fontName * 1.15}" fill="#fff" font-family="sans-serif" font-size="${fontName}">${escapeXml(label)}</text>`,
		);
	}

	const badgeHeight = fontSmall * 1.9;
	let badgeY = pad;
	for (const badge of state.badges.slice(0, 3)) {
		const badgeWidth = Math.min(width * 0.55, badge.shortLabel.length * fontSmall * 0.62 + badgeHeight + pad);
		const badgeX = width - pad - badgeWidth;
		parts.push(
			`<g>`,
			`<rect x="${badgeX}" y="${badgeY}" width="${badgeWidth}" height="${badgeHeight}" rx="${badgeHeight / 2}" fill="rgba(20,18,15,0.75)"/>`,
			`<circle cx="${badgeX + badgeHeight / 2}" cy="${badgeY + badgeHeight / 2}" r="${badgeHeight * 0.4}" fill="${badge.color}"/>`,
		);
		if (badge.iconPad) {
			const iconSize = badgeHeight * 0.55;
			const iconX = badgeX + badgeHeight / 2 - iconSize / 2;
			const iconY = badgeY + badgeHeight / 2 - iconSize / 2;
			parts.push(
				`<svg x="${iconX}" y="${iconY}" width="${iconSize}" height="${iconSize}" viewBox="0 0 24 24"><path d="${badge.iconPad}" fill="none" stroke="#fff" stroke-width="2"/></svg>`,
			);
		}
		parts.push(
			`<text x="${badgeX + badgeHeight + pad * 0.3}" y="${badgeY + badgeHeight / 2 + fontSmall * 0.35}" fill="#fff" font-family="sans-serif" font-size="${fontSmall}">${escapeXml(badge.shortLabel)}</text>`,
			`</g>`,
		);
		badgeY += badgeHeight + pad * 0.4;
	}

	parts.push(`</svg>`);
	return parts.join("");
}

export function svgToDataUrl(svg: string): string {
	return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
}
