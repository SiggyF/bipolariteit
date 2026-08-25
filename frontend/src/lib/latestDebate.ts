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

// Handmatige uitsluitlijst voor debatten waarvan bevestigd is dat de video
// niet afspeelt (bv. via pipeline/check_video_urls.py) -- zonder deze lijst
// zou "laatste debat" op de homepage zo'n kapotte video tonen totdat de bron
// het zelf weer oplost, wat voor dit specifieke debat niet lijkt te gebeuren
// (zie issue #152: alle vijf video-renditions geven HTTP 400 bij de Tweede
// Kamer zelf, alleen de audio-only rendition werkt nog). Bewust hier
// hardgecodeerd i.p.v. een gepersisteerde databasevlag: dit komt zelden voor
// en handmatig een id toevoegen/verwijderen is voor nu genoeg.
const BROKEN_VIDEO_DEBATE_IDS = new Set(["yn3moz"]);

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

	// Extractie, tagging en video-matching zijn losse pipeline-stages (zie
	// Makefile: extract -> tag -> fetch-debate-events/fetch-subtitles ->
	// match-video-spans, dat arguments.start_seconds vult) -- het net
	// geëxtraheerde debat kan dus nog geen tags hebben, en een net getagd
	// debat nog geen videomatch (match-video-spans draait pas later/los).
	// "Laatste geanalyseerde debat" moet pas tonen zodra beide stappen klaar
	// zijn: minstens één getagd argument, én minstens één argument met een
	// videomatch (start_seconds), anders oogt de kop als klaar terwijl de
	// tijdlijn leeg blijft en vorige/volgende niet werkt (issue #209).
	const latest = [...byDebateId.entries()]
		.filter(([id]) => !BROKEN_VIDEO_DEBATE_IDS.has(id))
		.filter(([, entry]) => entry.arguments.some((a) => a.tags.length > 0))
		.filter(([, entry]) => entry.arguments.some((a) => a.start_seconds !== null))
		.sort((a, b) => (b[1].earliestPublishedAt ?? "").localeCompare(a[1].earliestPublishedAt ?? ""))[0];
	if (!latest) return null;

	const [id, entry] = latest;
	entry.arguments.sort((a, b) => {
		if (a.start_seconds === null) return 1;
		if (b.start_seconds === null) return -1;
		return a.start_seconds - b.start_seconds;
	});
	return { id, topicSlug: entry.topicSlug, arguments: entry.arguments, earliestPublishedAt: entry.earliestPublishedAt };
}
