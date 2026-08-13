export interface TagSignaal {
	sleutel: string;
	n: number;
	ratio: number;
}

export interface TagSignalenOpties {
	/** Hoeveel favorieten/minst-favoriete tags teruggeven. */
	topN?: number;
	/** Minimaal aandeel van iemands eigen getagde argumenten om als favoriet
	 * te kwalificeren -- zie berekenTagSignalen. */
	minAandeelFavoriet?: number;
}

/** Per tag: hoe vaak deze persoon 'm gebruikt t.o.v. het gemiddelde aandeel
 * over iedereen. Favorieten zijn de tags met de hoogste ratio, met minimaal
 * `minAandeelFavoriet` van iemands eigen getagde argumenten -- zonder die
 * ondergrens zou 1 toevallige toekenning op een klein volume al een
 * torenhoge ratio geven. Minst-favoriete tags zijn de laagste ratio's (vaak
 * 0, bij een tag die verder gangbaar is); daar geldt geen ondergrens, want
 * een tag die niemand gebruikt is per definitie ook niet "favoriet" van
 * iemand die 'm nooit gebruikt. */
export function berekenTagSignalen(
	personTagCount: Map<string, number>,
	personTotal: number,
	globalTagCount: Map<string, number>,
	globalTagTotal: number,
	opties: TagSignalenOpties = {},
): { favorieten: TagSignaal[]; minstFavoriet: TagSignaal[] } {
	const topN = opties.topN ?? 1;
	const minAandeelFavoriet = opties.minAandeelFavoriet ?? 0.05;
	if (!personTotal) return { favorieten: [], minstFavoriet: [] };

	const signalen: TagSignaal[] = [];
	for (const [sleutel, globalN] of globalTagCount) {
		const n = personTagCount.get(sleutel) ?? 0;
		const ratio = n / personTotal / (globalN / globalTagTotal);
		signalen.push({ sleutel, n, ratio });
	}

	const favorieten = signalen
		.filter((s) => s.n / personTotal >= minAandeelFavoriet)
		.sort((a, b) => b.ratio - a.ratio)
		.slice(0, topN);

	// Bij een ratio van 0 (tag nooit gebruikt) breekt het globale gebruik de
	// gelijkstand: minst-favoriet is pas interessant bij een tag die anderen
	// wél vaak gebruiken, niet bij een obscure tag die toch bijna niemand
	// gebruikt.
	const minstFavoriet = [...signalen]
		.sort((a, b) => a.ratio - b.ratio || (globalTagCount.get(b.sleutel) ?? 0) - (globalTagCount.get(a.sleutel) ?? 0))
		.slice(0, topN);

	return { favorieten, minstFavoriet };
}

/** Factor + cijfers achter een favoriet/minst-favoriet-signaal, bv. "2.3x
 * vaker dan gemiddeld — 5 van 20 eigen getagde argumenten, tegenover 100 van
 * 5.000 over iedereen heen". Losstaand van signaalTitle zodat de aanroepende
 * pagina'm ook zichtbaar (niet alleen als hover-title) kan tonen. */
export function signaalDetail(
	signaal: TagSignaal,
	personTotal: number,
	globalTagCount: Map<string, number>,
	globalTagTotal: number,
): string {
	const globalN = globalTagCount.get(signaal.sleutel) ?? 0;
	const factor = signaal.ratio >= 1 ? `${signaal.ratio.toFixed(1)}x vaker dan gemiddeld` : `${signaal.ratio.toFixed(1)}x zo vaak als gemiddeld`;
	const cijfers = `${signaal.n} van ${personTotal} eigen getagde argumenten, tegenover ${globalN} van ${globalTagTotal} over iedereen heen`;
	return `${factor} — ${cijfers}`;
}

export function signaalTitle(
	signaal: TagSignaal,
	soort: "favoriet" | "minst favoriet",
	personTotal: number,
	globalTagCount: Map<string, number>,
	globalTagTotal: number,
	tagBeschrijving: Map<string, string>,
): string {
	const beschrijving = tagBeschrijving.get(signaal.sleutel);
	const detail = signaalDetail(signaal, personTotal, globalTagCount, globalTagTotal);
	return [`${soort}: ${signaal.sleutel}`, beschrijving, detail].filter(Boolean).join(" — ");
}
