import { debateId } from "./debateId";
import type { Argument } from "./types";

// Voor de homepage (issue #110): het meest recente debat over alle topics
// heen, i.p.v. per topic (zoals DebateList.vue op de topicpagina). Zelfde
// groeperingsprincipe als DebateList.vue/[id].astro: groeperen op
// debateId(raw_video_url), niet document.id, want één debat bestaat uit veel
// document-rijen (één per spreekbeurt) die dezelfde raw_video_url delen.

export interface LatestDebate {
	id: string;
	topicSlug: string;
	arguments: Argument[];
	earliestPublishedAt: string | null;
}

export function findLatestDebate(argumentsByTopic: { slug: string; arguments: Argument[] }[]): LatestDebate | null {
	const byDebateId = new Map<string, { topicSlug: string; arguments: Argument[]; earliestPublishedAt: string | null }>();

	for (const topic of argumentsByTopic) {
		for (const argument of topic.arguments) {
			const rawVideoUrl = argument.document.raw_video_url;
			if (!rawVideoUrl) continue;
			const id = debateId(rawVideoUrl);
			let entry = byDebateId.get(id);
			if (!entry) {
				entry = { topicSlug: topic.slug, arguments: [], earliestPublishedAt: null };
				byDebateId.set(id, entry);
			}
			entry.arguments.push(argument);
			if (
				argument.document.published_at &&
				(!entry.earliestPublishedAt || argument.document.published_at < entry.earliestPublishedAt)
			) {
				entry.earliestPublishedAt = argument.document.published_at;
			}
		}
	}

	const latest = [...byDebateId.entries()].sort(
		(a, b) => (b[1].earliestPublishedAt ?? "").localeCompare(a[1].earliestPublishedAt ?? ""),
	)[0];
	if (!latest) return null;

	const [id, entry] = latest;
	entry.arguments.sort((a, b) => {
		if (a.start_seconds === null) return 1;
		if (b.start_seconds === null) return -1;
		return a.start_seconds - b.start_seconds;
	});
	return { id, topicSlug: entry.topicSlug, arguments: entry.arguments, earliestPublishedAt: entry.earliestPublishedAt };
}
