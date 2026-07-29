import { describe, expect, it } from "vitest";
import { svd } from "./svd";

function maal(a: number[][], b: number[][]): number[][] {
	return a.map((rij) => b[0].map((_, j) => rij.reduce((som, waarde, k) => som + waarde * b[k][j], 0)));
}

function diag(s: number[]): number[][] {
	return s.map((waarde, i) => s.map((_, j) => (i === j ? waarde : 0)));
}

function transponeer(a: number[][]): number[][] {
	return a[0].map((_, j) => a.map((rij) => rij[j]));
}

/** Reconstrueert A uit U*Sigma*V' en geeft de grootste afwijking. */
function reconstructieFout(a: number[][]): number {
	const { u, s, v } = svd(a);
	const her = maal(maal(u, diag(s)), transponeer(v));
	let ergste = 0;
	for (let i = 0; i < a.length; i++) {
		for (let j = 0; j < a[0].length; j++) ergste = Math.max(ergste, Math.abs(a[i][j] - her[i][j]));
	}
	return ergste;
}

/** Grootste afwijking van M'M ten opzichte van de eenheidsmatrix. */
function orthonormaliteitsFout(m: number[][]): number {
	const g = maal(transponeer(m), m);
	let ergste = 0;
	for (let i = 0; i < g.length; i++) {
		for (let j = 0; j < g.length; j++) ergste = Math.max(ergste, Math.abs(g[i][j] - (i === j ? 1 : 0)));
	}
	return ergste;
}

// Vaste pseudo-random matrix: reproduceerbaar zonder seed-afhankelijkheid.
function testMatrix(m: number, n: number): number[][] {
	let zaad = 12345;
	const volgende = () => {
		zaad = (zaad * 1103515245 + 12345) % 2147483648;
		return zaad / 2147483648 - 0.5;
	};
	return Array.from({ length: m }, () => Array.from({ length: n }, volgende));
}

describe("svd", () => {
	it("reconstrueert een vierkante matrix", () => {
		expect(reconstructieFout(testMatrix(8, 8))).toBeLessThan(1e-12);
	});

	it("reconstrueert een hoge matrix", () => {
		expect(reconstructieFout(testMatrix(20, 6))).toBeLessThan(1e-12);
	});

	it("reconstrueert een brede matrix (intern getransponeerd)", () => {
		// Dit is de vorm die de correspondentieanalyse aanlevert: 19x37.
		expect(reconstructieFout(testMatrix(19, 37))).toBeLessThan(1e-12);
	});

	it("levert orthonormale U en V", () => {
		const { u, v } = svd(testMatrix(19, 37));
		expect(orthonormaliteitsFout(u)).toBeLessThan(1e-12);
		expect(orthonormaliteitsFout(v)).toBeLessThan(1e-12);
	});

	it("sorteert singuliere waarden aflopend en niet-negatief", () => {
		const { s } = svd(testMatrix(12, 9));
		expect(s.every((waarde) => waarde >= 0)).toBe(true);
		expect([...s].sort((a, b) => b - a)).toEqual(s);
	});

	it("is deterministisch over herhaalde aanroepen", () => {
		const a = testMatrix(19, 37);
		expect(svd(a)).toEqual(svd(a));
	});

	it("verwerkt een rangdeficiente matrix zonder NaN", () => {
		// Derde kolom is de som van de eerste twee -> rang 2.
		const a = [
			[1, 0, 1],
			[0, 1, 1],
			[2, 1, 3],
			[1, 1, 2],
		];
		const { u, s, v } = svd(a);
		expect(s[2]).toBeLessThan(1e-10);
		expect(reconstructieFout(a)).toBeLessThan(1e-12);
		expect([...u.flat(), ...v.flat(), ...s].every(Number.isFinite)).toBe(true);
	});

	it("weigert een lege matrix", () => {
		expect(() => svd([])).toThrow();
	});
});
