import { debateId } from "./debateId";
import { debateName } from "./debateName";
import type { Argument } from "./types";

// Generalisatie van findLatestDebate.ts: niet alleen het meest recente debat,
// maar alle debatten over alle topics heen, aflopend gesorteerd -- voor de
// debatlijst op /debatten/ (issue #132). Zelfde groeperingsprincipe als
// findLatestDebate.ts/DebateList.vue/[id].astro: groeperen op
// debateId(raw_video_url), niet document.id.

export interface DebateSummary {
	id: string;
	topicSlug: string;
	name: string | null;
	earliestPublishedAt: string | null;
	argumentCount: number;
}

export function groupByDebate(argumentsByTopic: { slug: string; arguments: Argument[] }[]): DebateSummary[] {
	const byDebateId = new Map<string, Omit<DebateSummary, "id">>();

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
				};
				byDebateId.set(id, entry);
			}
			entry.argumentCount++;
			if (
				argument.document.published_at &&
				(!entry.earliestPublishedAt || argument.document.published_at < entry.earliestPublishedAt)
			) {
				entry.earliestPublishedAt = argument.document.published_at;
			}
		}
	}

	return [...byDebateId.entries()]
		.map(([id, entry]) => ({ id, ...entry }))
		.sort((a, b) => (b.earliestPublishedAt ?? "").localeCompare(a.earliestPublishedAt ?? ""));
}
