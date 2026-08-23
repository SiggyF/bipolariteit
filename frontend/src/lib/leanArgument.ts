import type { Argument } from "./types";

// Gedeelde stripping van zware, per-argument herhaalde velden (videolinks,
// quote_context, claims, oppositions, tag-`reden`) die de tijdlijn- en
// correspondentiekaart-componenten (lib/filters.ts, lib/timeline.ts,
// lib/correspondence.ts) toch nooit lezen. Eén definitie, gebruikt door zowel
// de Astro-build (build-time aggregaten) als scripts/export_public_data.ts
// (client-side gefetchte data) -- zie issue #163 (Cloudflare Workers-
// assetlimiet van 25 MiB per bestand).
export function toLeanArgument(argument: any): Argument {
	return {
		id: argument.id,
		stance: argument.stance,
		typology: argument.typology,
		quote_text: argument.quote_text,
		quote_context: null,
		prompt_version: null,
		start_seconds: null,
		end_seconds: null,
		actor: argument.actor,
		document: {
			id: argument.document.id,
			url: null,
			video_url: null,
			published_at: argument.document.published_at,
			speaker_video_url: null,
			tweedekamer_activiteit_url: null,
			redactie_review: null,
			raw_video_url: null,
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
		oppositions: [],
	};
}
