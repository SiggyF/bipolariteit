function hexToRgb(hex: string): [number, number, number] {
	const h = hex.replace("#", "");
	return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16)) as [number, number, number];
}

/** `baseHex` als rgba-string met de opgegeven dekking -- voor de partij x
 * tag-heatmap op een perspectiefpagina, waar dekking (niet tint) het
 * percentage draagt en alle cellen dus dezelfde perspectiefkleur delen (zie
 * TagCorrespondenceMap.vue: perspectiefkleur is daar ook al de enige
 * betekenisdrager, geen los categorisch palet ernaast). */
export function withAlpha(hex: string, alpha: number): string {
	const [r, g, b] = hexToRgb(hex);
	return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/** Mengt `hex` met `baseHex` volgens `ratio` (0..1) tot een ondoorzichtige
 * hexkleur -- i.p.v. withAlpha()'s rgba-transparantie, die meekleurt met
 * wat eronder zit. Nodig zodra dezelfde "lichte tint"-stijl in meerdere
 * contexten met een verschillende achtergrond voorkomt (bv.
 * DebateCardTagBar.vue: een compacte kaartrij heeft geen eigen
 * kaartachtergrond, dus dezelfde rgba() oogt daar anders dan op een kaart
 * mét --blad). */
export function mixWithBase(hex: string, baseHex: string, ratio: number): string {
	const [r1, g1, b1] = hexToRgb(hex);
	const [r2, g2, b2] = hexToRgb(baseHex);
	const mix = (a: number, b: number) => Math.round(a * ratio + b * (1 - ratio));
	const toHex = (n: number) => n.toString(16).padStart(2, "0");
	return `#${toHex(mix(r1, r2))}${toHex(mix(g1, g2))}${toHex(mix(b1, b2))}`;
}
