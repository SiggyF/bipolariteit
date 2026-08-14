// Er is geen apart "titel van het debat"-veld in het datacontract, maar de
// slug in document.video_url (Debat Direct) bevat de titel al leesbaar, bv.
// ".../plenaire-zaal/samenhangende-aanpak-landbouw-natuur-en-stikstof-13-30/video"
// -> "Samenhangende aanpak landbouw natuur en stikstof". De laatste twee
// cijfergroepen zijn het starttijdstip (uur-minuut), geen deel van de titel.
export function debateName(videoUrl: string | null): string | null {
	if (!videoUrl) return null;
	let path: string;
	try {
		path = new URL(videoUrl).pathname;
	} catch {
		return null;
	}
	const segments = path.split("/").filter(Boolean);
	const slug = segments.at(-2);
	if (!slug) return null;
	const withoutTime = slug.replace(/-\d{1,2}-\d{2}$/, "");
	const words = withoutTime.split("-").filter(Boolean);
	if (!words.length) return null;
	const name = words.join(" ");
	return name.charAt(0).toUpperCase() + name.slice(1);
}
