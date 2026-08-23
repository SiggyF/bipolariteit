<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { scaleSqrt, scaleThreshold } from "d3-scale";
import { useTheme } from "../lib/useTheme";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { ScatterChart, CustomChart } from "echarts/charts";
import { TooltipComponent, GridComponent, DataZoomInsideComponent } from "echarts/components";

use([CanvasRenderer, ScatterChart, CustomChart, TooltipComponent, GridComponent, DataZoomInsideComponent]);

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
	text: string;
	actor: string;
	party: string;
	activiteit_soort: string | null;
	debate_title: string | null;
	published_at: string;
	cluster: number | null;
};

type ClusterHullItem = {
	cluster_id: number;
	name: string;
	duiding?: string;
	parent_id?: number | null;
	parent_name?: string | null;
	terms?: string[];
	size: number;
	centroid: [number, number];
	hull: [number, number][] | null;
	topic_breakdown: Record<string, number>;
};

type ClustersExport = {
	coarse: ClusterHullItem[];
	fine: ClusterHullItem[];
};

const props = defineProps<{
	points: RawExport;
	clusters?: ClustersExport | ClusterHullItem[];
	selectedClusterIds?: Set<number>;
}>();

const emit = defineEmits<{
	(e: "select-cluster", clusterId: number | null): void;
}>();

const showCoarseHulls = ref(true);
const showFineHulls = ref(true);
const showLabels = ref(true);
const showPoints = ref(true);

// Shoelace-formule: oppervlakte van een convex hull-polygoon in UMAP-eenheden.
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

// Breekt een labeltekst over maximaal 2 regels (op het spatie-punt dat de
// twee regels het meest gelijk in lengte maakt), zodat labels smaller
// worden en er meer naast elkaar passen.
function wrapLabelText(text: string, maxCharsPerLine = 14): string[] {
	if (text.length <= maxCharsPerLine) return [text];
	const words = text.split(" ");
	if (words.length < 2) return [text];
	let bestSplit = 1;
	let bestDiff = Infinity;
	for (let i = 1; i < words.length; i++) {
		const diff = Math.abs(words.slice(0, i).join(" ").length - words.slice(i).join(" ").length);
		if (diff < bestDiff) {
			bestDiff = diff;
			bestSplit = i;
		}
	}
	return [words.slice(0, bestSplit).join(" "), words.slice(bestSplit).join(" ")];
}

type LabelBox = { x: number; y: number; width: number; height: number };

// Schat de bounding box van een (mogelijk over 2 regels gebroken) label in
// schermpixels, voor de collision-detection hieronder. Karakterbreedte is
// een vaste schatting (geen canvas-tekstmeting nodig) -- precies genoeg om
// overlap te vermijden, niet om exact te passen.
function measureLabelBox(lines: string[], fontSize: number, x: number, y: number): LabelBox {
	const padding = 3;
	const charWidth = fontSize * 0.58;
	const width = Math.max(...lines.map((l) => l.length)) * charWidth;
	const height = lines.length * fontSize * 1.2;
	return { x: x - width / 2 - padding, y: y - height / 2 - padding, width: width + padding * 2, height: height + padding * 2 };
}

function boxesOverlap(a: LabelBox, b: LabelBox): boolean {
	return a.x < b.x + b.width && a.x + a.width > b.x && a.y < b.y + b.height && a.y + a.height > b.y;
}

// De boomwandeling-clustering (zie scripts/experiment_umap_documents.py::
// build_hierarchical_clusters) laat aan het eind altijd één "restgroep"
// over -- alles wat niet zinnig verder splitste. Die is inhoudelijk te
// divers voor één label (topic_breakdown bevestigt dat, live gezien: 88%
// "overig plenair" + brokstukken van alle 4 topics) en spreidt zich daarom
// over een veel groter deel van de UMAP-kaart uit dan een samenhangend
// onderwerp -- goed te herkennen aan een sterk uitschietende hull-
// oppervlakte (live gemeten: 61-66 tegenover 1-7 voor de rest). Filter 'm
// er daarom uit i.p.v. de LLM een misleidend specifieke naam te laten
// verzinnen voor een groep die geen coherent onderwerp is.
const HULL_AREA_HIDE_THRESHOLD = 15;

// Zelfde X-herschaling als decodedPoints hieronder toepassen op
// centroid/hull, anders komen de contouren en labels niet meer overeen
// met de (al herschaalde) puntenwolk.
function scaleClusterX(items: ClusterHullItem[], xScale: number): ClusterHullItem[] {
	return items.map((c) => ({
		...c,
		centroid: [c.centroid[0] * xScale, c.centroid[1]] as [number, number],
		hull: c.hull ? c.hull.map(([hx, hy]) => [hx * xScale, hy] as [number, number]) : null,
	}));
}

const coarseClusters = computed<ClusterHullItem[]>(() => {
	if (!props.clusters) return [];
	const xScale = canvasAspectRatio.value > 0 ? canvasAspectRatio.value : 1.618;
	if ("coarse" in props.clusters && Array.isArray(props.clusters.coarse)) {
		return scaleClusterX(props.clusters.coarse.filter((c) => hullArea(c.hull) <= HULL_AREA_HIDE_THRESHOLD), xScale);
	}
	return [];
});

const fineClusters = computed<ClusterHullItem[]>(() => {
	if (!props.clusters) return [];
	const xScale = canvasAspectRatio.value > 0 ? canvasAspectRatio.value : 1.618;
	if ("fine" in props.clusters && Array.isArray(props.clusters.fine)) {
		return scaleClusterX(props.clusters.fine.filter((c) => hullArea(c.hull) <= HULL_AREA_HIDE_THRESHOLD), xScale);
	}
	if (Array.isArray(props.clusters)) return scaleClusterX(props.clusters.filter((c) => hullArea(c.hull) <= HULL_AREA_HIDE_THRESHOLD), xScale);
	return [];
});

// UMAP-output is van zichzelf ~1:1 in X/Y (geen betekenisvolle eigen
// aspect ratio, alleen lokale nabijheid telt) -- vermenigvuldig daarom
// alle X-coördinaten met de canvas-aspectratio (breedte/hoogte), zodat de
// data zelf het canvas vult i.p.v. dat er lege marge overblijft naast een
// smaller-dan-canvas asvenster (zie axisBounds hieronder, die nu geen
// aparte as meer hoeft te verbreden -- dat zat 'm hier, in de data).
const decodedPoints = computed<PlenairPoint[]>(() => {
	const xScale = canvasAspectRatio.value > 0 ? canvasAspectRatio.value : 1.618;
	return props.points.points.map(([id, x, y, topicIdx, actorIdx, partyIdx, debateIdx, soortIdx, published_at, text, cluster]) => ({
		id,
		x: x * xScale,
		y,
		topic: props.points.topics[topicIdx],
		actor: props.points.actors[actorIdx],
		party: props.points.parties[partyIdx],
		debate_title: props.points.debates[debateIdx] || null,
		activiteit_soort: props.points.soorten[soortIdx] || null,
		published_at,
		text,
		cluster,
	}));
});

const clusterLabels = computed(() => {
	const map = new Map<number, { name: string; parent_name?: string | null; terms?: string[] }>();
	for (const c of fineClusters.value) {
		map.set(c.cluster_id, {
			name: c.name,
			parent_name: c.parent_name,
			terms: c.terms,
		});
	}
	for (const c of coarseClusters.value) {
		if (!map.has(c.cluster_id)) {
			map.set(c.cluster_id, {
				name: c.name,
				parent_name: null,
				terms: c.terms,
			});
		}
	}
	return map;
});

const isDark = useTheme();
const ink = computed(() => (isDark.value ? "#f2ede3" : "#221f1b"));
const muted = computed(() => (isDark.value ? "#a89e8c" : "#6f6558"));
const gridLine = computed(() => (isDark.value ? "#453f36" : "#ddd5c4"));

const TOPIC_COLOR: Record<string, string> = {
	stikstof: "#4a7a4a",
	abortus: "#a64d5f",
	asiel: "#c07a2e",
	energietransitie: "#3d6e8f",
};
const PLENAIR_COLOR = "#a89e8c";

const topics = computed(() => [...new Set(decodedPoints.value.map((p) => p.topic))].sort());

const topicCounts = computed(() => {
	const counts: Record<string, number> = {};
	for (const p of decodedPoints.value) {
		counts[p.topic] = (counts[p.topic] || 0) + 1;
	}
	return counts;
});

const wrapperEl = ref<HTMLElement | null>(null);
const canvasAspectRatio = ref(1.618);
let resizeObserver: ResizeObserver | null = null;

function measureCanvasAspectRatio(el: HTMLElement) {
	if (el.clientWidth > 0 && el.clientHeight > 0) {
		const w = Math.max(10, el.clientWidth - 32);
		const h = Math.max(10, el.clientHeight - 32);
		canvasAspectRatio.value = w / h;
	}
}

onMounted(() => {
	if (wrapperEl.value) {
		measureCanvasAspectRatio(wrapperEl.value);
	}
	if (typeof ResizeObserver !== "undefined" && wrapperEl.value) {
		resizeObserver = new ResizeObserver(([entry]) => measureCanvasAspectRatio(entry.target as HTMLElement));
		resizeObserver.observe(wrapperEl.value);
	}
});
onUnmounted(() => resizeObserver?.disconnect());

const plotPoints = computed(() => decodedPoints.value);

// decodedPoints se x is al met canvasAspectRatio herschaald (zie boven),
// dus de data zelf heeft nu al de juiste verhouding voor het canvas --
// hier alleen nog een symmetrische marge padden, geen aparte as meer
// hoeven verbreden (dat gaf lege ruimte naast de data i.p.v. de data het
// canvas te laten vullen).
const axisBounds = computed(() => {
	if (decodedPoints.value.length === 0) {
		return { x: [-10, 10], y: [-10, 10] };
	}
	const xs = decodedPoints.value.map((p) => p.x);
	const ys = decodedPoints.value.map((p) => p.y);
	const minX = Math.min(...xs);
	const maxX = Math.max(...xs);
	const minY = Math.min(...ys);
	const maxY = Math.max(...ys);

	const cx = (minX + maxX) / 2;
	const cy = (minY + maxY) / 2;
	const spanX = (maxX - minX) * 1.08 || 1;
	const spanY = (maxY - minY) * 1.08 || 1;

	return {
		x: [cx - spanX / 2, cx + spanX / 2],
		y: [cy - spanY / 2, cy + spanY / 2],
	};
});

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

const chartRef = ref<any>(null);
const zoomFactor = ref(1);

function onDataZoom() {
	const dz = chartRef.value?.getOption?.()?.dataZoom;
	if (!dz || dz.length < 2) return;
	const xSpan = (dz[0]?.end ?? 100) - (dz[0]?.start ?? 0);
	const ySpan = (dz[1]?.end ?? 100) - (dz[1]?.start ?? 0);
	const visiblePercent = Math.max(Math.min(xSpan, ySpan), 1);
	zoomFactor.value = Math.min(6, 100 / visiblePercent);
}

// scaleSqrt (i.p.v. scaleLinear): puntoppervlak groeit dan evenredig met de
// zoomfactor i.p.v. de straal -- bij sterk overlappende punten (dichte
// clusters, live geconstateerd bij ver inzoomen: een egale donkere klomp
// door overlappende cirkels) groeit de straal zo minder snel door dan bij
// een lineaire schaal, wat overlap beperkt.
const topicSizeScale = scaleSqrt().domain([1, 6]).range([4, 12]).clamp(true);

// "overig plenair" (large-mode, zie de toelichting bij de scatter-serie
// hieronder) mag niet continu met zoomFactor meeschalen -- elke wijziging
// van symbolSize/opacity dwingt ECharts de gedeelde large-mode-buffer voor
// alle ~33k punten opnieuw op te bouwen. Een vaste grootte bleek zelf ook
// niet te werken: bij ver inzoomen (waar de punten juist meer ruimte
// tussen elkaar krijgen) werden ze zo klein/doorzichtig dat ze nauwelijks
// nog zichtbaar waren. Compromis: een getrapte schaal met maar een paar
// niveaus, zodat de buffer alleen bij het kruisen van een niveaugrens
// opnieuw wordt opgebouwd (hooguit een paar keer tijdens een zoom-gebaar)
// in plaats van op elke tick. scaleThreshold (i.p.v. scaleSqrt/scaleLinear)
// is d3's primitief voor precies dit: een continue input op een klein
// aantal discrete uitvoerniveaus afbeelden.
const plenairSizeScale = scaleThreshold<number, number>().domain([1.5, 2.5, 4, 6]).range([3, 4.5, 6, 8, 8]);
const plenairOpacityScale = scaleThreshold<number, number>()
	.domain([1.5, 2.5, 4, 6])
	.range([0.12, 0.16, 0.2, 0.26, 0.26]);

const boxSelecting = ref(false);
const boxStart = ref<{ x: number; y: number } | null>(null);
const boxCurrent = ref<{ x: number; y: number } | null>(null);

const boxStyle = computed(() => {
	if (!boxSelecting.value || !boxStart.value || !boxCurrent.value) return { display: "none" };
	const x1 = Math.min(boxStart.value.x, boxCurrent.value.x);
	const y1 = Math.min(boxStart.value.y, boxCurrent.value.y);
	const x2 = Math.max(boxStart.value.x, boxCurrent.value.x);
	const y2 = Math.max(boxStart.value.y, boxCurrent.value.y);
	return {
		left: `${x1}px`,
		top: `${y1}px`,
		width: `${x2 - x1}px`,
		height: `${y2 - y1}px`,
	};
});

function relativePos(e: PointerEvent): { x: number; y: number } {
	const rect = wrapperEl.value?.getBoundingClientRect() ?? { left: 0, top: 0 };
	return { x: e.clientX - rect.left, y: e.clientY - rect.top };
}

function onBoxPointerDown(e: PointerEvent) {
	if (e.pointerType !== "mouse" || !e.shiftKey) return;
	e.preventDefault();
	boxSelecting.value = true;
	boxStart.value = boxCurrent.value = relativePos(e);
	(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
}

function onBoxPointerMove(e: PointerEvent) {
	if (!boxSelecting.value) return;
	boxCurrent.value = relativePos(e);
}

function onBoxPointerUp(e: PointerEvent) {
	if (!boxSelecting.value || !boxStart.value || !boxCurrent.value) return;
	boxSelecting.value = false;
	(e.currentTarget as HTMLElement).releasePointerCapture?.(e.pointerId);

	const dx = Math.abs(boxCurrent.value.x - boxStart.value.x);
	const dy = Math.abs(boxCurrent.value.y - boxStart.value.y);
	if (dx < 8 || dy < 8) return;

	const chart = chartRef.value;
	if (!chart?.convertFromPixel) return;
	let xMin = Math.min(chart.convertFromPixel({ xAxisIndex: 0 }, boxStart.value.x), chart.convertFromPixel({ xAxisIndex: 0 }, boxCurrent.value.x));
	let xMax = Math.max(chart.convertFromPixel({ xAxisIndex: 0 }, boxStart.value.x), chart.convertFromPixel({ xAxisIndex: 0 }, boxCurrent.value.x));
	let yMin = Math.min(chart.convertFromPixel({ yAxisIndex: 0 }, boxStart.value.y), chart.convertFromPixel({ yAxisIndex: 0 }, boxCurrent.value.y));
	let yMax = Math.max(chart.convertFromPixel({ yAxisIndex: 0 }, boxStart.value.y), chart.convertFromPixel({ yAxisIndex: 0 }, boxCurrent.value.y));

	// Een sleepbox heeft zelden precies de aspect ratio van het canvas --
	// zonder correctie zou de gezoomde weergave de UMAP-verhoudingen
	// vervormen (data-aspect moet 1:1 blijven, zie axisBounds hierboven
	// voor dezelfde aanpak op de volledige weergave). Breid hier de kortste
	// as (t.o.v. het canvas) uit rond het midden van de sleepbox, zodat de
	// aspect ratio ook na het zoomen constant blijft.
	const cx = (xMin + xMax) / 2;
	const cy = (yMin + yMax) / 2;
	const targetAspect = canvasAspectRatio.value > 0 ? canvasAspectRatio.value : 1.618;
	const currentAspect = (xMax - xMin) / (yMax - yMin);
	if (currentAspect < targetAspect) {
		const finalSpanX = (yMax - yMin) * targetAspect;
		xMin = cx - finalSpanX / 2;
		xMax = cx + finalSpanX / 2;
	} else {
		const finalSpanY = (xMax - xMin) / targetAspect;
		yMin = cy - finalSpanY / 2;
		yMax = cy + finalSpanY / 2;
	}

	chart.dispatchAction({ type: "dataZoom", dataZoomIndex: 0, startValue: xMin, endValue: xMax });
	chart.dispatchAction({ type: "dataZoom", dataZoomIndex: 1, startValue: yMin, endValue: yMax });
}

function onChartClick(params: any) {
	if (params?.data?.clusterId != null) {
		emit("select-cluster", params.data.clusterId);
	}
}

const hasFilter = computed(() => (props.selectedClusterIds?.size ?? 0) > 0);

// Puntendata per topic, losstaand van chartOption -- alleen afhankelijk van
// de punten/selectie zelf, NIET van zoomFactor. chartOption herbouwt anders
// bij elke zoom-tick (elke ~30ms tijdens een zoom-gebaar, zie dataZoom-
// throttle) de volledige ~40k-punten-array opnieuw (met tooltip-tekst,
// cluster-lookup, itemStyle, etc.) terwijl alleen de puntgrootte verandert
// -- dat was de resterende schokkerigheid na de eerdere throttle/progressive-
// fix (issue #184-vervolg). `isSelected`/`isDimmed` blijven wel in de data
// staan (voor itemStyle, die niet zoom-afhankelijk is); alleen symbolSize
// wordt in chartOption zelf als functie berekend, met de actuele baseSize
// uit de zoom-afhankelijke sluiting.
const pointsByTopic = computed(() => {
	const filterActive = hasFilter.value;
	const byTopic = new Map<string, any[]>();
	for (const topic of topics.value) byTopic.set(topic, []);
	for (const p of plotPoints.value) {
		const isSelected = filterActive && p.cluster != null && props.selectedClusterIds!.has(p.cluster);
		const isDimmed = filterActive && !isSelected;
		const arr = byTopic.get(p.topic);
		if (!arr) continue;
		arr.push({
			value: [p.x, p.y],
			actor: p.actor,
			party: p.party,
			activiteit_soort: p.activiteit_soort ?? "",
			debate_title: p.debate_title ?? "",
			published_at: p.published_at,
			text: p.text,
			clusterId: p.cluster,
			cluster: p.cluster != null ? clusterLabels.value.get(p.cluster) : undefined,
			isSelected,
			isDimmed,
			itemStyle: isDimmed
				? { opacity: 0.04, color: isDark.value ? "#555" : "#ccc" }
				: isSelected
				? { opacity: 0.95, color: TOPIC_COLOR[p.topic] ?? PLENAIR_COLOR }
				: undefined,
		});
	}
	return byTopic;
});

const chartOption = computed(() => {
	const seriesList: any[] = [];

	// 1. Coarse Domain Convex Hulls
	if (showCoarseHulls.value && coarseClusters.value.length > 0) {
		seriesList.push({
			type: "custom",
			id: "coarse-hulls",
			zlevel: 0,
			z: 0,
			// Twee vormen over elkaar: de gevulde polygon is silent (puur
			// visueel, geen hover) -- anders blokkeert het hele vlak de hover op
			// individuele punten eronder/erboven. Alleen de rand (fill:"none",
			// dus geen interior-hittest, enkel de stroke) vangt hover op --
			// daar zitten sowieso minder punten dan in de kern van een cluster.
			renderItem: (_params: any, api: any) => {
				const item = coarseClusters.value[_params.dataIndex];
				const hull = item?.hull;
				if (!hull || hull.length < 3) return;
				const pts = hull.map(([hx, hy]) => api.coord([hx, hy]));
				return {
					type: "group",
					children: [
						{
							type: "polygon",
							silent: true,
							shape: { points: pts },
							style: {
								fill: isDark.value ? "rgba(255, 255, 255, 0.04)" : "rgba(0, 0, 0, 0.03)",
								stroke: isDark.value ? "rgba(255, 255, 255, 0.25)" : "rgba(0, 0, 0, 0.18)",
								lineWidth: 1.5,
								lineDash: [6, 4],
							},
						},
						{
							type: "polygon",
							shape: { points: pts },
							style: {
								fill: "none",
								stroke: "rgba(0, 0, 0, 0.01)",
								lineWidth: 10,
							},
							emphasis: {
								style: {
									fill: isDark.value ? "rgba(255, 255, 255, 0.09)" : "rgba(0, 0, 0, 0.06)",
									stroke: isDark.value ? "rgba(255, 255, 255, 0.45)" : "rgba(0, 0, 0, 0.32)",
									lineWidth: 2,
								},
							},
						},
					],
				};
			},
			data: coarseClusters.value.map((c) => [c.centroid[0], c.centroid[1]]),
		});
	}

	// 2. Fine Sub-Topic Convex Hulls
	if (showFineHulls.value && fineClusters.value.length > 0) {
		seriesList.push({
			type: "custom",
			id: "fine-hulls",
			zlevel: 0,
			z: 1,
			// Zelfde twee-vormen-truc als coarse-hulls: gevulde vlak silent,
			// alleen de rand (fill:"none") vangt hover.
			renderItem: (_params: any, api: any) => {
				const item = fineClusters.value[_params.dataIndex];
				const hull = item?.hull;
				if (!hull || hull.length < 3) return;
				const pts = hull.map(([hx, hy]) => api.coord([hx, hy]));
				const isSelected = hasFilter.value && props.selectedClusterIds?.has(item.cluster_id);
				return {
					type: "group",
					children: [
						{
							type: "polygon",
							silent: true,
							shape: { points: pts },
							style: {
								fill: isSelected
									? (isDark.value ? "rgba(255, 255, 255, 0.16)" : "rgba(0, 0, 0, 0.08)")
									: (isDark.value ? "rgba(255, 255, 255, 0.02)" : "rgba(0, 0, 0, 0.015)"),
								stroke: isSelected
									? (isDark.value ? "#ffffff" : "#000000")
									: (isDark.value ? "rgba(255, 255, 255, 0.35)" : "rgba(0, 0, 0, 0.22)"),
								lineWidth: isSelected ? 2.5 : 1,
							},
						},
						{
							type: "polygon",
							shape: { points: pts },
							style: {
								fill: "none",
								stroke: "rgba(0, 0, 0, 0.01)",
								lineWidth: 10,
							},
							emphasis: {
								style: {
									fill: isDark.value ? "rgba(255, 255, 255, 0.12)" : "rgba(0, 0, 0, 0.07)",
									stroke: isDark.value ? "#ffffff" : "#000000",
									lineWidth: 2,
								},
							},
						},
					],
				};
			},
			data: fineClusters.value.map((c) => [c.centroid[0], c.centroid[1]]),
		});
	}

	// 3. Centroid Topic Labels (Hierarchical Level of Detail based on zoom)
	//
	// Met tientallen coarse/fine-clusters tegelijk in beeld overlappen platte
	// labels elkaar al snel (issue #184-vervolg). Standaardaanpak: label-
	// ordening (grootste cluster claimt eerst ruimte) + collision-detection
	// (een label dat een al-geplaatst label zou overlappen wordt
	// overgeslagen, niet verschoven) + labels over 2 regels breken zodat ze
	// smaller zijn. `placedLabelBoxes` is bewust gedeeld tussen de coarse-
	// en fine-reeks (zelfde chartOption-berekening), zodat een fine-label
	// ook een al-geplaatst coarse-label respecteert.
	if (showLabels.value) {
		// Gedeeld tussen coarse- en fine-reeks, zodat een fine-label ook een
		// al-geplaatst coarse-label respecteert. Reset bij dataIndex 0: ECharts'
		// custom series roept renderItem soms meermaals per render aan (een
		// meet-pas vóór de eigenlijke tekenpas) -- zonder reset zou de eerste
		// pas de array al vullen, waardoor de tekenpas daarna alles als
		// "already placed" ziet en er niets zichtbaar wordt (live
		// geconstateerd). "coarse-labels" is de eerste reeks die per pas
		// dataIndex 0 raakt, dus dat is het juiste resetmoment voor de hele
		// gedeelde array.
		const placedLabelBoxes: LabelBox[] = [];

		// A. Coarse Domain Labels (prominent at overview, softly fading on deep zoom)
		if (coarseClusters.value.length > 0 && zoomFactor.value < 3.2) {
			const coarseOpacity = zoomFactor.value > 2.0 ? Math.max(0.2, (3.2 - zoomFactor.value) / 1.2) : 1;
			const orderedCoarse = [...coarseClusters.value].sort((a, b) => b.size - a.size);
			seriesList.push({
				type: "custom",
				id: "coarse-labels",
				zlevel: 1,
				z: 4,
				silent: true,
				renderItem: (_params: any, api: any) => {
					if (_params.dataIndex === 0) placedLabelBoxes.length = 0;
					const item = orderedCoarse[_params.dataIndex];
					if (!item?.centroid) return;
					const [cx, cy] = item.centroid;
					const [x, y] = api.coord([cx, cy]);
					const fontSize = 14;
					const lines = wrapLabelText(item.name, 16);
					const box = measureLabelBox(lines, fontSize, x, y);
					if (placedLabelBoxes.some((p) => boxesOverlap(box, p))) return;
					placedLabelBoxes.push(box);
					return {
						type: "text",
						style: {
							text: lines.join("\n"),
							x,
							y,
							textAlign: "center",
							textVerticalAlign: "middle",
							lineHeight: fontSize * 1.2,
							font: `bold ${fontSize}px system-ui, sans-serif`,
							fill: ink.value,
							opacity: coarseOpacity,
							stroke: isDark.value ? "rgba(0, 0, 0, 0.8)" : "rgba(255, 255, 255, 0.9)",
							lineWidth: 2,
						},
					};
				},
				data: orderedCoarse.map((c) => [c.centroid[0], c.centroid[1]]),
			});
		}

		// B. Fine Sub-Cluster Labels (revealed dynamically as user zooms in)
		if (fineClusters.value.length > 0 && zoomFactor.value >= 1.5) {
			const visibleFine = fineClusters.value
				.filter((item) => {
					if (zoomFactor.value >= 3.0) return true;
					if (zoomFactor.value >= 2.2) return item.size >= 40;
					return item.size >= 100;
				})
				.sort((a, b) => b.size - a.size);

			seriesList.push({
				type: "custom",
				id: "fine-labels",
				zlevel: 1,
				z: 5,
				silent: true,
				renderItem: (_params: any, api: any) => {
					const item = visibleFine[_params.dataIndex];
					if (!item?.centroid) return;
					const [cx, cy] = item.centroid;
					const [x, y] = api.coord([cx, cy]);
					const fontSize = Math.min(13, Math.max(10, Math.round(9 + zoomFactor.value * 0.8)));
					const lines = wrapLabelText(item.name, 14);
					const box = measureLabelBox(lines, fontSize, x, y);
					if (placedLabelBoxes.some((p) => boxesOverlap(box, p))) return;
					placedLabelBoxes.push(box);
					return {
						type: "text",
						style: {
							text: lines.join("\n"),
							x,
							y,
							textAlign: "center",
							textVerticalAlign: "middle",
							lineHeight: fontSize * 1.2,
							font: `600 ${fontSize}px system-ui, sans-serif`,
							fill: ink.value,
							stroke: isDark.value ? "rgba(0, 0, 0, 0.75)" : "rgba(255, 255, 255, 0.85)",
							lineWidth: 1.5,
						},
					};
				},
				data: visibleFine.map((c) => [c.centroid[0], c.centroid[1]]),
			});
		}
	}

	// 4. Scatter Points (Speeches)
	//
	// De puntendata zelf komt uit pointsByTopic (hierboven, zoom-onafhankelijk
	// gecachet) -- hier alleen de zoom-afhankelijke grootte/dekking, als een
	// symbolSize-functie i.p.v. een vaste waarde per punt, zodat de dure
	// per-punt data-array niet bij elke zoom-tick opnieuw hoeft te worden
	// opgebouwd (issue #184-vervolg, "zoomen gaat schokkerig").
	if (showPoints.value) {
		for (const topic of topics.value) {
			const pts = pointsByTopic.value.get(topic) ?? [];
			const isPlenair = topic === "plenair";
			// "overig plenair" (~33k punten, large-mode) krijgt bewust een VASTE
			// grootte/dekking, niet meeschalend met zoomFactor: large-mode bakt
			// symbolSize/opacity in een gedeelde buffer voor de hele batch, dus
			// élke wijziging daarvan dwingt ECharts die buffer voor alle ~33k
			// punten opnieuw op te bouwen -- op elke zoom-tick (elke ~30ms tijdens
			// een zoom-gebaar). Live gemeten met Chrome DevTools Performance:
			// ~500ms blokkerende hoofdthread-tijd per tick, ook nadat de Vue-kant
			// (chartOption/pointsByTopic) al naar ~0ms was teruggebracht -- de
			// kosten zaten dus in ECharts' eigen large-mode-buffer, niet in onze
			// code. De 4 getrackte topics zijn klein genoeg (13-2791 punten, geen
			// large-mode) om wel goedkoop met de zoom mee te schalen.
			const baseSize = isPlenair
				? plenairSizeScale(zoomFactor.value) * (isMobile.value ? 1.6 : 1)
				: topicSizeScale(zoomFactor.value) * (isMobile.value ? 1.6 : 1);
			// De 4 getrackte topics (i.t.t. "overig plenair") mogen bij uitgezoomd
			// beeld al goed zichtbaar zijn -- vandaar een ondergrens i.p.v. puur
			// lineair met zoomFactor meeschalen vanaf bijna onzichtbaar.
			const baseOpacity = isPlenair
				? plenairOpacityScale(zoomFactor.value)
				: Math.max(0.35, Math.min(0.6, 0.09 * zoomFactor.value));

			// Een symbolSize-FUNCTIE i.p.v. een constante dwingt ECharts om 'm
			// per punt aan te roepen -- op de ~33k "plenair"-punten met
			// large:true (large mode is juist bedoeld voor precies dít geval,
			// duizenden identieke punten in één keer) verpest dat de large-mode-
			// optimalisatie volledig (live gemeten met Chrome DevTools Performance:
			// 353ms/tick in Vue's flushJobs, i.p.v. de eerdere ~189ms alleen-
			// ECharts-tijd -- de functie-aanroep zelf was de bottleneck, niet de
			// data-array). Zonder actieve selectie (hasFilter) is isSelected/
			// isDimmed sowieso overal false, dus dan volstaat een simpele
			// constante; de functie is alleen nodig zodra een cluster
			// geselecteerd is (en dan staat large ook al uit).
			seriesList.push({
				id: topic,
				name: topic,
				type: "scatter",
				symbolSize: hasFilter.value
					? (_value: any, params: any) => {
							const d = params.data;
							return d.isSelected ? baseSize * 1.4 : d.isDimmed ? Math.max(3, baseSize * 0.75) : baseSize;
						}
					: baseSize,
				large: isPlenair && !hasFilter.value,
				largeThreshold: 2000,
				// Rendert boven de drempel in stukjes over meerdere frames i.p.v.
				// alles in één keer -- voorkomt lange blocking renders bij elke
				// zoom-stap op de ~33k "overig plenair"-punten.
				progressive: 4000,
				progressiveThreshold: 4000,
				zlevel: isPlenair ? 0 : 1,
				z: isPlenair ? 2 : 3,
				blendMode: isDark.value ? "screen" : "multiply",
				itemStyle: {
					color: TOPIC_COLOR[topic] ?? PLENAIR_COLOR,
					opacity: baseOpacity,
				},
				data: pts,
			});
		}
	}

	return {
		backgroundColor: "transparent",
		animation: false,
		textStyle: { fontFamily: "inherit", color: ink.value },
		tooltip: {
			trigger: "item",
			extraCssText: "max-width: 280px; white-space: normal; line-height: 1.35;",
			formatter: (p: any) => {
				// Hover op het hull-vlak zelf (i.t.t. een individueel punt of een
				// label): toon clusterdetails i.p.v. spreekbeurt-info.
				if (p.seriesId === "coarse-hulls" || p.seriesId === "fine-hulls") {
					const item = (p.seriesId === "coarse-hulls" ? coarseClusters.value : fineClusters.value)[p.dataIndex];
					if (!item) return "";
					const parentLine = item.parent_name && item.parent_name !== item.name
						? `<span style="opacity:0.75; font-size:0.9em;">${item.parent_name} &rarr; </span>`
						: "";
					const duidingLine = item.duiding ? `<br/>${item.duiding}` : "";
					const termsLine = item.terms?.length
						? `<br/><span style="opacity:0.65; font-size:0.85em;">${item.terms.slice(0, 6).join(", ")}</span>`
						: "";
					const topTopics = Object.entries(item.topic_breakdown || {})
						.sort((a, b) => (b[1] as number) - (a[1] as number))
						.slice(0, 3)
						.map(([t, n]) => `${t} (${n})`)
						.join(", ");
					return `${parentLine}<strong>${item.name}</strong><br/><span style="opacity:0.7">${item.size} spreekbeurten${topTopics ? " &middot; " + topTopics : ""}</span>${duidingLine}${termsLine}`;
				}

				const d = p.data;
				if (!d?.actor) return "";
				const datum = d.published_at ? new Date(d.published_at).toLocaleDateString("nl-NL") : "";
				const clusterLine = d.cluster
					? `<br/><span style="opacity:0.8; font-size:0.9em;">thema: ${d.cluster.parent_name ? d.cluster.parent_name + " &rarr; " : ""}<strong>${d.cluster.name}</strong></span>`
					: "";
				return `<strong>${d.actor}</strong> (${d.party})<br/><span style="opacity:0.7">${d.activiteit_soort} &middot; ${datum}</span><br/><em>${d.debate_title}</em>${clusterLine}<br/>${d.text}`;
			},
		},
		grid: { top: 16, left: 16, right: 16, bottom: 16, containLabel: false },
		// throttle: 0 (elke scroll-tick direct verwerken) gaf schokkerig zoomen
		// -- elke datazoom-event triggert via onDataZoom() een zoomFactor-update
		// en dus een volledige chartOption-herberekening (label-collision-
		// detection + tienduizenden scatterpunten). 30ms batcht dat tot een
		// vloeiender aantal updates per zoom-gebaar.
		dataZoom: [
			{
				type: "inside",
				xAxisIndex: 0,
				filterMode: "none",
				throttle: 30,
				zoomOnMouseWheel: true,
				moveOnMouseMove: true,
				moveOnMouseWheel: false,
			},
			{
				type: "inside",
				yAxisIndex: 0,
				filterMode: "none",
				throttle: 30,
				zoomOnMouseWheel: true,
				moveOnMouseMove: true,
				moveOnMouseWheel: false,
			},
		],
		xAxis: {
			type: "value",
			min: axisBounds.value.x[0],
			max: axisBounds.value.x[1],
			show: false,
			splitLine: { lineStyle: { color: gridLine.value } },
		},
		yAxis: {
			type: "value",
			min: axisBounds.value.y[0],
			max: axisBounds.value.y[1],
			show: false,
			splitLine: { lineStyle: { color: gridLine.value } },
		},
		series: seriesList,
	};
});
</script>

<template>
	<section class="stats-panel plenair-map">
		<h2>Waar passen deze onderwerpen binnen de Kamer?</h2>
		<p class="panel-note panel-note-intro">
			Elk punt is één sprekersbeurt uit een plenair Kamerdebat, geplaatst op inhoudelijke gelijkenis (UMAP op
			tekst-embeddings). De getekende contouren (convex hulls) bakenen automatisch gevonden beleidsdomeinen en
			deelonderwerpen af.
		</p>

		<div class="topic-legend">
			<span v-for="t in topics" :key="t" class="legend-item">
				<span class="legend-dot" :style="{ backgroundColor: TOPIC_COLOR[t] ?? PLENAIR_COLOR }"></span>
				<span class="legend-name">{{ t === 'plenair' ? 'overig plenair' : t }}</span>
				<span class="legend-count">({{ topicCounts[t] ?? 0 }})</span>
			</span>
		</div>

		<div class="map-controls-bar">
			<div class="layer-toggles">
				<label class="toggle-label">
					<input v-model="showCoarseHulls" type="checkbox" />
					<span>Beleidsdomeinen</span>
				</label>
				<label class="toggle-label">
					<input v-model="showFineHulls" type="checkbox" />
					<span>Deelonderwerpen</span>
				</label>
				<label class="toggle-label">
					<input v-model="showLabels" type="checkbox" />
					<span>Themalabels</span>
				</label>
				<label class="toggle-label">
					<input v-model="showPoints" type="checkbox" />
					<span>Sprekersbeurten</span>
				</label>
			</div>

			<span class="control-hint">
				<template v-if="isMobile">Knijpen zoomt, één vinger pant</template>
				<template v-else>Scrollen zoomt, slepen pant &middot; shift + slepen zoomt in op een gebied</template>
			</span>
		</div>

		<div
			ref="wrapperEl"
			class="plenair-map-wrapper"
			@pointerdown="onBoxPointerDown"
			@pointermove="onBoxPointerMove"
			@pointerup="onBoxPointerUp"
			@pointercancel="onBoxPointerUp"
		>
			<VChart
				ref="chartRef"
				class="plenair-map-chart"
				:option="chartOption"
				autoresize
				@datazoom="onDataZoom"
				@click="onChartClick"
			/>
			<div class="plenair-map-boxzoom" :style="boxStyle"></div>
		</div>
	</section>
</template>

<style scoped>
.topic-legend {
	display: flex;
	flex-wrap: wrap;
	gap: var(--space-3, 0.75rem);
	margin-bottom: var(--space-2, 0.5rem);
	font-size: 0.9em;
}

.legend-item {
	display: inline-flex;
	align-items: center;
	gap: 6px;
}

.legend-dot {
	width: 10px;
	height: 10px;
	border-radius: 50%;
	display: inline-block;
	flex-shrink: 0;
}

.legend-name {
	font-weight: 500;
}

.legend-count {
	opacity: 0.65;
	font-size: 0.9em;
}

.map-controls-bar {
	display: flex;
	justify-content: space-between;
	align-items: center;
	flex-wrap: wrap;
	gap: var(--space-2, 0.5rem);
	margin-bottom: var(--space-2, 0.5rem);
	font-size: 0.85em;
}

.layer-toggles {
	display: flex;
	gap: var(--space-3, 0.75rem);
	flex-wrap: wrap;
}

.toggle-label {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	cursor: pointer;
	user-select: none;
	opacity: 0.85;
}

.toggle-label input {
	cursor: pointer;
}

.control-hint {
	opacity: 0.7;
}

.plenair-map-wrapper {
	position: relative;
}

.plenair-map-chart {
	width: 100%;
	height: 70vh;
	min-height: 520px;
}

.plenair-map-boxzoom {
	position: absolute;
	pointer-events: none;
	border: 1px dashed var(--ink, #221f1b);
	background: rgba(128, 128, 128, 0.15);
}
</style>
