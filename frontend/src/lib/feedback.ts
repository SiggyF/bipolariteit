// Lokale feedback-opslag (localStorage) voor argumentbeoordelingen door bezoekers.
// Nog geen backend: de site blijft statisch. Periodiek handmatig te dumpen via
// exportFeedback() (zie de "Feedback exporteren"-knop op de topic-pagina).

export const STORAGE_KEY = "bipolariteit_feedback";

export const ISSUE_TYPES = [
	{ key: "verkeerde_stance", label: "Verkeerde stance (pro/contra/onduidelijk)" },
	{ key: "verkeerde_typologie", label: "Verkeerde typologie" },
	{ key: "geen_argument", label: "Dit is geen argument" },
	{ key: "verkeerd_citaat", label: "Citaat klopt niet / onvolledig" },
	{ key: "anders", label: "Anders" },
] as const;

export type IssueKey = (typeof ISSUE_TYPES)[number]["key"];

export interface FeedbackEntry {
	argument_id: number;
	topic_slug: string;
	issues: IssueKey[];
	note: string | null;
	created_at: string;
}

function readAll(): FeedbackEntry[] {
	if (typeof window === "undefined") return [];
	try {
		const raw = window.localStorage.getItem(STORAGE_KEY);
		return raw ? JSON.parse(raw) : [];
	} catch {
		return [];
	}
}

function writeAll(entries: FeedbackEntry[]) {
	window.localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
}

export function getFeedbackFor(argumentId: number): FeedbackEntry | null {
	return readAll().find((e) => e.argument_id === argumentId) ?? null;
}

export function submitFeedback(entry: Omit<FeedbackEntry, "created_at">) {
	const entries = readAll().filter((e) => e.argument_id !== entry.argument_id);
	entries.push({ ...entry, created_at: new Date().toISOString() });
	writeAll(entries);
}

export function getAllFeedback(): FeedbackEntry[] {
	return readAll();
}

export function feedbackCount(): number {
	return readAll().length;
}

export function exportFeedback() {
	const entries = readAll();
	const blob = new Blob([JSON.stringify(entries, null, 2)], { type: "application/json" });
	const url = URL.createObjectURL(blob);
	const a = document.createElement("a");
	a.href = url;
	a.download = `bipolariteit_feedback_${new Date().toISOString().slice(0, 10)}.json`;
	a.click();
	URL.revokeObjectURL(url);
}
