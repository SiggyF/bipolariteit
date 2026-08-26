import { debateId } from "./debateId";
import { debateName } from "./debateName";
import type { Argument } from "./types";

// Generalisatie van findLatestDebate.ts: niet alleen het meest recente debat,
// maar alle debatten over alle topics heen, aflopend gesorteerd -- voor de
// debatlijst op /debatten/ (issue #132). Zelfde groeperingsprincipe als
// findLatestDebate.ts/DebateList.vue/[id].astro: groeperen op
// debateId(raw_video_url), niet document.id.

export interface DebateStanceCounts {
	pro: number;
	contra: number;
	unclear: number;
}

export interface DebateTagCount {
	sleutel: string;
	beschrijving: string;
	labelgroep: string;
	count: number;
}

export interface DebateSummary {
	id: string;
	topicSlug: string;
	name: string | null;
	earliestPublishedAt: string | null;
	argumentCount: number;
	speakerCount: number;
	/** Voor de debatkaarten (#112): pro/contra/onduidelijk-balk op de kaart. */
	stance: DebateStanceCounts;
	/** Aflopend gesorteerd op count. Alleen gevuld door DebateList.vue (niet
	 * door groupByDebate() hieronder, dat voedt /debatten/ waar geen
	 * perspectief-context is) -- voor de "extra"-slot op de perspectiefpagina
	 * (issue #112-vervolg), die hiermee pro/contra vervangt door een
	 * tag-verdeling. */
	tagCounts?: DebateTagCount[];
}

export function groupByDebate(argumentsByTopic: { slug: string; arguments: Argument[] }[]): DebateSummary[] {
	const byDebateId = new Map<string, Omit<DebateSummary, "id"> & { speakers: Set<string> }>();

	for (const topic of argumentsByTopic) {
		for (const argument of topic.arguments) {
			const rawVideoUrl = argument.document.raw_video_url;
			if (!rawVideoUrl) continue;
			const id = debateId(rawVideoUrl);
			let entry = byDebateId.get(id);
			if (!entry) {
				entry = {
					topicSlug: topic.slug,
					name: debateName(argument.document.video_url),
					earliestPublishedAt: null,
					argumentCount: 0,
					speakerCount: 0,
					speakers: new Set(),
					stance: { pro: 0, contra: 0, unclear: 0 },
				};
				byDebateId.set(id, entry);
			}
			entry.argumentCount++;
			entry.speakers.add(argument.actor.name);
			if (argument.stance === "pro" || argument.stance === "contra" || argument.stance === "unclear") {
				entry.stance[argument.stance]++;
			}
			if (
				argument.document.published_at &&
				(!entry.earliestPublishedAt || argument.document.published_at < entry.earliestPublishedAt)
			) {
				entry.earliestPublishedAt = argument.document.published_at;
			}
		}
	}
	for (const entry of byDebateId.values()) {
		entry.speakerCount = entry.speakers.size;
	}

	return [...byDebateId.entries()]
		.map(([id, { speakers, ...entry }]) => ({ id, ...entry }))
		.sort((a, b) => (b.earliestPublishedAt ?? "").localeCompare(a.earliestPublishedAt ?? ""));
}
