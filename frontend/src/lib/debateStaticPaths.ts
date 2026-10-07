import { debateId } from "./debateId";
import { debateThumbnailUrl } from "./debateThumbnail";

export interface DebateStaticPathProps {
	topicSlug: string;
	videoUrl: string | null;
	rawVideoUrl: string | null;
	posterUrl: string | null;
	publishedAt: string | null;
}

// Gedeeld door /debatten/[id].astro en /embed/debatten/[id].astro: beide
// routes groeperen dezelfde onderwerp-JSON op raw_video_url, niet op
// document.id (zie toelichting bij de oorspronkelijke /debatten/[id].astro) --
// één debat bestaat uit veel document-rijen (één per spreekbeurt) die
// allemaal dezelfde raw_video_url delen.
export function getDebateStaticPaths(): { params: { id: string }; props: DebateStaticPathProps }[] {
	const topicModules = import.meta.glob("../../../data/export/topics/*.json", { eager: true });

	const byDebateId = new Map<string, { arguments: any[]; topicSlug: string }>();
	for (const mod of Object.values(topicModules) as any[]) {
		for (const argument of mod.default.arguments) {
			const rawVideoUrl = argument.document.raw_video_url;
			if (!rawVideoUrl) continue;
			const id = debateId(rawVideoUrl);
			let entry = byDebateId.get(id);
			if (!entry) {
				entry = { arguments: [], topicSlug: mod.default.slug };
				byDebateId.set(id, entry);
			}
			entry.arguments.push(argument);
		}
	}

	return [...byDebateId.entries()].map(([id, entry]) => {
		let videoUrl: string | null = null;
		let rawVideoUrl: string | null = null;
		let posterUrl: string | null = null;
		// Vroegste published_at van alle spreekbeurten in dit debat -- zelfde
		// aanpak als DebateList.vue's earliestPublishedAt, want een debat kan
		// over middernacht heen lopen en de eerste spreekbeurt is dan de
		// betrouwbaarste datum-indicator.
		let publishedAt: string | null = null;
		for (const argument of entry.arguments) {
			videoUrl ??= argument.document.video_url ?? null;
			rawVideoUrl ??= argument.document.raw_video_url ?? null;
			posterUrl ??= debateThumbnailUrl(argument.document.video_url, argument.document.published_at, argument.start_seconds);
			if (argument.document.published_at && (!publishedAt || argument.document.published_at < publishedAt)) {
				publishedAt = argument.document.published_at;
			}
		}
		return { params: { id }, props: { topicSlug: entry.topicSlug, videoUrl, rawVideoUrl, posterUrl, publishedAt } };
	});
}
