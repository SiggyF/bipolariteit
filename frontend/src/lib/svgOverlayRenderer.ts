import type { OverlayState } from "./videoOverlayState";
import { displayPartyName } from "./videoOverlayState";
import { partyLogoSimple } from "./parties";

// Eén schaalbare SVG-eenheid voor de video-export (issue #179/#180), die de
// bestaande, door een designer gemaakte stijl van VideoOverlay.vue's
// live CSS overneemt (kleuren/lettertypen/vormen 1:1 uit
// frontend/src/styles/main.css en VideoOverlay.vue's <style>) -- geen eigen
// nieuwe vormgeving. Wel noodgedwongen met vaste, aan de breedte gekoppelde
// afmetingen i.p.v. VideoOverlay.vue's cqw/clamp()/container-queries: die
// bestaan niet in kale SVG zonder foreignObject (en foreignObject brengt de
// DOM-rasterization-beperkingen terug die dit hele bestand net vermijdt).

const FONT_HEADING = "'Libre Caslon Text', Georgia, serif";
const FONT_MONO = "'IBM Plex Mono', ui-monospace, 'SFMono-Regular', Menlo, monospace";

function escapeXml(text: string): string {
	return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

export function renderOverlaySvg(state: OverlayState, width: number, height: number): string {
	const parts: string[] = [];
	parts.push(`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`);

	// Zelfde scrim als .video-overlay: linear-gradient(to top, rgba(0,0,0,0.55)
	// 0%, rgba(0,0,0,0) 30%) -- zonder dit oogde tekst zonder eigen kader
	// (het naamplaatje) te weinig contrasterend tegen een lichte video-achtergrond.
	parts.push(
		`<defs><linearGradient id="scrim" x1="0" y1="1" x2="0" y2="0">` +
			`<stop offset="0" stop-color="rgba(0,0,0,0.55)"/>` +
			`<stop offset="0.3" stop-color="rgba(0,0,0,0)"/>` +
			`</linearGradient></defs>`,
		`<rect x="0" y="0" width="${width}" height="${height}" fill="url(#scrim)"/>`,
	);

	const pad = Math.round(width * 0.02);
	const fontTitle = Math.round(width * 0.032);
	const fontName = Math.round(width * 0.026);
	const fontSmall = Math.round(width * 0.02);

	// Titelkaart: zelfde rgba(0,0,0,0.55)-kader als .title-card, gecentreerd
	// bovenaan.
	if (state.showTitleCard && state.debateTitle) {
		const cardWidth = Math.round(width * 0.9);
		const cardHeight = Math.round(fontTitle * 1.8);
		const cardX = Math.round((width - cardWidth) / 2);
		parts.push(
			`<rect x="${cardX}" y="${pad}" width="${cardWidth}" height="${cardHeight}" rx="4" fill="rgba(0,0,0,0.55)"/>`,
			`<text x="${width / 2}" y="${pad + cardHeight / 2 + fontTitle * 0.35}" fill="#fff" font-family="${FONT_HEADING}" font-weight="bold" font-size="${fontTitle}" text-anchor="middle">${escapeXml(state.debateTitle)}</text>`,
		);
	}

	// Naamplaatje: GEEN kader (i.p.v. de vorige, verzonnen blauwe balk) --
	// .header-row/.nameplate-* in VideoOverlay.vue tekenen alleen tekst +
	// logo op de scrim hierboven, net als op de echte pagina.
	if (state.nameplate) {
		const baseline = height - pad - fontName * 0.3;
		let x = pad;
		parts.push(
			`<text x="${x}" y="${baseline}" fill="#fff" font-family="${FONT_HEADING}" font-style="italic" font-size="${fontName}">${escapeXml(state.nameplate.name)}</text>`,
		);
		x += state.nameplate.name.length * fontName * 0.52 + fontName * 0.4;

		if (state.nameplate.party) {
			const logoHref = partyLogoSimple(state.nameplate.party);
			if (logoHref) {
				const logoSize = fontName * 0.9;
				parts.push(
					`<image href="${logoHref}" x="${x}" y="${baseline - logoSize * 0.8}" width="${logoSize}" height="${logoSize}" style="filter:saturate(0.6)"/>`,
				);
				x += logoSize + fontName * 0.3;
			}
			parts.push(
				`<text x="${x}" y="${baseline}" fill="rgba(255,255,255,0.7)" font-family="${FONT_MONO}" font-size="${fontName * 0.75}" letter-spacing="1">${escapeXml(displayPartyName(state.nameplate.party).toUpperCase())}</text>`,
			);
		} else if (state.nameplate.role_title) {
			parts.push(
				`<text x="${x}" y="${baseline}" fill="rgba(255,255,255,0.7)" font-family="${FONT_MONO}" font-size="${fontName * 0.75}" letter-spacing="1">${escapeXml(state.nameplate.role_title.toUpperCase())}</text>`,
			);
		}
	}

	// Tag-badges: zelfde donkere kaart + gekleurde border-left + icoon-cirkel
	// als .badge in VideoOverlay.vue, i.p.v. de vorige (verzonnen) volle pil.
	const badgeHeight = Math.round(fontSmall * 1.9);
	let badgeY = pad;
	for (const badge of state.badges.slice(0, 3)) {
		const badgeWidth = Math.min(width * 0.55, badge.shortLabel.length * fontSmall * 0.6 + badgeHeight + pad * 1.5);
		const badgeX = width - pad - badgeWidth;
		parts.push(
			`<g>`,
			`<rect x="${badgeX}" y="${badgeY}" width="${badgeWidth}" height="${badgeHeight}" rx="3" fill="rgba(20,18,15,0.65)"/>`,
			`<rect x="${badgeX}" y="${badgeY}" width="2" height="${badgeHeight}" fill="${badge.color}"/>`,
			`<circle cx="${badgeX + badgeHeight / 2 + 4}" cy="${badgeY + badgeHeight / 2}" r="${badgeHeight * 0.4}" fill="${badge.color}"/>`,
		);
		if (badge.iconPad) {
			const iconSize = badgeHeight * 0.5;
			const iconX = badgeX + badgeHeight / 2 + 4 - iconSize / 2;
			const iconY = badgeY + badgeHeight / 2 - iconSize / 2;
			parts.push(
				`<svg x="${iconX}" y="${iconY}" width="${iconSize}" height="${iconSize}" viewBox="0 0 24 24"><path d="${badge.iconPad}" fill="none" stroke="#fff" stroke-width="2"/></svg>`,
			);
		}
		parts.push(
			`<text x="${badgeX + badgeHeight + 6}" y="${badgeY + badgeHeight / 2 + fontSmall * 0.35}" fill="#fff" font-family="${FONT_HEADING}" font-size="${fontSmall}">${escapeXml(badge.shortLabel)}</text>`,
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
