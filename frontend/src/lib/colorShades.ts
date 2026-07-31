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
