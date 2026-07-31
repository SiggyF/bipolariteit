<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useTheme } from "../lib/useTheme";
import { displayPartyName, partyInitial } from "../lib/parties";
import { logoSprite } from "../lib/partyLogoSprite";
import { PERSPECTIEVEN } from "../lib/tagIcons.generated";
import { filters, matches, toggleValue } from "../lib/filters";
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
const driedimensionaal = ref(false);

// Bij persoon als rij is een drempel van 3 te laag: veel sprekers hebben één of
// twee argumenten en zouden als losse punten de wolk vullen zonder iets te zeggen.
const MIN_ROW_TOTAL: Record<RowUnit, number> = { partij: 3, persoon: 12 };

// De analyse rekent op de volledige selectie, inclusief tag- en partijfilters:
// klikken op een tag/partij-punt filtert 'm dus net zo weg als elk ander
// filter. `buildTable` (correspondence.ts) geeft `null` bij minder dan 3
// rijen/kolommen i.p.v. iets te tonen dat niks meer zegt, dus een filter dat te
// ver doorschiet laat de kaart netjes leeg lopen in plaats van vast te lopen.
const gefilterd = computed(() => props.argumentList.filter(matches));

// Referentie over het hele corpus: waar de tekens van de assen aan opgehangen
// worden, zodat de kaart niet spiegelt terwijl je filtert.
//
// Altijd 3 componenten, ook in 2D-weergave: zou dit meebewegen met de toggle,
// dan meldt de referentie in 2D dat er maar 2 componenten zijn en kun je 3D
// nooit meer aanzetten.
const referentie = computed(() =>
	buildCorrespondence(props.argumentList, {
		nComponents: 3,
		unit: unit.value,
		minRowTotal: MIN_ROW_TOTAL[unit.value],
	}),
);

const correspondence = computed<Correspondence | null>(() => {
	const berekend = buildCorrespondence(gefilterd.value, {
		nComponents: driedimensionaal.value ? 3 : 2,
		unit: unit.value,
		minRowTotal: MIN_ROW_TOTAL[unit.value],
	});
	if (!berekend) return null;
	const ref = referentie.value;
	return ref ? alignSigns(ref, berekend) : berekend;
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
const COMPRESSIE_EXPONENT = 0.6;

function comprimeer(coords: number[]): number[] {
	const r = Math.hypot(...coords);
	if (r === 0) return coords;
	// r' = r^p, uniform herschaald langs dezelfde straal: r'/r = r^(p-1).
	const factor = r ** (COMPRESSIE_EXPONENT - 1);
	return coords.map((c) => c * factor);
}

const weergave = computed<Correspondence | null>(() => {
	const c = correspondence.value;
	if (!c) return null;
	return {
		...c,
		rows: c.rows.map((r) => ({ ...r, coords: comprimeer(r.coords) })),
		tags: c.tags.map((t) => ({ ...t, coords: comprimeer(t.coords) })),
	};
});

const heeftDerdeAs = computed(() => (referentie.value?.nComponents ?? 0) >= 3);

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
const PERSPECTIEF_KLEUR: Record<string, string> = Object.fromEntries(PERSPECTIEVEN.map((p) => [p.naam, p.kleur]));
const ONBEKENDE_KLEUR = "#6f6558";

// Achtergrondkleuren uit main.css; ECharts kan de CSS-variabelen niet lezen.
const ACHTERGROND = { licht: "#f2efe7", donker: "#1c1815" };

function ontleed(hex: string): [number, number, number] {
	const h = hex.replace("#", "");
	return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16)) as [number, number, number];
}

/** Luchtperspectief: hoe verder weg, hoe meer een kleur naar de achtergrond
 * toe trekt. Dat haalt in één bewerking zowel verzadiging als contrast weg --
 * precies wat mist met een berg in de verte doet -- en is een sterkere
 * dieptecue dan grootte alleen, omdat grootte hier ook al bezet is door het
 * aantal argumenten. `nabijheid` loopt van 0 (achterin) tot 1 (vooraan). */
function mist(kleur: string, nabijheid: number): string {
	if (!driedimensionaal.value) return kleur;
	const doel = ontleed(isDark.value ? ACHTERGROND.donker : ACHTERGROND.licht);
	const bron = ontleed(kleur);
	// Niet helemaal tot de achtergrond: het verste punt moet zichtbaar blijven.
	// Op 0,55 gemengd met de daaronder óók al aflopende opacity (zie tagSeries/
	// rijSerie) telden de twee dieptecues bij elkaar op tot een scène die als
	// geheel vager oogde dan 2D -- terwijl alleen het verste punt zo sterk hoefde
	// te vervagen. 0,35 laat het kleurverschil dichter bij de camera intact.
	const mengsel = 0.35 * (1 - nabijheid);
	const kanalen = bron.map((c, i) => Math.round(c + (doel[i] - c) * mengsel));
	return `rgb(${kanalen[0]}, ${kanalen[1]}, ${kanalen[2]})`;
}

const isDark = useTheme();
// Partijen zijn geen categorische serie maar een andere soort entiteit; inkt
// houdt de vier kleurslots vrij voor de perspectieven.
const inkt = computed(() => (isDark.value ? "#f2ede3" : "#221f1b"));
const gedempt = computed(() => (isDark.value ? "#a89e8c" : "#6f6558"));
const rasterLijn = computed(() => (isDark.value ? "#453f36" : "#ddd5c4"));

// Kleurlogo's zijn direct herkenbaar, maar ze brengen vijftien extra kleuren de
// kaart in en concurreren daarmee met de vier perspectiefkleuren, die hier de
// betekenisdragers zijn. Vast op 20% verzadiging -- nog altijd de eigen vorm
// en een vleugje eigen kleur, maar onderling consistent genoeg om niet met de
// perspectieven te wedijveren. Geen toggle (meer): in kleur verloor het altijd
// van die afweging, dus geen keuze om aan te bieden.
const LOGO_VERZADIGING = 0.2;

// Rijen zonder logo (geen partij, of een partij zonder logobestand) krijgen
// dezelfde initiaal-tegel als PartyLogo.vue's placeholder elders in de app --
// wit met ink-kleurige rand en letter -- i.p.v. een generieke stip, zodat het
// beeldtaal-consistent blijft. `partyInitial` (parties.ts) is dezelfde functie
// als PartyLogo.vue gebruikt, dus "Groep Markuszower" wordt hier en daar
// dezelfde letter.
function initiaalSprite(letter: string, kleur: string): string {
	const svg =
		`<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">` +
		`<rect x="1.5" y="1.5" width="21" height="21" rx="4" fill="#fff" stroke="${kleur}" stroke-width="1.5"/>` +
		`<text x="12" y="12.5" text-anchor="middle" dominant-baseline="central" font-family="sans-serif" ` +
		`font-size="13" font-weight="700" fill="${kleur}">${letter}</text>` +
		`</svg>`;
	return `image://data:image/svg+xml,${encodeURIComponent(svg)}`;
}

function stijlVoor(perspectief: string) {
	return PERSPECTIEF_KLEUR[perspectief] ?? ONBEKENDE_KLEUR;
}

const perspectieven = computed(() => {
	const gezien = new Set((correspondence.value?.tags ?? []).map((t) => t.perspectief));
	return [...gezien].sort();
});

// Bij personen als rij heeft de rij zelf geen logo, maar de spreker wel een
// partij. Dat logo zegt nog steeds waar iemand vandaan komt, en het is precies
// wat de losse zwarte stippen in die weergave niet deden.
const partijVanRij = computed(() => {
	const kaart = new Map<string, string>();
	for (const a of props.argumentList) {
		const rij = unit.value === "persoon" ? a.actor.name : a.actor.party ?? NO_PARTY;
		const partij = a.actor.party;
		if (partij && !kaart.has(rij)) kaart.set(rij, partij);
	}
	return kaart;
});

const rijenInSelectie = computed(
	() => new Set(gefilterd.value.map((a) => (unit.value === "persoon" ? a.actor.name : a.actor.party ?? NO_PARTY))),
);
const tagsInSelectie = computed(() => new Set(gefilterd.value.flatMap((a) => a.tags.map((t) => t.sleutel))));

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
const VASTE_TAGLABELS = 12;

// Letter per dimensie-index, gebruikt in zowel de 2D-aslabels (`asNaam`) als
// de 3D-aslabels hieronder -- zie issue #10.
const AS_LETTERS = ["x", "y", "z"];

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

const BEGIN_YAW = 0.6;
const BEGIN_PITCH = 0.35;

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
const CAMERA_AFSTAND = 4;

function projecteer(coords: number[]): { x: number; y: number; diepte: number; schaal: number } {
	if (!driedimensionaal.value || coords.length < 3) return { x: coords[0], y: coords[1], diepte: 0, schaal: 1 };
	const [x, y, z] = coords;
	const cy = Math.cos(yaw.value);
	const sy = Math.sin(yaw.value);
	const cp = Math.cos(pitch.value);
	const sp = Math.sin(pitch.value);
	const x1 = cy * x + sy * z;
	const z1 = -sy * x + cy * z;
	const y1 = cp * y - sp * z1;
	const z2 = sp * y + cp * z1;
	// z2 > 0 is naar de kijker toe, dus dichterbij = grotere schaal.
	const afstand = CAMERA_AFSTAND * straal.value;
	const schaal = afstand / Math.max(afstand - z2, afstand * 0.2);
	return { x: x1 * schaal, y: y1 * schaal, diepte: z2, schaal };
}

let sleept = false;
let laatsteX = 0;
let laatsteY = 0;
let startX = 0;
let startY = 0;
// Slepen eindigt op de canvas in een gewone click, en die zou anders een filter
// aan- of uitzetten. Een paar pixels speling, zodat een trillende hand nog wel
// gewoon klikt.
const KLIK_MARGE = 4;
let heeftGesleept = false;

function startSleep(e: PointerEvent) {
	if (!driedimensionaal.value) return;
	sleept = true;
	heeftGesleept = false;
	laatsteX = startX = e.clientX;
	laatsteY = startY = e.clientY;
	(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
}

function sleep(e: PointerEvent) {
	if (!sleept) return;
	if (Math.abs(e.clientX - startX) > KLIK_MARGE || Math.abs(e.clientY - startY) > KLIK_MARGE) heeftGesleept = true;
	yaw.value += (e.clientX - laatsteX) * 0.01;
	// Vastzetten net onder een kwartslag: verder doorschieten zet de kaart op
	// zijn kop en dan kloppen de aslabels niet meer met wat je ziet.
	pitch.value = Math.max(-1.4, Math.min(1.4, pitch.value + (e.clientY - laatsteY) * 0.01));
	laatsteX = e.clientX;
	laatsteY = e.clientY;
}

function stopSleep(e: PointerEvent) {
	sleept = false;
	(e.currentTarget as HTMLElement).releasePointerCapture?.(e.pointerId);
}

function wiel(e: WheelEvent) {
	// Ook in 2D altijd preventDefault: zonder dat scrollt de pagina onder de
	// muis vandaan zodra de cursor de grafiek nog maar even verlaat, en dan
	// landt de rest van de scrollbeweging niet meer op de kaart. In 2D doet
	// ECharts' eigen dataZoom de rest (zie chartOption); deze functie hoeft er
	// dan niets aan toe te voegen, alleen de paginascroll te blokkeren.
	e.preventDefault();
	if (!driedimensionaal.value) return;
	// Ondergrens ruim onder 1: het venster staat op het 90e percentiel, en de
	// verste tag ligt daar ~4x buiten. Bleef de ondergrens op 0,6 staan, dan was
	// die tag met geen enkele zoomstand in beeld te krijgen -- en bleef de hint
	// "buiten beeld" dus eeuwig staan.
	zoom.value = Math.min(6, Math.max(0.12, zoom.value * Math.exp(-e.deltaY * 0.0015)));
}

const chartRef = ref<any>(null);

function percentiel(waarden: number[], p: number): number {
	if (waarden.length === 0) return 1e-9;
	const gesorteerd = [...waarden].sort((a, b) => a - b);
	const index = Math.min(gesorteerd.length - 1, Math.floor(gesorteerd.length * p));
	return Math.max(gesorteerd[index], 1e-9);
}

/** Idem als `straal` hieronder, maar per as en dus ook zinvol in 2D: x en y
 * schalen daar los van elkaar, maar een enkele uitschieter (Ideologie-Links-
 * Economisch ligt ver van de rest) kan alsnog één van de twee assen alleen
 * domineren en de rest van die as tot een streep persen. Het 90e percentiel
 * per as geeft een venster waar de kern in past; de uitschieter valt er
 * standaard net als in 3D buiten, met dezelfde "zoom uit"-route terug. */
const asGrenzen = computed<[number, number]>(() => {
	const c = weergave.value;
	if (!c) return [1, 1];
	const punten = [...c.rows, ...c.tags];
	const x = percentiel(
		punten.map((p) => Math.abs(p.coords[0] ?? 0)),
		0.9,
	);
	const y = percentiel(
		punten.map((p) => Math.abs(p.coords[1] ?? 0)),
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
const asVolledigeGrenzen = computed<[number, number]>(() => {
	const c = weergave.value;
	if (!c) return [1, 1];
	const punten = [...c.rows, ...c.tags];
	const x = Math.max(...punten.map((p) => Math.abs(p.coords[0] ?? 0)), 1e-9);
	const y = Math.max(...punten.map((p) => Math.abs(p.coords[1] ?? 0)), 1e-9);
	return [x * 1.08, y * 1.08];
});

const buitenBeeld2D = computed(() => {
	const c = weergave.value;
	if (driedimensionaal.value || !c) return 0;
	const [gx, gy] = asGrenzen.value;
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
const forceerNormalisatie = ref(true);

function herstelAanzicht() {
	yaw.value = BEGIN_YAW;
	pitch.value = BEGIN_PITCH;
	zoom.value = 1;
	forceerNormalisatie.value = true;
	zicht2D.value = null;
}

// Wisselen tussen 2D en 3D betekent een compleet ander venstermodel (dataZoom
// vs. camera-zoom); een oud `zicht2D` zou anders de labelselectie in de
// nieuwe weergave nog even sturen op een stand die daar niet bij hoort.
watch(driedimensionaal, () => {
	zicht2D.value = null;
});

// Elke keer dat de onderliggende punten structureel veranderen -- elk filter
// (inclusief tag/partij, sinds die de tabel nu ook echt filteren) of wisselen
// van rij-eenheid/dimensiecount -- opnieuw normaliseren.
watch(correspondence, () => {
	forceerNormalisatie.value = true;
	zicht2D.value = null;
});

// Huidige zichtbare data-range in 2D, bijgehouden via het `datazoom`-event
// (zie VChart in de template) -- net als de dieptegebaseerde labelselectie in
// 3D, maar dan op basis van wat er na pannen/zoomen daadwerkelijk in beeld is
// i.p.v. camera-afstand. `null` betekent "nog niet gezoomd/gepand sinds de
// laatste normalisatie", dus dan valt de labelselectie hieronder terug op het
// volledige (genormaliseerde) venster.
const zicht2D = ref<{ x: [number, number]; y: [number, number] } | null>(null);

function opDataZoom() {
	const dz = chartRef.value?.getOption?.()?.dataZoom;
	if (!dz || dz.length < 2) return;
	const [volledigX, volledigY] = asVolledigeGrenzen.value;
	// start/end zijn percentages van de vaste as-grens (asVolledigeGrenzen),
	// dus terugrekenen naar data-eenheden kan zonder de as zelf te bevragen.
	const naarBereik = (start: number | undefined, end: number | undefined, grens: number): [number, number] => [
		-grens + ((start ?? 0) / 100) * 2 * grens,
		-grens + ((end ?? 100) / 100) * 2 * grens,
	];
	zicht2D.value = {
		x: naarBereik(dz[0]?.start, dz[0]?.end, volledigX),
		y: naarBereik(dz[1]?.start, dz[1]?.end, volledigY),
	};
}

const normen = computed(() => {
	const c = weergave.value;
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
const straal = computed(() => {
	const gesorteerd = normen.value;
	const index = Math.min(gesorteerd.length - 1, Math.floor(gesorteerd.length * 0.9));
	return Math.max(gesorteerd[index], 1e-9);
});

/** Punten die bij de huidige zoom gegarandeerd binnen het venster vallen, hebben
 * een norm onder deze grens; alles daarboven kán erbuiten liggen. */
const buitenBeeld = computed(() => {
	if (!driedimensionaal.value) return 0;
	const grens = (straal.value * 1.03) / zoom.value;
	return normen.value.filter((n) => n > grens).length;
});

// Verhouding van het tekengebied. Zonder dit staan er evenveel data-eenheden op
// een brede as als op een smalle, en dan is de projectie op het scherm geen
// rotatie meer maar een rotatie plus een uitrekking: het assenkruis lijkt bijna
// horizontaal te blijven terwijl de punten wel kantelen.
const wrapperEl = ref<HTMLElement | null>(null);
const plotVerhouding = ref(1);
let waarnemer: ResizeObserver | null = null;

function meet(el: HTMLElement) {
	const breedte = el.clientWidth - GRID.left - GRID.right;
	const hoogte = el.clientHeight - GRID.top - GRID.bottom;
	if (breedte > 0 && hoogte > 0) plotVerhouding.value = breedte / hoogte;
}

onMounted(() => {
	if (typeof ResizeObserver === "undefined") return;
	waarnemer = new ResizeObserver(([entry]) => meet(entry.target as HTMLElement));
	if (wrapperEl.value) waarnemer.observe(wrapperEl.value);
});

// De wrapper zit achter een v-if, dus hij kan later pas verschijnen.
watch(wrapperEl, (el) => {
	if (!waarnemer) return;
	waarnemer.disconnect();
	if (el) waarnemer.observe(el);
});

onUnmounted(() => waarnemer?.disconnect());

/** Diepte -> 0 (achterin) .. 1 (vooraan). Voert zowel de mist als het dimmen
 * van beeldsymbolen aan, die geen kleur kunnen aannemen. */
function nabijheid(diepte: number, bereik: number): number {
	if (!driedimensionaal.value || bereik <= 0) return 1;
	const lineair = Math.max(0, Math.min(1, (diepte + bereik) / (2 * bereik)));
	// De puntenwolk clustert rond het midden (diepte ~0), dus de meeste punten
	// zaten op deze lineaire schaal rond 0,5 -- ver van de "volle kleur" die
	// alleen het allervoorste punt (1,0) kreeg. Een machtscurve tilt het
	// middenbereik dichter naar 1 op, zodat de meerderheid van de wolk zijn
	// eigen kleur houdt en alleen de echte achterhoede nog merkbaar vervaagt.
	return Math.pow(lineair, 0.4);
}

/** 1, 2 of 5 maal een macht van tien: geeft rasterlijnen op afstanden die je
 * kunt aflezen i.p.v. op 0,3714. */
function netteStap(ruw: number): number {
	const macht = 10 ** Math.floor(Math.log10(ruw));
	const genormaliseerd = ruw / macht;
	return (genormaliseerd >= 5 ? 5 : genormaliseerd >= 2 ? 2 : 1) * macht;
}

const chartOption = computed(() => {
	const c = weergave.value;
	if (!c) return {};

	const geprojecteerd = {
		rows: c.rows.map((p) => ({ punt: p, ...projecteer(p.coords) })),
		tags: c.tags.map((p) => ({ punt: p, ...projecteer(p.coords) })),
	};
	const bereik = straal.value;

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
	const tagsInZicht2D = zicht2D.value
		? c.tags.filter(
				(t) => t.coords[0] >= zicht2D.value!.x[0] && t.coords[0] <= zicht2D.value!.x[1] &&
					t.coords[1] >= zicht2D.value!.y[0] && t.coords[1] <= zicht2D.value!.y[1],
			)
		: c.tags;
	const tagDrempel = driedimensionaal.value
		? ([...geprojecteerd.tags]
				.map((t) => t.diepte)
				.sort((a, b) => b - a)
				.slice(0, VASTE_TAGLABELS)
				.pop() ?? -Infinity)
		: ([...tagsInZicht2D]
				.map((t) => t.n)
				.sort((a, b) => b - a)
				.slice(0, VASTE_TAGLABELS)
				.pop() ?? 0);
	const tagInZichtSleutels = driedimensionaal.value ? null : new Set(tagsInZicht2D.map((t) => t.sleutel));

	const asStijl = { lineStyle: { color: rasterLijn.value } };
	// In 3D zijn de schermassen geen dimensies meer maar een gedraaide mengeling
	// van alle drie. Ze dan toch "dim 1" en "dim 2" noemen zou liegen, dus in die
	// modus verdwijnt het hele cartesische assenstelsel van ECharts en tekenen we
	// zelf een meegedraaid raster (zie hieronder).
	// `[ - ]`: CA-coördinaten zijn dimensieloos (geen euro's, geen aantallen) --
	// een expliciete "geen eenheid"-notatie is eerlijker dan er niets bij te
	// zetten, zie issue #10.
	const asNaam = (k: number) =>
		driedimensionaal.value ? "" : `${AS_LETTERS[k]} · dim ${k + 1} (${c.inertiaPct[k]}%) [ - ]`;
	const raster = driedimensionaal.value ? { show: false } : asStijl;
	const verborgenAs = {
		axisLine: { show: !driedimensionaal.value, ...asStijl },
		axisTick: { show: !driedimensionaal.value },
		splitLine: raster,
		axisLabel: { show: false },
	};

	const rijSerie = {
		id: "rijen",
		name: unit.value === "persoon" ? "Personen" : "Partijen",
		type: "scatter",
		cursor: "pointer",
		z: 3,
		itemStyle: { color: inkt.value },
		labelLayout: LABEL_LAYOUT,
		data: [...geprojecteerd.rows]
			.sort((a, b) => a.diepte - b.diepte)
			.map(({ punt, x, y, diepte, schaal }) => {
				const nabij = nabijheid(diepte, bereik);
				const inSelectie = rijenInSelectie.value.has(punt.label);
				// Het logo zegt in één blik welke partij het is. Alleen partijen
				// hebben logo's -- personen en fracties zonder officieel logo krijgen
				// dezelfde initiaal-tegel als PartyLogo.vue's placeholder (zie
				// `initiaalSprite`), geen generieke stip: dat is een van de twee
				// beeldtaal-tegels, niet buiten het systeem.
				const partij = unit.value === "partij" ? punt.label : partijVanRij.value.get(punt.label);
				const logo = partij ? logoSprite(partij, LOGO_VERZADIGING) : null;
				const symbool = logo?.symbool ?? initiaalSprite(partyInitial(punt.label), inkt.value);
				// De vereenvoudigde iconenset (en de initiaal-tegel) is één vast
				// vierkant canvas per partij, dus in tegenstelling tot de officiële
				// wordmarks hoeft de maat hier niet naar een eigen verhouding te kijken.
				const grootte = Math.max(9, Math.min(24, Math.sqrt(punt.n) * 3.2)) * schaal * 1.15;
				return {
					name: unit.value === "persoon" ? punt.label : displayPartyName(punt.label),
					rowLabel: punt.label,
					value: [x, y, punt.n],
					n: punt.n,
					symbol: symbool,
					symbolSize: grootte,
					itemStyle: {
						// Elke rij is nu een beeldsymbool (logo of initiaal-tegel), en dat
						// neemt geen kleur aan -- dus moet de mist via opacity, minder mooi,
						// maar de enige knop die er is. Niet lager dan 0,75: op deze lichte
						// achtergrond mengt een halftransparant vlak zichtbaar naar de
						// achtergrondkleur (bv. het logorood op 50% wordt een grijzige roze,
						// niet halfdoorzichtig rood) -- vooral merkbaar bij logo's, die al op
						// 20% verzadiging staan. 0,75 laat nog genoeg doorschijnen om
						// overlappende tegels niet helemaal dicht te slibben.
						opacity: (inSelectie ? 0.75 : DIM) * (0.7 + 0.3 * nabij),
					},
					// Een logo is zijn eigen label -- maar alleen als rij en logo dezelfde
					// entiteit zijn. Bij partijen is dat zo (dubbelop om de partijnaam er
					// nog eens bij te zetten), bij personen niet: het logo zegt alleen
					// welke partij, niet wie. Daar blijft de naam dus altijd nodig.
					label: {
						show: !logo || unit.value === "persoon",
						formatter: "{b}",
						position: "top",
						color: mist(inkt.value, nabij),
						fontSize: 11,
						fontWeight: 600,
					},
					emphasis: {
						label: { show: true, formatter: "{b}", position: "top", color: inkt.value, fontSize: 11, fontWeight: 600 },
					},
				};
			}),
	};

	const tagSeries = perspectieven.value.map((perspectief) => {
		const kleur = stijlVoor(perspectief);
		return {
			id: `tags-${perspectief}`,
			name: perspectief,
			type: "scatter",
			symbol: "circle",
			cursor: "pointer",
			z: 2,
			itemStyle: { color: kleur, opacity: 0.5 },
			labelLayout: LABEL_LAYOUT,
			data: geprojecteerd.tags
				.filter(({ punt }) => punt.perspectief === perspectief)
				.sort((a, b) => a.diepte - b.diepte)
				.map(({ punt, x, y, diepte, schaal }) => {
					const nabij = nabijheid(diepte, bereik);
					const inSelectie = tagsInSelectie.value.has(punt.sleutel);
					return {
						name: punt.sleutel,
						value: [x, y, punt.n],
						n: punt.n,
						beschrijving: punt.beschrijving,
						labelgroep: punt.labelgroep,
						perspectief: punt.perspectief,
						symbolSize: Math.max(13, Math.min(28, Math.sqrt(punt.n) * 3.2)) * schaal * 0.6,
						// Effen cirkel: iconen per tag (vijftig) en zelfs per perspectief
						// (vier) lazen op kaartschaal niet als teken, zeker in een dichte
						// cluster -- alleen kleur nog. Niet lager dan 0,75 opacity: op deze
						// lichte achtergrond mengt een halftransparant vlak zichtbaar naar de
						// achtergrondkleur (het perspectiefpalet is al gedempt "aardetinten",
						// dus op 50% wordt het nauwelijks meer dan grijs), en dat was precies
						// de klacht. 0,75 laat nog genoeg doorschijnen om overlappende punten
						// niet helemaal dicht te slibben.
						itemStyle: {
							color: mist(kleur, nabij),
							// Vloer op 0,7 i.p.v. 0,5: in 3D telde deze opacity-afname vroeger op
							// bij de kleurmist hierboven, en samen maakten ze de hele wolk vager
							// dan in 2D -- ook punten die niet eens ver weg lagen.
							opacity: (inSelectie ? 0.75 : DIM) * (0.7 + 0.3 * nabij),
						},
						label: {
							show: driedimensionaal.value
								? diepte >= tagDrempel
								: (tagInZichtSleutels?.has(punt.sleutel) ?? true) && punt.n >= tagDrempel,
							formatter: "{b}",
							position: "top",
							color: mist(gedempt.value, nabij),
							fontSize: 9,
						},
						emphasis: { label: { show: true, formatter: "{b}", position: "top", color: inkt.value, fontSize: 10 } },
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
	const maxSchaal = CAMERA_AFSTAND / (CAMERA_AFSTAND - 1);
	const halveHoogte = (straal.value * 1.03 * maxSchaal) / zoom.value;
	// In 3D is dit het venster zelf (het draait mee, zie hierboven); in 2D is
	// het de vaste, nooit-veranderende as-grens waarbinnen dataZoom pant en
	// zoomt -- zie `asVolledigeGrenzen`.
	const [volledigX, volledigY] = asVolledigeGrenzen.value;
	const grensY = driedimensionaal.value ? halveHoogte : volledigY;
	const grensX = driedimensionaal.value ? halveHoogte * plotVerhouding.value : volledigX;

	function lijnSerie(id: string, punten: number[][], kleur: string, breedte: number, z = 1) {
		return {
			id,
			type: "line",
			silent: true,
			showSymbol: false,
			animation: false,
			z,
			lineStyle: { color: kleur, width: breedte },
			data: punten.map((p) => {
				const q = projecteer(p);
				return [q.x, q.y];
			}),
		};
	}

	// Kader ruim binnen de bolstraal, zodat ook de verste hoekpunten van de kubus
	// bij elke rotatie binnen het venster blijven staan.
	const kaderStap = netteStap(straal.value / 2.5);
	const kaderStappen = Math.max(2, Math.round((straal.value * 0.7) / kaderStap));
	const kader = kaderStap * kaderStappen;
	const vloer = -kader;

	const frameSeries: any[] = [];
	if (driedimensionaal.value) {
		for (let i = 0; i <= 2 * kaderStappen; i++) {
			const t = -kader + i * kaderStap;
			frameSeries.push(lijnSerie(`vloer-a${i}`, [[-kader, vloer, t], [kader, vloer, t]], rasterLijn.value, 1));
			frameSeries.push(lijnSerie(`vloer-b${i}`, [[t, vloer, -kader], [t, vloer, kader]], rasterLijn.value, 1));
		}
		const hoeken: number[][] = [
			[-kader, -kader],
			[kader, -kader],
			[kader, kader],
			[-kader, kader],
		];
		hoeken.forEach(([x, z], i) => {
			const [nx, nz] = hoeken[(i + 1) % 4];
			frameSeries.push(lijnSerie(`ribbe-${i}`, [[x, vloer, z], [x, kader, z]], rasterLijn.value, 1));
			frameSeries.push(lijnSerie(`deksel-${i}`, [[x, kader, z], [nx, kader, nz]], rasterLijn.value, 1));
		});
		for (const k of [0, 1, 2]) {
			const eind = [0, 1, 2].map((as) => (as === k ? kader : 0));
			frameSeries.push(lijnSerie(`as-${k}`, [[0, 0, 0], eind], gedempt.value, 1.5, 2));
		}
		frameSeries.push({
			id: "as-labels",
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
				const q = projecteer([0, 1, 2].map((as) => (as === k ? kader : 0)));
				return {
					value: [q.x, q.y],
					label: {
						show: true,
						formatter: `${AS_LETTERS[k]} · dim ${k + 1} (${c.inertiaPct[k]}%) [ - ]`,
						color: gedempt.value,
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
				return `<strong>${p.data.name}</strong><br/><span style="opacity:0.7">${p.data.perspectief} &middot; ${p.data.labelgroep}</span><br/>${p.data.beschrijving}<br/><span style="opacity:0.7">${p.data.n}x toegekend</span>`;
			},
		},
		legend: {
			// Bewust niet klikbaar: een legenda die series lokaal verbergt is een
			// tweede, verborgen filter naast de filterbalk. Haar echt op de
			// gedeelde filterstore aansluiten staat als los punt in #3.
			selectedMode: false,
			data: [rijSerie.name, ...perspectieven.value],
			top: 0,
			type: "scroll",
			textStyle: { color: inkt.value, fontSize: 11 },
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
		dataZoom: driedimensionaal.value
			? []
			: [
					{
						type: "inside",
						xAxisIndex: 0,
						filterMode: "none",
						throttle: 0,
						...(forceerNormalisatie.value ? { startValue: -asGrenzen.value[0], endValue: asGrenzen.value[0] } : {}),
					},
					{
						type: "inside",
						yAxisIndex: 0,
						filterMode: "none",
						throttle: 0,
						...(forceerNormalisatie.value ? { startValue: -asGrenzen.value[1], endValue: asGrenzen.value[1] } : {}),
					},
				],
		grid: { ...GRID },
		xAxis: {
			type: "value",
			min: grensX === undefined ? undefined : -grensX,
			max: grensX,
			name: asNaam(0),
			nameLocation: "middle",
			nameGap: 28,
			nameTextStyle: { color: gedempt.value },
			...verborgenAs,
		},
		yAxis: {
			type: "value",
			min: grensY === undefined ? undefined : -grensY,
			max: grensY,
			name: asNaam(1),
			nameLocation: "middle",
			nameGap: 18,
			nameTextStyle: { color: gedempt.value },
			...verborgenAs,
		},
		series: [...frameSeries, rijSerie, ...tagSeries],
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
		if (forceerNormalisatie.value) forceerNormalisatie.value = false;
	},
	{ flush: "post" },
);

function onChartClick(p: any) {
	// Het einde van een sleep is ook een click; die mag geen filter omzetten.
	if (heeftGesleept) return;
	if (p.data?.rowLabel !== undefined) {
		// Personen zijn geen filterdimensie met dezelfde sleutel; alleen partijen
		// kunnen we hier direct doorzetten naar de filterstore.
		if (unit.value === "partij") toggleValue("partij", p.data.rowLabel);
		else toggleValue("persoon", p.data.rowLabel);
		return;
	}
	if (p.data?.name) toggleValue("tag", p.data.name);
}

const tagFilterActief = computed(() => filters.values.tag.length > 0 || filters.values.partij.length > 0);
</script>

<template>
	<section class="stats-panel">
		<h2>Partijen &amp; tags (correspondentieanalyse)</h2>
		<p class="panel-note">
			Rijen dicht bij elkaar gebruiken vergelijkbare soorten argumenten; een tag dicht bij een rij komt relatief vaak bij die rij
			voor. Kleur geeft het perspectief van de tag aan. Alleen de vaakst toegekende tags houden hun naam in beeld; wijs een punt
			aan voor de rest. Klik op een punt om erop te filteren.
		</p>
		<p class="panel-note">
			De analyse wordt op je selectie herberekend. Filters op <strong>tag</strong> en <strong>partij</strong> vormen de
			uitzondering: die zouden de tabel tot één rij of kolom terugbrengen, dus die dimmen alleen de punten buiten de selectie.
		</p>

		<div class="chart-controls">
			<div class="chart-controls-group">
				<span class="chart-controls-label">Rijen</span>
				<div class="toggle-group" role="group">
					<button type="button" class="toggle-btn" :class="{ 'is-active': unit === 'partij' }" @click="unit = 'partij'">
						Partijen
					</button>
					<button type="button" class="toggle-btn" :class="{ 'is-active': unit === 'persoon' }" @click="unit = 'persoon'">
						Personen
					</button>
				</div>
			</div>
			<div class="chart-controls-group">
				<span class="chart-controls-label">Weergave</span>
				<div class="toggle-group" role="group">
					<button type="button" class="toggle-btn" :class="{ 'is-active': !driedimensionaal }" @click="driedimensionaal = false">
						2D
					</button>
					<button
						type="button"
						class="toggle-btn"
						:class="{ 'is-active': driedimensionaal }"
						:disabled="!heeftDerdeAs"
						:title="heeftDerdeAs ? '' : 'Te weinig data voor een derde dimensie'"
						@click="driedimensionaal = true"
					>
						3D
					</button>
				</div>
				<button type="button" class="control-knop" @click="herstelAanzicht">Aanzicht herstellen</button>
			</div>
			<template v-if="driedimensionaal">
				<span class="control-hint">
					slepen draait, scrollen zoomt<template v-if="buitenBeeld">
						&middot; {{ buitenBeeld }} punt{{ buitenBeeld === 1 ? "" : "en" }} buiten beeld, zoom uit om ze te zien</template
					>
				</span>
			</template>
			<span v-else class="control-hint">
				scrollen zoomt, slepen verschuift<template v-if="buitenBeeld2D">
					&middot; {{ buitenBeeld2D }} punt{{ buitenBeeld2D === 1 ? "" : "en" }} buiten beeld, zoom uit om ze te zien</template
				><template v-if="!heeftDerdeAs"> &middot; 3D vereist minstens 4 rijen en 4 tags</template>
			</span>
		</div>

		<p v-if="tagFilterActief" class="panel-note">
			Er staat een tag- of partijfilter aan; de kaart toont daarom nog de volledige analyse met de selectie gemarkeerd.
		</p>

		<div
			v-if="weergave"
			ref="wrapperEl"
			class="correspondence-wrapper"
			:class="{ 'is-3d': driedimensionaal }"
			@pointerdown="startSleep"
			@pointermove="sleep"
			@pointerup="stopSleep"
			@pointercancel="stopSleep"
			@wheel="wiel"
		>
			<VChart
				ref="chartRef"
				class="party-chart correspondence-chart"
				:option="chartOption"
				:update-options="{ replaceMerge: ['series', 'dataZoom'] }"
				autoresize
				@click="onChartClick"
				@datazoom="opDataZoom"
			/>
		</div>
		<p v-else class="panel-note">
			Te weinig getagde data in deze selectie voor een zinnige analyse (minimaal 3 rijen en 3 tags met genoeg volume nodig).
		</p>
	</section>
</template>
