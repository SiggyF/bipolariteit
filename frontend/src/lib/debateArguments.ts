import { reactive } from "vue";
import type { Argument } from "./types";

// Gedeelde, module-scope reactive store voor de per-debat gepubliceerde
// argumentenlijst (data/export/gepubliceerd/debatten/<debateId>.json, issue
// #119). Meerdere client:only-islands op dezelfde pagina (bv. DebateVideoView
// en ClaimsHighlights op de homepage, beide over hetzelfde laatste debat)
// delen zo één fetch + één geparste array. Bewust per debat i.p.v. het hele
// onderwerp (data/export/gepubliceerd/onderwerpen/<slug>.json, issue #163):
// een onderwerp als energietransitie/asiel beslaat tientallen debatten en tot
// ~11 MB, terwijl DebateVideoView/ClaimsHighlights maar één debat nodig
// hebben -- filteren dat client-side uit het hele onderwerp bleek de
// oorspronkelijke Astro-prop-payload (~2,5-4,8 MB) juist te vervangen door
// een grotere download. Zelfde idee als videoSeek.ts/userScroll.ts:
// module-scope reactive singleton, geen Pinia.

type FetchStatus = "loading" | "ready" | "error";

interface Entry {
	status: FetchStatus;
	arguments: Argument[];
}

const cache = new Map<string, Entry>();

export function useDebateArguments(debateId: string, dataBaseUrl: string): Entry {
	let entry = cache.get(debateId);
	if (entry) return entry;

	entry = reactive({ status: "loading", arguments: [] }) as Entry;
	cache.set(debateId, entry);

	fetch(`${dataBaseUrl}/debatten/${debateId}.json`)
		.then((response) => {
			if (!response.ok) throw new Error(`onverwachte statuscode ${response.status}`);
			return response.json();
		})
		.then((data: Argument[]) => {
			entry!.arguments = data;
			entry!.status = "ready";
		})
		.catch(() => {
			entry!.status = "error";
		});

	return entry;
}
