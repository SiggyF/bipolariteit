// De brondata bevat voor sommige partijen zowel de afkorting als de voluit
// geschreven naam (bv. "NSC" én "Nieuw Sociaal Contract") -- zonder
// normalisatie splitst dat tellingen/logo-lookups in tweeën. Naar de
// afkorting, want dat is de sleutel die de logo-/kleurenkaarten hieronder
// gebruiken.
const PARTY_ALIASSEN: Record<string, string> = {
	"Nieuw Sociaal Contract": "NSC",
	FvD: "FVD",
};

/** Normaliseert een partijnaam uit de brondata naar de canonieke afkorting,
 * zodat aliassen niet als aparte partijen tellen. */
export function canonicalParty(party: string): string {
	return PARTY_ALIASSEN[party] ?? party;
}

// Disambiguatie voor partijnamen die zonder context verwarrend zijn.
// "PRO" is zowel een partijnaam als de stance-waarde "Pro" (voorstander) --
// overal "Partij PRO" tonen voorkomt die verwarring. Puur weergave -- de
// brondata blijft ongewijzigd.
const PARTY_DISPLAY_NAMES: Record<string, string> = {
	PRO: "PRO (PvdA/GroenLinks)",
};

export function displayPartyName(party: string): string {
	return PARTY_DISPLAY_NAMES[party] ?? party;
}

// Vereenvoudigde, uniforme iconenset (vierkant 160x160-canvas, door de
// ontwerper geleverd) -- voor gebruik als puntsymbool op klein formaat.
// De officiële fractielogo's/wordmarks (Wikimedia Commons, ooit hier als
// PARTY_LOGOS aanwezig) lopen sterk uiteen in verhouding (PVV is 13:1) en
// zijn pas bij tabelformaat leesbaar; op de vaste 18x18px van PartyLogo.vue
// werden ze onleesbaar klein. Deze set is de enige die nog gebruikt wordt
// (PartyLogo.vue, partyLogoSprite.ts/de correspondentiekaart) -- niet elke
// fractie/eenmansgroep heeft er een, dan geen icoon tonen i.p.v. iets te
// verzinnen (zie PartyLogo.vue's initiaal-placeholder).
const PARTY_LOGOS_SIMPLE: Record<string, string> = {
	BBB: "/party-logos/simplified/bbb.svg",
	CDA: "/party-logos/simplified/cda.svg",
	ChristenUnie: "/party-logos/simplified/christenunie.svg",
	D66: "/party-logos/simplified/d66.svg",
	DENK: "/party-logos/simplified/denk.svg",
	FVD: "/party-logos/simplified/fvd.svg",
	"GroenLinks-PvdA": "/party-logos/simplified/groenlinks-pvda.svg",
	JA21: "/party-logos/simplified/ja21.svg",
	NSC: "/party-logos/simplified/nsc.svg",
	PRO: "/party-logos/simplified/pro.svg",
	PvdD: "/party-logos/simplified/pvdd.svg",
	PVV: "/party-logos/simplified/pvv.svg",
	SGP: "/party-logos/simplified/sgp.svg",
	SP: "/party-logos/simplified/sp.svg",
	Volt: "/party-logos/simplified/volt.svg",
	VVD: "/party-logos/simplified/vvd.svg",
};

export function partyLogoSimple(party: string): string | null {
	return PARTY_LOGOS_SIMPLE[party] ?? null;
}

/** Initiaal voor de placeholder-tegel van een partij/fractie zonder logo
 * (PartyLogo.vue, en de rijen zonder logo op de correspondentiekaart). Het
 * voorvoegsel van eenmansgroepen ("Lid Keijzer", "Groep Markuszower") zegt
 * niets over wie het is -- de kern van de naam wel. */
export function partyInitial(party: string): string {
	const kern = party.replace(/^(Lid|Groep|Fractie)\s+/i, "").trim();
	return (kern.charAt(0) || party.charAt(0) || "?").toUpperCase();
}
