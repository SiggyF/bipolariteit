// Partij- en persoonscontouren op de plenaire kaart (issue #261): GeoJSON uit
// scripts/a0_map/generate_actor_party_contours.py (WGS84-variant, naast de
// pmtiles gepubliceerd). Per groep één feature per drempel (`threshold`:
// 1,5x en 3x het gemiddelde, geneste lagen).

export type ContourKind = "party" | "actor";

export type ContourProperties = {
	party?: string;
	actor?: string;
	n: number;
	color: string;
	threshold: number;
};

export type ContourCollection = GeoJSON.FeatureCollection<GeoJSON.MultiPolygon | GeoJSON.Polygon, ContourProperties>;

export const CONTOUR_FILE: Record<ContourKind, string> = {
	party: "plenair-map-full-party_contours.geojson",
	actor: "plenair-map-full-actor_contours.geojson",
};

export const CONTOUR_THRESHOLD_LABEL: Record<number, string> = {
	1.5: "meer dan 1,5x het gemiddelde",
	3: "meer dan 3x het gemiddelde",
};

const NAME_KEY: Record<ContourKind, "party" | "actor"> = { party: "party", actor: "actor" };

export async function fetchContours(baseUrl: string, kind: ContourKind): Promise<ContourCollection> {
	const response = await fetch(`${baseUrl}/${CONTOUR_FILE[kind]}`);
	if (!response.ok) throw new Error(`Status ${response.status} voor ${CONTOUR_FILE[kind]}`);
	return response.json();
}

/** Namen met een contour, op aantal spreekbeurten aflopend (grootste eerst). */
export function contourNames(collection: ContourCollection, kind: ContourKind): { name: string; n: number }[] {
	const key = NAME_KEY[kind];
	const byName = new Map<string, number>();
	for (const feature of collection.features) {
		const name = feature.properties[key];
		if (name) byName.set(name, feature.properties.n);
	}
	return [...byName].map(([name, n]) => ({ name, n })).sort((a, b) => b.n - a.n || a.name.localeCompare(b.name, "nl"));
}

/** De features van de geselecteerde groepen, voor de MapLibre-bron. */
export function selectContours(
	selections: { kind: ContourKind; collection: ContourCollection | null; name: string | null }[],
): GeoJSON.FeatureCollection {
	const features: GeoJSON.Feature[] = [];
	for (const { kind, collection, name } of selections) {
		if (!collection || !name) continue;
		const key = NAME_KEY[kind];
		for (const feature of collection.features) {
			if (feature.properties[key] === name) features.push(feature);
		}
	}
	return { type: "FeatureCollection", features };
}
