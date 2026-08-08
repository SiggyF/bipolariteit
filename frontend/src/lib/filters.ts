import { reactive } from "vue";
import { NO_PARTY, stanceLabel, type Argument } from "./types";
import { displayPartyName } from "./parties";

// Eén filterstore voor de hele topicpagina. Vervangt useTagFilter/usePartyFilter,
// die via DOM-CustomEvents tussen losse Astro-islands praatten -- alles wat
// filterbaar is zit nu in één island (TopicView.vue), dus een gewone
// module-scope reactive store volstaat en het event-geplak kan weg.
//
// De URL is de bron van waarheid: elke wijziging schrijft query params, en
// popstate leest ze terug. Daarmee is een gefilterde weergave deelbaar,
// overleeft-ie een refresh en werkt de terugknop.
//
// Model: multi-select per dimensie, OR *binnen* een dimensie en AND *tussen*
// dimensies. Twee tags = argumenten met tag A of B; plus een partij = én van
// die partij.

export interface Dimension {
	/** Interne sleutel én naam van de query param. */
	key: string;
	label: string;
	/** Alle waarden die dit argument voor deze dimensie heeft (leeg = matcht nooit een actief filter). */
	valuesOf(argument: Argument): string[];
	/** Weergavenaam voor een waarde; default de waarde zelf. */
	format?(value: string): string;
	/** Opties op tijd sorteren i.p.v. op aantal. Voor periodes is "Rutte IV,
	 * Schoof, Jetten" de enige leesbare volgorde; welke toevallig het meeste
	 * volume heeft zegt niets. De volgorde volgt uit de vroegste publicatie-
	 * datum binnen een periode, dus zonder extra veld in de export. */
	chronological?: boolean;
}

// Rol is alleen gevuld voor bewindspersonen (documents.speaker_role_title).
// Leeg betekent letterlijk "geen rol vermeld" -- er staat nergens "Kamerlid",
// dus dat leiden we hier ook niet af.
const NO_ROLE = "geen bewindspersoonsrol";

export const DIMENSIONS: Dimension[] = [
	{
		key: "stance",
		label: "Positie",
		valuesOf: (a) => [a.stance],
		format: stanceLabel,
	},
	{ key: "typologie", label: "Typologie", valuesOf: (a) => [a.typology] },
	{
		key: "partij",
		label: "Partij",
		valuesOf: (a) => [a.actor.party ?? NO_PARTY],
		format: displayPartyName,
	},
	{ key: "persoon", label: "Persoon", valuesOf: (a) => [a.actor.name] },
	{ key: "rol", label: "Rol", valuesOf: (a) => [a.actor.role_title ?? NO_ROLE] },
	// Kabinetten en Kamers wisselen op andere momenten dan kalenderjaren, en
	// niet gelijk met elkaar -- vandaar twee losse dimensies naast het vrije
	// datumbereik. De grenzen komen uit data/politieke-periodes.toml en zijn
	// in de pipeline al per argument opgezocht.
	{
		key: "regering",
		label: "Kabinet",
		valuesOf: (a) => (a.periode.regering ? [a.periode.regering] : []),
		chronological: true,
	},
	{
		key: "kamer",
		label: "Kamerperiode",
		valuesOf: (a) => (a.periode.kamer ? [a.periode.kamer] : []),
		chronological: true,
	},
	{ key: "tag", label: "Tag", valuesOf: (a) => a.tags.map((t) => t.sleutel) },
	{ key: "labelgroep", label: "Labelgroep", valuesOf: (a) => a.tags.map((t) => t.labelgroep) },
	{ key: "perspectief", label: "Perspectief", valuesOf: (a) => a.tags.map((t) => t.perspectief) },
];

const DIMENSION_BY_KEY = new Map(DIMENSIONS.map((d) => [d.key, d]));

export const DATE_FROM = "van";
export const DATE_TO = "tot";

export interface FilterState {
	/** dimensiesleutel -> geselecteerde waarden (OR binnen de dimensie). */
	values: Record<string, string[]>;
	/** Publicatiedatum van het brondocument, ISO yyyy-mm-dd, inclusief grenzen. */
	van: string | null;
	tot: string | null;
}

function emptyState(): FilterState {
	return { values: Object.fromEntries(DIMENSIONS.map((d) => [d.key, []])), van: null, tot: null };
}

export const filters = reactive<FilterState>(emptyState());

export function isActive(): boolean {
	return DIMENSIONS.some((d) => filters.values[d.key].length > 0) || !!filters.van || !!filters.tot;
}

export function activeCount(): number {
	const values = DIMENSIONS.reduce((n, d) => n + filters.values[d.key].length, 0);
	return values + (filters.van ? 1 : 0) + (filters.tot ? 1 : 0);
}

export function matches(argument: Argument): boolean {
	return matchesExcept(argument, []);
}

/** Als `matches`, maar met een paar dimensies overgeslagen. `skipKeys` mag
 * naast dimensiesleutels ook `DATE_FROM`/`DATE_TO` bevatten om het datumbereik
 * over te slaan.
 *
 * Bestaat voor de correspondentiekaart: die rekent zichzelf uit op de selectie,
 * maar haar hoofdactie is klikken op een tag om erop te filteren. Zou ze op de
 * volledig gefilterde lijst rekenen, dan bleef er na één klik één kolom over en
 * stortte de analyse in. De kaart slaat daarom `tag` en `partij` over bij het
 * rekenen en gebruikt die twee alleen nog om punten te dimmen.
 *
 * De argumententijdlijn slaat op dezelfde manier `DATE_FROM`/`DATE_TO` over:
 * klikken op een staaf zet het datumfilter, maar de tijdlijn moet alle
 * debatdagen blijven tonen om te laten zien wélke dag je selecteerde. */
export function matchesExcept(argument: Argument, skipKeys: string[]): boolean {
	for (const dimension of DIMENSIONS) {
		if (skipKeys.includes(dimension.key)) continue;
		const selected = filters.values[dimension.key];
		if (!selected.length) continue;
		const values = dimension.valuesOf(argument);
		if (!selected.some((value) => values.includes(value))) return false;
	}

	// published_at is naive lokale tijd; het datumdeel volstaat en vergelijkt
	// als string correct omdat ISO-8601 lexicografisch op datum sorteert.
	const date = argument.document.published_at?.slice(0, 10);
	if (!skipKeys.includes(DATE_FROM) && filters.van && (!date || date < filters.van)) return false;
	if (!skipKeys.includes(DATE_TO) && filters.tot && (!date || date > filters.tot)) return false;
	return true;
}

export function formatValue(dimensionKey: string, value: string): string {
	const dimension = DIMENSION_BY_KEY.get(dimensionKey);
	if (!dimension) throw new Error(`onbekende filterdimensie: ${dimensionKey}`);
	return dimension.format ? dimension.format(value) : value;
}

export function labelFor(dimensionKey: string): string {
	const dimension = DIMENSION_BY_KEY.get(dimensionKey);
	if (!dimension) throw new Error(`onbekende filterdimensie: ${dimensionKey}`);
	return dimension.label;
}

/** Beschikbare waarden per dimensie met hun aantal, over de *hele* topic. */
export function facetOptions(argumentList: Argument[]) {
	return DIMENSIONS.map((dimension) => {
		const counts = new Map<string, number>();
		const earliest = new Map<string, string>();
		for (const argument of argumentList) {
			const date = argument.document.published_at ?? "";
			// Set: een argument met 3 tags uit dezelfde labelgroep telt één keer
			// mee voor die labelgroep, net zoals het filter het één keer matcht.
			for (const value of new Set(dimension.valuesOf(argument))) {
				counts.set(value, (counts.get(value) ?? 0) + 1);
				const known = earliest.get(value);
				if (known === undefined || date < known) earliest.set(value, date);
			}
		}
		const options = [...counts].map(([value, count]) => ({
			value,
			count,
			label: formatValue(dimension.key, value),
		}));
		options.sort((a, b) =>
			dimension.chronological
				? earliest.get(a.value)!.localeCompare(earliest.get(b.value)!)
				: b.count - a.count || a.label.localeCompare(b.label, "nl"),
		);
		return { key: dimension.key, label: dimension.label, options };
	});
}

// --- mutaties -------------------------------------------------------------

export function toggleValue(dimensionKey: string, value: string) {
	const selected = filters.values[dimensionKey];
	if (!selected) throw new Error(`onbekende filterdimensie: ${dimensionKey}`);
	const i = selected.indexOf(value);
	if (i === -1) selected.push(value);
	else selected.splice(i, 1);
	syncToUrl();
}

export function removeValue(dimensionKey: string, value: string) {
	const selected = filters.values[dimensionKey];
	const i = selected.indexOf(value);
	if (i !== -1) selected.splice(i, 1);
	syncToUrl();
}

export function setDateRange(van: string | null, tot: string | null) {
	filters.van = van || null;
	filters.tot = tot || null;
	syncToUrl();
}

export function clearAll() {
	for (const dimension of DIMENSIONS) filters.values[dimension.key] = [];
	filters.van = null;
	filters.tot = null;
	syncToUrl();
}

// --- URL-synchronisatie ---------------------------------------------------

// Herhaalde params (?rol=a&rol=b) i.p.v. een komma-gescheiden lijst: rol-
// waarden bevatten zelf komma's ("minister van Landbouw, Visserij, ..."),
// dus elk scheidingsteken zou ontsnapping nodig hebben.
function toSearchParams(): URLSearchParams {
	const params = new URLSearchParams();
	for (const dimension of DIMENSIONS) {
		for (const value of filters.values[dimension.key]) params.append(dimension.key, value);
	}
	if (filters.van) params.set(DATE_FROM, filters.van);
	if (filters.tot) params.set(DATE_TO, filters.tot);
	return params;
}

// Waarden die daadwerkelijk in deze topic voorkomen, per dimensie. Query params
// zijn gebruikersinvoer: een handmatig getypte `?stance=bogus` mag geen filter
// worden dat nooit iets matcht (en al helemaal niet door een formatter knallen).
let knownValues = new Map<string, Set<string>>();

function applySearchParams(params: URLSearchParams) {
	for (const dimension of DIMENSIONS) {
		const known = knownValues.get(dimension.key)!;
		const requested = params.getAll(dimension.key);
		const accepted = requested.filter((value) => known.has(value));
		for (const value of requested) {
			if (!known.has(value)) console.warn(`filter genegeerd: ${dimension.key}=${value} komt niet voor in deze topic`);
		}
		filters.values[dimension.key] = accepted;
	}
	filters.van = parseDate(params.get(DATE_FROM));
	filters.tot = parseDate(params.get(DATE_TO));
}

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

function parseDate(value: string | null): string | null {
	if (!value) return null;
	if (!ISO_DATE.test(value)) {
		console.warn(`datumfilter genegeerd: ${value} is geen yyyy-mm-dd`);
		return null;
	}
	return value;
}

function syncToUrl() {
	const params = toSearchParams();
	const query = params.toString();
	history.pushState(null, "", query ? `?${query}${location.hash}` : `${location.pathname}${location.hash}`);
	persistToStorage(query);
}

function onPopState() {
	applySearchParams(new URLSearchParams(location.search));
}

// --- persistentie over paginanavigaties heen -------------------------------

// Deze site is een klassieke multi-page Astro-app (volle paginaladingen, geen
// client-router), dus de reactive store zelf overleeft geen navigatie. Om
// filters toch "autoscout24-achtig" over pagina's heen te laten gelden, bewaren
// we de laatste querystring in localStorage en lezen we hem terug zodra een
// nieuwe pagina met een lege URL start. Een pagina met een eigen querystring
// (bv. een expliciete "?persoon=..."-link) is een bewuste keuze en overschrijft
// de bewaarde filters volledig -- geen samenvoegen.
const STORAGE_KEY = "bipolariteit-filters";

function persistToStorage(query: string) {
	if (typeof window === "undefined") return;
	try {
		if (query) window.localStorage.setItem(STORAGE_KEY, query);
		else window.localStorage.removeItem(STORAGE_KEY);
	} catch {
		// localStorage kan ontbreken/geblokkeerd zijn (bv. privénavigatie); dan
		// werkt filteren nog gewoon, alleen zonder persistentie.
	}
}

function loadFromStorage(): string | null {
	if (typeof window === "undefined") return null;
	try {
		return window.localStorage.getItem(STORAGE_KEY);
	} catch {
		return null;
	}
}

/** Leest de URL (of, bij een lege URL, de bewaarde filters) in de store en
 * houdt beide daarna in sync. Bedoeld als één aanroep bij het opzetten van de
 * pagina, maar idempotent: HMR of een hermontage van het island mag geen
 * tweede popstate-listener opleveren, want dan zou elke URL-wijziging dubbel
 * verwerkt worden. */
export function initFiltersFromUrl(argumentList: Argument[]) {
	knownValues = new Map(
		DIMENSIONS.map((dimension) => [
			dimension.key,
			new Set(argumentList.flatMap((argument) => dimension.valuesOf(argument))),
		]),
	);

	if (location.search) {
		applySearchParams(new URLSearchParams(location.search));
	} else {
		const stored = loadFromStorage();
		if (stored) {
			applySearchParams(new URLSearchParams(stored));
			if (isActive()) syncToUrl();
		}
	}

	// Zelfde functiereferentie, dus een tweede registratie is een no-op.
	window.removeEventListener("popstate", onPopState);
	window.addEventListener("popstate", onPopState);
}
