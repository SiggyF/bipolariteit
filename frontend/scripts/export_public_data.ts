// Genereert de lean, al-gefilterde JSON-bestanden die gepubliceerd worden
// naar de publieke bipolariteit/bipolariteit-data-repo (issue #163). Draai
// met:
//
//   npx tsx scripts/export_public_data.ts
//
// Leest data/export/topics/*.json (van `make export`, dus geen database-
// toegang nodig) en schrijft:
//
// - per perspectief één bestand naar data/export/gepubliceerd/perspectieven/
//   <slug>.json. Dat is precies de argumentenlijst die PerspectiefView.vue
//   vroeger als Astro-prop kreeg (zie pages/perspectieven/[naam].astro): lean
//   gestript + gefilterd op de tags van dat ene perspectief.
// - per onderwerp één bestand naar data/export/gepubliceerd/onderwerpen/
//   <slug>.json. Ongestript (topic.arguments as-is): TopicView.vue rendert
//   volledige ArgumentCards (videolinks, quote_context, claims, tag-`reden`),
//   in tegenstelling tot PerspectiefView -- er valt hier dus niets lean te
//   maken zonder content te breken.
// - per debat (raw_video_url, issue #119-vervolg) één bestand naar
//   data/export/gepubliceerd/debatten/<debateId>.json. Ongestript, om
//   dezelfde reden als onderwerpen/ hierboven -- DebateVideoView.vue/
//   ClaimsHighlights.vue fetchen dit i.p.v. het hele onderwerp-bestand: een
//   onderwerp als energietransitie/asiel beslaat tientallen debatten en tot
//   ~11 MB, terwijl één debat daar maar een fractie van is.
// - per tag één bestand naar data/export/gepubliceerd/tags/<slug>.json:
//   ongestript, gefilterd tot de argumenten met die tag (zelfde als
//   filterArgumentsByTag deed in pages/tags/[sleutel].astro), met topicSlug/
//   topicName toegevoegd -- TagDetail.vue toont argumenten uit meerdere
//   onderwerpen door elkaar en heeft die annotatie per argument nodig.
// - een kopie van data/export/plenair-map.json en -clusters.json (samen
//   ~6 MB) naar data/export/gepubliceerd/. Die gingen als Astro-prop mee in
//   onderwerpen/index.astro, PlenairMap.vue fetcht ze nu client-side.
//
// data/export/gepubliceerd/ is een git submodule op de publieke repo
// bipolariteit/bipolariteit-data (.gitmodules) -- de hoofdrepo blijft
// private, alleen deze afgeleide, al publiek geserveerde data staat los en
// publiek zodat cdn.jsdelivr.net/gh/bipolariteit/bipolariteit-data er client-
// side bij kan (jsDelivr's GitHub-CDN werkt alleen tegen publieke repo's).
// `make publish-data` commit + pusht de submodule na deze stap.

import { copyFileSync, existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { toLeanArgument } from "../src/lib/leanArgument";
import { filterArgumentsByTag, filterTagsByPerspectief } from "../src/lib/aggregate";
import { groupByDebateId } from "../src/lib/debateId";
import { slugify } from "../src/lib/slug";
import { PERSPECTIEVEN } from "../src/lib/tagIcons.generated";
import { ALLE_TAGS } from "../src/lib/taxonomy";
import type { Argument } from "../src/lib/types";

const hier = dirname(fileURLToPath(import.meta.url));
const TOPICS_DIR = resolve(hier, "../../data/export/topics");
const UIT_DIR = resolve(hier, "../../data/export/gepubliceerd");

interface Topic {
	slug: string;
	name: string;
	arguments: Argument[];
}

type TopicTaggedArgument = Argument & { topicSlug: string; topicName: string };

function readTopics(): Topic[] {
	return readdirSync(TOPICS_DIR)
		.filter((bestand) => bestand.endsWith(".json"))
		.map((bestand) => JSON.parse(readFileSync(resolve(TOPICS_DIR, bestand), "utf8")));
}

function main(): void {
	const topics = readTopics();
	const argumentList = topics.flatMap((topic) => topic.arguments.map(toLeanArgument));
	console.log(`${argumentList.length} argumenten ingelezen uit ${TOPICS_DIR}`);

	const perspectievenDir = resolve(UIT_DIR, "perspectieven");
	mkdirSync(perspectievenDir, { recursive: true });

	for (const { naam: perspectief } of PERSPECTIEVEN) {
		const scopedList = filterTagsByPerspectief(argumentList, perspectief);
		const pad = resolve(perspectievenDir, `${slugify(perspectief)}.json`);
		writeFileSync(pad, JSON.stringify(scopedList), "utf8");
		console.log(`${pad}: ${scopedList.length} argumenten`);
	}

	const onderwerpenDir = resolve(UIT_DIR, "onderwerpen");
	mkdirSync(onderwerpenDir, { recursive: true });

	for (const topic of topics) {
		const pad = resolve(onderwerpenDir, `${topic.slug}.json`);
		writeFileSync(pad, JSON.stringify(topic.arguments), "utf8");
		console.log(`${pad}: ${topic.arguments.length} argumenten`);
	}

	const debattenDir = resolve(UIT_DIR, "debatten");
	mkdirSync(debattenDir, { recursive: true });

	const argumentenPerDebat = groupByDebateId(topics.flatMap((topic) => topic.arguments));
	for (const [id, debateArguments] of argumentenPerDebat) {
		const pad = resolve(debattenDir, `${id}.json`);
		writeFileSync(pad, JSON.stringify(debateArguments), "utf8");
		console.log(`${pad}: ${debateArguments.length} argumenten`);
	}

	const fullArgumentList: TopicTaggedArgument[] = topics.flatMap((topic) =>
		topic.arguments.map((argument) => ({ ...argument, topicSlug: topic.slug, topicName: topic.name })),
	);

	const tagsDir = resolve(UIT_DIR, "tags");
	mkdirSync(tagsDir, { recursive: true });

	for (const tag of ALLE_TAGS) {
		const taggedArguments = filterArgumentsByTag(fullArgumentList, tag.sleutel);
		const pad = resolve(tagsDir, `${slugify(tag.sleutel)}.json`);
		writeFileSync(pad, JSON.stringify(taggedArguments), "utf8");
		console.log(`${pad}: ${taggedArguments.length} argumenten`);
	}

	const publicDataDir = resolve(hier, "../public/data");
	mkdirSync(publicDataDir, { recursive: true });

	for (const bestand of ["plenair-map.json", "plenair-map-clusters.json", "plenair-map-videos.json"]) {
		const bron = resolve(hier, "../../data/export", bestand);
		if (existsSync(bron)) {
			const doel = resolve(UIT_DIR, bestand);
			copyFileSync(bron, doel);
			console.log(`${doel}: gekopieerd van ${bron}`);

			const publicDoel = resolve(publicDataDir, bestand);
			copyFileSync(bron, publicDoel);
		}
	}
}

main();
