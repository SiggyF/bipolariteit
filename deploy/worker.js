/**
 * Worker voor een preview-release van de statische site.
 *
 * De site is puur statisch; deze Worker bestaat alleen om elk antwoord een
 * `X-Robots-Tag: noindex` mee te geven. Dat kan niet via een `_headers`-bestand:
 * dat is een Cloudflare *Pages*-feature en wordt door Workers static assets
 * gewoon als een statisch bestand geserveerd, dus zonder effect en zonder fout.
 *
 * Dit is ook het aangrijpingspunt mocht er later echte toegangscontrole
 * (Cloudflare Access, basic auth) op de previews moeten komen.
 */
export default {
	async fetch(request, env) {
		const asset = await env.ASSETS.fetch(request);

		// Response is immutable zolang hij van ASSETS komt; kopieer om te kunnen
		// schrijven aan de headers.
		const antwoord = new Response(asset.body, asset);
		antwoord.headers.set("X-Robots-Tag", "noindex, nofollow");
		return antwoord;
	},
};
