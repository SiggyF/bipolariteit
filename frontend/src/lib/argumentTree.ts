// Vorm van de argumentenboom-export (data/export/argument-trees/<slug>.json,
// pipeline/build_argument_tree.py) en de afleidingen die de weergaven daarvan
// nodig hebben. De veldnamen (gist, citaat, spreker, ...) spiegelen 1:1 de
// export; de functies hieronder zijn pure afleidingen zonder Vue, zodat ze los
// te testen zijn.

export interface ExportArgument {
	id: number;
	citaat: string;
	typologie: string;
	stance: "pro" | "contra";
	spreker: string;
	partij: string | null;
	tags: string[];
	claims: { claim_text: string; attributed_source_text: string | null }[];
	tweedekamer_activiteit_url: string | null;
	raw_video_url: string | null;
	start_seconds: number | null;
	gist: string;
	samenvatting: string | null;
}

export interface Kid {
	id: number;
	scheme: string | null;
	reden: string;
}

export interface BandSlot {
	type: "node" | "ref";
	id?: number;
	kids?: Kid[];
	ref_id?: number;
	band_nummer?: number;
}

export interface Band {
	nummer: number;
	thema: string;
	pro: BandSlot | null;
	contra: BandSlot | null;
	oppositie: {
		argument_a_id: number;
		argument_b_id: number;
		scheme: string | null;
		reden: string;
	} | null;
}

export interface LosseGroep {
	kind: "group";
	label: string;
	samenvatting: string | null;
	member_ids: number[];
}

export interface Twijfel {
	argument_id: number;
	huidige_stance: string;
	reden: string;
}

export interface ConfrontatieExport {
	slug: string;
	name: string;
	topic_description: string | null;
	stats: { totaal_argumenten: number; aantal_pro: number; aantal_contra: number; aantal_geselecteerd: number };
	arguments: Record<string, ExportArgument>;
	bands: Band[];
	losse_groepen: LosseGroep[];
	losse_argumenten: number[];
	twijfelachtige_classificaties: Twijfel[];
}

export type Side = "pro" | "contra";

/** Welk deel van de boom een lijst toont: alles, één band (op nummer) of alleen
 * de argumenten zonder tegenhanger. */
export type Scope = "all" | "loose" | number;

const TYPE_NL: Record<string, string> = {
	factual: "feitelijk",
	moral: "moreel",
	legal: "juridisch",
	economic: "economisch",
	other: "overig",
};

export function typeNl(typology: string): string {
	return TYPE_NL[typology] ?? typology;
}

export function argumentById(tree: ConfrontatieExport, id: number | null | undefined): ExportArgument | undefined {
	if (id === null || id === undefined) return undefined;
	return tree.arguments[String(id)];
}

function slotOf(band: Band, side: Side): BandSlot | null {
	return side === "pro" ? band.pro : band.contra;
}

/** Id's van een band-kant: de hoofdknoop gevolgd door zijn onderbouwing. Een
 * verwijskaart (type "ref") telt niet mee: dat argument hangt elders. */
function slotIds(slot: BandSlot | null): number[] {
	if (!slot || slot.type !== "node" || slot.id === undefined) return [];
	return [slot.id, ...(slot.kids ?? []).map((kid) => kid.id)];
}

export interface BandSummary {
	nummer: number;
	thema: string;
	proCount: number;
	contraCount: number;
}

export function bandSummaries(tree: ConfrontatieExport): BandSummary[] {
	return tree.bands.map((band) => ({
		nummer: band.nummer,
		thema: band.thema,
		proCount: slotIds(band.pro).length,
		contraCount: slotIds(band.contra).length,
	}));
}

/** Aantal uitgelichte argumenten per kant. Bewust uit `arguments` geteld en
 * niet uit `stats`: die tellen het hele corpus, niet de uitgelichte selectie. */
export function sideTotals(tree: ConfrontatieExport): Record<Side, number> {
	const totals: Record<Side, number> = { pro: 0, contra: 0 };
	for (const argument of Object.values(tree.arguments)) {
		totals[argument.stance] += 1;
	}
	return totals;
}

function looseGroups(tree: ConfrontatieExport, side: Side): LosseGroep[] {
	return tree.losse_groepen.filter((group) => argumentById(tree, group.member_ids[0])?.stance === side);
}

function looseIds(tree: ConfrontatieExport, side: Side): number[] {
	return tree.losse_argumenten.filter((id) => argumentById(tree, id)?.stance === side);
}

/** Aantal argumenten zonder tegenhanger (coördinatieve groepen tellen met hun
 * leden mee), voor één kant of voor beide. */
export function looseCount(tree: ConfrontatieExport, side?: Side): number {
	const sides: Side[] = side ? [side] : ["pro", "contra"];
	let count = 0;
	for (const s of sides) {
		count += looseIds(tree, s).length;
		for (const group of looseGroups(tree, s)) count += group.member_ids.length;
	}
	return count;
}

export interface ListEntry {
	id: number;
	/** "node": hoofdargument; "kid": onderbouwing eronder; "ref": verwijzing
	 * naar een argument dat in een andere band hangt. */
	kind: "node" | "kid" | "ref";
	refBand?: number;
}

export interface ListGroup {
	key: string;
	/** Bandnummer als de groep een deelthema is, anders null. */
	nummer: number | null;
	title: string;
	summary: string | null;
	entries: ListEntry[];
}

function bandGroup(band: Band, side: Side): ListGroup | null {
	const slot = slotOf(band, side);
	if (!slot) return null;
	const entries: ListEntry[] = [];
	if (slot.type === "node" && slot.id !== undefined) {
		entries.push({ id: slot.id, kind: "node" });
		for (const kid of slot.kids ?? []) entries.push({ id: kid.id, kind: "kid" });
	} else if (slot.type === "ref" && slot.ref_id !== undefined) {
		entries.push({ id: slot.ref_id, kind: "ref", refBand: slot.band_nummer });
	}
	if (entries.length === 0) return null;
	return { key: `band-${band.nummer}`, nummer: band.nummer, title: band.thema, summary: null, entries };
}

function looseListGroups(tree: ConfrontatieExport, side: Side): ListGroup[] {
	const groups: ListGroup[] = looseGroups(tree, side).map((group) => ({
		key: `groep-${group.label}`,
		nummer: null,
		title: group.label,
		summary: group.samenvatting,
		entries: group.member_ids.map((id) => ({ id, kind: "node" as const })),
	}));
	const rest = looseIds(tree, side);
	if (rest.length) {
		groups.push({
			key: "los",
			nummer: null,
			title: "Zonder tegenhanger",
			summary: null,
			entries: rest.map((id) => ({ id, kind: "node" as const })),
		});
	}
	return groups;
}

/** De groepen van een lijst: per deelthema (of per losse groep) de
 * argumenten van één kant, onderbouwing direct onder het hoofdargument. */
export function listGroups(tree: ConfrontatieExport, side: Side, scope: Scope): ListGroup[] {
	if (scope === "loose") return looseListGroups(tree, side);
	const bands = scope === "all" ? tree.bands : tree.bands.filter((band) => band.nummer === scope);
	const groups = bands.map((band) => bandGroup(band, side)).filter((group): group is ListGroup => group !== null);
	if (scope === "all") groups.push(...looseListGroups(tree, side));
	return groups;
}

/** Het scope waarin een argument in de lijsten voorkomt: het nummer van zijn
 * band, of "loose" als het buiten de banden valt. */
export function scopeOf(tree: ConfrontatieExport, id: number): Scope {
	for (const band of tree.bands) {
		if (slotIds(band.pro).includes(id) || slotIds(band.contra).includes(id)) return band.nummer;
	}
	return "loose";
}

/** Per argument de argumenten waar het over de as tegenover staat (weerlegging). */
export function oppositionPartners(tree: ConfrontatieExport): Map<number, number[]> {
	const map = new Map<number, number[]>();
	for (const band of tree.bands) {
		const opposition = band.oppositie;
		if (!opposition) continue;
		const { argument_a_id: a, argument_b_id: b } = opposition;
		if (!map.has(a)) map.set(a, []);
		if (!map.has(b)) map.set(b, []);
		map.get(a)!.push(b);
		map.get(b)!.push(a);
	}
	return map;
}

/** Onderbouwing (kid) naar het argument dat het onderbouwt. */
export function parentOf(tree: ConfrontatieExport): Map<number, number> {
	const map = new Map<number, number>();
	for (const band of tree.bands) {
		for (const slot of [band.pro, band.contra]) {
			if (slot?.type !== "node" || slot.id === undefined) continue;
			for (const kid of slot.kids ?? []) map.set(kid.id, slot.id);
		}
	}
	return map;
}

/** Id's van de onderbouwing van een argument, in exportvolgorde. */
export function kidIdsOf(tree: ConfrontatieExport, id: number): number[] {
	for (const band of tree.bands) {
		for (const slot of [band.pro, band.contra]) {
			if (slot?.type === "node" && slot.id === id) return (slot.kids ?? []).map((kid) => kid.id);
		}
	}
	return [];
}
