// Eén "debat" (issue #94) is één raw_video_url (het HLS-manifest), niet één
// document.id: elke spreekbeurt heeft een eigen document-rij, maar deelt de
// raw_video_url met alle andere spreekbeurten in datzelfde debat. Overal waar
// we naar /debat/[id]/ linken of die route opbouwen, moet dezelfde sleutel
// gebruikt worden -- vandaar deze ene functie i.p.v. m.document.id te pakken.
// FNV-1a, 32-bit: geen cryptografische eis, alleen een korte, stabiele,
// URL-veilige sleutel per raw_video_url.
export function debateId(rawVideoUrl: string): string {
	let hash = 0x811c9dc5;
	for (let i = 0; i < rawVideoUrl.length; i++) {
		hash ^= rawVideoUrl.charCodeAt(i);
		hash = Math.imul(hash, 0x01000193);
	}
	return (hash >>> 0).toString(36);
}
