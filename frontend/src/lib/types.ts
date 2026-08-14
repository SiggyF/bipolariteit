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
	// Zin-precies gematchte videospanne (pipeline/match_argument_spans.py); null
	// zolang quote_text niet tegen de ondertitels gematcht kon worden -- val dan
	// terug op document.published_at t.o.v. de debat-aanvangstijd plus een vaste duur.
	start_seconds: number | null;
	end_seconds: number | null;
	actor: { name: string; party: string | null; role_title: string | null };
	document: {
		id: number;
		url: string | null;
		video_url: string | null;
		published_at: string | null;
		speaker_video_url: string | null;
		tweedekamer_activiteit_url: string | null;
		redactie_review: { pass_status: string; notes: string | null } | null;
		// Het afspeelbare HLS-manifest (pipeline/fetch_subtitles.py); null zolang
		// dat nog niet (succesvol) opgehaald is voor dit debat.
		raw_video_url: string | null;
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
// Wat "pro" en "contra" concreet betekenen wordt per onderwerp apart
// gedefinieerd (topics.description in de database, zichtbaar bovenaan elke
// topicpagina) -- het is niet overal hetzelfde als "voor/tegen het beleid".
// Bij stikstof is dat wel zo, bij abortus gaat de as bijvoorbeeld over
// keuzevrijheid t.o.v. bescherming van het ongeboren kind.
const STANCE_LABELS: Record<Stance, { label: string; beschrijving: string }> = {
	pro: { label: "Pro", beschrijving: "De 'pro'-kant van de pro/contra-as die per onderwerp apart is gedefinieerd, zie de toelichting bovenaan de topicpagina." },
	contra: { label: "Contra", beschrijving: "De 'contra'-kant van diezelfde onderwerpsspecifieke as." },
	unclear: { label: "Onduidelijk", beschrijving: "Richting t.o.v. die as is niet eenduidig, of het argument gaat over het debat zelf." },
};

export const STANCES = Object.keys(STANCE_LABELS) as Stance[];

/** Faalt hard op een onbekende stance: dan loopt deze lijst uit de pas met het
 * DB-schema, en dat willen we zien i.p.v. een rauwe waarde tonen alsof het een
 * label is. */
export function stanceLabel(stance: string): string {
	const entry = STANCE_LABELS[stance as Stance];
	if (!entry) throw new Error(`onbekende stance: ${stance} (schema.sql gewijzigd?)`);
	return entry.label;
}

export function stanceDescription(stance: string): string {
	const entry = STANCE_LABELS[stance as Stance];
	if (!entry) throw new Error(`onbekende stance: ${stance} (schema.sql gewijzigd?)`);
	return entry.beschrijving;
}

// Weergavenamen en -omschrijvingen voor de vijf typology-waarden, zoals
// gedefinieerd in pipeline/prompts/extract_argument.md.
const TYPOLOGY_LABELS: Record<Typology, { label: string; beschrijving: string }> = {
	factual: {
		label: "Feitelijk",
		beschrijving: "Feiten, cijfers, of beleidsinhoudelijke/bestuurlijke constateringen, zoals een norm, een fractiestandpunt, of wie iets wel/niet steunt.",
	},
	moral: { label: "Moreel", beschrijving: "Beroept zich op ethiek of waarden." },
	economic: { label: "Economisch", beschrijving: "Gaat over kosten en baten." },
	legal: {
		label: "Juridisch",
		beschrijving: "Verwijst naar een specifieke wet, regelgeving, of juridische toetsing/procedure.",
	},
	other: {
		label: "Overig",
		beschrijving: "Past niet in de andere categorieën, bijvoorbeeld metadiscours over het debat zelf.",
	},
};

export const TYPOLOGIES = Object.keys(TYPOLOGY_LABELS) as Typology[];

/** Faalt hard op een onbekende typology, om dezelfde reden als stanceLabel. */
export function typologyLabel(typology: string): string {
	const entry = TYPOLOGY_LABELS[typology as Typology];
	if (!entry) throw new Error(`onbekende typology: ${typology} (schema.sql gewijzigd?)`);
	return entry.label;
}

export function typologyDescription(typology: string): string {
	const entry = TYPOLOGY_LABELS[typology as Typology];
	if (!entry) throw new Error(`onbekende typology: ${typology} (schema.sql gewijzigd?)`);
	return entry.beschrijving;
}
