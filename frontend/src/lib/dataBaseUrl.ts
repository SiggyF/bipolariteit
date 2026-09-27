// Eén definitie voor waar de perspectieven/onderwerpen/tags-data client-side
// vandaan gehaald wordt (issue #163: te groot om als build-asset mee te
// bakken, dus altijd client-side gefetcht i.p.v. als Astro-prop). In dev
// staat data/export/gepubliceerd/ lokaal al gecheckout (git submodule) --
// geserveerd op /data door de sirv-middleware in astro.config.mjs, geen
// aparte publicatiestap nodig om lokaal te ontwikkelen. In productie de
// jsDelivr-CDN-kopie van de publieke bipolariteit-data-repo.
const CDN_BASE_URL = "https://cdn.jsdelivr.net/gh/bipolariteit/bipolariteit-data@main";

export function resolveDataBaseUrl(): string {
	return import.meta.env.PUBLIC_DATA_BASE_URL ?? (import.meta.env.DEV ? "/data" : CDN_BASE_URL);
}

// Losse basis-URL voor de tile-pyramide van de plenaire kaart
// (plenair-map.pmtiles/-grid.json, TiledPlenairMap.vue): pmtiles hoort bij
// Hugging Face, niet bij de compacte jsDelivr-hosting hierboven (zie
// docs/data-layout.md, issue #316) -- ook de kleine variant, ondanks dat
// jsDelivr's 20 MB-limiet er nog onder zou blijven, om niet twee
// publicatiepaden voor hetzelfde bestandstype te laten bestaan. Geen aparte
// /data-fallback in dev (zoals resolveDataBaseUrl hierboven): er is geen
// publiceerstap die de tegelpyramide ooit in data/export/gepubliceerd/ (de
// lokale checkout van die /data-mirror) zet, dus die sirv-route heeft er
// nooit iets liggen -- altijd rechtstreeks tegen Hugging Face, zoals
// plenair-map-viewer-hf.html ook al doet.
//
// /plenair-map is de submap waar scripts/publish_huggingface.py
// (--repo-subdir, default "plenair-map") naartoe publiceert -- één submap
// per dataset in deze repo, i.p.v. alle bestanden plat naast elkaar, nu er
// zowel de kleine als de volle-dataset-bundel in dezelfde HF-repo komen.
const TILES_CDN_BASE_URL = "https://huggingface.co/datasets/SiggyF/bipolariteit-pmtiles/resolve/main/plenair-map";

export function resolveTilesBaseUrl(): string {
	return import.meta.env.PUBLIC_TILES_BASE_URL ?? TILES_CDN_BASE_URL;
}
