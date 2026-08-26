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
