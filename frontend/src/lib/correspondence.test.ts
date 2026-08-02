import { describe, expect, it } from "vitest";
import { alignSigns, analyseTable, buildCorrespondence, canonicalSigns } from "./correspondence";
import gouden from "./__fixtures__/ca-stikstof.json";
import topic from "../../../data/export/topics/stikstof.json";
import type { Argument } from "./types";

// De fixture komt uit scripts/dump_ca_fixture.py: dezelfde tabel door `prince`
// met engine="scipy", plus onze eigen tekenconventie. Slaagt dit bestand, dan
// rekent de TypeScript-versie aantoonbaar hetzelfde als de Python-versie die
// hij vervangt.

const argumenten = topic.arguments as unknown as Argument[];

function ergsteVerschil(a: number[][], b: number[][]): number {
	let ergste = 0;
	for (let i = 0; i < a.length; i++) {
		for (let j = 0; j < a[i].length; j++) ergste = Math.max(ergste, Math.abs(a[i][j] - b[i][j]));
	}
	return ergste;
}

describe("contingentietabel uit de argumentenlijst", () => {
	const ca = buildCorrespondence(argumenten, { nComponents: 3 })!;

	it("levert dezelfde partijen en tags als de SQL-versie", () => {
		expect(ca.rows.map((r) => r.label)).toEqual(gouden.rowLabels);
		expect(ca.tags.map((t) => t.sleutel)).toEqual(gouden.colLabels);
	});

	it("levert dezelfde totalen per punt", () => {
		expect(ca.rows.map((r) => r.n)).toEqual(gouden.rowTotals);
		expect(ca.tags.map((t) => t.n)).toEqual(gouden.colTotals);
	});
});

describe("correspondentieanalyse tegen de prince-fixture", () => {
	it("reproduceert de rijcoordinaten", () => {
		const ca = buildCorrespondence(argumenten, { nComponents: 3 })!;
		expect(ergsteVerschil(ca.rows.map((r) => r.coords), gouden.F)).toBeLessThan(1e-8);
	});

	it("reproduceert de kolomcoordinaten", () => {
		const ca = buildCorrespondence(argumenten, { nComponents: 3 })!;
		expect(ergsteVerschil(ca.tags.map((t) => t.coords), gouden.G)).toBeLessThan(1e-8);
	});

	it("reproduceert de verklaarde inertie", () => {
		const ca = buildCorrespondence(argumenten, { nComponents: 3 })!;
		ca.inertiaPct.forEach((waarde, k) => {
			expect(waarde).toBeCloseTo(Math.round(gouden.inertiaPct[k] * 10) / 10, 10);
		});
		expect(ca.inertiaPct).toEqual(gouden.inertiaPct.map((v) => Math.round(v * 10) / 10));
	});

	it("gebruikt de volledige inertie als noemer, niet de som van de gebruikte componenten", () => {
		// Dit is de klassieke portfout: met de top-k als noemer wordt 39,6% ineens ~70%.
		const twee = buildCorrespondence(argumenten, { nComponents: 2 })!;
		expect(twee.inertiaPct).toEqual(gouden.inertiaPct.slice(0, 2).map((v) => Math.round(v * 10) / 10));

		const alle = analyseTable(gouden.counts, 100)!;
		expect(alle.nComponents).toBe(Math.min(...[gouden.counts.length, gouden.counts[0].length]) - 1);
		const som = alle.inertiaPct.reduce((a, b) => a + b, 0);
		expect(som).toBeGreaterThan(99.4);
		expect(som).toBeLessThan(100.6);
	});

	it("voldoet aan de CA-identiteiten r'F = 0 en c'G = 0", () => {
		// Onafhankelijk van prince: dit vangt schaalfouten die de fixture zou missen
		// als die met dezelfde fout gegenereerd was.
		const ca = buildCorrespondence(argumenten, { nComponents: 3 })!;
		const totaalRij = ca.rows.reduce((s, r) => s + r.n, 0);
		const totaalTag = ca.tags.reduce((s, t) => s + t.n, 0);
		for (let k = 0; k < 3; k++) {
			const rF = ca.rows.reduce((s, r) => s + (r.n / totaalRij) * r.coords[k], 0);
			const cG = ca.tags.reduce((s, t) => s + (t.n / totaalTag) * t.coords[k], 0);
			expect(Math.abs(rF)).toBeLessThan(1e-9);
			expect(Math.abs(cG)).toBeLessThan(1e-9);
		}
	});
});

describe("tekenconventie", () => {
	it("is onafhankelijk van de volgorde van de argumenten", () => {
		// Husselen mag niets veranderen -- niet de coordinaten en niet de tekens.
		const zaad = [...argumenten];
		for (let i = zaad.length - 1; i > 0; i--) {
			const j = (i * 7919) % (i + 1);
			[zaad[i], zaad[j]] = [zaad[j], zaad[i]];
		}
		expect(buildCorrespondence(zaad, { nComponents: 3 })).toEqual(
			buildCorrespondence(argumenten, { nComponents: 3 }),
		);
	});

	it("is idempotent", () => {
		const ca = buildCorrespondence(argumenten, { nComponents: 3 })!;
		expect(canonicalSigns(ca)).toEqual(ca);
	});

	it("houdt de kaart stil als er gefilterd wordt", () => {
		// Het echte scenario: een deelselectie mag de puntenwolk niet spiegelen.
		const referentie = buildCorrespondence(argumenten, { nComponents: 3 })!;
		const zonderKleinste = argumenten.filter((a) => a.actor.party !== referentie.rows[0].label);
		const deel = buildCorrespondence(zonderKleinste, { nComponents: 3 })!;
		const uitgelijnd = alignSigns(referentie, deel);

		const refCoords = new Map(referentie.tags.map((t) => [t.sleutel, t.coords]));
		let gedeeld = 0;
		let zelfdeKant = 0;
		for (const tag of uitgelijnd.tags) {
			const ref = refCoords.get(tag.sleutel);
			if (!ref) continue;
			gedeeld++;
			if (Math.sign(ref[0]) === Math.sign(tag.coords[0])) zelfdeKant++;
		}
		expect(gedeeld).toBeGreaterThan(20);
		// Individuele punten mogen best bewegen; een spiegeling zou vrijwel alles
		// tegelijk omklappen, en dat is wat we uitsluiten.
		expect(zelfdeKant / gedeeld).toBeGreaterThan(0.8);
	});

	it("spiegelt rijen en kolommen altijd samen", () => {
		const ca = buildCorrespondence(argumenten, { nComponents: 2 })!;
		const gespiegeld: typeof ca = {
			...ca,
			rows: ca.rows.map((r) => ({ ...r, coords: r.coords.map((v) => -v) })),
			tags: ca.tags.map((t) => ({ ...t, coords: t.coords.map((v) => -v) })),
		};
		// Terugdraaien naar canoniek moet exact het origineel opleveren.
		expect(canonicalSigns(gespiegeld)).toEqual(ca);
	});
});

describe("ondergrenzen en rang", () => {
	it("geeft null bij te weinig partijen", () => {
		const eenPartij = argumenten.filter((a) => a.actor.party === gouden.rowLabels[0]);
		expect(buildCorrespondence(eenPartij)).toBeNull();
	});

	it("geeft null bij te weinig tags", () => {
		const kaal = argumenten.map((a) => ({ ...a, tags: a.tags.slice(0, 1) }));
		expect(buildCorrespondence(kaal as Argument[], { minColTotal: 1e9 })).toBeNull();
	});

	it("valt terug op 2 componenten als de rang er geen 3 draagt", () => {
		// 3x3-tabel: min(m,n)-1 = 2, dus een derde component bestaat niet.
		const klein = analyseTable(
			[
				[5, 1, 1],
				[1, 5, 1],
				[1, 1, 5],
			],
			3,
		)!;
		expect(klein.nComponents).toBe(2);
		expect(klein.inertiaPct).toHaveLength(2);
	});

	it("geeft null bij een lege tabel", () => {
		expect(analyseTable([[0, 0, 0], [0, 0, 0], [0, 0, 0]], 2)).toBeNull();
	});
});
