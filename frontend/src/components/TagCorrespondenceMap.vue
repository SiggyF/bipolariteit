<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useTheme } from "../lib/useTheme";
import { displayPartyName } from "../lib/parties";
import { logoSprite } from "../lib/partyLogoSprite";
import { ICOON_PAD, PERSPECTIEVEN, TAG_ICOON } from "../lib/tagIcons.generated";
import { filters, matches, matchesExcept, toggleValue } from "../lib/filters";
import { NO_PARTY, type Argument } from "../lib/types";
import { alignSigns, buildCorrespondence, type Correspondence, type RowUnit } from "../lib/correspondence";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { LineChart, ScatterChart } from "echarts/charts";
import { TooltipComponent, GridComponent, LegendComponent, DataZoomInsideComponent } from "echarts/components";

use([CanvasRenderer, ScatterChart, LineChart, TooltipComponent, GridComponent, LegendComponent, DataZoomInsideComponent]);

const props = defineProps<{ argumentList: Argument[] }>();

// De analyse rekent op alles behalve de tag- en partijfilters -- klikken op een
// tag zou anders de tabel tot één kolom terugbrengen en de analyse laten
// instorten. Die twee filters sturen alleen nog het dimmen aan.
const REKENT_NIET_OP = ["tag", "partij"];

const unit = ref<RowUnit>("partij");
const driedimensionaal = ref(false);

// Bij persoon als rij is een drempel van 3 te laag: veel sprekers hebben één of
// twee argumenten en zouden als losse punten de wolk vullen zonder iets te zeggen.
const MIN_ROW_TOTAL: Record<RowUnit, number> = { partij: 3, persoon: 12 };

const rekenLijst = computed(() => props.argumentList.filter((a) => matchesExcept(a, REKENT_NIET_OP)));
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
	const berekend = buildCorrespondence(rekenLijst.value, {
		nComponents: driedimensionaal.value ? 3 : 2,
		unit: unit.value,
		minRowTotal: MIN_ROW_TOTAL[unit.value],
	});
	if (!berekend) return null;
	const ref = referentie.value;
	return ref ? alignSigns(ref, berekend) : berekend;
});

const heeftDerdeAs = computed(() => (referentie.value?.nComponents ?? 0) >= 3);

// Kleur en icoon per perspectief komen uit het ontwerpsysteem in
// docs/design/tag-iconografie/ -- één bron, en niet nog een keer overgetypt in
// deze component. `scripts/build_tag_icons.mjs` maakt daar
// lib/tagIcons.generated.ts van.
//
// Let op wat dit palet wél en niet doet. Het is mono-accent: vier gedempte
// aardetinten die naast elkaar liggen in plaats van tegen elkaar schreeuwen.
// Mooier op deze achtergrond, maar het onderlinge kleurverschil is kleiner dan
// bij het palet dat hier eerder stond, en zeker onder kleurenblindheid draagt
// kleur alleen de vier perspectieven niet meer uit elkaar. Het icoon is hier
// dus geen versiering maar de eigenlijke codering; de kleur bevestigt alleen.
// Daarom hebben de tagpunten hun tagicoon en niet een generiek bolletje.
//
// Eén palet voor beide modes: aardetinten van deze verzadiging houden op zowel
// #f2efe7 als #1c1815 genoeg contrast, dus een aparte donkere variant zou hier
// alleen maar uit elkaar gaan lopen.
const PERSPECTIEF_STIJL: Record<string, { kleur: string; icoon: string }> = Object.fromEntries(
	PERSPECTIEVEN.map((p) => [p.naam, { kleur: p.kleur, icoon: p.icoon }]),
);
const ONBEKEND_PERSPECTIEF = { kleur: "#6f6558", icoon: "circle-help" };

/** Lucide-iconen zijn lijntekeningen, dus een tagpunt is een contour en geen
 * vlak. Vandaar dat de kleur hieronder in `borderColor` terechtkomt. */
function icoonSymbool(naam: string): string {
	const pad = ICOON_PAD[naam];
	return pad ? `path://${pad}` : "circle";
}

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
	const mengsel = 0.55 * (1 - nabijheid);
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
// betekenisdragers zijn. De outline-variant zet ze terug naar één inkt. Als
// toggle en niet als besluit: welke van de twee wint, hangt af van hoe druk de
// wolk is, en dat verschilt per selectie.
const logoStijl = ref<"kleur" | "inkt">("inkt");
const logoInkt = computed(() => (logoStijl.value === "inkt" ? inkt.value : null));

function stijlVoor(perspectief: string) {
	const stijl = PERSPECTIEF_STIJL[perspectief] ?? ONBEKEND_PERSPECTIEF;
	return { kleur: stijl.kleur, symbool: icoonSymbool(stijl.icoon) };
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
// verdienen -- de vaakst toegekende -- en krijgt de rest zijn naam bij hover.
// Rijen (hooguit een stuk of twintig partijen) houden altijd hun label; dat
// zijn de ankers waaraan je de rest afleest.
const VASTE_TAGLABELS = 12;

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
	if (!driedimensionaal.value) return;
	e.preventDefault();
	// Ondergrens ruim onder 1: het venster staat op het 90e percentiel, en de
	// verste tag ligt daar ~4x buiten. Bleef de ondergrens op 0,6 staan, dan was
	// die tag met geen enkele zoomstand in beeld te krijgen -- en bleef de hint
	// "buiten beeld" dus eeuwig staan.
	zoom.value = Math.min(6, Math.max(0.12, zoom.value * Math.exp(-e.deltaY * 0.0015)));
}

const chartRef = ref<any>(null);

function herstelAanzicht() {
	yaw.value = BEGIN_YAW;
	pitch.value = BEGIN_PITCH;
	zoom.value = 1;
	// De 2D-zoom zit in ECharts' eigen state en niet in een ref van ons, dus die
	// moet expliciet terug naar het volledige bereik.
	chartRef.value?.dispatchAction({ type: "dataZoom", start: 0, end: 100 });
}

const normen = computed(() => {
	const c = correspondence.value;
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
	return Math.max(0, Math.min(1, (diepte + bereik) / (2 * bereik)));
}

/** 1, 2 of 5 maal een macht van tien: geeft rasterlijnen op afstanden die je
 * kunt aflezen i.p.v. op 0,3714. */
function netteStap(ruw: number): number {
	const macht = 10 ** Math.floor(Math.log10(ruw));
	const genormaliseerd = ruw / macht;
	return (genormaliseerd >= 5 ? 5 : genormaliseerd >= 2 ? 2 : 1) * macht;
}

const chartOption = computed(() => {
	const c = correspondence.value;
	if (!c) return {};

	const geprojecteerd = {
		rows: c.rows.map((p) => ({ punt: p, ...projecteer(p.coords) })),
		tags: c.tags.map((p) => ({ punt: p, ...projecteer(p.coords) })),
	};
	const bereik = straal.value;

	// Drempel waarboven een tag zijn naam vast in beeld houdt.
	const tagDrempel = [...c.tags]
		.map((t) => t.n)
		.sort((a, b) => b - a)
		.slice(0, VASTE_TAGLABELS)
		.pop() ?? 0;

	const asStijl = { lineStyle: { color: rasterLijn.value } };
	// In 3D zijn de schermassen geen dimensies meer maar een gedraaide mengeling
	// van alle drie. Ze dan toch "dim 1" en "dim 2" noemen zou liegen, dus in die
	// modus verdwijnt het hele cartesische assenstelsel van ECharts en tekenen we
	// zelf een meegedraaid raster (zie hieronder).
	const asNaam = (k: number) => (driedimensionaal.value ? "" : `dim ${k + 1} (${c.inertiaPct[k]}%)`);
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
				// Het logo zegt in één blik welke partij het is; de zwarte stip zei
				// dat pas via het label ernaast. Alleen partijen hebben logo's --
				// personen en fracties zonder officieel logo houden de stip.
				const partij = unit.value === "partij" ? punt.label : partijVanRij.value.get(punt.label);
				const logo = partij ? logoSprite(partij, logoInkt.value) : null;
				const basis = Math.max(9, Math.min(24, Math.sqrt(punt.n) * 3.2)) * schaal;
				// Een beeldsymbool wordt in het vak geperst dat je opgeeft, dus een
				// vierkante maat maakt van elk wordmerk een uitgerekt wordmerk. De
				// hoogte volgt de puntgrootte, de breedte de eigen verhouding --
				// afgetopt, want PVV is 13:1 en dat wordt een streep over de kaart.
				const grootte = logo ? [basis * 1.15 * Math.min(logo.verhouding, 3), basis * 1.15] : basis;
				return {
					name: unit.value === "persoon" ? punt.label : displayPartyName(punt.label),
					rowLabel: punt.label,
					value: [x, y, punt.n],
					n: punt.n,
					symbol: logo ? logo.symbool : "circle",
					symbolSize: grootte,
					itemStyle: {
						// Een beeldsymbool neemt geen kleur aan, dus daar moet de mist
						// via opacity: minder mooi, maar het is de enige knop die er is.
						color: mist(inkt.value, nabij),
						// Iets doorschijnend, zodat overlappende logo's elkaar niet
						// helemaal wegdrukken in het dichte midden van de wolk.
						opacity: (inSelectie ? (logo ? 0.8 : 0.9) : DIM) * (logo ? 0.55 + 0.45 * nabij : 1),
					},
					// Een logo is zijn eigen label; de partijnaam eronder zetten is dan
					// dubbelop en kost precies de ruimte die de kaart niet heeft. Voor
					// fracties zonder logo blijft de naam het enige aanknopingspunt.
					label: {
						show: !logo,
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
		const { kleur, symbool } = stijlVoor(perspectief);
		return {
			id: `tags-${perspectief}`,
			name: perspectief,
			type: "scatter",
			symbol: symbool,
			cursor: "pointer",
			z: 2,
			itemStyle: { color: "transparent", borderColor: kleur, borderWidth: 1.6 },
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
						// Ruimer dan de oude 7..20: een icoon heeft meer pixels nodig dan
						// een cirkel voordat het silhouet leesbaar wordt.
						// Het perspectiefsymbool is de terugval; heeft de tag een eigen
						// icoon in het ontwerpsysteem, dan wint dat. Op de kaart is dat bij
						// ~16 px vooral textuur, maar in de tooltip en de legenda telt het
						// wel, en zo staat er overal hetzelfde teken voor dezelfde tag.
						symbol: icoonSymbool(TAG_ICOON[punt.sleutel] ?? ""),
						symbolSize: Math.max(13, Math.min(28, Math.sqrt(punt.n) * 3.2)) * schaal,
						// Lijntekening: de kleur zit in de rand, de vulling blijft leeg.
						itemStyle: {
							color: "transparent",
							borderColor: mist(kleur, nabij),
							borderWidth: 1.6,
							opacity: inSelectie ? 0.9 : DIM,
						},
						label: {
							show: punt.n >= tagDrempel,
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
	const grensY = driedimensionaal.value ? halveHoogte : undefined;
	const grensX = driedimensionaal.value ? halveHoogte * plotVerhouding.value : undefined;

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
						formatter: `dim ${k + 1} (${c.inertiaPct[k]}%)`,
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
		dataZoom: driedimensionaal.value
			? []
			: [
					{ type: "inside", xAxisIndex: 0, filterMode: "none" },
					{ type: "inside", yAxisIndex: 0, filterMode: "none" },
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
			voor. Kleur en icoon geven het perspectief van de tag aan. Alleen de vaakst toegekende tags houden hun naam in beeld; wijs
			een punt aan voor de rest. Klik op een punt om erop te filteren.
		</p>
		<p class="panel-note">
			De analyse wordt op je selectie herberekend. Filters op <strong>tag</strong> en <strong>partij</strong> vormen de
			uitzondering: die zouden de tabel tot één rij of kolom terugbrengen, dus die dimmen alleen de punten buiten de selectie.
		</p>

		<div class="chart-controls">
			<label>
				Rijen:
				<select v-model="unit">
					<option value="partij">partijen</option>
					<option value="persoon">personen</option>
				</select>
			</label>
			<label>
				Logo's:
				<select v-model="logoStijl">
					<option value="kleur">in kleur</option>
					<option value="inkt">als contour</option>
				</select>
			</label>
			<label :title="heeftDerdeAs ? '' : 'Te weinig data voor een derde dimensie'">
				<input type="checkbox" v-model="driedimensionaal" :disabled="!heeftDerdeAs" />
				3D
			</label>
			<button type="button" class="control-knop" @click="herstelAanzicht">Aanzicht herstellen</button>
			<template v-if="driedimensionaal">
				<span class="control-hint">
					slepen draait, scrollen zoomt<template v-if="buitenBeeld">
						&middot; {{ buitenBeeld }} punt{{ buitenBeeld === 1 ? "" : "en" }} buiten beeld, zoom uit om ze te zien</template
					>
				</span>
			</template>
			<span v-else class="control-hint">
				scrollen zoomt, slepen verschuift<template v-if="!heeftDerdeAs"> &middot; 3D vereist minstens 4 rijen en 4 tags</template>
			</span>
		</div>

		<p v-if="tagFilterActief" class="panel-note">
			Er staat een tag- of partijfilter aan; de kaart toont daarom nog de volledige analyse met de selectie gemarkeerd.
		</p>

		<div
			v-if="correspondence"
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
			/>
		</div>
		<p v-else class="panel-note">
			Te weinig getagde data in deze selectie voor een zinnige analyse (minimaal 3 rijen en 3 tags met genoeg volume nodig).
		</p>
	</section>
</template>
