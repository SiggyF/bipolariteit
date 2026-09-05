import { debateName } from "./debateName";
import { formatDate } from "./formatDate";
import { displayPartyName } from "./parties";
import { perspectiefWeergaveNaam, tagIconPath } from "./tagIcon";
import { PERSPECTIEVEN } from "./tagIcons.generated";
import { stanceLabel, typologyLabel, type Argument } from "./types";
import { activeArguments, nextArgumentAfter, prevArgumentBefore, selectBadgeTags } from "./videoLabels";
import { formatClock } from "./videoTime";

// Overlay-toestand (titelkaart, naamplaatje, tag-badges, vorig/volgend) als
// pure, component-onafhankelijke afleiding van (arguments, currentTime, off)
// -- losgetrokken uit VideoOverlay.vue (issue #179) zodat zowel de live
// DOM-overlay als de canvas/SVG-exportpijplijn (clipExport.ts, issue #180)
// precies dezelfde bron van waarheid gebruiken. Geen los heruitgevonden
// "wat staat er nu in beeld"-logica in de exportpad, die anders bij elke
// wijziging aan de live overlay stilzwijgend uit de pas zou lopen.

const colorByPerspective = new Map(PERSPECTIEVEN.map((p) => [p.naam, p.kleur]));

export interface OverlayBadge {
	key: string;
	label: string;
	shortLabel: string;
	iconPad: string | null;
	color: string;
	tooltip: string;
}

export interface OverlayNameplate {
	name: string;
	party: string | null;
	role_title: string | null;
}

export interface OverlayState {
	debateTitle: string | null;
	debateDate: string | null;
	showTitleCard: boolean;
	introBadge: string | null;
	badges: OverlayBadge[];
	nameplate: OverlayNameplate | null;
	prevArgument: Argument | null;
	nextArgument: Argument | null;
	timeRangeText: string | null;
}

function shortTagLabel(sleutel: string): string {
	const parts = sleutel.split("-");
	return parts.length > 1 ? parts.slice(1).join(" ") : sleutel;
}

export function buildOverlayState(
	args: Argument[],
	currentTime: number,
	isVisible: (tag: { perspectief: string }) => boolean,
): OverlayState {
	const active = activeArguments(args, currentTime);

	const debateTitle = debateName(args[0]?.document.video_url ?? null);
	const debateDate = formatDate(args[0]?.document.published_at ?? null);
	const showTitleCard = currentTime < 4.5;

	const nextArgument = nextArgumentAfter(args, currentTime);
	const prevArgument = prevArgumentBefore(args, active[0]?.start_seconds ?? currentTime);

	const nameplate: OverlayNameplate | null = (() => {
		if (active[0]) return active[0].actor;
		const past = args
			.filter((a) => a.start_seconds !== null && a.start_seconds <= currentTime)
			.sort((a, b) => (b.start_seconds as number) - (a.start_seconds as number))[0];
		return past?.actor ?? nextArgument?.actor ?? null;
	})();

	const timeRangeText = (() => {
		const current = active[0];
		if (current?.start_seconds != null && current?.end_seconds != null) {
			return `${formatClock(current.start_seconds)}–${formatClock(current.end_seconds)}`;
		}
		return null;
	})();

	const introBadge = (() => {
		const argument = active[0];
		if (!argument || argument.start_seconds === null) return null;
		const sinceStart = currentTime - argument.start_seconds;
		if (sinceStart < 0 || sinceStart > 3) return null;
		return `${typologyLabel(argument.typology)} · ${stanceLabel(argument.stance)}`;
	})();

	const badges: OverlayBadge[] = active.flatMap((argument) =>
		selectBadgeTags(argument, args, isVisible).map((tag) => ({
			key: `${argument.id}-${tag.sleutel}`,
			label: tag.sleutel,
			shortLabel: shortTagLabel(tag.sleutel),
			iconPad: tagIconPath(tag.sleutel),
			color: colorByPerspective.get(tag.perspectief) ?? "#888",
			tooltip: tag.reden
				? `${tag.labelgroep} · ${perspectiefWeergaveNaam(tag.perspectief)}\n\n${tag.reden}`
				: `${tag.labelgroep} · ${perspectiefWeergaveNaam(tag.perspectief)}`,
		})),
	);

	return { debateTitle, debateDate, showTitleCard, introBadge, badges, nameplate, prevArgument, nextArgument, timeRangeText };
}

export { displayPartyName };
