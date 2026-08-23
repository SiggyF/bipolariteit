<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { scaleLinear } from "d3-scale";
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

const coarseClusters = computed<ClusterHullItem[]>(() => {
	if (!props.clusters) return [];
	if ("coarse" in props.clusters && Array.isArray(props.clusters.coarse)) {
		return props.clusters.coarse;
	}
	return [];
});

const fineClusters = computed<ClusterHullItem[]>(() => {
	if (!props.clusters) return [];
	if ("fine" in props.clusters && Array.isArray(props.clusters.fine)) {
		return props.clusters.fine;
	}
	if (Array.isArray(props.clusters)) return props.clusters;
	return [];
});

const decodedPoints = computed<PlenairPoint[]>(() =>
	props.points.points.map(([id, x, y, topicIdx, actorIdx, partyIdx, debateIdx, soortIdx, published_at, text, cluster]) => ({
		id,
		x,
		y,
		topic: props.points.topics[topicIdx],
		actor: props.points.actors[actorIdx],
		party: props.points.parties[partyIdx],
		debate_title: props.points.debates[debateIdx] || null,
		activiteit_soort: props.points.soorten[soortIdx] || null,
		published_at,
		text,
		cluster,
	})),
);

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

	// Target aspect ratio comes directly from canvas width / height
	const targetAspect = canvasAspectRatio.value > 0 ? canvasAspectRatio.value : 1.618;
	const currentAspect = spanX / spanY;

	let finalSpanX = spanX;
	let finalSpanY = spanY;

	if (currentAspect < targetAspect) {
		// Canvas is wider than data -> widen X span to match canvas aspect ratio
		finalSpanX = spanY * targetAspect;
	} else {
		// Canvas is taller than data -> heighten Y span to match canvas aspect ratio
		finalSpanY = spanX / targetAspect;
	}

	return {
		x: [cx - finalSpanX / 2, cx + finalSpanX / 2],
		y: [cy - finalSpanY / 2, cy + finalSpanY / 2],
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

const plenairSizeScale = scaleLinear().domain([1, 6]).range([4, 20]).clamp(true);
const topicSizeScale = scaleLinear().domain([1, 6]).range([6, 26]).clamp(true);

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
	const xMin = Math.min(chart.convertFromPixel({ xAxisIndex: 0 }, boxStart.value.x), chart.convertFromPixel({ xAxisIndex: 0 }, boxCurrent.value.x));
	const xMax = Math.max(chart.convertFromPixel({ xAxisIndex: 0 }, boxStart.value.x), chart.convertFromPixel({ xAxisIndex: 0 }, boxCurrent.value.x));
	const yMin = Math.min(chart.convertFromPixel({ yAxisIndex: 0 }, boxStart.value.y), chart.convertFromPixel({ yAxisIndex: 0 }, boxCurrent.value.y));
	const yMax = Math.max(chart.convertFromPixel({ yAxisIndex: 0 }, boxStart.value.y), chart.convertFromPixel({ yAxisIndex: 0 }, boxCurrent.value.y));

	chart.dispatchAction({ type: "dataZoom", dataZoomIndex: 0, startValue: xMin, endValue: xMax });
	chart.dispatchAction({ type: "dataZoom", dataZoomIndex: 1, startValue: yMin, endValue: yMax });
}

function onChartClick(params: any) {
	if (params?.data?.clusterId != null) {
		emit("select-cluster", params.data.clusterId);
	}
}

const chartOption = computed(() => {
	const hasFilter = (props.selectedClusterIds?.size ?? 0) > 0;
	const seriesList: any[] = [];

	// 1. Coarse Domain Convex Hulls
	if (showCoarseHulls.value && coarseClusters.value.length > 0) {
		seriesList.push({
			type: "custom",
			id: "coarse-hulls",
			zlevel: 0,
			z: 0,
			silent: true,
			renderItem: (_params: any, api: any) => {
				const item = coarseClusters.value[_params.dataIndex];
				const hull = item?.hull;
				if (!hull || hull.length < 3) return;
				const pts = hull.map(([hx, hy]) => api.coord([hx, hy]));
				return {
					type: "polygon",
					shape: { points: pts },
					style: {
						fill: isDark.value ? "rgba(255, 255, 255, 0.04)" : "rgba(0, 0, 0, 0.03)",
						stroke: isDark.value ? "rgba(255, 255, 255, 0.25)" : "rgba(0, 0, 0, 0.18)",
						lineWidth: 1.5,
						lineDash: [6, 4],
					},
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
			silent: true,
			renderItem: (_params: any, api: any) => {
				const item = fineClusters.value[_params.dataIndex];
				const hull = item?.hull;
				if (!hull || hull.length < 3) return;
				const pts = hull.map(([hx, hy]) => api.coord([hx, hy]));
				const isSelected = hasFilter && props.selectedClusterIds?.has(item.cluster_id);
				return {
					type: "polygon",
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
				};
			},
			data: fineClusters.value.map((c) => [c.centroid[0], c.centroid[1]]),
		});
	}

	// 3. Centroid Topic Labels (Hierarchical Level of Detail based on zoom)
	if (showLabels.value) {
		// A. Coarse Domain Labels (prominent at overview, softly fading on deep zoom)
		if (coarseClusters.value.length > 0 && zoomFactor.value < 3.2) {
			const coarseOpacity = zoomFactor.value > 2.0 ? Math.max(0.2, (3.2 - zoomFactor.value) / 1.2) : 1;
			seriesList.push({
				type: "custom",
				id: "coarse-labels",
				zlevel: 1,
				z: 3,
				silent: true,
				renderItem: (_params: any, api: any) => {
					const item = coarseClusters.value[_params.dataIndex];
					if (!item?.centroid) return;
					const [cx, cy] = item.centroid;
					const [x, y] = api.coord([cx, cy]);
					return {
						type: "text",
						style: {
							text: item.name,
							x,
							y,
							textAlign: "center",
							textVerticalAlign: "middle",
							font: "bold 14px system-ui, sans-serif",
							fill: ink.value,
							opacity: coarseOpacity,
							stroke: isDark.value ? "rgba(0, 0, 0, 0.85)" : "rgba(255, 255, 255, 0.95)",
							lineWidth: 3.5,
						},
					};
				},
				data: coarseClusters.value.map((c) => [c.centroid[0], c.centroid[1]]),
			});
		}

		// B. Fine Sub-Cluster Labels (revealed dynamically as user zooms in)
		if (fineClusters.value.length > 0 && zoomFactor.value >= 1.5) {
			const visibleFine = fineClusters.value.filter((item) => {
				if (zoomFactor.value >= 3.0) return true;
				if (zoomFactor.value >= 2.2) return item.size >= 40;
				return item.size >= 100;
			});

			seriesList.push({
				type: "custom",
				id: "fine-labels",
				zlevel: 1,
				z: 4,
				silent: true,
				renderItem: (_params: any, api: any) => {
					const item = visibleFine[_params.dataIndex];
					if (!item?.centroid) return;
					const [cx, cy] = item.centroid;
					const [x, y] = api.coord([cx, cy]);
					const fontSize = Math.min(13, Math.max(10, Math.round(9 + zoomFactor.value * 0.8)));
					return {
						type: "text",
						style: {
							text: item.name,
							x,
							y,
							textAlign: "center",
							textVerticalAlign: "middle",
							font: `600 ${fontSize}px system-ui, sans-serif`,
							fill: ink.value,
							stroke: isDark.value ? "rgba(0, 0, 0, 0.8)" : "rgba(255, 255, 255, 0.9)",
							lineWidth: 2.5,
						},
					};
				},
				data: visibleFine.map((c) => [c.centroid[0], c.centroid[1]]),
			});
		}
	}

	// 4. Scatter Points (Speeches)
	if (showPoints.value) {
		for (const topic of topics.value) {
			const pts = plotPoints.value.filter((p) => p.topic === topic);
			const isPlenair = topic === "plenair";
			const baseSize =
				(isPlenair ? plenairSizeScale(zoomFactor.value) : topicSizeScale(zoomFactor.value)) *
				(isMobile.value ? 1.6 : 1);
			const baseOpacity = Math.min(0.95, (isPlenair ? 0.075 : 0.14) * zoomFactor.value);

			seriesList.push({
				id: topic,
				name: topic,
				type: "scatter",
				symbolSize: baseSize,
				large: isPlenair && !hasFilter,
				largeThreshold: 2000,
				zlevel: isPlenair ? 0 : 1,
				z: isPlenair ? 1 : 2,
				blendMode: isDark.value ? "screen" : "multiply",
				itemStyle: {
					color: TOPIC_COLOR[topic] ?? PLENAIR_COLOR,
					opacity: baseOpacity,
				},
				data: pts.map((p) => {
					const isSelected = hasFilter && p.cluster != null && props.selectedClusterIds!.has(p.cluster);
					const isDimmed = hasFilter && !isSelected;

					return {
						value: [p.x, p.y],
						actor: p.actor,
						party: p.party,
						activiteit_soort: p.activiteit_soort ?? "",
						debate_title: p.debate_title ?? "",
						published_at: p.published_at,
						text: p.text,
						clusterId: p.cluster,
						cluster: p.cluster != null ? clusterLabels.value.get(p.cluster) : undefined,
						itemStyle: isDimmed
							? { opacity: 0.04, color: isDark.value ? "#555" : "#ccc" }
							: isSelected
							? { opacity: 0.95, color: TOPIC_COLOR[topic] ?? PLENAIR_COLOR }
							: undefined,
						symbolSize: isSelected ? baseSize * 1.4 : isDimmed ? Math.max(3, baseSize * 0.75) : undefined,
					};
				}),
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
		dataZoom: [
			{
				type: "inside",
				xAxisIndex: 0,
				filterMode: "none",
				throttle: 0,
				zoomOnMouseWheel: true,
				moveOnMouseMove: true,
				moveOnMouseWheel: false,
			},
			{
				type: "inside",
				yAxisIndex: 0,
				filterMode: "none",
				throttle: 0,
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
