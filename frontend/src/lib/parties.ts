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
