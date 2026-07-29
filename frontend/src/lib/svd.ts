// Thin SVD via eenzijdige Jacobi (Hestenes). Geen dependency: de matrix hier
// is de partij x tag-tabel, nu 19x37 en hooguit groeiend naar iets als 40x60.
// Dat is ~5*10^5 flops -- sneller dan een frame, dus geen Web Worker en geen
// debounce; die zouden complexiteit toevoegen voor een berekening die je niet
// kunt voelen. Een WASM-kernel is om dezelfde reden zinloos: die verdient zich
// pas terug bij matrices van duizenden bij duizenden.
//
// De methode roteert kolomparen tot ze orthogonaal zijn. Na convergentie geldt
// A*V = U*Sigma, oftewel A = U*Sigma*V'.
//
// Determinisme is hier geen detail maar een eis: de kaart herberekent bij elke
// filterwijziging, en een solver die per aanroep een andere basis kiest zou de
// puntenwolk laten springen. Vandaar vaste paarvolgorde, vaste drempels, een
// vaste sweeplimiet en nergens een random start.

export interface Svd {
	/** m x k, orthonormale kolommen. */
	u: number[][];
	/** k singuliere waarden, aflopend. */
	s: number[];
	/** n x k -- let op: V zelf, niet V-transpose. */
	v: number[][];
}

const ORTHOGONAAL = 1e-14;
const MAX_SWEEPS = 30;
const NUL_DREMPEL = 1e-12;

function transponeer(a: number[][]): number[][] {
	const m = a.length;
	const n = a[0].length;
	const t: number[][] = Array.from({ length: n }, () => new Array<number>(m));
	for (let i = 0; i < m; i++) for (let j = 0; j < n; j++) t[j][i] = a[i][j];
	return t;
}

/** Jacobi wil een matrix die minstens zo hoog als breed is. */
function jacobi(b: number[][]): { kolommen: number[][]; v: number[][] } {
	const p = b.length;
	const q = b[0].length;
	const work = b.map((rij) => [...rij]);
	const v: number[][] = Array.from({ length: q }, (_, i) =>
		Array.from({ length: q }, (_, j) => (i === j ? 1 : 0)),
	);

	for (let sweep = 0; sweep < MAX_SWEEPS; sweep++) {
		let rotaties = 0;
		for (let j1 = 0; j1 < q - 1; j1++) {
			for (let j2 = j1 + 1; j2 < q; j2++) {
				let alpha = 0;
				let beta = 0;
				let gamma = 0;
				for (let i = 0; i < p; i++) {
					alpha += work[i][j1] * work[i][j1];
					beta += work[i][j2] * work[i][j2];
					gamma += work[i][j1] * work[i][j2];
				}
				// Al orthogonaal genoeg -- niet roteren, anders blijft een sweep
				// eeuwig "werk doen" op ruis en convergeert hij nooit.
				if (Math.abs(gamma) <= ORTHOGONAAL * Math.sqrt(alpha * beta)) continue;

				const zeta = (beta - alpha) / (2 * gamma);
				const teken = zeta >= 0 ? 1 : -1;
				const t = teken / (Math.abs(zeta) + Math.sqrt(1 + zeta * zeta));
				const c = 1 / Math.sqrt(1 + t * t);
				const s = c * t;

				for (let i = 0; i < p; i++) {
					const x = work[i][j1];
					const y = work[i][j2];
					work[i][j1] = c * x - s * y;
					work[i][j2] = s * x + c * y;
				}
				for (let i = 0; i < q; i++) {
					const x = v[i][j1];
					const y = v[i][j2];
					v[i][j1] = c * x - s * y;
					v[i][j2] = s * x + c * y;
				}
				rotaties++;
			}
		}
		if (rotaties === 0) break;
	}

	return { kolommen: work, v };
}

export function svd(a: number[][]): Svd {
	if (!a.length || !a[0].length) throw new Error("svd: lege matrix");
	const m = a.length;
	const n = a[0].length;

	// Bij een brede matrix draaien we hem om en wisselen U en V in het
	// resultaat: A = U S V' impliceert A' = V S U'.
	const gedraaid = m < n;
	const b = gedraaid ? transponeer(a) : a;
	const { kolommen, v } = jacobi(b);

	const p = b.length;
	const q = b[0].length;
	const sigma = new Array<number>(q);
	for (let j = 0; j < q; j++) {
		let som = 0;
		for (let i = 0; i < p; i++) som += kolommen[i][j] * kolommen[i][j];
		sigma[j] = Math.sqrt(som);
	}

	// Stabiel sorteren op index als tiebreak, zodat gelijke singuliere waarden
	// altijd dezelfde volgorde krijgen.
	const orde = sigma.map((_, j) => j).sort((x, y) => sigma[y] - sigma[x] || x - y);
	const grootste = sigma[orde[0]] || 0;

	const uB: number[][] = Array.from({ length: p }, () => new Array<number>(q));
	const vB: number[][] = Array.from({ length: q }, () => new Array<number>(q));
	const s = new Array<number>(q);

	orde.forEach((bron, doel) => {
		s[doel] = sigma[bron];
		const verwaarloosbaar = sigma[bron] <= NUL_DREMPEL * grootste;
		for (let i = 0; i < p; i++) uB[i][doel] = verwaarloosbaar ? 0 : kolommen[i][bron] / sigma[bron];
		for (let i = 0; i < q; i++) vB[i][doel] = v[i][bron];
	});

	return gedraaid ? { u: vB, s, v: uB } : { u: uB, s, v: vB };
}
