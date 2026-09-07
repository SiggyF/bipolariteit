import type { Argument } from "./types";

// Gedeelde stripping van zware, per-argument herhaalde velden (quote_context,
// claims, tag-`reden`) die de filter- en
// correspondentiekaart-componenten (lib/filters.ts, lib/correspondence.ts)
// toch nooit lezen. Eén definitie, gebruikt door zowel
// de Astro-build (build-time aggregaten) als scripts/export_public_data.ts
// (client-side gefetchte data) -- zie issue #163 (Cloudflare Workers-
// assetlimiet van 25 MiB per bestand).
//
// raw_video_url blijft wél staan (issue #112-vervolg: DebateList/DebateCard
// op de perspectiefpagina groepeert/linkt debatten hierop) -- kost ~180
// tekens/argument, op de huidige ~8800 argumenten per perspectief ca. +1,5MB,
// ruim binnen de #163-limiet. start_seconds/end_seconds ook (verwaarloosbare
// grootte, twee getallen) -- debateThumbnailUrl() heeft start_seconds nodig
// om de videostill op de uitgelichte debatkaart te tonen, anders altijd leeg.
export function toLeanArgument(argument: any): Argument {
	return {
		id: argument.id,
		stance: argument.stance,
		typology: argument.typology,
		quote_text: argument.quote_text,
		quote_context: null,
		prompt_version: null,
		start_seconds: argument.start_seconds,
		end_seconds: argument.end_seconds,
		actor: argument.actor,
		document: {
			id: argument.document.id,
			url: null,
			video_url: argument.document.video_url,
			published_at: argument.document.published_at,
			speaker_video_url: null,
			tweedekamer_activiteit_url: null,
			raw_video_url: argument.document.raw_video_url,
		},
		periode: argument.periode,
		claims: [],
		tags: argument.tags.map((tag: any) => ({
			sleutel: tag.sleutel,
			beschrijving: tag.beschrijving,
			labelgroep: tag.labelgroep,
			perspectief: tag.perspectief,
			created_by: tag.created_by,
			reden: null,
		})),
	};
}
