<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { scaleLinear, scaleSqrt, scaleThreshold } from "d3-scale";
import { select } from "d3-selection";
import { zoom as d3zoom, zoomIdentity, type D3ZoomEvent } from "d3-zoom";
import { useTheme } from "../lib/useTheme";

type RawExport = {
	topics: string[];
	actors: string[];
	parties: string[];
	debates: string[];
	soorten: string[];
	points: [number, number, number, number, number, number, number, number, string, string, number | null][];
};

type PlenairPoint = {
	id: number;
	x: number;
	y: number;
	topic: string;
	topicIdx: number;
	text: string;
	actor: string;
	party: string;
	activiteit_soort: string | null;
	debate_title: string | null;
	published_at: string;
	cluster: number | null;
};

type ClusterDebateItem = {
	title: string;
	count: number;
	link: { href: string; is_internal: boolean } | null;
};

type ClusterHullItem = {
	cluster_id: number;
	name: string;
	duiding?: string;
	parent_id?: number | null;
	parent_name?: string | null;
	terms?: string[];
	top_debates?: ClusterDebateItem[];
	size: number;
	centroid: [number, number];
	hull: [number, number][] | null;
	topic_breakdown: Record<string, number>;
	// contained_by_sibling is het cluster_id van het buurcluster dat deze hull
	// geometrisch omsluit (render-artefact), of null als er geen is -- geen
	// boolean. "Actief" betekent dus != null, niet === true.
	contained_by_sibling?: number | null;
	redundant_with_parent?: boolean;
};

type ClustersExport = {
	coarse: ClusterHullItem[];
	fine: ClusterHullItem[];
};

type VideoLinkInfo = {
	href: string;
	label: string;
	is_internal: boolean;
};

type ClusterLevel = "coarse" | "fine";

type DisplayItem =
	| { type: "point"; data: PlenairPoint; clusterInfo?: ClusterHullItem | null }
	| { type: "cluster"; data: ClusterHullItem; level: ClusterLevel };

const props = defineProps<{
	dataBaseUrl: string;
	selectedClusterIds?: Set<number>;
}>();

const emit = defineEmits<{
	(e: "select-cluster", clusterId: number | null): void;
}>();

type FetchStatus = "loading" | "ready" | "error";
const status = ref<FetchStatus>("loading");
const pointsData = ref<RawExport>({ topics: [], actors: [], parties: [], debates: [], soorten: [], points: [] });
const clustersData = ref<ClustersExport | ClusterHullItem[] | undefined>(undefined);
const videosData = ref<Record<number, VideoLinkInfo>>({});

onMounted(async () => {
	try {
		const [pointsResponse, clustersResponse, videosResponse] = await Promise.all([
			fetch(`${props.dataBaseUrl}/plenair-map.json`),
			fetch(`${props.dataBaseUrl}/plenair-map-clusters.json`),
			fetch(`${props.dataBaseUrl}/plenair-map-videos.json`).catch(() => null),
		]);
		if (!pointsResponse.ok) throw new Error(`Status ${pointsResponse.status}`);
		if (!clustersResponse.ok) throw new Error(`Status ${clustersResponse.status}`);
		pointsData.value = await pointsResponse.json();
		clustersData.value = await clustersResponse.json();
		if (videosResponse && videosResponse.ok) {
			videosData.value = await videosResponse.json();
		}
		status.value = "ready";
	} catch {
		status.value = "error";
	}
});

const isDark = useTheme();
const ink = computed(() => (isDark.value ? "#f2ede3" : "#221f1b"));
const muted = computed(() => (isDark.value ? "#a89e8c" : "#6f6558"));

const TOPIC_COLOR: Record<string, string> = {
	stikstof: "#4a7a4a",
	abortus: "#a64d5f",
	asiel: "#c07a2e",
	energietransitie: "#3d6e8f",
	plenair: "#a89e8c",
};

// Canvas & Viewport State
const canvasRef = ref<HTMLCanvasElement | null>(null);
const wrapperEl = ref<HTMLElement | null>(null);
const canvasWidth = ref(900);
const canvasHeight = ref(540);
const canvasAspectRatio = computed(() => (canvasHeight.value > 0 ? canvasWidth.value / canvasHeight.value : 1.618));

const zoom = ref(1);
const panX = ref(0);
const panY = ref(0);
let d3ZoomBehavior: any = null;

// Topic filter
const selectedTopicFilter = ref<string | null>(null);

// Interactive Hover & Fixed Pinned Selection
const hoveredItem = ref<DisplayItem | null>(null);
const pinnedItem = ref<DisplayItem | null>(null);
// Coarse- en fine-clusters hebben elk hun eigen id-ruimte (beide beginnen
// vanaf 0), dus een enkel getal is niet genoeg om een actief cluster te
// identificeren -- het niveau moet erbij (issue #198: coarse-selectie werd
// hierdoor onterecht tegen fine-cluster-ids van punten vergeleken).
const activeCluster = ref<{ id: number; level: ClusterLevel } | null>(null);

const activeDisplayItem = computed<DisplayItem | null>(() => pinnedItem.value || hoveredItem.value || null);
const isPinned = computed(() => pinnedItem.value != null);

const activePointVideo = computed<VideoLinkInfo | null>(() => {
	if (activeDisplayItem.value?.type !== "point") return null;
	const docId = activeDisplayItem.value.data.id;
	return videosData.value[docId] || null;
});

// Dezelfde href als activePointVideo: voor interne links wijst die al naar de
// debatpagina zelf (geen timestamp-fragment), dus bruikbaar als "bekijk
// debat"-link voor de titel-badge hieronder.
const activePointDebateLink = computed<VideoLinkInfo | null>(() => activePointVideo.value);

const hoveredPoint = computed<PlenairPoint | null>(() => {
	if (hoveredItem.value?.type === "point") return hoveredItem.value.data;
	if (pinnedItem.value?.type === "point") return pinnedItem.value.data;
	return null;
});

const hoveredCluster = computed<ClusterHullItem | null>(() => {
	if (hoveredItem.value?.type === "cluster") return hoveredItem.value.data;
	if (pinnedItem.value?.type === "cluster") return pinnedItem.value.data;
	return null;
});

const hoveredClusterLevel = computed<ClusterLevel | null>(() => {
	if (hoveredItem.value?.type === "cluster") return hoveredItem.value.level;
	if (pinnedItem.value?.type === "cluster") return pinnedItem.value.level;
	return null;
});

// Mobile & Responsive Support
const isMobile = ref(false);

function updateIsMobile() {
	if (typeof window === "undefined") return;
	isMobile.value = window.innerWidth <= 840;
}

// Grove hardware-inschatting (issue #226): desktop ging er voorheen van uit
// dat elke desktop de volle ~40k achtergrondpunten probleemloos trekt (zie
// benchmark issue #186) -- dat klopt niet voor bijv. een sober uitgeruste
// kantoor-/ambtenarenlaptop met weinig cores/geheugen en een integrated GPU.
// hardwareConcurrency/deviceMemory zijn geen perfecte proxy voor GPU-kracht,
// maar wel een goedkope, breed ondersteunde (op deviceMemory na, Safari mist
// die) heuristiek zonder dat er een canvas-benchmark bij render nodig is.
const isLowPerfDevice = ref(false);

function updateIsLowPerfDevice() {
	if (typeof navigator === "undefined") return;
	const cores = navigator.hardwareConcurrency ?? 8;
	const mem = (navigator as unknown as { deviceMemory?: number }).deviceMemory ?? 8;
	isLowPerfDevice.value = cores <= 4 || mem <= 4;
}

onMounted(() => {
	updateIsMobile();
	updateIsLowPerfDevice();
	window.addEventListener("resize", updateIsMobile);
	window.addEventListener("resize", updateCanvasDimensions);
});

onUnmounted(() => {
	window.removeEventListener("resize", updateIsMobile);
	window.removeEventListener("resize", updateCanvasDimensions);
});

function updateCanvasDimensions() {
	if (wrapperEl.value) {
		const rect = wrapperEl.value.getBoundingClientRect();
		const newW = Math.max(300, Math.round(rect.width));
		const newH = Math.max(300, isMobile.value ? 380 : 540);
		if (canvasWidth.value !== newW || canvasHeight.value !== newH) {
			canvasWidth.value = newW;
			canvasHeight.value = newH;
			triggerRender();
		}
	}
}

// -------------------------------------------------------------
// Data Normalization & Clusters
// -------------------------------------------------------------
function hullArea(hull: [number, number][] | null): number {
	if (!hull || hull.length < 3) return 0;
	let sum = 0;
	for (let i = 0; i < hull.length; i++) {
		const [x1, y1] = hull[i];
		const [x2, y2] = hull[(i + 1) % hull.length];
		sum += x1 * y2 - x2 * y1;
	}
	return Math.abs(sum) / 2;
}

const HULL_AREA_HIDE_THRESHOLD = 18;

// Vlaggen berekend in de Python-pijplijn (scripts/experiment_umap_documents.py,
// build_multilevel_clusters/label_multilevel_clusters, issue #281): "fat
// pipeline, thin client" -- topologie (redundantie/containment) wordt
// offline berekend, de client filtert hier alleen. redundant_with_parent
// dekt een kind-hull die vrijwel identiek is aan zijn ouder (geen nieuwe
// ruimtelijke info); contained_by_sibling (een cluster_id, geen boolean)
// dekt een hull die volledig binnen een ander cluster op hetzelfde niveau
// ligt (altijd een render-artefact, clusters zijn per niveau disjunct qua
// punten maar niet qua hull-geometrie). Beide zijn puur teken-filters: het
// onderliggende punt blijft aanklikbaar/highlightbaar (zie rawFineClusters).
function isHullRenderArtefact(c: ClusterHullItem): boolean {
	return c.redundant_with_parent === true || (c.contained_by_sibling ?? null) !== null;
}

function scaleClusterX(items: ClusterHullItem[], xScale: number): ClusterHullItem[] {
	return items.map((c) => ({
		...c,
		centroid: [c.centroid[0] * xScale, c.centroid[1]] as [number, number],
		hull: c.hull ? c.hull.map(([hx, hy]) => [hx * xScale, hy] as [number, number]) : null,
	}));
}

const coarseClusters = computed<ClusterHullItem[]>(() => {
	if (!clustersData.value) return [];
	const xScale = canvasAspectRatio.value > 0 ? canvasAspectRatio.value : 1.618;
	if ("coarse" in clustersData.value && Array.isArray(clustersData.value.coarse)) {
		return scaleClusterX(
			clustersData.value.coarse.filter((c) => hullArea(c.hull) <= HULL_AREA_HIDE_THRESHOLD && !isHullRenderArtefact(c)),
			xScale,
		);
	}
	return [];
});

const fineClusters = computed<ClusterHullItem[]>(() => {
	if (!clustersData.value) return [];
	const xScale = canvasAspectRatio.value > 0 ? canvasAspectRatio.value : 1.618;
	if ("fine" in clustersData.value && Array.isArray(clustersData.value.fine)) {
		return scaleClusterX(
			clustersData.value.fine.filter((c) => hullArea(c.hull) <= HULL_AREA_HIDE_THRESHOLD && !isHullRenderArtefact(c)),
			xScale,
		);
	}
	if (Array.isArray(clustersData.value)) {
		return scaleClusterX(
			clustersData.value.filter((c) => hullArea(c.hull) <= HULL_AREA_HIDE_THRESHOLD && !isHullRenderArtefact(c)),
			xScale,
		);
	}
	return [];
});

// Ongefilterde fine-clusterlijst (los van de hull-oppervlakte-drempel
// hierboven) zodat lookups op cluster_id altijd het juiste fine-cluster
// vinden, ook als de hull te klein is om te tekenen.
const rawFineClusters = computed<ClusterHullItem[]>(() => {
	const data = clustersData.value;
	if (!data) return [];
	if ("fine" in data && Array.isArray(data.fine)) return data.fine;
	if (Array.isArray(data)) return data;
	return [];
});

const fineClusterById = computed<Map<number, ClusterHullItem>>(() => {
	const map = new Map<number, ClusterHullItem>();
	for (const c of rawFineClusters.value) map.set(c.cluster_id, c);
	return map;
});

// Elk punt bewaart alleen het fine-cluster-id (zie experiment_umap_documents.py);
// deze map vertaalt dat naar het bijbehorende coarse-domein zodat een
// coarse-selectie de juiste punten kan markeren.
const fineParentMap = computed<Map<number, number>>(() => {
	const map = new Map<number, number>();
	for (const c of rawFineClusters.value) {
		if (c.parent_id != null) map.set(c.cluster_id, c.parent_id);
	}
	return map;
});

function pointMatchesActiveCluster(p: PlenairPoint, ac: { id: number; level: ClusterLevel }): boolean {
	if (p.cluster == null) return false;
	if (ac.level === "fine") return p.cluster === ac.id;
	return fineParentMap.value.get(p.cluster) === ac.id;
}

const decodedPoints = computed<PlenairPoint[]>(() => {
	const raw = pointsData.value;
	if (!raw.points.length) return [];
	const xScale = canvasAspectRatio.value > 0 ? canvasAspectRatio.value : 1.618;
	return raw.points.map(([id, x, y, topicIdx, actorIdx, partyIdx, debateIdx, soortIdx, published_at, text, cluster]) => ({
		id,
		x: x * xScale,
		y,
		topic: raw.topics[topicIdx] || "plenair",
		topicIdx,
		actor: raw.actors[actorIdx] || "",
		party: raw.parties[partyIdx] || "",
		activiteit_soort: raw.soorten[soortIdx] || null,
		debate_title: raw.debates[debateIdx] || null,
		published_at,
		text,
		cluster,
	}));
});

const topics = computed(() => [...new Set(decodedPoints.value.map((p) => p.topic))].sort());

const topicCounts = computed(() => {
	const counts: Record<string, number> = {};
	for (const p of decodedPoints.value) {
		counts[p.topic] = (counts[p.topic] || 0) + 1;
	}
	return counts;
});

const rawBounds = computed(() => {
	const pts = decodedPoints.value;
	if (!pts.length) return { minX: -10, maxX: 10, minY: -10, maxY: 10, cx: 0, cy: 0, spanX: 20, spanY: 20 };
	let minX = Infinity,
		maxX = -Infinity,
		minY = Infinity,
		maxY = -Infinity;
	for (const p of pts) {
		if (p.x < minX) minX = p.x;
		if (p.x > maxX) maxX = p.x;
		if (p.y < minY) minY = p.y;
		if (p.y > maxY) maxY = p.y;
	}
	const cx = (minX + maxX) / 2;
	const cy = (minY + maxY) / 2;
	const spanX = (maxX - minX) * 1.08 || 1;
	const spanY = (maxY - minY) * 1.08 || 1;
	return { minX, maxX, minY, maxY, cx, cy, spanX, spanY };
});

// -------------------------------------------------------------
// Coordinate Transformations
// -------------------------------------------------------------
let currentTransform = zoomIdentity;

function worldToScreen(wx: number, wy: number): [number, number] {
	const b = rawBounds.value;
	const w = canvasWidth.value;
	const h = canvasHeight.value;

	const nx = (wx - b.cx) / (b.spanX / 2);
	const ny = (wy - b.cy) / (b.spanY / 2);

	const baseX = w / 2 + nx * (w / 2);
	const baseY = h / 2 - ny * (h / 2);

	const sx = currentTransform.x + currentTransform.k * baseX;
	const sy = currentTransform.y + currentTransform.k * baseY;
	return [sx, sy];
}

function screenToWorld(sx: number, sy: number): [number, number] {
	const b = rawBounds.value;
	const w = canvasWidth.value;
	const h = canvasHeight.value;

	const k = currentTransform.k || 1;
	const baseX = (sx - currentTransform.x) / k;
	const baseY = (sy - currentTransform.y) / k;

	const nx = (baseX - w / 2) / (w / 2);
	const ny = -(baseY - h / 2) / (h / 2);

	const wx = b.cx + nx * (b.spanX / 2);
	const wy = b.cy + ny * (b.spanY / 2);
	return [wx, wy];
}

// Wereld-rechthoek van wat er nu zichtbaar is, met een marge zodat punten niet
// abrupt pop-in/out geven bij pannen. Gebruikt om ver-buiten-beeld punten
// vóór het tekenen te skippen (issue #186, zoomperformance) i.p.v. elk frame
// alle ~40k punten te itereren en te arc()'en ongeacht wat er op het scherm past.
function visibleWorldRect(marginFrac = 0.15) {
	const w = canvasWidth.value;
	const h = canvasHeight.value;
	const marginX = w * marginFrac;
	const marginY = h * marginFrac;
	const [x0, y0] = screenToWorld(-marginX, -marginY);
	const [x1, y1] = screenToWorld(w + marginX, h + marginY);
	return {
		minX: Math.min(x0, x1),
		maxX: Math.max(x0, x1),
		minY: Math.min(y0, y1),
		maxY: Math.max(y0, y1),
	};
}

// Deterministische pseudo-random score in [0,1) per punt-id, één keer
// "getrokken" en daarna stabiel (puur een functie van het punt-id, nooit van
// zoom/pan/canvasgrootte). randomSample() houdt een punt aan zodra zijn score
// onder de keep-fractie voor het huidige zoomniveau ligt.
//
// Eerdere versie deed dit via een rooster-met-1-representant-per-cel i.p.v.
// gewoon filteren op deze score. Twee problemen daarmee, live gezien: (1) de
// gekozen representant kon bij een net iets andere celindeling een ander
// onderliggend punt worden, zichtbaar als punten die van plek leken te
// verspringen; (2) elke cel leverde precies 1 punt op ongeacht of er 2 of 500
// punten in zaten, wat de werkelijke dichtheidsverdeling juist verborg i.p.v.
// toonde. Puur proportioneel random samplen lost beide op: een getoond punt
// staat altijd op zijn eigen vaste (x, y), nooit vervangen door een buurpunt;
// en een gebied met 10x zoveel punten houdt na sampling nog steeds ~10x zoveel
// over, dus de relatieve dichtheid blijft zichtbaar. Monotoon oplopend met
// zoom (keepFraction groeit alleen maar), dus een eenmaal getoond punt
// verdwijnt niet meer bij verder inzoomen -- zonder dat daar een rooster met
// afgeronde zoomniveaus voor nodig is: de score van een punt verandert nooit,
// alleen de drempel waar 'ie tegenaan gehouden wordt.
function pointPriority(id: number): number {
	let h = id ^ 0x9e3779b9;
	h = Math.imul(h ^ (h >>> 16), 0x45d9f3b);
	h = Math.imul(h ^ (h >>> 16), 0x45d9f3b);
	h = h ^ (h >>> 16);
	return (h >>> 0) / 4294967296;
}

function randomSample(points: PlenairPoint[], keepFraction: number): PlenairPoint[] {
	if (keepFraction >= 1) return points;
	return points.filter((p) => pointPriority(p.id) < keepFraction);
}

// Hoeveel fractie van de "overig plenair"-achtergrond getoond wordt op
// mobiel (puur performance-gedreven, zie benchmark issue #186). Domein loopt
// door tot zoom 16 (het maximum, scaleExtent), niet tot 8: plenairSizeScale
// bevriest de puntgrootte vanaf zoom 8 (clamp), dus pas ná dat punt zorgt
// verder inzoomen nog echt voor meer ruimte tussen de punten i.p.v. dat
// grotere punten de winst van "meer punten tonen" weer opeten. Groeit daarom
// bewust langzaam door tot het echte zoom-maximum.
const plenairKeepFractionScale = scaleLinear().domain([1, 16]).range([0.08, 1]).clamp(true);

// Hoeveel fractie van een topic-cluster getoond wordt, op mobiel én desktop:
// dit is geen performance-fix (~6.300 topic-punten totaal is triviaal) maar
// een legibiliteit-fix -- bij volledig tekenen verzadigden dichte UMAP-
// clusters via de `multiply`-blending naar egale zwarte vlekken (live
// gezien). Zelfde reden voor het domein tot 16 als bij plenairKeepFractionScale
// hierboven: topicSizeScale bevriest ook pas bij zoom 8 -- bij een domein
// tot 6 (eerdere versie) liep de sample-fractie al bijna vol terwijl de
// punten ondertussen ook nog fors groeiden, met als resultaat dat dichte
// clusters bij gematigd inzoomen nog steeds als zwarte vlek oogden (live
// gezien, issue #186). Mobiel start op 30% van het desktop-startpunt (9%
// i.p.v. 30%): kleiner scherm, dus dezelfde absolute puntdichtheid oogt er
// dichter.
const topicKeepFractionScaleDesktop = scaleLinear().domain([1, 16]).range([0.3, 1]).clamp(true);
const topicKeepFractionScaleMobile = scaleLinear().domain([1, 16]).range([0.09, 1]).clamp(true);
function topicKeepFraction(zoomLevel: number): number {
	return (isMobile.value ? topicKeepFractionScaleMobile : topicKeepFractionScaleDesktop)(zoomLevel);
}

// -------------------------------------------------------------
// Spatial Grid Index for Fast Hit-Testing
// -------------------------------------------------------------
const GRID_CELLS = 40;
let spatialGrid: PlenairPoint[][][] = [];

function buildSpatialGrid() {
	const b = rawBounds.value;
	spatialGrid = Array.from({ length: GRID_CELLS }, () => Array.from({ length: GRID_CELLS }, () => []));

	for (const p of decodedPoints.value) {
		const gx = Math.floor(((p.x - b.minX) / (b.maxX - b.minX || 1)) * (GRID_CELLS - 1));
		const gy = Math.floor(((p.y - b.minY) / (b.maxY - b.minY || 1)) * (GRID_CELLS - 1));
		if (gx >= 0 && gx < GRID_CELLS && gy >= 0 && gy < GRID_CELLS) {
			spatialGrid[gx][gy].push(p);
		}
	}
}

watch(decodedPoints, () => buildSpatialGrid(), { immediate: true });

function findNearestPoint(screenX: number, screenY: number, maxScreenRadius = 14): PlenairPoint | null {
	const [wx, wy] = screenToWorld(screenX, screenY);
	const b = rawBounds.value;

	const gx = Math.floor(((wx - b.minX) / (b.maxX - b.minX || 1)) * (GRID_CELLS - 1));
	const gy = Math.floor(((wy - b.minY) / (b.maxY - b.minY || 1)) * (GRID_CELLS - 1));

	let nearest: PlenairPoint | null = null;
	let minDistSq = Infinity;
	const maxScreenRadiusSq = maxScreenRadius * maxScreenRadius;

	const minCellX = Math.max(0, gx - 1);
	const maxCellX = Math.min(GRID_CELLS - 1, gx + 1);
	const minCellY = Math.max(0, gy - 1);
	const maxCellY = Math.min(GRID_CELLS - 1, gy + 1);

	for (let x = minCellX; x <= maxCellX; x++) {
		for (let y = minCellY; y <= maxCellY; y++) {
			const cell = spatialGrid[x]?.[y];
			if (!cell) continue;
			for (let i = 0; i < cell.length; i++) {
				const p = cell[i];
				const [sx, sy] = worldToScreen(p.x, p.y);
				const distSq = (sx - screenX) * (sx - screenX) + (sy - screenY) * (sy - screenY);
				if (distSq <= maxScreenRadiusSq && distSq < minDistSq) {
					minDistSq = distSq;
					nearest = p;
				}
			}
		}
	}
	return nearest;
}

// Check if point is inside a polygon
function isPointInPolygon(px: number, py: number, poly: [number, number][]): boolean {
	let inside = false;
	for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
		const xi = poly[i][0],
			yi = poly[i][1];
		const xj = poly[j][0],
			yj = poly[j][1];
		const intersect = yi > py !== yj > py && px < ((xj - xi) * (py - yi)) / (yj - yi || 1e-9) + xi;
		if (intersect) inside = !inside;
	}
	return inside;
}

// Calculate distance from screen point to a line segment
function distanceSqToSegment(px: number, py: number, x1: number, y1: number, x2: number, y2: number): number {
	const l2 = (x2 - x1) * (x2 - x1) + (y2 - y1) * (y2 - y1);
	if (l2 === 0) return (px - x1) * (px - x1) + (py - y1) * (py - y1);
	let t = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / l2;
	t = Math.max(0, Math.min(1, t));
	const projX = x1 + t * (x2 - x1);
	const projY = y1 + t * (y2 - y1);
	return (px - projX) * (px - projX) + (py - projY) * (py - projY);
}

// Calculate shortest distance from screen point to hull contour boundary in screen pixels
function distanceToHullBoundaryScreen(sx: number, sy: number, hull: [number, number][]): number {
	if (!hull || hull.length < 3) return Infinity;
	let minDistSq = Infinity;
	for (let i = 0; i < hull.length; i++) {
		const [x1, y1] = worldToScreen(hull[i][0], hull[i][1]);
		const [x2, y2] = worldToScreen(hull[(i + 1) % hull.length][0], hull[(i + 1) % hull.length][1]);
		const dSq = distanceSqToSegment(sx, sy, x1, y1, x2, y2);
		if (dSq < minDistSq) minDistSq = dSq;
	}
	return Math.sqrt(minDistSq);
}

// Text wrapping helper for compact 2-line cluster labels
function wrapLabel(text: string, maxChars = 16): string[] {
	if (text.length <= maxChars) return [text];
	const words = text.split(" ");
	if (words.length <= 1) return [text];

	const lines: string[] = [];
	let currentLine = "";

	for (const word of words) {
		if (!currentLine) {
			currentLine = word;
		} else if ((currentLine + " " + word).length <= maxChars) {
			currentLine += " " + word;
		} else {
			lines.push(currentLine);
			currentLine = word;
		}
	}
	if (currentLine) lines.push(currentLine);
	return lines;
}

type LeveledCluster = { level: ClusterLevel; data: ClusterHullItem };

function getVisibleClusters(): LeveledCluster[] {
	const showCoarse = zoom.value < 2.3;
	const showFine = zoom.value >= 1.7;
	const list: LeveledCluster[] = [];
	if (showFine) list.push(...fineClusters.value.map((data) => ({ level: "fine" as const, data })));
	if (showCoarse) list.push(...coarseClusters.value.map((data) => ({ level: "coarse" as const, data })));
	return list;
}

// 1. Precise visible contour boundary hit-testing (within 4.5px of drawn contour line)
function findContourBoundaryNearScreen(sx: number, sy: number, maxBoundaryDist = 4.5): LeveledCluster | null {
	const visible = getVisibleClusters();
	let best: LeveledCluster | null = null;
	let bestDist = Infinity;

	for (const c of visible) {
		if (!c.data.hull || c.data.hull.length < 3) continue;
		const boundaryDist = distanceToHullBoundaryScreen(sx, sy, c.data.hull);
		if (boundaryDist <= maxBoundaryDist && boundaryDist < bestDist) {
			bestDist = boundaryDist;
			best = c;
		}
	}
	return best;
}

let renderedLabels: { level: ClusterLevel; cluster: ClusterHullItem; box: { x: number; y: number; w: number; h: number } }[] = [];

// 2. Visible cluster label hit-testing (cursor physically over the label box)
function findClusterLabelNearScreen(sx: number, sy: number): LeveledCluster | null {
	for (let i = renderedLabels.length - 1; i >= 0; i--) {
		const l = renderedLabels[i];
		if (sx >= l.box.x && sx <= l.box.x + l.box.w && sy >= l.box.y && sy <= l.box.y + l.box.h) {
			return { level: l.level, data: l.cluster };
		}
	}
	return null;
}

// -------------------------------------------------------------
// D3 Canvas Render Engine
// -------------------------------------------------------------
const plenairSizeScale = scaleSqrt().domain([1, 8]).range([2, 5.5]).clamp(true);
const topicSizeScale = scaleSqrt().domain([1, 8]).range([4, 11]).clamp(true);
// Minimale fine-cluster-grootte om een label te tonen: onder zoom 2.2 alleen
// de grootste (>=90), tussen 2.2 en 3.0 ook middelgrote (>=40), vanaf 3.0 alle.
const fineClusterMinSizeScale = scaleThreshold<number, number>().domain([2.2, 3.0]).range([90, 40, 0]);

function render() {
	if (!canvasRef.value) return;
	const canvas = canvasRef.value;
	const ctx = canvas.getContext("2d");
	if (!ctx) return;

	const dpr = Math.min(2, window.devicePixelRatio || 1);
	const w = canvasWidth.value;
	const h = canvasHeight.value;

	// Math.round: canvas.width/height accepteert alleen integers en kapt
	// intern af (niet rondt af) bij een fractionele devicePixelRatio (bv. 1.5,
	// gangbaar op Windows/oudere laptops) -- die afkapping maakte de backing
	// store net iets kleiner dan de CSS-box, met afgekapte buitenranden tot
	// gevolg (issue #205).
	const backingW = Math.round(w * dpr);
	const backingH = Math.round(h * dpr);
	if (canvas.width !== backingW || canvas.height !== backingH) {
		canvas.width = backingW;
		canvas.height = backingH;
	}

	ctx.save();
	ctx.scale(dpr, dpr);
	ctx.clearRect(0, 0, w, h);

	// Paper base fill for multiply blending
	ctx.fillStyle = isDark.value ? "#161412" : "#fdfbf7";
	ctx.fillRect(0, 0, w, h);

	// 1. Draw Points with true Ink-blending (watercolor density)
	ctx.globalCompositeOperation = isDark.value ? "screen" : "multiply";

	const activeC = activeCluster.value;
	const activeTopic = selectedTopicFilter.value;
	const hasActiveFilter = activeC != null || activeTopic != null;

	const groups: Record<string, PlenairPoint[]> = {
		plenair: [],
		stikstof: [],
		abortus: [],
		asiel: [],
		energietransitie: [],
	};

	const rect = visibleWorldRect();
	const pts = decodedPoints.value;
	for (let i = 0; i < pts.length; i++) {
		const p = pts[i];
		if (p.x < rect.minX || p.x > rect.maxX || p.y < rect.minY || p.y > rect.maxY) continue;
		if (groups[p.topic]) {
			groups[p.topic].push(p);
		} else {
			groups.plenair.push(p);
		}
	}

	// Desktop-achtergrond 2x kleiner (0.5x i.p.v. 1x): bij volle 40k
	// ongesamplede achtergrondpunten vielen de losse stippen te dominant op,
	// live gezien op de uitgezoomde weergave.
	const basePlenairR = plenairSizeScale(zoom.value) * (isMobile.value ? 1.3 : 0.5);
	const baseTopicR = topicSizeScale(zoom.value) * (isMobile.value ? 1.3 : 1);

	// Achtergrond ("overig plenair") dunnen op mobiel én op ingeschat
	// laagperformante desktops (issue #226) -- een gemiddelde desktop trekt de
	// volle ~40k achtergrondpunten probleemloos (zie benchmark issue #186),
	// maar niet elke desktop is gemiddeld. De topic-gekleurde clusters worden
	// altijd gedund, op mobiel én desktop: dat is geen performance-fix maar
	// een legibiliteit-fix (zie toelichting bij randomSample hierboven).
	if (isMobile.value || isLowPerfDevice.value) {
		groups.plenair = randomSample(groups.plenair, plenairKeepFractionScale(zoom.value));
	}
	const topicKeep = topicKeepFraction(zoom.value);
	groups.stikstof = randomSample(groups.stikstof, topicKeep);
	groups.abortus = randomSample(groups.abortus, topicKeep);
	groups.asiel = randomSample(groups.asiel, topicKeep);
	groups.energietransitie = randomSample(groups.energietransitie, topicKeep);

	for (const [topic, topicPts] of Object.entries(groups)) {
		if (topicPts.length === 0) continue;
		const isPlenair = topic === "plenair";
		const r = isPlenair ? basePlenairR : baseTopicR;
		const baseColor = TOPIC_COLOR[topic] || TOPIC_COLOR.plenair;

		for (let i = 0; i < topicPts.length; i++) {
			const p = topicPts[i];
			const isPointSelected =
				(activeC != null && pointMatchesActiveCluster(p, activeC)) || (activeTopic != null && p.topic === activeTopic);
			const isDimmed = hasActiveFilter && !isPointSelected;

			ctx.fillStyle = isDimmed ? (isDark.value ? "#333" : "#ddd") : baseColor;
			ctx.globalAlpha = isDimmed
				? 0.04
				: isPointSelected
				? 0.95
				: isPlenair
				? isDark.value
					? 0.32
					: 0.22
				: 0.7;

			const [sx, sy] = worldToScreen(p.x, p.y);
			const finalR = isPointSelected ? r * 1.3 : r;

			ctx.beginPath();
			ctx.arc(sx, sy, finalR, 0, Math.PI * 2);
			ctx.fill();
		}
	}
	ctx.globalCompositeOperation = "source-over";

	// 2. Draw Automatic Hierarchical Cluster Hulls
	const showCoarse = zoom.value < 2.3;
	const showFine = zoom.value >= 1.7;

	if (showCoarse && coarseClusters.value.length > 0) {
		const coarseAlpha = zoom.value > 1.8 ? Math.max(0.1, (2.3 - zoom.value) / 0.5) : 1;
		ctx.globalAlpha = coarseAlpha;

		for (const c of coarseClusters.value) {
			if (!c.hull || c.hull.length < 3) continue;
			const isClusterActive = activeC?.level === "coarse" && activeC.id === c.cluster_id;
			const isClusterHovered = hoveredClusterLevel.value === "coarse" && hoveredCluster.value?.cluster_id === c.cluster_id;
			const pts = c.hull.map(([hx, hy]) => worldToScreen(hx, hy));

			ctx.beginPath();
			ctx.moveTo(pts[0][0], pts[0][1]);
			for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
			ctx.closePath();

			ctx.fillStyle = isClusterActive
				? isDark.value
					? "rgba(255, 255, 255, 0.12)"
					: "rgba(0, 0, 0, 0.06)"
				: isClusterHovered
				? isDark.value
					? "rgba(255, 255, 255, 0.07)"
					: "rgba(0, 0, 0, 0.035)"
				: isDark.value
				? "rgba(255, 255, 255, 0.02)"
				: "rgba(0, 0, 0, 0.015)";
			ctx.fill();

			ctx.strokeStyle = isClusterActive
				? isDark.value
					? "#ffffff"
					: "#000000"
				: isClusterHovered
				? isDark.value
					? "rgba(255, 255, 255, 0.95)"
					: "rgba(0, 0, 0, 0.85)"
				: isDark.value
				? "rgba(255, 255, 255, 0.35)"
				: "rgba(0, 0, 0, 0.28)";
			ctx.lineWidth = isClusterActive ? 3.5 : isClusterHovered ? 2.8 : 1.8;
			ctx.setLineDash([8, 5]);
			ctx.stroke();
			ctx.setLineDash([]);
		}
		ctx.globalAlpha = 1.0;
	}

	if (showFine && fineClusters.value.length > 0) {
		const fineAlpha = zoom.value < 2.3 ? Math.max(0.1, (zoom.value - 1.7) / 0.6) : 1;
		ctx.globalAlpha = fineAlpha;

		for (const c of fineClusters.value) {
			if (!c.hull || c.hull.length < 3) continue;
			const isClusterActive = activeC?.level === "fine" && activeC.id === c.cluster_id;
			const isClusterHovered = hoveredClusterLevel.value === "fine" && hoveredCluster.value?.cluster_id === c.cluster_id;
			const pts = c.hull.map(([hx, hy]) => worldToScreen(hx, hy));

			ctx.beginPath();
			ctx.moveTo(pts[0][0], pts[0][1]);
			for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
			ctx.closePath();

			ctx.fillStyle = isClusterActive
				? isDark.value
					? "rgba(255, 255, 255, 0.16)"
					: "rgba(0, 0, 0, 0.08)"
				: isClusterHovered
				? isDark.value
					? "rgba(255, 255, 255, 0.09)"
					: "rgba(0, 0, 0, 0.05)"
				: isDark.value
				? "rgba(255, 255, 255, 0.018)"
				: "rgba(0, 0, 0, 0.015)";
			ctx.fill();

			ctx.strokeStyle = isClusterActive
				? isDark.value
					? "#ffffff"
					: "#000000"
				: isClusterHovered
				? isDark.value
					? "rgba(255, 255, 255, 0.95)"
					: "rgba(0, 0, 0, 0.85)"
				: isDark.value
				? "rgba(255, 255, 255, 0.38)"
				: "rgba(0, 0, 0, 0.26)";
			ctx.lineWidth = isClusterActive ? 3.2 : isClusterHovered ? 2.6 : 1.6;
			ctx.stroke();
		}
		ctx.globalAlpha = 1.0;
	}

	// 3. Draw Thematic Labels with Collision Avoidance
	renderedLabels = [];
	const placedBoxes: { x: number; y: number; w: number; h: number }[] = [];

	function drawLabel(cluster: ClusterHullItem, level: ClusterLevel, fontSize: number, isBold = false) {
		const [x, y] = worldToScreen(cluster.centroid[0], cluster.centroid[1]);
		if (x < -60 || x > w + 60 || y < -60 || y > h + 60) return;

		const lines = wrapLabel(cluster.name, isBold ? 14 : 18);
		const lineHeight = fontSize * 1.25;
		const totalH = lines.length * lineHeight;
		const maxLineLength = Math.max(...lines.map((l) => l.length));
		const boxW = maxLineLength * fontSize * 0.58 + 8;
		const boxH = totalH + 6;
		const box = { x: x - boxW / 2, y: y - boxH / 2, w: boxW, h: boxH };

		for (const b of placedBoxes) {
			if (box.x < b.x + b.w && box.x + box.w > b.x && box.y < b.y + b.h && box.y + box.h > b.y) {
				return;
			}
		}
		placedBoxes.push(box);
		renderedLabels.push({ level, cluster, box });

		ctx.font = `${isBold ? "bold" : "600"} ${fontSize}px system-ui, sans-serif`;
		ctx.textAlign = "center";
		ctx.textBaseline = "middle";
		ctx.lineJoin = "round";

		const startY = y - ((lines.length - 1) * lineHeight) / 2;

		for (let i = 0; i < lines.length; i++) {
			const lineY = startY + i * lineHeight;
			ctx.strokeStyle = isDark.value ? "rgba(20, 18, 16, 0.88)" : "rgba(255, 255, 255, 0.92)";
			ctx.lineWidth = fontSize >= 13 ? 3.5 : 2.5;
			ctx.strokeText(lines[i], x, lineY);

			ctx.fillStyle = ink.value;
			ctx.fillText(lines[i], x, lineY);
		}
	}

	if (showCoarse) {
		for (const c of coarseClusters.value) {
			drawLabel(c, "coarse", 13.5, true);
		}
	}

	if (showFine) {
		const visibleFine = fineClusters.value
			.filter((c) => c.size >= fineClusterMinSizeScale(zoom.value))
			.sort((a, b) => b.size - a.size);

		for (const c of visibleFine) {
			drawLabel(c, "fine", Math.min(12.5, Math.max(9.5, 9 + zoom.value * 0.7)), false);
		}
	}

	// 4. Draw Indicator Circle on Active/Hovered Point
	const pt = hoveredPoint.value;
	if (pt) {
		const [sx, sy] = worldToScreen(pt.x, pt.y);
		ctx.beginPath();
		ctx.arc(sx, sy, isMobile.value ? 12 : 9, 0, Math.PI * 2);
		ctx.strokeStyle = isDark.value ? "#ffffff" : "#000000";
		ctx.lineWidth = 2.5;
		ctx.stroke();

		ctx.beginPath();
		ctx.arc(sx, sy, 3, 0, Math.PI * 2);
		ctx.fillStyle = isDark.value ? "#ffffff" : "#000000";
		ctx.fill();
	}
	ctx.restore();
}

let renderFrameId: number | null = null;
function triggerRender() {
	if (renderFrameId != null) cancelAnimationFrame(renderFrameId);
	renderFrameId = requestAnimationFrame(() => render());
}

// -------------------------------------------------------------
// D3 Zoom & Gesture Setup
// -------------------------------------------------------------
function initD3Zoom() {
	if (!canvasRef.value) return;
	const sel = select(canvasRef.value);

	d3ZoomBehavior = d3zoom<HTMLCanvasElement, unknown>()
		.scaleExtent([0.75, 16])
		.wheelDelta((event) => {
			const delta = -event.deltaY * (event.deltaMode === 1 ? 0.05 : event.deltaMode ? 1 : 0.002);
			return event.ctrlKey ? delta * 4 : delta;
		})
		.on("zoom", (event: D3ZoomEvent<HTMLCanvasElement, unknown>) => {
			currentTransform = event.transform;
			zoom.value = event.transform.k;
			triggerRender();
		});

	sel.call(d3ZoomBehavior);
}

function zoomIn() {
	if (canvasRef.value && d3ZoomBehavior) {
		select(canvasRef.value).transition().duration(250).call(d3ZoomBehavior.scaleBy, 1.45);
	}
}

function zoomOut() {
	if (canvasRef.value && d3ZoomBehavior) {
		select(canvasRef.value).transition().duration(250).call(d3ZoomBehavior.scaleBy, 0.69);
	}
}

watch(status, async (newStatus) => {
	if (newStatus === "ready") {
		await nextTick();
		updateCanvasDimensions();
		initD3Zoom();
		triggerRender();
	}
});

onMounted(() => {
	if (status.value === "ready") {
		updateCanvasDimensions();
		initD3Zoom();
		triggerRender();
	}
});

watch([isDark, activeCluster, selectedTopicFilter], () => {
	triggerRender();
});

function resetView() {
	pinnedItem.value = null;
	hoveredItem.value = null;
	activeCluster.value = null;
	selectedTopicFilter.value = null;
	emit("select-cluster", null);

	if (canvasRef.value && d3ZoomBehavior) {
		select(canvasRef.value)
			.transition()
			.duration(600)
			.call(d3ZoomBehavior.transform, zoomIdentity);
	}
}

function clearSelection() {
	pinnedItem.value = null;
	activeCluster.value = null;
	emit("select-cluster", null);
	triggerRender();
}

// -------------------------------------------------------------
// Mouse & Pointer Interactions (Hover & Click)
// -------------------------------------------------------------
let pointerStartX = 0;
let pointerStartY = 0;

function onPointerDown(e: PointerEvent) {
	pointerStartX = e.clientX;
	pointerStartY = e.clientY;
}

function onPointerMove(e: PointerEvent) {
	if (e.pointerType === "touch") return; // Touch uses tap
	const rect = canvasRef.value?.getBoundingClientRect();
	if (!rect) return;

	const mx = e.clientX - rect.left;
	const my = e.clientY - rect.top;

	// 1. Precise contour boundary line (4.5px target on the visible line itself)
	const contour = findContourBoundaryNearScreen(mx, my, 4.5);
	if (contour) {
		hoveredItem.value = { type: "cluster", data: contour.data, level: contour.level };
		triggerRender();
		return;
	}

	// 2. Direct hit on visible cluster label box
	const labelCluster = findClusterLabelNearScreen(mx, my);
	if (labelCluster) {
		hoveredItem.value = { type: "cluster", data: labelCluster.data, level: labelCluster.level };
		triggerRender();
		return;
	}

	// 3. Individual speech points (12px target)
	const pt = findNearestPoint(mx, my, 12);
	if (pt) {
		const clusterInfo = pt.cluster != null ? fineClusterById.value.get(pt.cluster) || null : null;
		hoveredItem.value = { type: "point", data: pt, clusterInfo };
		triggerRender();
		return;
	}

	// In empty space
	if (hoveredItem.value != null) {
		hoveredItem.value = null;
		triggerRender();
	}
}

function onPointerLeave() {
	if (hoveredItem.value != null) {
		hoveredItem.value = null;
		triggerRender();
	}
}

function onCanvasClick(e: MouseEvent) {
	// If dragged (> 5px), ignore click to prevent accidental selection
	const distMoved = Math.hypot(e.clientX - pointerStartX, e.clientY - pointerStartY);
	if (distMoved > 5) return;

	const rect = canvasRef.value?.getBoundingClientRect();
	if (!rect) return;

	const mx = e.clientX - rect.left;
	const my = e.clientY - rect.top;

	// 1. Click on contour boundary line (6.0px target)
	const contour = findContourBoundaryNearScreen(mx, my, 6.0);
	if (contour) {
		pinnedItem.value = { type: "cluster", data: contour.data, level: contour.level };
		activeCluster.value = { id: contour.data.cluster_id, level: contour.level };
		emit("select-cluster", contour.data.cluster_id);
		triggerRender();
		return;
	}

	// 2. Click directly on visible cluster label box
	const labelCluster = findClusterLabelNearScreen(mx, my);
	if (labelCluster) {
		pinnedItem.value = { type: "cluster", data: labelCluster.data, level: labelCluster.level };
		activeCluster.value = { id: labelCluster.data.cluster_id, level: labelCluster.level };
		emit("select-cluster", labelCluster.data.cluster_id);
		triggerRender();
		return;
	}

	// 3. Click directly on a speech point (14px target). Alleen het punt zelf
	// wordt gemarkeerd (ring), verder blijft de kaart ongewijzigd -- geen
	// cluster-brede dimming/highlight (issue #198: puntselectie deed voorheen
	// hetzelfde als clusterselectie, wat als "te veel" voelde).
	const pt = findNearestPoint(mx, my, 14);
	if (pt) {
		const clusterInfo = pt.cluster != null ? fineClusterById.value.get(pt.cluster) || null : null;
		pinnedItem.value = { type: "point", data: pt, clusterInfo };
		triggerRender();
		return;
	}

	// Click on empty space: unpin
	if (pinnedItem.value != null || activeCluster.value != null) {
		pinnedItem.value = null;
		activeCluster.value = null;
		emit("select-cluster", null);
		triggerRender();
	}
}
</script>

<template>
	<section class="stats-panel plenair-map">
		<div class="map-heading-row">
			<div>
				<h2>Waar passen deze onderwerpen binnen de Kamer?</h2>
				<p class="panel-note panel-note-intro">
					Elk punt is één sprekersbeurt uit een plenair Kamerdebat, geplaatst op inhoudelijke gelijkenis (UMAP op
					tekst-embeddings). De getekende contouren bakenen automatisch gevonden beleidsdomeinen en deelthema's af.
					<a href="/over/#plenaire-kaart" class="map-help-link">Wat zie ik op deze kaart? &rarr;</a>
				</p>
			</div>
		</div>

		<p v-if="status === 'error'" class="panel-note panel-error">Kon de kaartdata niet laden. Probeer de pagina te verversen.</p>
		<p v-else-if="status === 'loading'" class="panel-note">Bezig met laden van {{ decodedPoints.length || '38.000' }} spreekbeurten&hellip;</p>

		<template v-else>
			<!-- Top Toolbar: Legend & Active Selection Controls -->
			<div class="map-toolbar-row">
				<div class="topic-legend">
					<button
						v-for="t in topics"
						:key="t"
						class="legend-item"
						:class="{ active: selectedTopicFilter === t }"
						@click="selectedTopicFilter = selectedTopicFilter === t ? null : t"
						:title="`Filter op ${t}`"
					>
						<span class="legend-dot" :style="{ backgroundColor: TOPIC_COLOR[t] ?? TOPIC_COLOR.plenair }"></span>
						<span class="legend-name">{{ t === 'plenair' ? 'overig plenair' : t }}</span>
						<span class="legend-count">({{ topicCounts[t] ?? 0 }})</span>
					</button>
				</div>

				<div class="toolbar-right">
					<span class="control-hint">
						<template v-if="isMobile">Knijpen zoomt, slepen pant &middot; tik op een punt of contour</template>
						<template v-else>Scrollen zoomt op cursor, slepen pant &middot; klik om vast te zetten</template>
					</span>
				</div>
			</div>

			<!-- Interactive D3 Canvas Viewport (No Floating Popups) -->
			<div
				ref="wrapperEl"
				class="plenair-map-wrapper"
				@pointerdown="onPointerDown"
				@pointermove="onPointerMove"
				@pointerleave="onPointerLeave"
				@click="onCanvasClick"
			>
				<canvas
					ref="canvasRef"
					class="d3-map-canvas"
					:style="{ width: `${canvasWidth}px`, height: `${canvasHeight}px` }"
				/>

				<!-- Floating Zoom & Reset Buttons -->
				<div class="map-floating-controls">
					<button class="map-zoom-btn" @click.stop="zoomIn" title="Inzoomen" aria-label="Inzoomen">+</button>
					<button class="map-zoom-btn" @click.stop="zoomOut" title="Uitzoomen" aria-label="Uitzoomen">&minus;</button>
					<button class="map-zoom-btn map-reset-icon-btn" @click.stop="resetView" title="Weergave resetten" aria-label="Weergave resetten">&#8635;</button>
				</div>
			</div>

			<!-- Fixed Information Panel (Consistent across Desktop & Mobile) -->
			<div class="map-info-panel" :class="{ 'is-pinned': isPinned }">
				<!-- 1. Point / Speech Details -->
				<template v-if="activeDisplayItem?.type === 'point'">
					<div class="info-panel-header">
						<div class="info-speaker-line">
							<strong class="info-speaker">{{ activeDisplayItem.data.actor || 'Onbekende spreker' }}</strong>
							<span v-if="activeDisplayItem.data.party" class="party-tag">{{ activeDisplayItem.data.party }}</span>
							<span v-if="activeDisplayItem.data.activiteit_soort" class="activity-tag">{{ activeDisplayItem.data.activiteit_soort }}</span>
							<span v-if="activeDisplayItem.data.published_at" class="date-tag">
								{{ new Date(activeDisplayItem.data.published_at).toLocaleDateString('nl-NL') }}
							</span>
						</div>

						<div class="info-header-actions">
							<a
								v-if="activePointVideo"
								:href="activePointVideo.href"
								:target="activePointVideo.is_internal ? '_self' : '_blank'"
								rel="noopener noreferrer"
								class="video-link-btn"
								:title="activePointVideo.label"
							>
								<img v-if="!activePointVideo.is_internal" src="/icons/tk.svg" alt="" class="tk-link-icon" />
								<span v-else class="video-play-icon">&#9654;</span>
								<span>{{ activePointVideo.is_internal ? 'Bekijk in videospeler' : 'Bekijk video' }}</span>
								<span v-if="!activePointVideo.is_internal" class="external-arrow">&nearr;</span>
							</a>
							<span v-if="isPinned" class="pinned-indicator">Vastgezet</span>
							<button v-if="isPinned" class="close-info-btn" @click="clearSelection" title="Sluit vastzetting" aria-label="Sluit">&times;</button>
						</div>
					</div>

					<div class="info-context-row">
						<span v-if="activeDisplayItem.clusterInfo" class="cluster-context-badge">
							Thema: <strong>{{ activeDisplayItem.clusterInfo.name }}</strong>
							<template v-if="activeDisplayItem.clusterInfo.parent_name && activeDisplayItem.clusterInfo.parent_name !== activeDisplayItem.clusterInfo.name">
								({{ activeDisplayItem.clusterInfo.parent_name }})
							</template>
						</span>
						<a
							v-if="activePointDebateLink"
							:href="activePointDebateLink.href"
							:target="activePointDebateLink.is_internal ? '_self' : '_blank'"
							rel="noopener noreferrer"
							class="debate-link-badge"
							:title="`Bekijk debat: ${activeDisplayItem.data.debate_title}`"
						>
							<img v-if="!activePointDebateLink.is_internal" src="/icons/tk.svg" alt="" class="tk-link-icon" />
							<span v-else class="debate-icon">&#128462;</span>
							<em class="debate-title-link">{{ activeDisplayItem.data.debate_title }}</em>
							<span v-if="!activePointDebateLink.is_internal" class="external-arrow">&nearr;</span>
						</a>
						<span v-else-if="activeDisplayItem.data.debate_title" class="debate-title-text">
							<em>{{ activeDisplayItem.data.debate_title }}</em>
						</span>
					</div>

					<blockquote class="info-quote-text">
						&ldquo;{{ activeDisplayItem.data.text }}&rdquo;
					</blockquote>
				</template>

				<!-- 2. Cluster / Region Details -->
				<template v-else-if="activeDisplayItem?.type === 'cluster'">
					<div class="info-panel-header">
						<div class="info-cluster-title-line">
							<span v-if="activeDisplayItem.data.parent_name && activeDisplayItem.data.parent_name !== activeDisplayItem.data.name" class="cluster-breadcrumb">
								{{ activeDisplayItem.data.parent_name }} &rarr;
							</span>
							<strong class="info-cluster-name">{{ activeDisplayItem.data.name }}</strong>
							<span class="cluster-size-badge">{{ activeDisplayItem.data.size }} spreekbeurten</span>
						</div>

						<div class="info-header-actions">
							<span v-if="isPinned" class="pinned-indicator">Vastgezet</span>
							<button v-if="isPinned" class="close-info-btn" @click="clearSelection" title="Sluit vastzetting" aria-label="Sluit">&times;</button>
						</div>
					</div>

					<p v-if="activeDisplayItem.data.duiding" class="info-duiding-text">
						{{ activeDisplayItem.data.duiding }}
					</p>

					<div v-if="activeDisplayItem.data.top_debates?.length" class="info-cluster-debates-row">
						<span class="terms-heading">Belangrijkste debatten:</span>
						<template v-for="(deb, idx) in activeDisplayItem.data.top_debates" :key="deb.title">
							<a
								v-if="deb.link"
								:href="deb.link.href"
								:target="deb.link.is_internal ? '_self' : '_blank'"
								rel="noopener noreferrer"
								class="cluster-debate-link-badge"
								:title="deb.title"
							>
								<img v-if="!deb.link.is_internal" src="/icons/tk.svg" alt="" class="tk-link-icon" />
								<span v-else class="debate-icon">&#128462;</span>
								<span class="cluster-debate-title">{{ deb.title }}</span>
								<span class="cluster-debate-count">({{ deb.count }})</span>
								<span v-if="!deb.link.is_internal" class="external-arrow">&nearr;</span>
							</a>
							<span v-else class="cluster-debate-plain">
								{{ deb.title }} ({{ deb.count }})
							</span>
						</template>
					</div>

					<div v-if="activeDisplayItem.data.terms?.length" class="info-terms-row">
						<span class="terms-heading">Trefwoorden:</span>
						<span v-for="term in activeDisplayItem.data.terms.slice(0, 10)" :key="term" class="term-pill">
							{{ term }}
						</span>
					</div>
				</template>

				<!-- 3. Resting / Idle State -->
				<template v-else>
					<div class="info-panel-idle">
						<span class="idle-text">Beweeg over of tik op een punt of themacontour om details, sprekers en duiding te bekijken.</span>
					</div>
				</template>
			</div>
		</template>
	</section>
</template>

<style scoped>
.plenair-map {
	margin-top: var(--space-4, 1.5rem);
}

.map-heading-row {
	display: flex;
	justify-content: space-between;
	align-items: flex-start;
	flex-wrap: wrap;
	gap: var(--space-2, 0.5rem);
}

.map-help-link {
	display: inline-block;
	margin-left: 0.5rem;
	font-size: 0.88em;
	color: var(--color-accent, #2563eb);
	text-decoration: underline;
	text-underline-offset: 2px;
}

.panel-error {
	color: var(--kleur-fout, #b3261e);
}

.map-toolbar-row {
	display: flex;
	justify-content: space-between;
	align-items: center;
	flex-wrap: wrap;
	gap: 0.75rem;
	margin: 0.75rem 0 0.5rem;
}

.topic-legend {
	display: flex;
	flex-wrap: wrap;
	gap: 0.5rem;
}

.legend-item {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	background: var(--color-surface, #f9f8f6);
	border: 1px solid var(--color-border, #e5e0d8);
	border-radius: 6px;
	padding: 0.3rem 0.6rem;
	font-size: 0.82rem;
	cursor: pointer;
	color: var(--color-ink, #221f1b);
	transition: background 0.15s, border-color 0.15s;
}

.legend-item:hover {
	background: var(--color-surface-hover, #ede9e1);
}

.legend-item.active {
	border-color: var(--color-ink, #221f1b);
	font-weight: 600;
	background: var(--color-surface-hover, #ede9e1);
}

.legend-dot {
	width: 9px;
	height: 9px;
	border-radius: 50%;
	display: inline-block;
	flex-shrink: 0;
}

.legend-count {
	opacity: 0.65;
	font-size: 0.9em;
}

.toolbar-right {
	display: flex;
	align-items: center;
	gap: 0.75rem;
	margin-left: auto;
}

.control-hint {
	font-size: 0.76rem;
	color: var(--color-muted, #736b5e);
}

/* Canvas Viewport */
.plenair-map-wrapper {
	position: relative;
	width: 100%;
	height: 540px;
	background: var(--color-surface, #f9f8f6);
	border: 1px solid var(--color-border, #e5e0d8);
	border-radius: 8px 8px 0 0;
	overflow: hidden;
	user-select: none;
	touch-action: none;
	cursor: grab;
}

.plenair-map-wrapper:active {
	cursor: grabbing;
}

.map-floating-controls {
	position: absolute;
	top: 12px;
	right: 12px;
	display: flex;
	flex-direction: column;
	gap: 4px;
	z-index: 15;
}

.map-zoom-btn {
	width: 32px;
	height: 32px;
	background: var(--color-bg, #ffffff);
	border: 1px solid var(--color-border, #e5e0d8);
	border-radius: 6px;
	box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 1.15rem;
	font-weight: 600;
	cursor: pointer;
	color: var(--color-ink, #221f1b);
	user-select: none;
	transition: background 0.15s, transform 0.1s;
}

.map-zoom-btn:hover {
	background: var(--color-surface, #f9f8f6);
}

.map-zoom-btn:active {
	transform: scale(0.95);
}

.map-reset-icon-btn {
	font-size: 1.05rem;
	margin-top: 2px;
}

.d3-map-canvas {
	display: block;
	width: 100%;
	height: 100%;
}

/* Dedicated Fixed Information Panel */
.map-info-panel {
	background: var(--color-bg, #ffffff);
	border: 1px solid var(--color-border, #e5e0d8);
	border-top: none;
	border-radius: 0 0 8px 8px;
	padding: 0.75rem 1rem;
	height: 145px;
	box-sizing: border-box;
	display: flex;
	flex-direction: column;
	justify-content: flex-start;
	gap: 0.35rem;
	overflow-y: auto;
	contain: layout;
	transition: border-color 0.15s, background-color 0.15s;
}

.map-info-panel.is-pinned {
	border-color: var(--color-ink, #221f1b);
	background: var(--color-surface, #f9f8f6);
}

.info-panel-idle {
	display: flex;
	align-items: center;
	height: 100%;
	color: var(--color-muted, #736b5e);
	font-size: 0.84rem;
	font-style: italic;
}

.info-panel-header {
	display: flex;
	justify-content: space-between;
	align-items: flex-start;
	flex-wrap: wrap;
	gap: 0.5rem;
}

.info-speaker-line,
.info-cluster-title-line {
	display: flex;
	align-items: center;
	flex-wrap: wrap;
	gap: 6px;
	font-size: 0.95rem;
}

.info-speaker,
.info-cluster-name {
	color: var(--color-ink, #221f1b);
	font-size: 1rem;
}

.party-tag {
	font-weight: 600;
	background: rgba(0, 0, 0, 0.06);
	padding: 1px 6px;
	border-radius: 4px;
	font-size: 0.82rem;
}

.activity-tag,
.date-tag {
	color: var(--color-muted, #736b5e);
	font-size: 0.82rem;
}

.info-header-actions {
	display: flex;
	align-items: center;
	gap: 6px;
	margin-left: auto;
}

.video-link-btn {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	background: var(--color-surface, #ede9e1);
	border: 1px solid var(--color-border, #e5e0d8);
	color: var(--color-ink, #221f1b) !important;
	border-radius: 4px;
	padding: 2px 7px;
	font-size: 0.76rem;
	font-weight: 600;
	text-decoration: none;
	transition: background-color 0.15s, border-color 0.15s, transform 0.1s;
}

.video-link-btn:hover {
	background: var(--color-surface-hover, #dfdad0);
	border-color: var(--color-ink, #221f1b);
	transform: translateY(-1px);
}

.video-play-icon {
	font-size: 0.65rem;
	opacity: 0.85;
}

.tk-link-icon {
	width: 13px;
	height: 13px;
	object-fit: contain;
	vertical-align: middle;
	filter: saturate(0.6);
	display: inline-block;
}

.external-arrow {
	font-size: 0.8rem;
	opacity: 0.7;
}

.pinned-indicator {
	font-size: 0.72rem;
	font-weight: 600;
	text-transform: uppercase;
	letter-spacing: 0.04em;
	background: var(--color-ink, #221f1b);
	color: var(--color-bg, #ffffff);
	padding: 1px 6px;
	border-radius: 3px;
}

.close-info-btn {
	background: none;
	border: none;
	font-size: 1.3rem;
	line-height: 1;
	cursor: pointer;
	color: var(--color-muted, #736b5e);
	padding: 0 4px;
}

.info-context-row {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 8px;
	font-size: 0.82rem;
}

.cluster-context-badge {
	background: rgba(0, 0, 0, 0.04);
	padding: 2px 7px;
	border-radius: 4px;
}

.debate-title-text {
	color: var(--color-muted, #736b5e);
}

.debate-link-badge {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	color: var(--color-ink, #221f1b);
	text-decoration: underline;
	text-decoration-color: var(--color-border, #d5d0c8);
	text-underline-offset: 3px;
	-webkit-line-clamp: 3;
	-webkit-box-orient: vertical;
	overflow: hidden;
}

.cluster-breadcrumb {
	opacity: 0.7;
	font-size: 0.88em;
}

.cluster-size-badge {
	font-size: 0.78rem;
	background: rgba(0, 0, 0, 0.06);
	padding: 2px 6px;
	border-radius: 4px;
}

.info-duiding-text {
	margin: 0.2rem 0 0.3rem;
	font-size: 0.85rem;
	line-height: 1.4;
	color: var(--color-ink, #221f1b);
	display: -webkit-box;
	-webkit-line-clamp: 3;
	-webkit-box-orient: vertical;
	overflow: hidden;
}

.info-cluster-debates-row,
.info-terms-row {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 6px;
	font-size: 0.78rem;
	margin-top: 0.25rem;
}

.cluster-debate-link-badge {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	background: var(--color-surface, #ede9e1);
	border: 1px solid var(--color-border, #e5e0d8);
	color: var(--color-ink, #221f1b) !important;
	padding: 2px 7px;
	border-radius: 4px;
	text-decoration: none;
	font-weight: 500;
	transition: background-color 0.15s, border-color 0.15s;
}

.cluster-debate-link-badge:hover {
	background: var(--color-surface-hover, #dfdad0);
	border-color: var(--color-ink, #221f1b);
}

.cluster-debate-count {
	opacity: 0.75;
	font-size: 0.72rem;
}

.cluster-debate-plain {
	background: rgba(0, 0, 0, 0.05);
	padding: 2px 6px;
	border-radius: 4px;
	font-size: 0.76rem;
}

.terms-heading {
	font-weight: 600;
	color: var(--color-muted, #736b5e);
	margin-right: 4px;
}

.term-pill {
	background: var(--color-bg, #ffffff);
	border: 1px solid var(--color-border, #e5e0d8);
	border-radius: 4px;
	padding: 1px 6px;
}

@media (max-width: 840px) {
	.plenair-map-wrapper {
		height: 380px;
	}

	.map-info-panel {
		height: 160px;
		padding: 0.65rem 0.8rem;
	}
}
</style>
