// Gedeelde datumnotatie voor publicatiedata (DebateList.vue, VideoOverlay.vue
// -- allebei tonen ze document.published_at op dezelfde manier).
export function formatDate(iso: string | null): string {
	if (!iso) return "datum onbekend";
	return new Date(iso).toLocaleDateString("nl-NL", { day: "numeric", month: "long", year: "numeric" });
}
