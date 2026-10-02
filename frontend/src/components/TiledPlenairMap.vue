<script setup lang="ts">
// Alternatief renderpad naast PlenairMap.vue (die ongewijzigd blijft, zie
// issue #215/#253): leest dezelfde brondata niet als één platte JSON, maar
// als een vector-tile-pyramide (.pmtiles, gebouwd door
// `pipeline.tiling.build_pyramid`) op de volle dataset (issue #293/#259).
//
// MapLibre GL voor achtergrond/cluster-hullen/-labels/basiskaart (v2, zie
// git-historie voor de eerdere eigen d3-zoom/@mapbox-vector-tile-opzet: die
// had geen zoom-debounce en geen "toon het vorige niveau tot het nieuwe
// geladen is"-gedrag). De puntenlaag zelf (v3) draait op deck.gl
// (`@deck.gl/mapbox`'s MapboxOverlay bovenop dezelfde MapLibre-kaart), want
// MapLibre's circle-layer ondersteunt geen echte GL-blendmode
// (screen/multiply) -- deck.gl's layers wel, via `parameters.blendFunc`.
// deck.gl's TileLayer kent geen pmtiles-protocol, dus de puntenlaag decodeert
// zijn tiles zelf via `pmtiles.getZxy()` + `@mapbox/vector-tile` (dezelfde
// aanpak als de vroegere v1-canvasrenderer, nu alleen gebruikt om deck.gl van
// data te voorzien, niet om zelf te tekenen/zoomen/cachen -- dat blijft
// TileLayer's eigen taak).
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { PMTiles, Protocol } from "pmtiles";
import { VectorTile } from "@mapbox/vector-tile";
import { PbfReader } from "pbf";
import { TileLayer } from "@deck.gl/geo-layers";
import { ScatterplotLayer } from "@deck.gl/layers";
import { MapboxOverlay } from "@deck.gl/mapbox";
import { useTheme } from "../lib/useTheme";
import { DEFAULT_TOPIC_COLOR, TOPIC_COLOR, clusterColorRgb, partyColorRgb, yearColorRgb } from "../lib/plenairMapColors";
import {
	mercatorMetersToLngLat,
	smoothClosedRing,
	tileBoundsMeters,
	tileLocalToLngLat,
	umapToMercator,
	type GridMetadata,
	type TileIndex,
} from "../lib/tiledMapTransform";

const props = defineProps<{
	// pmtiles + grid-metadata + cluster-hulls komen van Hugging Face (volle
	// dataset, zie lib/dataBaseUrl.ts, issue #316/#293) -- deze component
	// gebruikt geen jsDelivr-databasis. video-links zitten als MVT-eigenschap
	// in de tiles zelf (pipeline/tiling/encode.py), dus ook geen losse
	// dataBaseUrl meer nodig zoals PlenairMap.vue die wel heeft.
	tilesBaseUrl: string;
}>();

const emit = defineEmits<{
	(e: "select-cluster", clusterId: number | null): void;
}>();

type ClusterHullItem = {
	cluster_id: number;
	name: string;
	centroid: [number, number];
	hull: [number, number][] | null;
	size: number;
	terms?: string[];
	parent_name?: string | null;
};

type DeckPoint = {
	id: number;
	position: [number, number];
	topic: string;
	actor: string;
	party: string;
	debate: string;
	text: string;
	publishedAt: string;
	cluster: number | null;
	year: number | null;
	// Video-deep-link, als MVT-eigenschap meegecodeerd per punt
	// (pipeline/tiling/build_pyramid.py::load_video_hrefs()) i.p.v. via een
	// los plenair-map-videos.json -- dat bestand dekte voor de volle dataset
	// maar ~5,5% en zou bij volledige dekking tot ~190MB ongecomprimeerd
	// groeien (issue #356-vervolg). Twee vormen, te onderscheiden aan het
	// pad (zie activePointVideo hieronder): een site-relatief pad
	// ("/debatten/{id}/") naar onze eigen interne videospeler-pagina (de
	// ~5300 gecureerde entries uit plenair-map-videos.json), of anders een
	// absolute externe Debat Direct-URL.
	video: string | null;
};

// Zelfde "pin wint van hover, klik op leegte unpint" model als PlenairMap.vue
// (activeDisplayItem/pinnedItem/hoveredItem daar) -- alleen is hit-testing
// hier niet zelf gebouwd (spatial grid, contour-afstand): deck.gl's eigen
// GPU-picking (punten) en MapLibre's queryRenderedFeatures (hullen/labels)
// doen dat al.
type DisplayItem = { type: "point"; data: DeckPoint } | { type: "cluster"; data: ClusterHullItem };

// Welk punt-attribuut de puntkleur bepaalt (issue #259: "we willen kunnen
// kleuren op verschillende elementen" -- topic/cluster/partij/jaar).
type ColorBy = "topic" | "cluster" | "party" | "year";
const colorBy = ref<ColorBy>("cluster");

const COLOR_BY_OPTIONS: { value: ColorBy; label: string }[] = [
	{ value: "cluster", label: "Cluster" },
	{ value: "year", label: "Jaar" },
	{ value: "topic", label: "Onderwerp" },
	{ value: "party", label: "Partij" },
];

// "Kleur op"-keuze als MapLibre-eigen kaartcontrol (IControl) i.p.v. een los
// HTML-blok boven de kaart -- consistent met de zoom-knoppen (zelfde
// maplibregl-ctrl-opmaak, zelfde hoek van de kaart), en één plek waar alle
// kaart-UI samenkomt.
class ColorByControl implements maplibregl.IControl {
	private container: HTMLDivElement | null = null;
	private buttons = new Map<ColorBy, HTMLButtonElement>();
	private stopWatch: (() => void) | null = null;

	onAdd(): HTMLElement {
		const container = document.createElement("div");
		container.className = "maplibregl-ctrl maplibregl-ctrl-group color-by-ctrl";
		for (const { value, label } of COLOR_BY_OPTIONS) {
			const button = document.createElement("button");
			button.type = "button";
			button.className = "color-by-ctrl-btn";
			button.textContent = label;
			button.addEventListener("click", () => {
				colorBy.value = value;
			});
			// Hover-affordance via JS i.p.v. CSS :hover: de achtergrond-/
			// tekstkleur van elke knop staat als inline style (zie de watch
			// hieronder), en inline styles winnen altijd van een :hover-regel in
			// het stylesheet, ongeacht specificiteit -- een CSS :hover-regel zou
			// hier dus domweg nooit zichtbaar worden.
			button.addEventListener("mouseenter", () => {
				if (button.dataset.active !== "true") button.style.background = "rgba(128, 128, 128, 0.12)";
			});
			button.addEventListener("mouseleave", () => {
				if (button.dataset.active !== "true") button.style.background = "transparent";
			});
			this.buttons.set(value, button);
			container.appendChild(button);
		}
		this.stopWatch = watch(
			[colorBy, isDark],
			([active, dark]) => {
				// Rechtstreeks de theme-kleuren zetten i.p.v. CSS currentColor: een
				// custom property als `--map-ink: currentColor` "bevriest" de
				// waarde niet bij definitie -- `var(--map-ink)` wordt bij gebruik
				// letterlijk vervangen door `currentColor`, dat op zijn beurt weer
				// resolvet tegen de EIGEN (net gewijzigde) `color` van het element.
				// Voor de actieve knop (achtergrond=inkt, tekst=canvas) gaf dat
				// structureel dezelfde kleur voor allebei -- onzichtbare tekst.
				const theme = dark ? THEME_COLOR.dark : THEME_COLOR.light;
				for (const [value, button] of this.buttons) {
					const isActive = value === active;
					button.dataset.active = String(isActive);
					button.setAttribute("aria-pressed", String(isActive));
					button.style.background = isActive ? theme.muted : "transparent";
					button.style.color = isActive ? theme.bg : theme.muted;
				}
			},
			{ immediate: true },
		);
		this.container = container;
		return container;
	}

	onRemove(): void {
		this.stopWatch?.();
		this.container?.remove();
		this.container = null;
		this.buttons.clear();
	}

	getDefaultPosition(): string {
		return "top-left";
	}
}

// "Weergave resetten"-knop (PlenairMap.vue's resetView()): wist pin/hover/
// topic-filter en vliegt terug naar het startcentrum/-zoomniveau. Losse
// IControl i.p.v. een HTML-knop over de kaart heen, consistent met
// ColorByControl en de zoom-knoppen.
class ResetViewControl implements maplibregl.IControl {
	private container: HTMLDivElement | null = null;

	onAdd(mapInstance: maplibregl.Map): HTMLElement {
		const container = document.createElement("div");
		container.className = "maplibregl-ctrl maplibregl-ctrl-group";
		const button = document.createElement("button");
		button.type = "button";
		button.title = "Weergave resetten";
		button.setAttribute("aria-label", "Weergave resetten");
		button.textContent = "↺";
		button.addEventListener("click", () => {
			pinnedItem.value = null;
			hoveredPointItem.value = null;
			hoveredClusterItem.value = null;
			selectedTopicFilter.value = null;
			emit("select-cluster", null);
			mapInstance.flyTo({ center: initialCenter, zoom: 3, duration: 600 });
		});
		container.appendChild(button);
		this.container = container;
		return container;
	}

	onRemove(): void {
		this.container?.remove();
		this.container = null;
	}

	getDefaultPosition(): string {
		return "bottom-right";
	}
}

type FetchStatus = "loading" | "ready" | "error";
const status = ref<FetchStatus>("loading");
const mapEl = ref<HTMLDivElement | null>(null);

// Hover komt uit twee onafhankelijke bronnen (deck.gl's GPU-picking voor
// punten, MapLibre's queryRenderedFeatures voor hullen/labels) -- een punt
// onder de cursor wint altijd van een cluster (net als bij PlenairMap.vue's
// hit-test-volgorde, waar de kleinste/dichtstbijzijnde trefkans voorrang
// kreeg). Pin overschrijft hover, net als in PlenairMap.vue.
const hoveredPointItem = ref<DeckPoint | null>(null);
const hoveredClusterItem = ref<ClusterHullItem | null>(null);
const hoveredItem = computed<DisplayItem | null>(() =>
	hoveredPointItem.value ? { type: "point", data: hoveredPointItem.value } : hoveredClusterItem.value ? { type: "cluster", data: hoveredClusterItem.value } : null,
);
const pinnedItem = ref<DisplayItem | null>(null);
const activeDisplayItem = computed<DisplayItem | null>(() => pinnedItem.value ?? hoveredItem.value);
const isPinned = computed(() => pinnedItem.value != null);

const activePointVideo = computed<{ href: string; isInternal: boolean } | null>(() => {
	if (activeDisplayItem.value?.type !== "point") return null;
	const { video } = activeDisplayItem.value.data;
	// Site-relatief ("/debatten/{id}/", onze eigen videospeler-pagina) i.p.v.
	// absoluut (externe Debat Direct-URL) -- zie DeckPoint.video hierboven.
	return video ? { href: video, isInternal: video.startsWith("/") } : null;
});

// Topics zonder live telling (i.t.t. PlenairMap.vue's topicCounts): die telt
// over ALLE punten, die hier nooit allemaal tegelijk in het geheugen zitten
// (ze komen per tile/zoomniveau binnen via deck.gl's TileLayer, niet als één
// platte lijst zoals bij PlenairMap.vue) -- vandaar de vaste domeinlijst i.p.v.
// een berekende.
const TOPIC_FILTER_OPTIONS = Object.keys(TOPIC_COLOR);
const selectedTopicFilter = ref<string | null>(null);

// cluster_id -> volledig ClusterHullItem, voor de klik-/hoverhandlers op de
// hulls/labels-MapLibre-laag (die zelf alleen cluster_id in de
// feature-properties dragen, zie buildClusterGeoJSON()).
let clustersById = new Map<number, ClusterHullItem>();
let initialCenter: [number, number] = [0, 0];

let map: maplibregl.Map | null = null;
let deckOverlay: MapboxOverlay | null = null;
let pmtiles: PMTiles | null = null;

const isDark = useTheme();

// pmtiles://-protocol is proces-breed (maplibregl.addProtocol), niet per
// component-instantie -- dubbel registreren bij een tweede mount (bv.
// Astro view-transition) zou een harmloze maar overbodige herregistratie
// zijn, dit voorkomt dat.
let protocolRegistered = false;
function ensurePmtilesProtocol() {
	if (protocolRegistered) return;
	maplibregl.addProtocol("pmtiles", new Protocol().tile);
	protocolRegistered = true;
}

const THEME_COLOR = {
	light: { bg: "#f7f3ea", muted: "#6f6558" },
	dark: { bg: "#221f1b", muted: "#a89e8c" },
};

// Rechthoekig, wit vlak achter elke clusterlabel, met een zachte
// (canvas-blur) rand i.p.v. een harde rechthoek. Nog steeds een negen-slice-
// sprite (stretchX/stretchY/content, zie map.addImage() hieronder) zodat
// icon-text-fit 'm naar elke tekstbbox uitrekt -- het platte, onvervaagde
// binnenste stuk (ver genoeg van de rand af dat de blur er niet meer komt) is
// het stretch-/content-gebied; de vervaagde rand eromheen wordt mee-uitgerekt
// als zachte schaduw/gloed.
const LABEL_BG_IMAGE_ID = "label-bg";
// Een échte backdrop-blur (het kaartbeeld ACHTER het label vervagen, "matglas"-
// stijl) kent MapLibre/deck.gl niet -- er is geen per-rechthoek backdrop-filter
// in deze renderpijplijn, dat zou een eigen WebGL-nabewerkingspass vergen. Een
// vervaagde rand op de rechthoek zelf (eerder geprobeerd) gaf i.p.v. een
// nette box een vage waas. Gewoon een scherpe rechthoek, geen blur.
function createLabelBackgroundImage(): { width: number; height: number; data: Uint8ClampedArray } {
	const size = 12;
	const inset = 2;
	const canvas = document.createElement("canvas");
	canvas.width = size;
	canvas.height = size;
	const ctx = canvas.getContext("2d");
	if (!ctx) return { width: size, height: size, data: new Uint8ClampedArray(size * size * 4).fill(255) };
	ctx.fillStyle = "#fff";
	ctx.beginPath();
	ctx.roundRect(inset, inset, size - inset * 2, size - inset * 2, 3);
	ctx.fill();
	return { width: size, height: size, data: ctx.getImageData(0, 0, size, size).data };
}
// Veilige zone binnenin om te stretchen/tekst op te plaatsen -- zie
// createLabelBackgroundImage().
const LABEL_BG_STRETCH: [number, number] = [4, 8];
const LABEL_BG_CONTENT: [number, number, number, number] = [4, 4, 8, 8];

// luma.gl v9's Parameters-vorm (WebGPU-stijl, losse src/dst/operation per
// kanaalgroep) i.p.v. het oude WebGL1 blendFunc()/blendEquation()-paar --
// zie node_modules/@luma.gl/core/dist/adapter/types/parameters.d.ts.
// Cruciaal: alleen blendColor* overschrijven, blendAlpha* met rust laten op
// deck.gl's eigen default (normale over-compositing). Een eerdere versie
// hiervan zette ook het alpha-kanaal op "dst * 0" (multiply-i.p.v.-optellen)
// -- op deck.gl's eigen, aanvankelijk volledig transparante canvas (alpha=0)
// blijft alles-maal-nul voor altijd nul, dus er verscheen structureel nooit
// een zichtbaar punt (alpha=0 op het samengestelde beeld). Puur de
// kleurkanalen vermenigvuldigen/max'en, alpha gewoon normaal laten opbouwen,
// lost dat op.
const BLEND_PARAMETERS = {
	// "Inkt"-multiply (result = src * dst): dichtheid moet zichtbaar donkerder
	// worden, niet enkel dekkender -- gewone alpha-over-compositing gaf daarvoor
	// geen enkel signaal meer (een paar overlappende punten waren al vlak
	// dekkend, dus de hele puntenwolk werd één plat beige vlak, dicht of dun).
	// De eerdere multiply-poging sloeg juist te snel om naar zwart, omdat het
	// de volledig verzadigde puntkleur multiplyde: multiply gebruikt geen alpha
	// (die factor komt in deze formule niet voor), dus een lagere
	// zoom-afhankelijke alpha had daar domweg geen effect op. De kleur zelf
	// lichter maken (richting wit mixen, zie `tintTowardsWhite()`) is wat een
	// multiply-blend WEL hoort: één punt verkleurt de achtergrond dan nauwelijks,
	// pas veel overlappende punten bouwen zichtbare, geleidelijke verdonkering op.
	light: { blend: true, blendColorOperation: "add", blendColorSrcFactor: "dst", blendColorDstFactor: "zero" },
	// Benadering van "screen"-blending op een donkere achtergrond (echte screen-
	// formule (1-(1-src)(1-dst)) kent geen simpele blendFunc-vorm). Eerst
	// geprobeerd met additive blending (operation "add", src/dst "src-alpha"/"one")
	// -- bleek bij deze puntdichtheid meteen naar egaal wit te verzadigen (elke
	// overlap telt op, geen bovengrens). "max" i.p.v. "add" als operation neemt
	// per pixel gewoon het lichtste punt, geen optelling -- geeft wel een
	// gloei-indruk bij overlap, zonder ooit uit te slaan naar wit.
	dark: { blend: true, blendColorOperation: "max", blendColorSrcFactor: "one", blendColorDstFactor: "one" },
};

function hexToRgb(hex: string): [number, number, number] {
	return [parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16), parseInt(hex.slice(5, 7), 16)];
}

// Voor de lichte-thema multiply-blend (zie BLEND_PARAMETERS.light): mixt een
// kleur naar wit met sterkte `strength` (0 = wit, dus multiply laat de
// achtergrond ongemoeid; 1 = volledig verzadigde kleur). Voor het donkere
// thema (max-blend) is dit niet nodig -- daar mag de kleur altijd vol
// verzadigd zijn, dus strength=1 daar.
function tintTowardsWhite([r, g, b]: [number, number, number], strength: number): [number, number, number, number] {
	const mix = (channel: number) => Math.round(255 * (1 - strength) + channel * strength);
	return [mix(r), mix(g), mix(b), 255];
}

// Voor de topic-legenda-filter (dempt niet-matchende punten, PlenairMap.vue's
// gedrag): de "dempingsrichting" hangt af van de blend-modus, niet enkel van
// alpha verlagen -- alpha doet in beide BLEND_PARAMETERS-modi niets voor de
// kleurkanalen (zie de toelichting daar). Licht thema (multiply): dempen
// betekent richting wit mixen, zoals tintTowardsWhite hierboven al doet voor
// zoom-afhankelijke verzadiging. Donker thema (max): richting wit mixen zou
// juist het OMGEKEERDE effect geven -- wit wint een max-vergelijking altijd,
// dus een "gedempt" punt zou dan als felst opvallen i.p.v. wegvallen. Daar
// moet dempen dus richting zwart (de achtergrond) mixen.
function dimColor([r, g, b, a]: [number, number, number, number], dark: boolean, amount: number): [number, number, number, number] {
	const target = dark ? 0 : 255;
	const mix = (channel: number) => Math.round(channel + (target - channel) * amount);
	return [mix(r), mix(g), mix(b), a];
}

function topicColorRgba(topic: string, strength: number): [number, number, number, number] {
	const hex = TOPIC_COLOR[topic] ?? DEFAULT_TOPIC_COLOR;
	return tintTowardsWhite(hexToRgb(hex), strength);
}

// Punten zonder cluster vallen terug op dezelfde neutrale kleur als een
// onbekend topic, i.p.v. een willekeurige hue -- `-1` is DBSCAN's eigen
// "noise"-waarde (zie pipeline/plenary_map/cluster.py) en komt zo vaak voor
// dat een losse hue ervoor de hele puntenwolk in die ene kleur zou zetten.
function clusterPointColorRgba(cluster: number | null, strength: number): [number, number, number, number] {
	if (cluster === null || cluster === -1) return tintTowardsWhite(hexToRgb(DEFAULT_TOPIC_COLOR), strength);
	return tintTowardsWhite(clusterColorRgb(cluster), strength);
}

function partyPointColorRgba(party: string, strength: number): [number, number, number, number] {
	if (!party) return tintTowardsWhite(hexToRgb(DEFAULT_TOPIC_COLOR), strength);
	return tintTowardsWhite(partyColorRgb(party), strength);
}

function yearPointColorRgba(year: number | null, strength: number): [number, number, number, number] {
	if (year === null) return tintTowardsWhite(hexToRgb(DEFAULT_TOPIC_COLOR), strength);
	return tintTowardsWhite(yearColorRgb(year), strength);
}

function pointColorRgba(point: DeckPoint, strength: number): [number, number, number, number] {
	switch (colorBy.value) {
		case "cluster":
			return clusterPointColorRgba(point.cluster, strength);
		case "party":
			return partyPointColorRgba(point.party, strength);
		case "year":
			return yearPointColorRgba(point.year, strength);
		default:
			return topicColorRgba(point.topic, strength);
	}
}

// Shoelace-formule (absolute waarde): oppervlakte van een polygon-ring in
// dezelfde eenheden als de coördinaten zelf (hier: ruwe UMAP-ruimte).
function polygonArea(ring: [number, number][]): number {
	let sum = 0;
	for (let i = 0; i < ring.length; i++) {
		const [x1, y1] = ring[i];
		const [x2, y2] = ring[(i + 1) % ring.length];
		sum += x1 * y2 - x2 * y1;
	}
	return Math.abs(sum) / 2;
}

// De UMAP-bounding-box-center (Mercator [0,0], zie tiledMapTransform.ts) is
// per definitie het midden van de bounding box, niet van de puntenwolk zelf
// -- een UMAP-embedding is typisch een onregelmatige klodder, niet symmetrisch
// binnen zijn eigen bbox, dus [0,0] als startcentrum liet de kaart bij het
// laden duidelijk uit het midden staan. Een oppervlakte-gewogen gemiddelde
// van de cluster-centroids (grotere/dichtere clusters wegen zwaarder mee dan
// kleine) benadert het echte visuele zwaartepunt van de data veel beter,
// zonder dat de pipeline een aparte centroid hoeft weg te schrijven.
function weightedDataCentroid(clusters: ClusterHullItem[]): [number, number] {
	let sumX = 0;
	let sumY = 0;
	let sumWeight = 0;
	for (const cluster of clusters) {
		const weight = cluster.hull && cluster.hull.length > 2 ? polygonArea(cluster.hull) : 0;
		if (weight <= 0) continue;
		sumX += cluster.centroid[0] * weight;
		sumY += cluster.centroid[1] * weight;
		sumWeight += weight;
	}
	if (sumWeight > 0) return [sumX / sumWeight, sumY / sumWeight];
	// Fallback: geen (bruikbare) hullen -- simpel gemiddelde van de centroids.
	if (clusters.length > 0) {
		const [cx, cy] = clusters.reduce(([ax, ay], c) => [ax + c.centroid[0], ay + c.centroid[1]], [0, 0]);
		return [cx / clusters.length, cy / clusters.length];
	}
	return [0, 0];
}

// Hoe eerder (lager) een label pas vanaf welke zoom mag verschijnen, gebaseerd
// op de RANG van zijn PUNTENAANTAL (cluster.size) t.o.v. alle andere clusters
// (niet de absolute waarde -- die is vaak sterk scheefverdeeld door een paar
// uitschieters, wat de meeste clusters dan allemaal naar dezelfde
// (hoge) drempel zou duwen). Eerder op hull-oppervlakte gesorteerd, maar een
// kleine/nichetopic (bv. "geitenhouderij") kan een geografisch verspreide
// (dus grote) hull hebben terwijl het maar weinig punten bevat -- die
// verscheen daardoor al op zoom 3. Puntenaantal is de betere maat voor
// "grote cluster". Grootste cluster (rang 0) is altijd zichtbaar; de
// kleinste pas kort voor de fijnste zoom -- zo verschijnen bij uitzoomen
// enkel de grote clusters, en komen kleinere pas in beeld bij inzoomen.
function computeLabelMinZooms(clusters: ClusterHullItem[], grid: GridMetadata): Map<ClusterHullItem, number> {
	const sizes = clusters.map((c) => c.size ?? 0);
	const order = clusters.map((_, i) => i).sort((a, b) => sizes[b] - sizes[a]);
	// Volle zoomrange (niet slechts 60% ervan) en een sqrt-curve i.p.v. lineair:
	// sqrt(percentile) ligt vóór 1.0 boven de lineaire lijn, dus de meeste
	// (midden- en kleinere) clusters krijgen een HOGERE (latere) minzoom dan
	// lineair zou geven -- minder labels op lagere zoomniveaus (zoom 3 toonde
	// hiervoor al ~60% van alle clusters, veel te veel). Alleen de allergrootste
	// clusters (percentile dicht bij 0) blijven vanaf het begin zichtbaar.
	const zoomSpan = grid.maxzoom - grid.minzoom;
	const minZooms = new Map<ClusterHullItem, number>();
	order.forEach((clusterIdx, rank) => {
		const percentile = order.length > 1 ? rank / (order.length - 1) : 0;
		minZooms.set(clusters[clusterIdx], grid.minzoom + Math.sqrt(percentile) * zoomSpan);
	});
	return minZooms;
}

function buildClusterGeoJSON(clusters: ClusterHullItem[], grid: GridMetadata) {
	const hullFeatures: GeoJSON.Feature[] = [];
	const labelFeatures: GeoJSON.Feature[] = [];
	const labelMinZooms = computeLabelMinZooms(clusters, grid);
	for (const cluster of clusters) {
		if (cluster.hull && cluster.hull.length > 2) {
			const corners = cluster.hull.map(([hx, hy]) => mercatorMetersToLngLat(...umapToMercator(hx, hy, grid)));
			// Vloeiende hullen i.p.v. hoekige polygonen (zie smoothClosedRing()) --
			// een centripetale Catmull-Rom-spline door de originele hoekpunten.
			const ring = smoothClosedRing(corners);
			ring.push(ring[0]);
			hullFeatures.push({
				type: "Feature",
				// cluster_id: enige veld dat de klik-/hoverhandlers op de hulls-laag
				// nodig hebben (zie findClusterIdAtPoint()) -- de rest van de info
				// (size/terms/...) komt via clustersById, niet dubbel in de GeoJSON.
				properties: { name: cluster.name, cluster_id: cluster.cluster_id },
				geometry: { type: "Polygon", coordinates: [ring] },
			});
		}
		labelFeatures.push({
			type: "Feature",
			properties: { name: cluster.name, cluster_id: cluster.cluster_id, minzoom: labelMinZooms.get(cluster) ?? grid.minzoom },
			geometry: { type: "Point", coordinates: mercatorMetersToLngLat(...umapToMercator(cluster.centroid[0], cluster.centroid[1], grid)) },
		});
	}
	return {
		hulls: { type: "FeatureCollection", features: hullFeatures } as GeoJSON.FeatureCollection,
		labels: { type: "FeatureCollection", features: labelFeatures } as GeoJSON.FeatureCollection,
	};
}

// `published_at` is een ISO-datumstring ("YYYY-MM-DD..."); alleen het
// jaartal (eerste 4 tekens) is nodig voor de "kleur op jaar"-gradient.
function parseYear(publishedAt: unknown): number | null {
	const year = parseInt(String(publishedAt ?? "").slice(0, 4), 10);
	return Number.isNaN(year) ? null : year;
}

// deck.gl's TileLayer kent geen pmtiles-protocol (dat is puur een MapLibre-
// plugin) -- per opgevraagde (z,x,y) zelf de tegelbytes ophalen uit de al
// open PMTiles-instantie en decoderen, zelfde aanpak als de vroegere
// v1-canvasrenderer's `loadTile()`.
async function getTileData({ index }: { index: TileIndex }): Promise<DeckPoint[]> {
	if (!pmtiles) return [];
	const result = await pmtiles.getZxy(index.z, index.x, index.y);
	if (!result) return [];
	const vt = new VectorTile(new PbfReader(new Uint8Array(result.data)));
	const layer = vt.layers.points;
	if (!layer) return [];
	const bounds = tileBoundsMeters(index);
	const points: DeckPoint[] = [];
	for (let i = 0; i < layer.length; i++) {
		const feature = layer.feature(i);
		const [[pt]] = feature.loadGeometry();
		const position = tileLocalToLngLat(pt.x, pt.y, feature.extent, bounds);
		const p = feature.properties as Record<string, unknown>;
		points.push({
			id: typeof p.id === "number" ? p.id : -1,
			position,
			topic: String(p.topic ?? ""),
			actor: String(p.actor ?? ""),
			party: String(p.party ?? ""),
			debate: String(p.debate ?? ""),
			text: String(p.text ?? ""),
			publishedAt: String(p.published_at ?? ""),
			cluster: typeof p.cluster === "number" ? p.cluster : null,
			year: parseYear(p.published_at),
			video: typeof p.video === "string" && p.video ? p.video : null,
		});
	}
	return points;
}

function buildPointsLayer(grid: GridMetadata): TileLayer {
	return new TileLayer<DeckPoint[]>({
		id: "plenair-points",
		// Interleaved (zie MapboxOverlay hieronder): plaatst deze laag in
		// MapLibre's eigen tekenvolgorde, vlak voor de "labels"-laag (dus na
		// bg+hulls, onder de clusternaam-labels).
		beforeId: "labels",
		getTileData,
		minZoom: grid.minzoom,
		maxZoom: grid.maxzoom,
		tileSize: grid.tile_size,
		// TileLayer zelf vergelijkt `renderSubLayers` (een functie) niet op
		// waarde -- alleen updateTriggers/data-wijzigingen leiden tot een
		// updateState()-run die de per-tile sublaag-cache leegmaakt (zie
		// node_modules/@deck.gl/geo-layers/src/tile-layer/tile-layer.ts:
		// updateState() went alleen `tile.layers = null` als propsChanged, en
		// een nieuwe renderSubLayers-closure alléén telt daar NIET als
		// "propsChanged"). Zonder deze updateTriggers hier (op de TileLayer
		// zelf, niet enkel op de ScatterplotLayer die renderSubLayers teruggeeft)
		// bleven alle al geladen tiles domweg hun oude, gecachte kleur houden
		// zodra colorBy/isDark wijzigde -- precies de "kleur op"-knop deed
		// niets-bug.
		updateTriggers: { renderSubLayers: [colorBy.value, isDark.value, selectedTopicFilter.value] },
		renderSubLayers: (subProps) => {
			const zoom = subProps.tile.index.z;
			// Zoom-fractie (0 op het grofste niveau, 1 op het fijnste) -- stuurt
			// zowel de puntgrootte als de dekking. Op het grofste niveau liggen
			// veel meer punten per tile (zie thin_zoom_points_globally()), dus
			// kleiner én transparanter houdt dat overzichtelijk; op het fijnste
			// niveau, met veel minder punten per tile, mogen ze groter en
			// dekkender.
			const t = grid.maxzoom > grid.minzoom ? (zoom - grid.minzoom) / (grid.maxzoom - grid.minzoom) : 0;
			const radius = 0.6 + t * (3.5 - 0.6);
			// Lichte thema (multiply-blend, zie BLEND_PARAMETERS.light): hoe minder
			// verzadigd (dichter naar wit) de puntkleur zelf is, hoe minder één punt
			// de achtergrond verdonkert -- pas veel overlappende punten (hoge
			// dichtheid) bouwen dan zichtbare verdonkering/kleur op. Op het grofste
			// niveau liggen veel meer punten per tile (thin_zoom_points_globally()),
			// dus daar moet een enkel punt haast onzichtbaar zijn; op het fijnste
			// niveau, met veel minder overlap, mag de kleur bijna vol verzadigd zijn.
			// Donkere thema (max-blend) verdonkert nooit vanzelf, dus daar altijd
			// vol verzadigd.
			const colorStrength = isDark.value ? 1 : 0.12 + t * (0.55 - 0.12);
			const topicFilter = selectedTopicFilter.value;
			// Niet-matchende punten sterk dempen i.p.v. eruit filteren (net als
			// PlenairMap.vue's topic-legenda-filter, issue #186) -- via dimColor()
			// i.p.v. gewoon een lagere `strength`, want de dempingsrichting moet
			// per blend-modus omgekeerd zijn (zie dimColor()'s toelichting).
			const colorFor = (d: DeckPoint) => {
				const color = pointColorRgba(d, colorStrength);
				return topicFilter && d.topic !== topicFilter ? dimColor(color, isDark.value, 0.85) : color;
			};
			return [
				new ScatterplotLayer<DeckPoint>({
					id: `${subProps.id}-scatter`,
					data: subProps.data,
					getPosition: (d) => d.position,
					getFillColor: colorFor,
					// colorBy/isDark/topicFilter zijn Vue-refs buiten deck.gl's eigen
					// reactiviteit -- zonder updateTriggers herkent TileLayer's tile-cache
					// niet dat een eerder gegenereerde sublaag opnieuw moet kleuren (issue
					// #259: de "Kleur op"-knoppen deden zichtbaar niets zolang er geen
					// nieuwe tiles werden geladen).
					updateTriggers: { getFillColor: [colorBy.value, colorStrength, topicFilter] },
					getRadius: radius,
					radiusUnits: "pixels",
					// Niet zelf pickable: de onzichtbare hit-target-laag hieronder
					// verzorgt de picking, met een veel ruimere trefzone. Anders
					// wisselt de cursor bij elke muisbeweging in dichte gebieden
					// grillig tussen pointer/normaal, omdat het picking-doel dan
					// exact zo klein is als de getekende stip (soms <1px).
					pickable: false,
					parameters: isDark.value ? BLEND_PARAMETERS.dark : BLEND_PARAMETERS.light,
				}),
				new ScatterplotLayer<DeckPoint>({
					id: `${subProps.id}-hit-target`,
					data: subProps.data,
					getPosition: (d) => d.position,
					getFillColor: [0, 0, 0, 0],
					// Zelfde trefzone-gedachte als PlenairMap.vue's 12px hit-tolerance
					// (findNearestPoint()) -- een vaste, ruimere pixelradius dan het
					// zichtbare punt zelf, zodat hoveren/klikken niet pixel-precies moet.
					getRadius: 6,
					radiusUnits: "pixels",
					radiusMinPixels: 6,
					pickable: true,
					// Geen custom blend-parameters: deck.gl's picking-pass gebruikt sowieso
					// een eigen, ondoorzichtige kleurcodering los van wat hier zichtbaar
					// getekend wordt -- gewone alpha-blending (default) houdt deze laag
					// dus onzichtbaar (alpha=0) zonder de picking te beïnvloeden.
				}),
			];
		},
	});
}

onMounted(async () => {
	ensurePmtilesProtocol();
	try {
		// -full-bestanden (issue #293/#259: de volle dataset is nu de
		// standaard, niet de kleine steekproef) -- clusters.levels hoort bij
		// die volle run, staat niet in de kleine jsDelivr-databasis, dus ook
		// die fetch gaat via tilesBaseUrl (HF).
		const [gridResponse, clustersResponse] = await Promise.all([
			fetch(`${props.tilesBaseUrl}/plenair-map-full-grid.json`),
			fetch(`${props.tilesBaseUrl}/plenair-map-clusters-full.json`).catch(() => null),
		]);
		if (!gridResponse.ok) throw new Error(`Status ${gridResponse.status}`);
		const grid: GridMetadata = await gridResponse.json();

		let hulls: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };
		let labels: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };
		if (clustersResponse && clustersResponse.ok) {
			const clusters = await clustersResponse.json();
			// Twee mogelijke vormen: het oude vaste coarse/fine-formaat
			// (plenair-map-clusters.json) of het nieuwe N-laagse formaat
			// (plenair-map-clusters-full.json, alleen een "levels"-array) --
			// in beide gevallen tonen we hier het grofste niveau. De twee niveaus
			// in "levels" zijn voor deze dataset momenteel identiek verdeeld (zelfde
			// 390 clusters, zelfde groottes) -- een echte coarse/fine-zoomwissel
			// zoals PlenairMap.vue die heeft, is dus nog niet zinvol te bouwen totdat
			// de pipeline daadwerkelijk verschillende granulariteiten produceert.
			const raw: ClusterHullItem[] = Array.isArray(clusters) ? clusters : (clusters.levels?.[0] ?? clusters.coarse ?? []);
			({ hulls, labels } = buildClusterGeoJSON(raw, grid));
			clustersById = new Map(raw.map((c) => [c.cluster_id, c]));
			const [cx, cy] = weightedDataCentroid(raw);
			initialCenter = mercatorMetersToLngLat(...umapToMercator(cx, cy, grid));
		}

		if (!mapEl.value) return;
		pmtiles = new PMTiles(`${props.tilesBaseUrl}/plenair-map-full.pmtiles`);

		const theme = isDark.value ? THEME_COLOR.dark : THEME_COLOR.light;
		map = new maplibregl.Map({
			container: mapEl.value,
			style: {
				version: 8,
				// Nodig voor de cluster-naam-labels hieronder (symbol-layer met
				// text-field vereist een glyphs-bron) -- MapLibre's eigen publieke
				// demo-fontendpoint, geen eigen fontserver nodig voor deze paar
				// Latijnse labels.
				glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
				sources: {
					hulls: { type: "geojson", data: hulls },
					labels: { type: "geojson", data: labels },
				},
				layers: [
					{ id: "bg", type: "background", paint: { "background-color": theme.bg } },
					{ id: "hulls", type: "line", source: "hulls", paint: { "line-color": theme.muted, "line-width": 1 } },
					{
						id: "labels",
						type: "symbol",
						source: "labels",
						// Toon een label pas vanaf zijn eigen minzoom (computeLabelMinZooms()
						// hierboven, op basis van hull-oppervlakte-rang): bij uitzoomen
						// alleen de grote clusters, bij inzoomen komen kleinere erbij.
						// ["zoom"] mag in filters (MapLibre-stijlspec, sectie "expressions").
						filter: ["<=", ["get", "minzoom"], ["zoom"]],
						layout: {
							"text-field": ["get", "name"],
							"text-font": ["Noto Sans Regular"],
							"text-size": 13,
							"text-anchor": "top",
							"text-allow-overlap": false,
							// Grotere clusters (lagere minzoom) winnen de overlap-competitie --
							// een lagere sort-key betekent hogere prioriteit bij MapLibre's
							// collision-detectie, en minzoom is precies zo opgebouwd (grootste
							// cluster = laagste minzoom). Vooral relevant bínnen één
							// zoomniveau; het minzoom-filter hierboven doet het meeste werk.
							"symbol-sort-key": ["coalesce", ["get", "minzoom"], 0],
							// Rechthoekige achtergrond achter elk label: een stretchbare
							// sprite (LABEL_BG_IMAGE_ID, hieronder via map.addImage()
							// geregistreerd) die icon-text-fit automatisch om de
							// tekstbbox past, inclusief marge via icon-text-fit-padding.
							"icon-image": LABEL_BG_IMAGE_ID,
							"icon-text-fit": "both",
							"icon-text-fit-padding": [2, 4, 2, 4],
							"icon-allow-overlap": false,
						},
						// Zwart, ongeacht thema: de labelachtergrond is altijd een wit
						// vlak (createLabelBackgroundImage()), dus zwarte tekst blijft in
						// beide thema's leesbaar -- de vroegere thema-afhankelijke
						// gedempte tekstkleur (theme.muted) had op die lichte achtergrond
						// te weinig contrast. Ondoorzichtig (icon-opacity 1) i.p.v. 0,55:
						// bij die lagere opacity scheen de kleurrijke puntenwolk erdoorheen
						// en werd het vlak op de donkere achtergrond een grijzige waas --
						// precies het "onleesbaar"-effect. text-halo als vangnet voor het
						// geval de sprite een lang label niet volledig dekt.
						paint: {
							"text-color": "#000000",
							"text-halo-color": "#ffffff",
							"text-halo-width": 1.5,
							"icon-opacity": 1,
						},
					},
				],
			},
			center: initialCenter,
			zoom: 3,
			minZoom: grid.minzoom,
			maxZoom: grid.maxzoom,
			attributionControl: false,
		});
		map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
		map.addControl(new ResetViewControl(), "bottom-right");
		map.addControl(new ColorByControl(), "top-left");
		const labelBg = createLabelBackgroundImage();
		map.addImage(LABEL_BG_IMAGE_ID, labelBg, { stretchX: [LABEL_BG_STRETCH], stretchY: [LABEL_BG_STRETCH], content: LABEL_BG_CONTENT });

		// deck.gl's onClick hieronder zet dit vlak vóór het MapLibre "click"-event
		// hieronder synchroon afgaat (zelfde klik, interleaved deelt de
		// event-bus) -- ruim genoeg venster om "was dit net al een puntklik" te
		// onderscheiden zonder daar ook nog een cluster bovenop te pinnen.
		let lastPointClickAt = 0;
		deckOverlay = new MapboxOverlay({
			// Interleaved i.p.v. overlaid: deck.gl tekent dan in MapLibre's eigen
			// WebGL-context/framebuffer, dus de blend-`dst` in BLEND_PARAMETERS is
			// het echte kaartbeeld (bg-kleur/hullen) i.p.v. een eigen, aanvankelijk
			// volledig transparante deck-canvas. Dat laatste was de kern van de
			// "punten zijn zwart in het lichte thema"-bug: multiply tegen
			// transparant-zwart geeft altijd zwart, ongeacht puntkleur.
			interleaved: true,
			layers: [buildPointsLayer(grid)],
			getTooltip: () => null,
			onHover: (info) => {
				hoveredPointItem.value = (info.object as DeckPoint | undefined) ?? null;
				updateCursor();
			},
			// Puntklik wint van een eventuele cluster op dezelfde plek (zie
			// map.on("click", ...) hieronder, dat dit via lastPointClickAt checkt) --
			// zelfde volgorde als de hover-precedentie hierboven.
			onClick: (info) => {
				if (info.object) {
					pinnedItem.value = { type: "point", data: info.object as DeckPoint };
					lastPointClickAt = performance.now();
				}
			},
		});
		map.addControl(deckOverlay);

		// cluster_id -> ClusterHullItem via de hulls/labels-features onder de
		// cursor/klik (queryRenderedFeatures, MapLibre's eigen GPU-picking) --
		// geen eigen contour-afstandsberekening nodig zoals bij PlenairMap.vue.
		function findClusterAtPoint(point: maplibregl.PointLike): ClusterHullItem | null {
			if (!map) return null;
			const features = map.queryRenderedFeatures(point, { layers: ["hulls", "labels"] });
			const clusterId = features[0]?.properties?.cluster_id;
			return typeof clusterId === "number" ? (clustersById.get(clusterId) ?? null) : null;
		}

		// Eén plek die de cursor daadwerkelijk zet, vanuit de gecombineerde
		// hover-state (punt EN cluster) -- niet los vanuit zowel deck.gl's
		// onHover hierboven als deze mousemove-handler elk voor zich. Die twee
		// draaien via dezelfde onderliggende "mousemove"-events (interleaved
		// deelt de event-bus), en schreven voorheen allebei onafhankelijk naar
		// canvas.style.cursor -- bij welke van de twee toevallig als laatste
		// afging "won", wat de cursor bij een puntenmassa liet knipperen tussen
		// pointer en MapLibre's eigen "grab"-cursor (de kaart is zelf ook
		// sleepbaar). Eén functie die altijd de VOLLEDIGE huidige status leest,
		// voorkomt dat gedeeltelijke updates elkaar tegenspreken.
		// Tijdens het slepen van de kaart moet MapLibre's eigen "grabbing"-cursor
		// gewoon zichtbaar blijven (niet overschreven door een pointer die nog van
		// vóór de drag stamt); zodra de drag stopt, wil de gebruiker weer een
		// vinger zien als er op dat moment iets onder de cursor zit -- niet
		// MapLibre's eigen "grab"-reset, die zonder deze vlag als laatste zou
		// schrijven en de pointer-cursor zou overschrijven.
		let isDragging = false;
		function updateCursor() {
			if (!map || isDragging) return;
			map.getCanvas().style.cursor = hoveredPointItem.value || hoveredClusterItem.value ? "pointer" : "";
		}
		map.on("dragstart", () => {
			isDragging = true;
		});
		map.on("dragend", () => {
			isDragging = false;
			updateCursor();
		});

		map.on("mousemove", (e) => {
			// Een punt onder de cursor (deck.gl's onHover hierboven) wint altijd --
			// alleen als er GEEN punt geraakt is, tellen hullen/labels mee.
			if (hoveredPointItem.value) return;
			hoveredClusterItem.value = findClusterAtPoint(e.point);
			updateCursor();
		});
		map.on("mouseleave", "hulls", () => {
			hoveredClusterItem.value = null;
			updateCursor();
		});

		map.on("click", (e) => {
			if (performance.now() - lastPointClickAt < 50) return;
			const cluster = findClusterAtPoint(e.point);
			if (cluster) {
				pinnedItem.value = { type: "cluster", data: cluster };
				emit("select-cluster", cluster.cluster_id);
				return;
			}
			// Klik op lege ruimte: unpin (PlenairMap.vue's gedrag).
			if (pinnedItem.value) {
				pinnedItem.value = null;
				emit("select-cluster", null);
			}
		});

		map.on("load", () => {
			status.value = "ready";
		});
		map.on("error", (e: maplibregl.ErrorEvent) => {
			console.error("TiledPlenairMap MapLibre error", e.error);
			status.value = "error";
		});

		watch(isDark, (dark) => {
			if (!map || !deckOverlay) return;
			const t = dark ? THEME_COLOR.dark : THEME_COLOR.light;
			map.setPaintProperty("bg", "background-color", t.bg);
			map.setPaintProperty("hulls", "line-color", t.muted);
			deckOverlay.setProps({ layers: [buildPointsLayer(grid)] });
		});
		watch(colorBy, () => {
			if (!deckOverlay) return;
			deckOverlay.setProps({ layers: [buildPointsLayer(grid)] });
		});
		watch(selectedTopicFilter, () => {
			if (!deckOverlay) return;
			deckOverlay.setProps({ layers: [buildPointsLayer(grid)] });
		});
	} catch (err) {
		console.error("TiledPlenairMap init failed", err);
		status.value = "error";
	}
});

onUnmounted(() => {
	map?.remove();
	map = null;
	deckOverlay = null;
});
</script>

<template>
	<div class="tiled-plenair-map">
		<p v-if="status === 'loading'">Kaart laden...</p>
		<p v-else-if="status === 'error'">Kon de kaartdata niet laden.</p>
		<!-- v-show i.p.v. v-if: mapEl moet al in de DOM staan vóórdat onMounted de
		     kaart kan aanmaken (en dus status ooit naar "ready" kan zetten) -- een
		     v-if hier zou een kip-of-ei-blokkade geven: geen mapEl zonder ready,
		     geen ready zonder mapEl. -->
		<div v-show="status === 'ready'">
			<div class="topic-legend">
				<button
					v-for="t in TOPIC_FILTER_OPTIONS"
					:key="t"
					class="legend-item"
					:class="{ active: selectedTopicFilter === t }"
					@click="selectedTopicFilter = selectedTopicFilter === t ? null : t"
					:title="`Filter op ${t}`"
				>
					<span class="legend-dot" :style="{ backgroundColor: TOPIC_COLOR[t] }"></span>
					<span class="legend-name">{{ t === "plenair" ? "overig plenair" : t }}</span>
				</button>
			</div>

			<div ref="mapEl" class="map-el" />

			<div class="map-info-panel" :class="{ 'is-pinned': isPinned }">
				<template v-if="activeDisplayItem?.type === 'point'">
					<div class="info-panel-header">
						<div class="info-speaker-line">
							<strong class="info-speaker">{{ activeDisplayItem.data.actor || "Onbekende spreker" }}</strong>
							<span v-if="activeDisplayItem.data.party" class="party-tag">{{ activeDisplayItem.data.party }}</span>
							<span v-if="activeDisplayItem.data.publishedAt" class="date-tag">
								{{ new Date(activeDisplayItem.data.publishedAt).toLocaleDateString("nl-NL") }}
							</span>
						</div>
						<div class="info-header-actions">
							<a
								v-if="activePointVideo"
								:href="activePointVideo.href"
								:target="activePointVideo.isInternal ? '_self' : '_blank'"
								rel="noopener noreferrer"
								class="video-link-btn"
								:title="activePointVideo.isInternal ? 'Bekijk in interne videospeler' : 'Bekijk spreekbeurt op Debat Direct'"
							>
								<span>{{ activePointVideo.isInternal ? "Bekijk in videospeler" : "Bekijk video" }}</span>
							</a>
							<span v-if="isPinned" class="pinned-indicator">Vastgezet</span>
							<button v-if="isPinned" class="close-info-btn" @click="pinnedItem = null" title="Sluit vastzetting" aria-label="Sluit">&times;</button>
						</div>
					</div>
					<div class="info-context-row">
						<span v-if="activeDisplayItem.data.cluster !== null && clustersById.get(activeDisplayItem.data.cluster)" class="cluster-context-badge">
							Thema: <strong>{{ clustersById.get(activeDisplayItem.data.cluster)?.name }}</strong>
						</span>
						<span v-if="activeDisplayItem.data.debate" class="debate-title-text"><em>{{ activeDisplayItem.data.debate }}</em></span>
					</div>
					<blockquote class="info-quote-text">&ldquo;{{ activeDisplayItem.data.text }}&rdquo;</blockquote>
				</template>

				<template v-else-if="activeDisplayItem?.type === 'cluster'">
					<div class="info-panel-header">
						<div class="info-cluster-title-line">
							<span
								v-if="activeDisplayItem.data.parent_name && activeDisplayItem.data.parent_name !== activeDisplayItem.data.name"
								class="cluster-breadcrumb"
							>
								{{ activeDisplayItem.data.parent_name }} &rarr;
							</span>
							<strong class="info-cluster-name">{{ activeDisplayItem.data.name }}</strong>
							<span class="cluster-size-badge">{{ activeDisplayItem.data.size }} spreekbeurten</span>
						</div>
						<div class="info-header-actions">
							<span v-if="isPinned" class="pinned-indicator">Vastgezet</span>
							<button v-if="isPinned" class="close-info-btn" @click="pinnedItem = null" title="Sluit vastzetting" aria-label="Sluit">&times;</button>
						</div>
					</div>
					<div v-if="activeDisplayItem.data.terms?.length" class="info-terms-row">
						<span class="terms-heading">Trefwoorden:</span>
						<span v-for="term in activeDisplayItem.data.terms.slice(0, 10)" :key="term" class="term-pill">{{ term }}</span>
					</div>
				</template>

				<template v-else>
					<div class="info-panel-idle">
						<span class="idle-text">Beweeg over of tik op een punt of themacontour om details te bekijken.</span>
					</div>
				</template>
			</div>
		</div>
	</div>
</template>

<style scoped>
.tiled-plenair-map {
	position: relative;
	width: 100%;
}
.map-el {
	width: 100%;
	aspect-ratio: 1.618;
	min-height: 320px;
}
/* ColorByControl's DOM wordt door MapLibre zelf in de kaart geïnjecteerd
   (buiten Vue's render tree, al wel binnen deze scoped root) -- vandaar
   :deep() voor elke regel hieronder. Overschrijft het standaard
   maplibregl-ctrl-group-knopformaat (vast vierkant voor icoon-knoppen) voor
   deze tekst-knoppen. */
:deep(.color-by-ctrl) {
	display: flex;
	overflow: hidden;
}
:deep(.color-by-ctrl-btn) {
	/* Achtergrond/tekstkleur worden bewust via inline style vanuit
	   ColorByControl's isDark-watch gezet, niet hier -- currentColor binnen
	   eenzelfde regel als een eigen `color`-override (bv. voor de actieve
	   knop) resolvet tegen de EIGEN net-berekende kleur i.p.v. de omringende
	   inkt-kleur, wat achtergrond en tekst altijd gelijk maakte (onzichtbare
	   tekst). Een CSS custom property "bevriest" die waarde niet: `var(...)`
	   wordt bij gebruik weer letterlijk `currentColor`, dus dat loste het niet
	   op. Vandaar gewoon JS met de bestaande THEME_COLOR-waarden. */
	all: unset;
	box-sizing: border-box;
	padding: 0.4rem 0.7rem;
	font-size: 0.75rem;
	line-height: 1;
	white-space: nowrap;
	cursor: pointer;
	transition: background-color 0.15s ease, color 0.15s ease;
}
:deep(.color-by-ctrl-btn + .color-by-ctrl-btn) {
	border-left: 1px solid rgba(128, 128, 128, 0.25);
}
:deep(.color-by-ctrl-btn:focus-visible) {
	outline: 2px solid rgba(128, 128, 128, 0.6);
	outline-offset: -2px;
}
.topic-legend {
	display: flex;
	flex-wrap: wrap;
	gap: 0.4rem;
	margin-bottom: 0.6rem;
}
.legend-item {
	display: inline-flex;
	align-items: center;
	gap: 0.35rem;
	padding: 0.25rem 0.6rem;
	border: 1px solid color-mix(in srgb, currentColor 20%, transparent);
	border-radius: 999px;
	background: transparent;
	font-size: 0.75rem;
	color: inherit;
	cursor: pointer;
}
.legend-item.active {
	background: color-mix(in srgb, currentColor 12%, transparent);
	border-color: currentColor;
}
.legend-dot {
	width: 0.6rem;
	height: 0.6rem;
	border-radius: 50%;
	flex: none;
}
.map-info-panel {
	margin-top: 0.6rem;
	min-height: 4.5rem;
	border: 1px solid color-mix(in srgb, currentColor 20%, transparent);
	border-radius: 0.5rem;
	padding: 0.6rem 0.8rem;
	font-size: 0.85rem;
}
.map-info-panel.is-pinned {
	border-color: currentColor;
}
.info-panel-header {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 0.75rem;
	flex-wrap: wrap;
}
.info-speaker-line,
.info-cluster-title-line {
	display: flex;
	align-items: baseline;
	gap: 0.5rem;
	flex-wrap: wrap;
}
.party-tag,
.date-tag,
.cluster-size-badge {
	font-size: 0.75rem;
	color: color-mix(in srgb, currentColor 65%, transparent);
}
.info-header-actions {
	display: flex;
	align-items: center;
	gap: 0.5rem;
}
.video-link-btn {
	font-size: 0.75rem;
	text-decoration: underline;
}
.pinned-indicator {
	font-size: 0.7rem;
	color: color-mix(in srgb, currentColor 65%, transparent);
}
.close-info-btn {
	all: unset;
	cursor: pointer;
	font-size: 1rem;
	line-height: 1;
	padding: 0 0.2rem;
}
.info-context-row {
	display: flex;
	gap: 0.75rem;
	flex-wrap: wrap;
	margin-top: 0.3rem;
	font-size: 0.75rem;
}
.cluster-context-badge {
	color: color-mix(in srgb, currentColor 75%, transparent);
}
.debate-title-text {
	color: color-mix(in srgb, currentColor 65%, transparent);
}
.info-quote-text {
	margin: 0.5rem 0 0;
	font-style: italic;
}
.cluster-breadcrumb {
	font-size: 0.75rem;
	color: color-mix(in srgb, currentColor 55%, transparent);
}
.info-terms-row {
	margin-top: 0.4rem;
	display: flex;
	flex-wrap: wrap;
	gap: 0.35rem;
	align-items: center;
}
.terms-heading {
	font-size: 0.75rem;
	color: color-mix(in srgb, currentColor 55%, transparent);
}
.term-pill {
	font-size: 0.7rem;
	padding: 0.1rem 0.5rem;
	border-radius: 999px;
	background: color-mix(in srgb, currentColor 10%, transparent);
}
.info-panel-idle .idle-text {
	color: color-mix(in srgb, currentColor 55%, transparent);
	font-size: 0.8rem;
}
</style>
