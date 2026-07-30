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

// Officiële fractielogo's (SVG), gedownload van Wikimedia Commons
// (Category:SVG_logos_of_political_parties_in_the_Netherlands, via de
// Wikimedia API -- frontend/public/party-logos/). Niet elke fractie/
// eenmansgroep heeft een eigen logo -- dan geen icoon tonen i.p.v. iets
// te verzinnen (zie PartyLogo.vue's initiaal-placeholder).
const PARTY_LOGOS: Record<string, string> = {
	BBB: "/party-logos/bbb.svg",
	CDA: "/party-logos/cda.svg",
	ChristenUnie: "/party-logos/christenunie.svg",
	D66: "/party-logos/d66.svg",
	DENK: "/party-logos/denk.svg",
	FVD: "/party-logos/fvd.svg",
	"GroenLinks-PvdA": "/party-logos/groenlinks-pvda.svg",
	JA21: "/party-logos/ja21.svg",
	NSC: "/party-logos/nsc.svg",
	PRO: "/party-logos/pro.svg",
	PvdD: "/party-logos/pvdd.svg",
	PVV: "/party-logos/pvv.svg",
	SGP: "/party-logos/sgp.svg",
	SP: "/party-logos/sp.svg",
	Volt: "/party-logos/volt.svg",
	VVD: "/party-logos/vvd.svg",
};

export function partyLogo(party: string): string | null {
	return PARTY_LOGOS[party] ?? null;
}

// Vereenvoudigde, uniforme iconenset (vierkant 160x160-kavas, door de
// ontwerper geleverd) -- voor gebruik als puntsymbool op de correspondentiekaart.
// De officiële wordmarks hierboven passen daar niet: sterk uiteenlopende
// verhoudingen (PVV is 13:1) en detail dat pas bij tabelformaat leesbaar wordt.
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
