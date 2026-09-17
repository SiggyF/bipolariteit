// PoC (issue #113): genereert per kandidaat-tag (zie live_tagger.py,
// CANDIDATE_TAG_KEYS) een los SVG-bestand met exact hetzelfde icoon/kleur
// als de site zelf -- hergebruikt frontend/src/lib/tagIcon.ts rechtstreeks
// i.p.v. de icoon-/kleurdata in Python opnieuw te parsen (zou kunnen
// verlopen zodra tagIcons.generated.ts opnieuw gegenereerd wordt).
// run_live_stream.sh rasterized deze SVG's daarna via ffmpeg/librsvg (zie
// frontend/public/youtube-logo.png voor dezelfde aanpak) naar PNG-badges
// voor de live-overlay.
//
// Gebruik (vanuit docs/poc/live-tagging/): npx --prefix ../../../frontend tsx generate_icon_badges.mjs <output_dir>

import { writeFileSync, mkdirSync } from "node:fs";
import { tagIconPath, tagKleur } from "../../../frontend/src/lib/tagIcon.ts";

const CANDIDATE_TAG_KEYS = [
	"Walton-Causaal", "Walton-Consequentie", "Walton-Expertise", "Walton-Analogie",
	"Debatzet-Persoon-Aanspreken", "Debatzet-Herformuleren", "Debatzet-Keuze-Aanscherpen",
	"Debatzet-Gevoelens-Verwoorden", "Debatzet-Cirkelredenering",
	"Stijl-Slogan", "Stijl-Herhaling", "Stijl-Retorische-Vraag", "Stijl-Godwin",
];

const outDir = process.argv[2];
if (!outDir) {
	console.error("gebruik: generate_icon_badges.mjs <output_dir>");
	process.exit(1);
}
mkdirSync(outDir, { recursive: true });

const CREME = "#F2EDE3";

for (const sleutel of CANDIDATE_TAG_KEYS) {
	const pad = tagIconPath(sleutel);
	const kleur = tagKleur(sleutel) ?? "#221F1B";
	if (!pad) {
		console.warn(`geen icoon voor ${sleutel}, overgeslagen`);
		continue;
	}
	// Op zichzelf staande badge (vierkant in de perspectiefkleur + icoon in
	// crème erop) i.p.v. los icoon: zo is het één rechthoekige overlay-PNG
	// in run_live_stream.sh, geen aparte achtergrond-laag nodig in ffmpeg.
	const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="480" height="480" viewBox="0 0 24 24">
	<rect x="0" y="0" width="24" height="24" fill="${kleur}" />
	<path d="${pad}" fill="none" stroke="${CREME}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" transform="translate(2 2) scale(0.833)" />
</svg>`;
	writeFileSync(`${outDir}/${sleutel}.svg`, svg);
	console.log(`${sleutel} -> ${outDir}/${sleutel}.svg (badge, kleur ${kleur})`);
}
