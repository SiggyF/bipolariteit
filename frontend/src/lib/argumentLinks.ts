import { debateId } from "./debateId";

// Eén gedeelde regelset voor de bronlinks onder een argument (issue #173):
// eerder implementeerden ArgumentCard.vue en ArgumentTree.vue elk hun eigen
// variant, met een wisselend aantal links en een label ("video (dit moment)")
// dat afhankelijk van het component naar een externe tweedekamer.nl-pagina óf
// naar de eigen videospeler verwees. Hier staat de volgorde en labeling op
// één plek, met een expliciet onderscheid tussen extern (tweedekamer.nl) en
// intern (eigen videospeler) in het label zelf.

export interface ArgumentSourceFields {
	tweedekamer_activiteit_url: string | null;
	document_url: string | null;
	speaker_video_url: string | null;
	video_url: string | null;
}

export interface ArgumentLink {
	key: string;
	href: string;
	label: string;
	title?: string;
	external: boolean;
}

/** Links naar externe bronnen (tweedekamer.nl, ruwe XML). Vaste volgorde:
 * Tweede Kamer-pagina, brondata, video. De video-link wijst naar het exacte
 * spreekmoment (speaker_video_url) als dat er is, anders naar het hele debat
 * (video_url) -- nooit beide tegelijk, want speaker_video_url is al een
 * tijdgestempelde variant van diezelfde video. */
export function externalArgumentLinks(fields: ArgumentSourceFields): ArgumentLink[] {
	const links: ArgumentLink[] = [];
	if (fields.tweedekamer_activiteit_url) {
		links.push({
			key: "tweedekamer",
			href: fields.tweedekamer_activiteit_url,
			label: "bekijk in de Tweede Kamer",
			title: "Officiële tweedekamer.nl-pagina van dit debat (Verslag/Handelingen + video)",
			external: true,
		});
	}
	if (fields.document_url) {
		links.push({
			key: "xml",
			href: fields.document_url,
			label: "ruwe brondata (XML)",
			title: "Ruwe brondata (XML) van de Tweede Kamer -- machine-leesbaar, geen leesbare pagina",
			external: true,
		});
	}
	if (fields.speaker_video_url) {
		links.push({
			key: "video-extern",
			href: fields.speaker_video_url,
			label: "video op tweedekamer.nl (dit moment)",
			title: "Springt naar het moment dat deze spreker begint, op de tweedekamer.nl-videospeler",
			external: true,
		});
	} else if (fields.video_url) {
		links.push({
			key: "video-extern",
			href: fields.video_url,
			label: "video op tweedekamer.nl (heel debat)",
			external: true,
		});
	}
	return links;
}

/** Link naar de eigen (interne) videospeler op /debatten/[id]/, met een
 * tijdstempel (?t=) als het argument een gematchte videospanne heeft. Null
 * zonder raw_video_url -- dan bestaat er geen interne speler voor dit debat. */
export function internalVideoLink(
	rawVideoUrl: string | null,
	startSeconds: number | null,
): ArgumentLink | null {
	if (!rawVideoUrl) return null;
	const id = debateId(rawVideoUrl);
	if (startSeconds !== null) {
		return {
			key: "video-intern",
			href: `/debatten/${id}/?t=${Math.floor(startSeconds)}`,
			label: "bekijk dit moment in videospeler",
			title: "Bekijk dit debat met argumentannotaties over de video, gesprongen naar dit moment",
			external: false,
		};
	}
	return {
		key: "video-intern",
		href: `/debatten/${id}/`,
		label: "bekijk in videospeler",
		title: "Bekijk dit debat met argumentannotaties over de video",
		external: false,
	};
}
