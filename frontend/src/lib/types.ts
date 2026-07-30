// Vorm van één argument in data/export/topics/<slug>.json (zie
// pipeline/build_static_data.py: fetch_arguments). De export is bewust plat
// en ongeaggregeerd -- alles wat de frontend toont is hiervan afgeleid.

export type Stance = "pro" | "contra" | "unclear";
export type Typology = "factual" | "moral" | "economic" | "legal" | "other";

export interface Claim {
	claim_text: string;
	attributed_source_text: string | null;
}

export interface Tag {
	sleutel: string;
	beschrijving: string;
	labelgroep: string;
	perspectief: string;
	created_by: "llm" | "derived" | "manual";
	reden: string | null;
}

export interface Argument {
	id: number;
	stance: Stance;
	typology: Typology;
	quote_text: string;
	quote_context: string | null;
	prompt_version: string | null;
	actor: { name: string; party: string | null; role_title: string | null };
	document: {
		url: string | null;
		video_url: string | null;
		published_at: string | null;
		speaker_video_url: string | null;
		tweedekamer_activiteit_url: string | null;
		redactie_review: { pass_status: string; notes: string | null } | null;
	};
	// Staatsrechtelijke context van de publicatiedatum, afgeleid in de pipeline
	// uit data/politieke-periodes.toml. Null als het document geen datum heeft.
	periode: { kamer: string | null; regering: string | null };
	claims: Claim[];
	tags: Tag[];
	oppositions: { argument_id: number; relation_type: string; confidence: number | null }[];
}

// Sentinel voor argumenten waarvan de spreker geen partij heeft. Eén plek,
// zodat filter, statistieken en grafieken gegarandeerd hetzelfde bedoelen.
export const NO_PARTY = "Onbekend";

// Weergavenamen voor de drie stance-waarden uit pipeline/db/schema.sql
// (CHECK stance IN ('pro','contra','unclear')). De taxonomie uit
// data/tags.toml staat hier bewust *niet* in: tag/labelgroep/perspectief zijn
// gewone strings en de filterfacetten worden uit de data afgeleid, zodat
// tags.toml bewerkt kan worden zonder de frontend aan te raken.
const STANCE_LABELS: Record<Stance, string> = {
	pro: "Pro",
	contra: "Contra",
	unclear: "Onduidelijk",
};

export const STANCES = Object.keys(STANCE_LABELS) as Stance[];

/** Faalt hard op een onbekende stance: dan loopt deze lijst uit de pas met het
 * DB-schema, en dat willen we zien i.p.v. een rauwe waarde tonen alsof het een
 * label is. */
export function stanceLabel(stance: string): string {
	const label = STANCE_LABELS[stance as Stance];
	if (!label) throw new Error(`onbekende stance: ${stance} (schema.sql gewijzigd?)`);
	return label;
}
