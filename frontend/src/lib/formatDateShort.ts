// Korte datumnotatie ("1 jul") voor de compacte debatkaart-rijen (#112) --
// de volledige formatDate() ("1 juli 2026") is te breed voor een dichte
// lijst van tientallen rijen.
export function formatDateShort(iso: string | null): string {
	if (!iso) return "onbekend";
	return new Date(iso).toLocaleDateString("nl-NL", { day: "numeric", month: "short" });
}
