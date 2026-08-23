// Genereert de lean, al-gefilterde JSON-bestanden die gepubliceerd worden
// naar de publieke bipolariteit/bipolariteit-data-repo (issue #163). Draai
// met:
//
//   npx tsx scripts/export_public_data.ts
//
// Leest data/export/topics/*.json (van `make export`, dus geen database-
// toegang nodig) en schrijft per perspectief één bestand naar
// data/export/gepubliceerd/perspectieven/<slug>.json. Dat is precies de
// argumentenlijst die PerspectiefView.vue vroeger als Astro-prop kreeg (zie
// pages/perspectieven/[naam].astro): lean gestript + gefilterd op de tags
// van dat ene perspectief.
//
// data/export/gepubliceerd/ is een git submodule op de publieke repo
// bipolariteit/bipolariteit-data (.gitmodules) -- de hoofdrepo blijft
// private, alleen deze afgeleide, al publiek geserveerde data staat los en
// publiek zodat cdn.jsdelivr.net/gh/bipolariteit/bipolariteit-data er client-
// side bij kan (jsDelivr's GitHub-CDN werkt alleen tegen publieke repo's).
// `make publish-data` commit + pusht de submodule na deze stap.

import { mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { toLeanArgument } from "../src/lib/leanArgument";
import { filterTagsByPerspectief } from "../src/lib/aggregate";
import { slugify } from "../src/lib/slug";
import { PERSPECTIEVEN } from "../src/lib/tagIcons.generated";
import type { Argument } from "../src/lib/types";

const hier = dirname(fileURLToPath(import.meta.url));
const TOPICS_DIR = resolve(hier, "../../data/export/topics");
const UIT_DIR = resolve(hier, "../../data/export/gepubliceerd");

function allArguments(): Argument[] {
	return readdirSync(TOPICS_DIR)
		.filter((bestand) => bestand.endsWith(".json"))
		.flatMap((bestand) => {
			const topic = JSON.parse(readFileSync(resolve(TOPICS_DIR, bestand), "utf8"));
			return topic.arguments.map(toLeanArgument);
		});
}

function main(): void {
	const argumentList = allArguments();
	console.log(`${argumentList.length} argumenten ingelezen uit ${TOPICS_DIR}`);

	const perspectievenDir = resolve(UIT_DIR, "perspectieven");
	mkdirSync(perspectievenDir, { recursive: true });

	for (const { naam: perspectief } of PERSPECTIEVEN) {
		const scopedList = filterTagsByPerspectief(argumentList, perspectief);
		const pad = resolve(perspectievenDir, `${slugify(perspectief)}.json`);
		writeFileSync(pad, JSON.stringify(scopedList), "utf8");
		console.log(`${pad}: ${scopedList.length} argumenten`);
	}
}

main();
