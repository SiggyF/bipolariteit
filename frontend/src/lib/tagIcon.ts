import { ICOON_PAD, PERSPECTIEVEN } from "./tagIcons.generated";

// tagsleutel -> icoonpad, over alle perspectieven heen. Eén lookup i.p.v. dit
// in elke component die een tagicoon toont opnieuw te doorzoeken.
const TAG_ICOON_PAD = new Map<string, string>();
for (const perspectief of PERSPECTIEVEN) {
	for (const [sleutel, icoon] of Object.entries(perspectief.tags)) {
		const pad = ICOON_PAD[icoon];
		if (pad) TAG_ICOON_PAD.set(sleutel, pad);
	}
}

/** Icoonpad voor een tagsleutel, of `null` als de tag geen icoon heeft
 * (bv. de "overig"-rij uit `bucketSmallCounts`). */
export function tagIconPath(sleutel: string): string | null {
	return TAG_ICOON_PAD.get(sleutel) ?? null;
}
