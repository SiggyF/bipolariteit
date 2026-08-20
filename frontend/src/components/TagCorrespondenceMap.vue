<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useTheme } from "../lib/useTheme";
import { displayPartyName, partyInitial } from "../lib/parties";
import { logoSprite } from "../lib/partyLogoSprite";
import { slugify } from "../lib/slug";
import { PERSPECTIEVEN } from "../lib/tagIcons.generated";
import { filters, isActive, matches, toggleValue } from "../lib/filters";
import { NO_PARTY, type Argument } from "../lib/types";
import { alignSigns, buildCorrespondence, type Correspondence, type RowUnit } from "../lib/correspondence";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { LineChart, ScatterChart } from "echarts/charts";
import { TooltipComponent, GridComponent, LegendComponent, DataZoomInsideComponent } from "echarts/components";

use([CanvasRenderer, ScatterChart, LineChart, TooltipComponent, GridComponent, LegendComponent, DataZoomInsideComponent]);

const props = defineProps<{ argumentList: Argument[] }>();

// Personen boven partijen: een partij is een optelsom van tientallen sprekers
// met uiteenlopende eigen stijl, en die nuance is precies waar de kaart voor
// bedoeld is -- partijen blijven een schakelbare optie, geen standaard.
const unit = ref<RowUnit>("persoon");
const threeDimensional = ref(false);

// Bij persoon als rij is een drempel van 3 te laag: veel sprekers hebben één of
// twee argumenten en zouden als losse punten de wolk vullen zonder iets te zeggen.
// 10 is de ondergrens waarop een partij met maar één actieve spreker in een
// onderwerp (bv. FVD bij abortus) nog wél meetelt, zonder de drempel zo laag te
// zetten dat sprekers met een enkel argument de wolk weer gaan vullen.
const MIN_ROW_TOTAL: Record<RowUnit, number> = { partij: 3, persoon: 10 };

const filtered = computed(() => props.argumentList.filter(matches));

// Twee manieren om met een actief filter om te gaan -- welke dimensie(s) ook,
// dus niet alleen tag/partij: elke selectie kan de tabel tot een handjevol
// rijen/kolommen laten terugvallen, en dat verdient overal dezelfde knop i.p.v.
// een uitzondering die per dimensie verschilt.
// - "focus" (standaard): rekent op de ongefilterde volledige lijst en dimt de
//   punten buiten de selectie. Zo blijft de hele wolk zichtbaar terwijl de
//   selectie oplicht -- handig om te zien waar iets t.o.v. de rest staat, en
//   voorkomt dat de tabel na een klik op een tag-/partijpunt (of een filter in
//   de zijbalk) tot één rij/kolom terugvalt.
// - "detail": herberekent de analyse alleen op de gefilterde selectie, net
//   als de rest van de pagina. `buildTable` (correspondence.ts) geeft `null`
//   bij minder dan 3 rijen/kolommen i.p.v. iets te tonen dat niks meer zegt,
//   dus een filter dat te ver doorschiet laat de kaart netjes leeg lopen i.p.v.
//   vast te lopen.
const analysisMode = ref<"focus" | "detail">("focus");

// BELANGRIJKE INVARIANT, niet opnieuw laten wegglippen (zie #39): `matches()`
// (lib/filters.ts) telt een argument al mee zodra één van zijn tags aan een
// tag-dimensie (tag/labelgroep/perspectief) voldoet -- OR binnen de dimensie.
// Zo'n argument kan dus best nog andere, niet-geselecteerde tags dragen. Voor
// de rijen (personen/partijen) is dat correct: het argument telt terecht mee.
// Voor de kolommen (tags) is het dat niet -- die andere tags horen zelf niet
// bij de selectie en mogen dus geen kolom worden (sourceList/detail) én niet
// als "in selectie" (dus onopvallend/niet-gedimd) getoond worden in "focus"
// (tagsInSelection). Beide plekken moeten daarom per tag filteren, niet per
// argument -- gebruik hiervoor altijd deze functie, nooit een kale
// `argument.tags.map(...)`/`.flatMap(...)`.
function tagMatchesTagFilters(tag: Argument["tags"][number]): boolean {
	const { tag: tagSel, labelgroep: labelgroepSel, perspectief: perspectiefSel } = filters.values;
	if (tagSel.length && !tagSel.includes(tag.sleutel)) return false;
	if (labelgroepSel.length && !labelgroepSel.includes(tag.labelgroep)) return false;
	if (perspectiefSel.length && !perspectiefSel.includes(tag.perspectief)) return false;
	return true;
}

const sourceList = computed(() => {
	if (analysisMode.value !== "detail") return props.argumentList;
	return filtered.value.map((a) => ({ ...a, tags: a.tags.filter(tagMatchesTagFilters) }));
});

// Referentie over het hele corpus: waar de tekens van de assen aan opgehangen
// worden, zodat de kaart niet spiegelt terwijl je filtert.
//
// Altijd 3 componenten, ook in 2D-weergave: zou dit meebewegen met de toggle,
// dan meldt de referentie in 2D dat er maar 2 componenten zijn en kun je 3D
// nooit meer aanzetten.
const reference = computed(() =>
	buildCorrespondence(props.argumentList, {
		nComponents: 3,
		unit: unit.value,
		minRowTotal: MIN_ROW_TOTAL[unit.value],
	}),
);

const correspondence = computed<Correspondence | null>(() => {
	const calculated = buildCorrespondence(sourceList.value, {
		nComponents: threeDimensional.value ? 3 : 2,
		unit: unit.value,
		minRowTotal: MIN_ROW_TOTAL[unit.value],
	});
	if (!calculated) return null;
	const ref = reference.value;
	return ref ? alignSigns(ref, calculated) : calculated;
});

// Ideologie-Links-Economisch (n=43, de zeldzaamste tag) ligt in de ruwe
// correspondentieanalyse op een Mahalanobis-afstand van ~6x de mediaan --
// standaard CA-gedrag voor een zeldzame kolom (kleine kolommassa versterkt de
// coordinaat), maar het perst de rest van de wolk tot een vlekje. Radiale
// compressie (r' = r^p, richting ongewijzigd) trekt uitschieters naar de kern
// zonder ze te verbergen: bij p=0.6 daalt die afstand naar ~2,9x de mediaan,
// en -- neveneffect, want r^p > r zodra r < 1 -- duwt het juist de dichte
// kern uit elkaar, waar het overlapprobleem eigenlijk zit.
//
// Zuiver een weergavetransformatie: alleen hier, ná de echte CA en ná
// alignSigns. Klikken-om-te-filteren gaat op tagsleutel/rijlabel, niet op
// coordinaten, dus die blijft correct. Wat wél verloren gaat: afstanden op de
// kaart zijn na compressie geen letterlijke chi-kwadraatafstanden meer, alleen
// richting en relatieve volgorde blijven behouden.
const COMPRESSION_EXPONENT = 0.6;

function compress(coords: number[]): number[] {
	const r = Math.hypot(...coords);
	if (r === 0) return coords;
	// r' = r^p, uniform herschaald langs dezelfde straal: r'/r = r^(p-1).
	const factor = r ** (COMPRESSION_EXPONENT - 1);
	return coords.map((c) => c * factor);
}

const display = computed<Correspondence | null>(() => {
	const c = correspondence.value;
	if (!c) return null;
	return {
		...c,
		rows: c.rows.map((r) => ({ ...r, coords: compress(r.coords) })),
		tags: c.tags.map((t) => ({ ...t, coords: compress(t.coords) })),
	};
});

const hasThirdAxis = computed(() => (reference.value?.nComponents ?? 0) >= 3);

// Kleur per perspectief komt uit het ontwerpsysteem in
// docs/design/tag-iconografie/ -- één bron, en niet nog een keer overgetypt in
// deze component. `scripts/build_tag_icons.mjs` maakt daar
// lib/tagIcons.generated.ts van.
//
// Tagpunten zijn effen, halftransparante cirkels: de perspectieficonen (brein,
// weegschaal, ...) lazen op kaartschaal niet als teken maar als ruis, zeker
// zodra tags van hetzelfde perspectief clusteren. Kleur draagt de codering nu
// dus alleen -- het ontwerpsysteem definieert ook een aparte markeringsvorm
// per perspectief (`marker` in tag-styles.json: circle/triangle/diamond/
// square) voor precies dit soort gevallen, mocht kleur alleen ooit weer te
// weinig onderscheid geven.
//
// Eén palet voor beide modes: aardetinten van deze verzadiging houden op zowel
// #f2efe7 als #1c1815 genoeg contrast, dus een aparte donkere variant zou hier
// alleen maar uit elkaar gaan lopen.
const PERSPECTIEF_COLOR: Record<string, string> = Object.fromEntries(PERSPECTIEVEN.map((p) => [p.naam, p.kleur]));
const UNKNOWN_COLOR = "#6f6558";

// Achtergrondkleuren uit main.css; ECharts kan de CSS-variabelen niet lezen.
const BACKGROUND = { light: "#f2efe7", dark: "#1c1815" };

function toRgb(hex: string): [number, number, number] {
	const h = hex.replace("#", "");
	return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16)) as [number, number, number];
}

/** Luchtperspectief: hoe verder weg, hoe meer een kleur naar de achtergrond
 * toe trekt. Dat haalt in één bewerking zowel verzadiging als contrast weg --
 * precies wat mist met een berg in de verte doet -- en is een sterkere
 * dieptecue dan grootte alleen, omdat grootte hier ook al bezet is door het
 * aantal argumenten. `nabijheid` loopt van 0 (achterin) tot 1 (vooraan). */
function fog(color: string, proximity: number): string {
	if (!threeDimensional.value) return color;
	const target = toRgb(isDark.value ? BACKGROUND.dark : BACKGROUND.light);
	const source = toRgb(color);
	// Niet helemaal tot de achtergrond: het verste punt moet zichtbaar blijven.
	// Op 0,55 gemengd met de daaronder óók al aflopende opacity (zie tagSeries/
	// rijSerie) telden de twee dieptecues bij elkaar op tot een scène die als
	// geheel vager oogde dan 2D -- terwijl alleen het verste punt zo sterk hoefde
	// te vervagen. 0,35 laat het kleurverschil dichter bij de camera intact.
	const mix = 0.35 * (1 - proximity);
	const channels = source.map((c, i) => Math.round(c + (target[i] - c) * mix));
	return `rgb(${channels[0]}, ${channels[1]}, ${channels[2]})`;
}

const isDark = useTheme();
// Partijen zijn geen categorische serie maar een andere soort entiteit; inkt
// houdt de vier kleurslots vrij voor de perspectieven.
const ink = computed(() => (isDark.value ? "#f2ede3" : "#221f1b"));
const muted = computed(() => (isDark.value ? "#a89e8c" : "#6f6558"));
const gridLine = computed(() => (isDark.value ? "#453f36" : "#ddd5c4"));

// Kleurlogo's zijn direct herkenbaar, maar ze brengen vijftien extra kleuren de
// kaart in en concurreren daarmee met de vier perspectiefkleuren, die hier de
// betekenisdragers zijn. Vast op 20% verzadiging -- nog altijd de eigen vorm
// en een vleugje eigen kleur, maar onderling consistent genoeg om niet met de
// perspectieven te wedijveren. Geen toggle (meer): in kleur verloor het altijd
// van die afweging, dus geen keuze om aan te bieden.
const LOGO_SATURATION = 0.2;

// Rijen zonder logo (geen partij, of een partij zonder logobestand) krijgen
// dezelfde initiaal-tegel als PartyLogo.vue's placeholder elders in de app --
// wit met ink-kleurige rand en letter -- i.p.v. een generieke stip, zodat het
// beeldtaal-consistent blijft. `partyInitial` (parties.ts) is dezelfde functie
// als PartyLogo.vue gebruikt, dus "Groep Markuszower" wordt hier en daar
// dezelfde letter.
function initialSprite(letter: string, color: string): string {
	const svg =
		`<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">` +
		`<rect x="1.5" y="1.5" width="21" height="21" rx="4" fill="#fff" stroke="${color}" stroke-width="1.5"/>` +
		`<text x="12" y="12.5" text-anchor="middle" dominant-baseline="central" font-family="sans-serif" ` +
		`font-size="13" font-weight="700" fill="${color}">${letter}</text>` +
		`</svg>`;
	return `image://data:image/svg+xml,${encodeURIComponent(svg)}`;
}

function styleFor(perspectief: string) {
	return PERSPECTIEF_COLOR[perspectief] ?? UNKNOWN_COLOR;
}

const perspectieven = computed(() => {
	const seen = new Set((correspondence.value?.tags ?? []).map((t) => t.perspectief));
	return [...seen].sort();
});

// Bij personen als rij heeft de rij zelf geen logo, maar de spreker wel een
// partij. Dat logo zegt nog steeds waar iemand vandaan komt, en het is precies
// wat de losse zwarte stippen in die weergave niet deden.
const partyOfRow = computed(() => {
	const map = new Map<string, string>();
	for (const a of props.argumentList) {
		const row = unit.value === "persoon" ? a.actor.name : a.actor.party ?? NO_PARTY;
		const party = a.actor.party;
		if (party && !map.has(row)) map.set(row, party);
	}
	return map;
});

const rowsInSelection = computed(
	() => new Set(filtered.value.map((a) => (unit.value === "persoon" ? a.actor.name : a.actor.party ?? NO_PARTY))),
);
// Zie de invariant bij tagMatchesTagFilters hierboven.
const tagsInSelection = computed(
	() => new Set(filtered.value.flatMap((a) => a.tags.filter(tagMatchesTagFilters).map((t) => t.sleutel))),
);

const DIM = 0.15;

// Ja, `labelLayout` werkt hier -- en juist omdát dit geen echarts-gl
// `scatter3D` is maar een gewone 2D-scatter met een eigen projectie ervoor.
// `labelLayout` is een 2D-cartesische feature; scatter3D heeft geen labelmanager
// en kent hem niet. De callback-vorm geeft per label toegang tot de berekende
// positie, dus die kunnen we ook per punt anders invullen.
//
// `hideOverlap` alleen liet de kaart nog dichtslibben: het verbergt pas als
// twee labels elkaar echt raken en schuift niets op. Met `moveOverlap` mogen
// labels eerst verticaal uitwijken, en verdwijnt alleen wat daarna nog botst.
const LABEL_LAYOUT = () => ({ hideOverlap: true, moveOverlap: "shiftY" });

// Maar `hideOverlap` is een noodrem, geen ontwerp: welk label het overleeft
// hangt af van de tekenvolgorde, dus bij het inzoomen wisselt willekeurig welke
// tags een naam hebben. Daarom kiezen we zelf welke tags een vast label
// verdienen -- in 2D de vaakst toegekende, in 3D de twaalf die nu het dichtst
// bij de camera liggen (zie `tagDrempel` in `chartOption`), zodat de selectie
// meedraait met wat je bekijkt in plaats van vast te staan op een globale
// telling -- en krijgt de rest zijn naam bij hover. Rijen (hooguit een stuk of
// twintig partijen) houden altijd hun label; dat zijn de ankers waaraan je de
// rest afleest.
const FIXED_TAG_LABELS = 12;

// Letter per dimensie-index, gebruikt in zowel de 2D-aslabels (`asNaam`) als
// de 3D-aslabels hieronder -- zie issue #10.
const AXIS_LETTERS = ["x", "y", "z"];

// --- 3D: eigen projectie ---------------------------------------------------
// Bewust geen echarts-gl of three.js. Die brengen een tweede renderer én een
// eigen option-oppervlak mee, waardoor klikken-om-te-filteren, de tooltip, het
// per-punt dimmen en de labelplaatsing allemaal opnieuw gebouwd zouden moeten
// worden voor alleen de 3D-modus. Zo blijft 3D een aanvulling op dezelfde
// scatter i.p.v. een tweede implementatie ernaast.
//
// Diepte zit in perspectief, puntgrootte, opacity en tekenvolgorde.
const yaw = ref(0.6);
const pitch = ref(0.35);
const zoom = ref(1);

const INITIAL_YAW = 0.6;
const INITIAL_PITCH = 0.35;

// Als constante, want de aslimieten hieronder moeten dezelfde marges kennen om
// het tekengebied vierkant te kunnen maken.
const GRID = { left: 40, right: 24, top: 56, bottom: 40 };

// Camera-afstand in eenheden van `straal`. Een orthografische projectie (geen
// deling door de diepte) geeft die isometrische, "technische tekening"-look
// waarin voor- en achterkant van de kubus even groot zijn en het oog de
// draairichting kan omklappen. Deze deling maakt van de kubus een echte
// perspectiefdoos. Lager = sterker perspectief; op 2,5 is de voorste ribbe
// bijna twee keer de achterste en gaat de kaart eerder over de doos dan over de
// data. Vier is genoeg om de dubbelzinnigheid weg te nemen zonder dat je een
// groothoeklens ziet.
const CAMERA_DISTANCE = 4;

function project(coords: number[]): { x: number; y: number; depth: number; scale: number } {
	if (!threeDimensional.value) return { x: coords[0] ?? 0, y: coords[1] ?? 0, depth: 0, scale: 1 };
	const x = coords[0] ?? 0;
	const y = coords[1] ?? 0;
	const z = coords[2] ?? 0;
	const cy = Math.cos(yaw.value);
	const sy = Math.sin(yaw.value);
	const cp = Math.cos(pitch.value);
	const sp = Math.sin(pitch.value);
	const x1 = cy * x + sy * z;
	const z1 = -sy * x + cy * z;
	const y1 = cp * y - sp * z1;
	const z2 = sp * y + cp * z1;
	// z2 > 0 is naar de kijker toe, dus dichterbij = grotere schaal.
	const distance = CAMERA_DISTANCE * radius.value;
	const scale = distance / Math.max(distance - z2, distance * 0.2);
	return { x: x1 * scale, y: y1 * scale, depth: z2, scale };
}

let dragging = false;
let lastX = 0;
let lastY = 0;
let startX = 0;
let startY = 0;
// Slepen eindigt op de canvas in een gewone click, en die zou anders een filter
// aan- of uitzetten. Een paar pixels speling, zodat een trillende hand nog wel
// gewoon klikt.
const CLICK_MARGIN = 4;
let hasDragged = false;

function startDrag(e: PointerEvent) {
	if (!threeDimensional.value) return;
	dragging = true;
	hasDragged = false;
	lastX = startX = e.clientX;
	lastY = startY = e.clientY;
	(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
}

function drag(e: PointerEvent) {
	if (!dragging) return;
	if (Math.abs(e.clientX - startX) > CLICK_MARGIN || Math.abs(e.clientY - startY) > CLICK_MARGIN) hasDragged = true;
	yaw.value += (e.clientX - lastX) * 0.01;
	// Vastzetten net onder een kwartslag: verder doorschieten zet de kaart op
	// zijn kop en dan kloppen de aslabels niet meer met wat je ziet.
	pitch.value = Math.max(-1.4, Math.min(1.4, pitch.value + (e.clientY - lastY) * 0.01));
	lastX = e.clientX;
	lastY = e.clientY;
}

function stopDrag(e: PointerEvent) {
	dragging = false;
	(e.currentTarget as HTMLElement).releasePointerCapture?.(e.pointerId);
}

function onWheel(e: WheelEvent) {
	// Ook in 2D altijd preventDefault: zonder dat scrollt de pagina onder de
	// muis vandaan zodra de cursor de grafiek nog maar even verlaat, en dan
	// landt de rest van de scrollbeweging niet meer op de kaart. In 2D doet
	// ECharts' eigen dataZoom de rest (zie chartOption); deze functie hoeft er
	// dan niets aan toe te voegen, alleen de paginascroll te blokkeren.
	e.preventDefault();
	if (!threeDimensional.value) return;
	// Ondergrens ruim onder 1: het venster staat op het 90e percentiel, en de
	// verste tag ligt daar ~4x buiten. Bleef de ondergrens op 0,6 staan, dan was
	// die tag met geen enkele zoomstand in beeld te krijgen -- en bleef de hint
	// "buiten beeld" dus eeuwig staan.
	zoom.value = Math.min(6, Math.max(0.12, zoom.value * Math.exp(-e.deltaY * 0.0015)));
}

const chartRef = ref<any>(null);

function percentile(values: number[], p: number): number {
	if (values.length === 0) return 1e-9;
	const sorted = [...values].sort((a, b) => a - b);
	const index = Math.min(sorted.length - 1, Math.floor(sorted.length * p));
	return Math.max(sorted[index], 1e-9);
}

/** Idem als `straal` hieronder, maar per as en dus ook zinvol in 2D: x en y
 * schalen daar los van elkaar, maar een enkele uitschieter (Ideologie-Links-
 * Economisch ligt ver van de rest) kan alsnog één van de twee assen alleen
 * domineren en de rest van die as tot een streep persen. Het 90e percentiel
 * per as geeft een venster waar de kern in past; de uitschieter valt er
 * standaard net als in 3D buiten, met dezelfde "zoom uit"-route terug. */
const axisLimits = computed<[number, number]>(() => {
	const c = display.value;
	if (!c) return [1, 1];
	const points = [...c.rows, ...c.tags];
	const x = percentile(
		points.map((p) => Math.abs(p.coords[0] ?? 0)),
		0.9,
	);
	const y = percentile(
		points.map((p) => Math.abs(p.coords[1] ?? 0)),
		0.9,
	);
	return [x * 1.15, y * 1.15];
});

/** De echte, volledige spreiding per as (het maximum, niet het percentiel).
 * Dit is de vaste `xAxis`/`yAxis`-grens in 2D -- zonder een vaste grens laat
 * ECharts de as auto-schalen op basis van wat er *op dat moment* zichtbaar
 * is, en dan wordt het venster dat `normaliseer2D` uitzet zelf de nieuwe
 * 0%-100%-referentie: uitzoomen heeft dan letterlijk nergens heen. Met een
 * vaste grens is 100% altijd de echte uitschieter, en blijft er ruimte om
 * daar met scrollen te komen. */
const axisFullLimits = computed<[number, number]>(() => {
	const c = display.value;
	if (!c) return [1, 1];
	const points = [...c.rows, ...c.tags];
	const x = Math.max(...points.map((p) => Math.abs(p.coords[0] ?? 0)), 1e-9);
	const y = Math.max(...points.map((p) => Math.abs(p.coords[1] ?? 0)), 1e-9);
	return [x * 1.08, y * 1.08];
});

const outOfView2D = computed(() => {
	const c = display.value;
	if (threeDimensional.value || !c) return 0;
	const [gx, gy] = axisLimits.value;
	return [...c.rows, ...c.tags].filter((p) => Math.abs(p.coords[0] ?? 0) > gx || Math.abs(p.coords[1] ?? 0) > gy).length;
});

// Zet het 2D-venster terug op het 90e-percentielvenster. `dispatchAction` op
// de chartinstantie bleek onbetrouwbaar: `chartRef.value` is al waar zodra
// VChart's component-instantie bestaat, ruim vóórdat VChart's eigen onMounted
// de ECharts-instantie initialiseert, en zelfs met een requestAnimationFrame-
// herkansing bleef de dispatch een stille no-op (geverifieerd via
// `getOption()`: startValue/endValue bleven op de volle asgrens staan).
// Daarom nu declaratief: `forceerNormalisatie` bepaalt of `chartOption`
// hieronder zelf startValue/endValue meegeeft in de dataZoom-config. Dat gaat
// mee in dezelfde `setOption`-aanroep die de kaart toch al ververst, dus geen
// race meer. Ná die ene toepassing gaat de vlag weer uit (zie de watcher op
// `chartOption` verderop), zodat latere her-renders (bv. een tagklik, die
// alleen opacity raakt) geen startValue/endValue meer meesturen en de
// handmatige zoomstand van de gebruiker met rust laten.
const forceNormalization = ref(true);

function resetView() {
	yaw.value = INITIAL_YAW;
	pitch.value = INITIAL_PITCH;
	zoom.value = 1;
	forceNormalization.value = true;
	view2D.value = null;
}

// Wisselen tussen 2D en 3D betekent een compleet ander venstermodel (dataZoom
// vs. camera-zoom); een oud `zicht2D` zou anders de labelselectie in de
// nieuwe weergave nog even sturen op een stand die daar niet bij hoort.
watch(threeDimensional, () => {
	view2D.value = null;
});

// Elke keer dat de onderliggende punten structureel veranderen opnieuw
// normaliseren: een filter dat `rekenLijst` raakt (in "focus" alles behalve
// tag/partij, in "detail" ook die twee), wisselen van rij-eenheid/
// dimensiecount, of wisselen tussen focus/detail zelf.
watch(correspondence, () => {
	forceNormalization.value = true;
	view2D.value = null;
});

// Huidige zichtbare data-range in 2D, bijgehouden via het `datazoom`-event
// (zie VChart in de template) -- net als de dieptegebaseerde labelselectie in
// 3D, maar dan op basis van wat er na pannen/zoomen daadwerkelijk in beeld is
// i.p.v. camera-afstand. `null` betekent "nog niet gezoomd/gepand sinds de
// laatste normalisatie", dus dan valt de labelselectie hieronder terug op het
// volledige (genormaliseerde) venster.
const view2D = ref<{ x: [number, number]; y: [number, number] } | null>(null);

function onDataZoom() {
	const dz = chartRef.value?.getOption?.()?.dataZoom;
	if (!dz || dz.length < 2) return;
	const [fullX, fullY] = axisFullLimits.value;
	// start/end zijn percentages van de vaste as-grens (asVolledigeGrenzen),
	// dus terugrekenen naar data-eenheden kan zonder de as zelf te bevragen.
	const toRange = (start: number | undefined, end: number | undefined, limit: number): [number, number] => [
		-limit + ((start ?? 0) / 100) * 2 * limit,
		-limit + ((end ?? 100) / 100) * 2 * limit,
	];
	view2D.value = {
		x: toRange(dz[0]?.start, dz[0]?.end, fullX),
		y: toRange(dz[1]?.start, dz[1]?.end, fullY),
	};
}

const norms = computed(() => {
	const c = display.value;
	if (!c) return [0];
	return [...c.rows, ...c.tags].map((p) => Math.hypot(p.coords[0] ?? 0, p.coords[1] ?? 0, p.coords[2] ?? 0)).sort((a, b) => a - b);
});

/** Straal van de bol waar het beeld op past -- de enige maat die niet verandert
 * als je draait. Het venster op de geprojecteerde punten laten meeschalen (wat
 * hier eerder gebeurde) zoomt de kaart bij elke muisbeweging in en uit, en dan
 * lijkt de puntenwolk los te staan van het assenkruis.
 *
 * Het 90e percentiel en niet het maximum: één tag (Ideologie-Links-Economisch)
 * ligt vier keer zo ver als de kern, en een venster dat die insluit perst de
 * rest tot een vlekje. In 2D valt dat niet op omdat elke as daar los schaalt;
 * hier moeten x en y dezelfde schaal houden, anders is de projectie geen
 * rotatie meer. De uitschieters vallen dus standaard buiten beeld -- vandaar de
 * telling hieronder en de hint om uit te zoomen. */
const radius = computed(() => {
	const sorted = norms.value;
	const index = Math.min(sorted.length - 1, Math.floor(sorted.length * 0.9));
	return Math.max(sorted[index], 1e-9);
});

/** Punten die bij de huidige zoom gegarandeerd binnen het venster vallen, hebben
 * een norm onder deze grens; alles daarboven kán erbuiten liggen. */
const outOfView = computed(() => {
	if (!threeDimensional.value) return 0;
	const limit = (radius.value * 1.03) / zoom.value;
	return norms.value.filter((n) => n > limit).length;
});

// Verhouding van het tekengebied. Zonder dit staan er evenveel data-eenheden op
// een brede as als op een smalle, en dan is de projectie op het scherm geen
// rotatie meer maar een rotatie plus een uitrekking: het assenkruis lijkt bijna
// horizontaal te blijven terwijl de punten wel kantelen.
const wrapperEl = ref<HTMLElement | null>(null);
const plotAspectRatio = ref(1);
let observer: ResizeObserver | null = null;

function measure(el: HTMLElement) {
	const width = el.clientWidth - GRID.left - GRID.right;
	const height = el.clientHeight - GRID.top - GRID.bottom;
	if (width > 0 && height > 0) plotAspectRatio.value = width / height;
}

onMounted(() => {
	if (typeof ResizeObserver === "undefined") return;
	observer = new ResizeObserver(([entry]) => measure(entry.target as HTMLElement));
	if (wrapperEl.value) observer.observe(wrapperEl.value);
});

// De wrapper zit achter een v-if, dus hij kan later pas verschijnen.
watch(wrapperEl, (el) => {
	if (!observer) return;
	observer.disconnect();
	if (el) observer.observe(el);
});

onUnmounted(() => observer?.disconnect());

// Zelfde breakpoint als de rest van de mobiele laag (main.css). 3D-slepen
// conflicteert met paginascroll op touch, dus die modus is onder dit
// breakpoint niet beschikbaar (zie de watcher hieronder en de v-if in de
// template).
const MOBILE_QUERY = "(max-width: 900px)";
const isMobile = ref(false);
let mobileQuery: MediaQueryList | null = null;

function updateIsMobile() {
	isMobile.value = mobileQuery?.matches ?? false;
}

onMounted(() => {
	if (typeof matchMedia === "undefined") return;
	mobileQuery = matchMedia(MOBILE_QUERY);
	updateIsMobile();
	mobileQuery.addEventListener("change", updateIsMobile);
});

onUnmounted(() => mobileQuery?.removeEventListener("change", updateIsMobile));

watch(isMobile, (mobile) => {
	if (mobile) threeDimensional.value = false;
});

/** Diepte -> 0 (achterin) .. 1 (vooraan). Voert zowel de mist als het dimmen
 * van beeldsymbolen aan, die geen kleur kunnen aannemen. */
function proximity(depth: number, range: number): number {
	if (!threeDimensional.value || range <= 0) return 1;
	const linear = Math.max(0, Math.min(1, (depth + range) / (2 * range)));
	// De puntenwolk clustert rond het midden (diepte ~0), dus de meeste punten
	// zaten op deze lineaire schaal rond 0,5 -- ver van de "volle kleur" die
	// alleen het allervoorste punt (1,0) kreeg. Een machtscurve tilt het
	// middenbereik dichter naar 1 op, zodat de meerderheid van de wolk zijn
	// eigen kleur houdt en alleen de echte achterhoede nog merkbaar vervaagt.
	return Math.pow(linear, 0.4);
}

/** 1, 2 of 5 maal een macht van tien: geeft rasterlijnen op afstanden die je
 * kunt aflezen i.p.v. op 0,3714. */
function niceStep(ruw: number): number {
	const magnitude = 10 ** Math.floor(Math.log10(ruw));
	const normalized = ruw / magnitude;
	return (normalized >= 5 ? 5 : normalized >= 2 ? 2 : 1) * magnitude;
}

// Onder 900px is er geen ruimte voor alle labels tegelijk: alleen punten
// duidelijk buiten de kern van de wolk houden een naam, de rest wordt een
// kale stip (nog altijd aanklikbaar, zie onChartClick). Genormaliseerd op
// hetzelfde 90e-percentielvenster als de assen (axisLimits) zodat de drempel
// per topic hetzelfde relatieve gebied dekt, ongeacht de absolute schaal van
// de correspondentieanalyse. Alleen relevant in 2D: 3D staat al uit onder
// 900px (zie de watcher op isMobile hierboven).
const MOBILE_LABEL_DISTANCE = 0.35;
function isAwayFromCenter(x: number, y: number): boolean {
	const [gx, gy] = axisLimits.value;
	return Math.hypot(x / gx, y / gy) > MOBILE_LABEL_DISTANCE;
}

const chartOption = computed(() => {
	const c = display.value;
	if (!c) return {};

	const projected = {
		rows: c.rows.map((p) => ({ point: p, ...project(p.coords) })),
		tags: c.tags.map((p) => ({ point: p, ...project(p.coords) })),
	};
	const range = radius.value;

	// Relatief aan de grootste `n` in déze selectie, niet aan een vaste absolute
	// waarde: bij een topic met veel argumenten (bv. stikstof, ~2000) haalt
	// vrijwel elke tag/rij eerder al `sqrt(n) * 3,2` boven de oude vaste
	// bovengrens, en werd bijna elk punt hetzelfde maximale formaat (zie #88).
	// Schalen t.o.v. het eigen maximum houdt het volledige bereik (min..max)
	// altijd in gebruik, ongeacht hoe groot het topic is.
	const maxRowN = Math.max(...c.rows.map((p) => p.n), 1);
	const maxTagN = Math.max(...c.tags.map((p) => p.n), 1);
	// Onder 900px is er geen ruimte voor de volle desktop-spreiding: partijlogo's
	// blijven rond de 13-14px i.p.v. uit te lopen tot 24px.
	const ROW_SIZE = isMobile.value ? { min: 8, max: 14 } : { min: 9, max: 24 };
	const TAG_SIZE = isMobile.value ? { min: 9, max: 16 } : { min: 13, max: 28 };
	function sizeFor(n: number, maxN: number, { min, max }: { min: number; max: number }): number {
		return min + (max - min) * Math.sqrt(n / maxN);
	}

	// Drempel waarboven een tag zijn naam vast in beeld houdt. In 3D op diepte
	// i.p.v. frequentie: anders blijft het altijd dezelfde twaalf (globaal
	// vaakst toegekende) tags, ook als je wegdraait van de plek waar ze staan.
	// Op diepte draait de selectie mee -- de twaalf tags die nu vooraan liggen
	// krijgen een naam, en dat verandert elke keer dat `projecteer` opnieuw
	// draait tijdens het slepen.
	//
	// In 2D is er geen diepte, maar hetzelfde probleem doet zich voor bij
	// inzoomen: de globale top-twaalf kan volledig buiten het gezoomde venster
	// vallen, en dan blijft er niets gelabeld terwijl je juist wél op een
	// cluster hebt ingezoomd. `zicht2D` (bijgehouden via het `datazoom`-event)
	// beperkt de top-twaalf-selectie dan tot wat er nu in beeld is.
	const tagsInView2D = view2D.value
		? c.tags.filter(
				(t) => t.coords[0] >= view2D.value!.x[0] && t.coords[0] <= view2D.value!.x[1] &&
					t.coords[1] >= view2D.value!.y[0] && t.coords[1] <= view2D.value!.y[1],
			)
		: c.tags;
	const tagThreshold = threeDimensional.value
		? ([...projected.tags]
				.map((t) => t.depth)
				.sort((a, b) => b - a)
				.slice(0, FIXED_TAG_LABELS)
				.pop() ?? -Infinity)
		: ([...tagsInView2D]
				.map((t) => t.n)
				.sort((a, b) => b - a)
				.slice(0, FIXED_TAG_LABELS)
				.pop() ?? 0);
	const tagKeysInView = threeDimensional.value ? null : new Set(tagsInView2D.map((t) => t.sleutel));

	const axisStyle = { lineStyle: { color: gridLine.value } };
	// In 3D tekenen we zelf een meegedraaid raster (zie hieronder) i.p.v. het
	// cartesische assenstelsel van ECharts.
	// `[ - ]`: CA-coördinaten zijn dimensieloos (geen euro's, geen aantallen) --
	// een expliciete "geen eenheid"-notatie is eerlijker dan er niets bij te
	// zetten, zie issue #10.
	const axisName = (k: number) =>
		threeDimensional.value ? "" : `${AXIS_LETTERS[k]} (${c.inertiaPct[k] ?? 0}% van de inertie) [ - ]`;
	const raster = threeDimensional.value ? { show: false } : axisStyle;
	const hiddenAxis = {
		axisLine: { show: !threeDimensional.value, ...axisStyle },
		axisTick: { show: !threeDimensional.value },
		splitLine: raster,
		axisLabel: { show: false },
	};

	const rowSeries = {
		id: "rows",
		name: unit.value === "persoon" ? "Personen" : "Partijen",
		type: "scatter",
		cursor: "pointer",
		z: 3,
		itemStyle: { color: ink.value },
		labelLayout: LABEL_LAYOUT,
		data: [...projected.rows]
			.sort((a, b) => a.depth - b.depth)
			.map(({ point, x, y, depth, scale }) => {
				const prox = proximity(depth, range);
				const inSelection = rowsInSelection.value.has(point.label);
				// Het logo zegt in één blik welke partij het is. Alleen partijen
				// hebben logo's -- personen en fracties zonder officieel logo krijgen
				// dezelfde initiaal-tegel als PartyLogo.vue's placeholder (zie
				// `initiaalSprite`), geen generieke stip: dat is een van de twee
				// beeldtaal-tegels, niet buiten het systeem.
				const party = unit.value === "partij" ? point.label : partyOfRow.value.get(point.label);
				const logo = party ? logoSprite(party, LOGO_SATURATION) : null;
				const markerSymbol = logo?.symbool ?? initialSprite(partyInitial(point.label), ink.value);
				// De vereenvoudigde iconenset (en de initiaal-tegel) is één vast
				// vierkant canvas per partij, dus in tegenstelling tot de officiële
				// wordmarks hoeft de maat hier niet naar een eigen verhouding te kijken.
				const size = sizeFor(point.n, maxRowN, ROW_SIZE) * scale * 1.15;
				return {
					name: unit.value === "persoon" ? point.label : displayPartyName(point.label),
					rowLabel: point.label,
					value: [x, y, point.n],
					n: point.n,
					symbol: markerSymbol,
					symbolSize: size,
					itemStyle: {
						// Elke rij is nu een beeldsymbool (logo of initiaal-tegel), en dat
						// neemt geen kleur aan -- dus moet de mist via opacity, minder mooi,
						// maar de enige knop die er is. Niet lager dan 0,75: op deze lichte
						// achtergrond mengt een halftransparant vlak zichtbaar naar de
						// achtergrondkleur (bv. het logorood op 50% wordt een grijzige roze,
						// niet halfdoorzichtig rood) -- vooral merkbaar bij logo's, die al op
						// 20% verzadiging staan. 0,75 laat nog genoeg doorschijnen om
						// overlappende tegels niet helemaal dicht te slibben.
						opacity: (inSelection ? 0.75 : DIM) * (0.7 + 0.3 * prox),
					},
					// Een logo is zijn eigen label -- maar alleen als rij en logo dezelfde
					// entiteit zijn. Bij partijen is dat zo (dubbelop om de partijnaam er
					// nog eens bij te zetten), bij personen niet: het logo zegt alleen
					// welke partij, niet wie. Daar blijft de naam dus altijd nodig.
					label: {
						show: (!logo || unit.value === "persoon") && (!isMobile.value || isAwayFromCenter(x, y)),
						formatter: "{b}",
						position: "top",
						color: fog(ink.value, prox),
						fontSize: 11,
						fontWeight: 600,
					},
					emphasis: {
						label: { show: true, formatter: "{b}", position: "top", color: ink.value, fontSize: 11, fontWeight: 600 },
					},
				};
			}),
	};

	const tagSeries = perspectieven.value.map((perspectief) => {
		const color = styleFor(perspectief);
		return {
			id: `tags-${perspectief}`,
			name: perspectief,
			type: "scatter",
			symbol: "circle",
			cursor: "pointer",
			z: 2,
			itemStyle: { color, opacity: 0.5 },
			labelLayout: LABEL_LAYOUT,
			data: projected.tags
				.filter(({ point }) => point.perspectief === perspectief)
				.sort((a, b) => a.depth - b.depth)
				.map(({ point, x, y, depth, scale }) => {
					const prox = proximity(depth, range);
					const inSelection = tagsInSelection.value.has(point.sleutel);
					return {
						name: point.sleutel,
						value: [x, y, point.n],
						n: point.n,
						beschrijving: point.beschrijving,
						labelgroep: point.labelgroep,
						perspectief: point.perspectief,
						symbolSize: sizeFor(point.n, maxTagN, TAG_SIZE) * scale * 0.6,
						// Effen cirkel: iconen per tag (vijftig) en zelfs per perspectief
						// (vier) lazen op kaartschaal niet als teken, zeker in een dichte
						// cluster -- alleen kleur nog. Niet lager dan 0,75 opacity: op deze
						// lichte achtergrond mengt een halftransparant vlak zichtbaar naar de
						// achtergrondkleur (het perspectiefpalet is al gedempt "aardetinten",
						// dus op 50% wordt het nauwelijks meer dan grijs), en dat was precies
						// de klacht. 0,75 laat nog genoeg doorschijnen om overlappende punten
						// niet helemaal dicht te slibben.
						itemStyle: {
							color: fog(color, prox),
							// Vloer op 0,7 i.p.v. 0,5: in 3D telde deze opacity-afname vroeger op
							// bij de kleurmist hierboven, en samen maakten ze de hele wolk vager
							// dan in 2D -- ook punten die niet eens ver weg lagen.
							opacity: (inSelection ? 0.75 : DIM) * (0.7 + 0.3 * prox),
						},
						label: {
							show:
								(threeDimensional.value
									? depth >= tagThreshold
									: (tagKeysInView?.has(point.sleutel) ?? true) && point.n >= tagThreshold) &&
								(!isMobile.value || isAwayFromCenter(x, y)),
							formatter: "{b}",
							position: "top",
							color: fog(muted.value, prox),
							fontSize: 9,
						},
						emphasis: { label: { show: true, formatter: "{b}", position: "top", color: ink.value, fontSize: 10 } },
					};
				}),
		};
	});

	// Meegedraaid referentiekader: zonder raster is een gedraaide puntenwolk
	// stuurloos -- je ziet wel diepte, maar niet welke kant welke dimensie op
	// wijst en hoe ver een punt van de oorsprong ligt. Een vloerraster in het
	// dim1-dim3-vlak, de ribben van de kubus eromheen, en drie aslijnen vanuit de
	// oorsprong. Alles door dezelfde `projecteer` als de punten, dus het draait
	// per definitie mee.
	//
	// Het venster hangt aan `straal` (rotatie-invariant) en niet meer aan de
	// geprojecteerde punten: dat laatste liet de kaart bij elke muisbeweging in-
	// en uitzoomen. Het venster is bovendien op beide assen even veel eenheden
	// per pixel, want anders is de projectie op het scherm geen rotatie.
	// De perspectiefdeling vergroot alles wat vóór de oorsprong ligt, dus het
	// venster moet die factor meenemen -- anders valt de voorste ribbe van de
	// doos buiten beeld.
	const maxScale = CAMERA_DISTANCE / (CAMERA_DISTANCE - 1);
	const halfHeight = (radius.value * 1.03 * maxScale) / zoom.value;
	// In 3D is dit het venster zelf (het draait mee, zie hierboven); in 2D is
	// het de vaste, nooit-veranderende as-grens waarbinnen dataZoom pant en
	// zoomt -- zie `asVolledigeGrenzen`.
	const [fullX, fullY] = axisFullLimits.value;
	const limitY = threeDimensional.value ? halfHeight : fullY;
	const limitX = threeDimensional.value ? halfHeight * plotAspectRatio.value : fullX;

	function lineSeries(id: string, points: number[][], color: string, width: number, z = 1) {
		return {
			id,
			type: "line",
			silent: true,
			showSymbol: false,
			animation: false,
			z,
			lineStyle: { color, width },
			data: points.map((p) => {
				const q = project(p);
				return [q.x, q.y];
			}),
		};
	}

	// Kader ruim binnen de bolstraal, zodat ook de verste hoekpunten van de kubus
	// bij elke rotatie binnen het venster blijven staan.
	const frameStep = niceStep(radius.value / 2.5);
	const frameSteps = Math.max(2, Math.round((radius.value * 0.7) / frameStep));
	const frame = frameStep * frameSteps;
	const floor = -frame;

	const frameSeries: any[] = [];
	if (threeDimensional.value) {
		for (let i = 0; i <= 2 * frameSteps; i++) {
			const t = -frame + i * frameStep;
			frameSeries.push(lineSeries(`floor-a${i}`, [[-frame, floor, t], [frame, floor, t]], gridLine.value, 1));
			frameSeries.push(lineSeries(`floor-b${i}`, [[t, floor, -frame], [t, floor, frame]], gridLine.value, 1));
		}
		const corners: number[][] = [
			[-frame, -frame],
			[frame, -frame],
			[frame, frame],
			[-frame, frame],
		];
		corners.forEach(([x, z], i) => {
			const [nx, nz] = corners[(i + 1) % 4];
			frameSeries.push(lineSeries(`edge-${i}`, [[x, floor, z], [x, frame, z]], gridLine.value, 1));
			frameSeries.push(lineSeries(`top-${i}`, [[x, frame, z], [nx, frame, nz]], gridLine.value, 1));
		});
		for (const k of [0, 1, 2]) {
			const end = [0, 1, 2].map((axis) => (axis === k ? frame : 0));
			frameSeries.push(lineSeries(`axis-${k}`, [[0, 0, 0], end], muted.value, 1.5, 2));
		}
		frameSeries.push({
			id: "axis-labels",
			type: "scatter",
			silent: true,
			animation: false,
			z: 2,
			// Onzichtbaar punt: het label is het enige dat hier getekend moet
			// worden, en een scatter-label rendert betrouwbaarder dan een label op
			// het eindpunt van een line-serie zonder symbolen.
			// Transparant en niet opacity 0: dat laatste vervaagt het label mee.
			symbolSize: 1,
			itemStyle: { color: "transparent" },
			data: [0, 1, 2].map((k) => {
				const q = project([0, 1, 2].map((axis) => (axis === k ? frame : 0)));
				return {
					value: [q.x, q.y],
					label: {
						show: true,
						formatter: `${AXIS_LETTERS[k]} (${c.inertiaPct[k] ?? 0}% van de inertie) [ - ]`,
						color: muted.value,
						fontSize: 10,
						position: "top",
					},
				};
			}),
		});
	}

	return {
		backgroundColor: "transparent",
		textStyle: { fontFamily: "inherit" },
		// Uit, in beide weergaven. In 3D wordt de kaart per muisbeweging opnieuw
		// opgebouwd en wisselt de tekenvolgorde van de punten (diepte-sortering);
		// ECharts koppelt zijn overgangsanimatie aan de index in de data-array en
		// laat punten dan naar de plek van hun buurman glijden. In 2D animeert
		// ECharts elke zoom- en panstap over 300 ms, waardoor scrollen in horten en
		// stoten aankomt in plaats van onder je muis mee te bewegen.
		animation: false,
		tooltip: {
			trigger: "item",
			extraCssText: "max-width: 240px; white-space: normal; line-height: 1.35;",
			formatter: (p: any) => {
				if (p.data.rowLabel !== undefined) return `<strong>${p.data.name}</strong><br/>${p.data.n} tags`;
				return `<strong>${p.data.name}</strong><br/><span style="opacity:0.7">${p.data.perspectief} &middot; ${p.data.labelgroep}</span><br/>${p.data.beschrijving}<br/><span style="opacity:0.7">${p.data.n}x toegekend</span><br/><span style="opacity:0.7">klik: filter &middot; ctrl/cmd-klik: tagpagina</span>`;
			},
		},
		legend: {
			// Klikbaar, maar niet als ECharts' eigen lokale verbergen: dat zou een
			// tweede, verborgen filter naast de filterbalk zijn. `onLegendSelectChanged`
			// hieronder zet de klik in plaats daarvan om in een `perspectief`-filter op
			// de gedeelde filterstore en herstelt meteen de eigen selectiestatus, zodat
			// de bestaande opacity-demping (`inSelection`) de enige zichtbare
			// filterfeedback blijft -- zie #3.
			selectedMode: true,
			data: [rowSeries.name, ...perspectieven.value],
			top: 0,
			type: "scroll",
			textStyle: { color: ink.value, fontSize: 11 },
		},
		// In 2D doet ECharts het pannen en zoomen zelf: `inside` betekent scrollen
		// en slepen op de grafiek, zonder schuifbalk eromheen. In 3D moet hij weg,
		// want daar zijn scrollen en slepen al bezet door de eigen zoom en rotatie.
		//
		// `filterMode: "none"` is hier het punt: de standaard gooit punten buiten
		// het venster uit de serie, en dan herberekent ECharts de labelplaatsing en
		// springen de overgebleven labels rond bij elke zoomstap. Nu worden ze
		// alleen afgekapt.
		// throttle: 0 -- ECharts' eigen advies bij animation:false (hierboven):
		// de standaard 100ms-throttle is bedoeld om animatieframes te sparen, en
		// zonder animatie levert die throttle alleen vertraging op, geen besparing.
		// Zonder deze regel voelde slepen in 2D hortend/beperkt aan.
		dataZoom: threeDimensional.value
			? []
			: [
					{
						id: "dataZoomX",
						type: "inside",
						xAxisIndex: 0,
						filterMode: "none",
						throttle: 0,
						...(forceNormalization.value ? { startValue: -axisLimits.value[0], endValue: axisLimits.value[0] } : {}),
					},
					{
						id: "dataZoomY",
						type: "inside",
						yAxisIndex: 0,
						filterMode: "none",
						throttle: 0,
						...(forceNormalization.value ? { startValue: -axisLimits.value[1], endValue: axisLimits.value[1] } : {}),
					},
				],
		grid: { ...GRID },
		xAxis: {
			type: "value",
			min: limitX === undefined ? undefined : -limitX,
			max: limitX,
			name: axisName(0),
			nameLocation: "middle",
			nameGap: 28,
			nameTextStyle: { color: muted.value },
			...hiddenAxis,
		},
		yAxis: {
			type: "value",
			min: limitY === undefined ? undefined : -limitY,
			max: limitY,
			name: axisName(1),
			nameLocation: "middle",
			nameGap: 18,
			nameTextStyle: { color: muted.value },
			...hiddenAxis,
		},
		series: [...frameSeries, rowSeries, ...tagSeries],
	};
});

// Na de render waarin `forceerNormalisatie` zijn startValue/endValue heeft
// laten meesturen, de vlag weer uit -- anders zou elke volgende her-render
// (bv. een tagklik, die alleen opacity raakt) de gebruiker terugzetten op het
// normalisatievenster. `flush: "post"` zodat dit pas ná de echte chart-update
// gebeurt, niet ervoor.
watch(
	chartOption,
	() => {
		if (forceNormalization.value) forceNormalization.value = false;
	},
	{ flush: "post" },
);

function onChartClick(p: any) {
	// Het einde van een sleep is ook een click; die mag geen filter omzetten.
	if (hasDragged) return;
	if (p.data?.rowLabel !== undefined) {
		// Personen zijn geen filterdimensie met dezelfde sleutel; alleen partijen
		// kunnen we hier direct doorzetten naar de filterstore.
		if (unit.value === "partij") toggleValue("partij", p.data.rowLabel);
		else toggleValue("persoon", p.data.rowLabel);
		return;
	}
	if (p.data?.name) {
		const native = p.event?.event ?? p.event;
		if (native?.ctrlKey || native?.metaKey || native?.button === 1) {
			window.open(`/tags/${slugify(p.data.name)}/`, "_blank", "noopener");
			return;
		}
		toggleValue("tag", p.data.name);
	}
}

// Legendaklik verbergt hier bewust geen series lokaal (dat zou een tweede,
// niet-gedeelde filter zijn): een klik op een perspectief zet het om in een
// `perspectief`-filter op de gedeelde filterstore, en de eigen ECharts-
// selectiestatus wordt meteen hersteld zodat de kaart altijd alle series
// toont. "Partijen"/"Personen" heeft geen bijpassende filterdimensie, dus die
// blijft alleen aanwezig in de legenda, niet klikbaar.
function onLegendSelectChanged(p: { name: string }) {
	if (perspectieven.value.includes(p.name)) toggleValue("perspectief", p.name);
	chartRef.value?.dispatchAction?.({ type: "legendAllSelect" });
}

const filterActive = computed(isActive);
</script>

<template>
	<section class="stats-panel">
		<h2>
			Partijen &amp; tags (correspondentieanalyse)
			<a href="/over/#correspondentiekaart-methode" class="info-link" title="Hoe deze kaart tot stand komt" aria-label="Uitleg: hoe deze kaart tot stand komt">?</a>
		</h2>
		<p class="panel-note panel-note-intro">
			Rijen dicht bij elkaar gebruiken vergelijkbare soorten argumenten; een tag dicht bij een rij komt relatief vaak bij die rij
			voor. Kleur geeft het perspectief van de tag aan. Alleen de vaakst toegekende tags houden hun naam in beeld; wijs een punt
			aan voor de rest. Klik op een punt om erop te filteren.
		</p>
		<p class="panel-note panel-note-intro">
			Staat er een filter aan, dan dimt "focus" (standaard) alleen de punten buiten de selectie, zodat de tabel niet tot
			één rij/kolom terugvalt. Kies "detail" om de kaart net als de rest van de pagina volledig op de selectie te
			herberekenen.
		</p>

		<div class="chart-controls">
			<div class="chart-controls-group">
				<span class="chart-controls-label">Rijen</span>
				<div class="toggle-group" role="group" aria-label="Rijen">
					<button type="button" class="toggle-btn" :class="{ 'is-active': unit === 'partij' }" @click="unit = 'partij'">
						Partijen
					</button>
					<button type="button" class="toggle-btn" :class="{ 'is-active': unit === 'persoon' }" @click="unit = 'persoon'">
						Personen
					</button>
				</div>
			</div>
			<div v-if="filterActive" class="chart-controls-group">
				<span class="chart-controls-label">Filter</span>
				<div class="toggle-group" role="group" aria-label="Filter: focus of detail">
					<button type="button" class="toggle-btn" :class="{ 'is-active': analysisMode === 'focus' }" @click="analysisMode = 'focus'">
						Focus
					</button>
					<button type="button" class="toggle-btn" :class="{ 'is-active': analysisMode === 'detail' }" @click="analysisMode = 'detail'">
						Detail
					</button>
				</div>
			</div>
			<div class="chart-controls-group">
				<template v-if="!isMobile">
					<span class="chart-controls-label">Weergave</span>
					<div class="toggle-group" role="group" aria-label="Weergave">
						<button type="button" class="toggle-btn" :class="{ 'is-active': !threeDimensional }" @click="threeDimensional = false">
							2D
						</button>
						<button
							type="button"
							class="toggle-btn"
							:class="{ 'is-active': threeDimensional }"
							:disabled="!hasThirdAxis"
							:title="hasThirdAxis ? '' : 'Te weinig data voor een derde dimensie'"
							@click="threeDimensional = true"
						>
							3D
						</button>
					</div>
				</template>
				<button type="button" class="control-knop" @click="resetView">Aanzicht herstellen</button>
			</div>
			<template v-if="threeDimensional">
				<span class="control-hint">
					slepen draait, scrollen zoomt<template v-if="outOfView">
						&middot; {{ outOfView }} punt{{ outOfView === 1 ? "" : "en" }} buiten beeld, zoom uit om ze te zien</template
					>
				</span>
			</template>
			<span v-else class="control-hint">
				scrollen zoomt, slepen verschuift<template v-if="outOfView2D">
					&middot; {{ outOfView2D }} punt{{ outOfView2D === 1 ? "" : "en" }} buiten beeld, zoom uit om ze te zien</template
				><template v-if="!hasThirdAxis"> &middot; 3D vereist minstens 4 rijen en 4 tags</template>
			</span>
		</div>

		<p v-if="filterActive" class="panel-note">
			<template v-if="analysisMode === 'focus'">
				Er staat een filter aan; de kaart toont in "focus" nog de volledige analyse met de selectie gemarkeerd.
			</template>
			<template v-else> Er staat een filter aan; de kaart in "detail" rekent alleen nog op de selectie. </template>
		</p>

		<div
			v-if="display"
			ref="wrapperEl"
			class="correspondence-wrapper"
			:class="{ 'is-3d': threeDimensional }"
			@pointerdown="startDrag"
			@pointermove="drag"
			@pointerup="stopDrag"
			@pointercancel="stopDrag"
			@wheel="onWheel"
		>
			<VChart
				ref="chartRef"
				class="party-chart correspondence-chart"
				:option="chartOption"
				:update-options="{ replaceMerge: ['series', 'dataZoom'] }"
				autoresize
				@click="onChartClick"
				@datazoom="onDataZoom"
				@legendselectchanged="onLegendSelectChanged"
			/>
		</div>
		<p v-else class="panel-note">
			Te weinig getagde data in deze selectie voor een zinnige analyse (minimaal 3 rijen en 3 tags met genoeg volume nodig).
		</p>
	</section>
</template>
