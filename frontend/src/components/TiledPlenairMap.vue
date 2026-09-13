<script setup lang="ts">
// Alternatief renderpad naast PlenairMap.vue (die ongewijzigd blijft, zie
// issue #215/#253): leest dezelfde brondata niet als één platte JSON, maar
// als een vector-tile-pyramide (.pmtiles, gebouwd door
// `pipeline.tiling.build_pyramid`) plus een klein grid-metadatabestand
// (plenair-map-grid.json). Dat maakt het schaalbaar naar veel meer punten
// (alleen zichtbare tiles worden opgehaald/gedecodeerd) en behoudt properties
// per punt (incl. `cluster`-id) in de tile zelf.
//
// v1, bewust eenvoudig gehouden t.o.v. PlenairMap.vue: geen zoom-afhankelijke
// sampling (de tile-pyramide zelf is de schaalstrategie), geen label-
// collision voor cluster-namen, brute-force hit-testing over de momenteel
// geladen tiles (ruim voldoende bij een paar honderd zichtbare punten).
import { computed, onMounted, onUnmounted, ref, shallowRef } from "vue";
import { select } from "d3-selection";
import { zoom as d3zoom, zoomIdentity, type D3ZoomEvent } from "d3-zoom";
import { PMTiles } from "pmtiles";
import { VectorTile } from "@mapbox/vector-tile";
import { PbfReader } from "pbf";
import { useTheme } from "../lib/useTheme";
import { DEFAULT_TOPIC_COLOR, TOPIC_COLOR } from "../lib/plenairMapColors";
import {
	makeScreenToWorld,
	makeWorldToScreen,
	tileBounds,
	tileLocalToWorld,
	tilesForWorldRect,
	umapToMercator,
	type GridMetadata,
	type TileKey,
} from "../lib/tiledMapTransform";

const props = defineProps<{
	dataBaseUrl: string;
	// pmtiles + grid-metadata komen van Hugging Face, niet van de
	// jsDelivr-databasis hierboven (zie lib/dataBaseUrl.ts, issue #316).
	tilesBaseUrl: string;
}>();

type DecodedPoint = {
	x: number;
	y: number;
	id: number;
	topic: string;
	actor: string;
	party: string;
	debate: string;
	soort: string;
	published_at: string;
	text: string;
	cluster: number | null;
};

type ClusterHullItem = {
	cluster_id: number;
	name: string;
	centroid: [number, number];
	hull: [number, number][] | null;
};

type FetchStatus = "loading" | "ready" | "error";
const status = ref<FetchStatus>("loading");
const gridMeta = ref<GridMetadata | null>(null);
const coarseClusters = ref<ClusterHullItem[]>([]);
let pmtiles: PMTiles | null = null;

const tileCache = new Map<string, DecodedPoint[]>();
const tilesInFlight = new Set<string>();

const isDark = useTheme();
const ink = computed(() => (isDark.value ? "#f2ede3" : "#221f1b"));
const muted = computed(() => (isDark.value ? "#a89e8c" : "#6f6558"));
const paper = computed(() => (isDark.value ? "#221f1b" : "#f7f3ea"));

const canvasRef = ref<HTMLCanvasElement | null>(null);
const wrapperEl = ref<HTMLElement | null>(null);
const canvasWidth = ref(900);
const canvasHeight = ref(540);

const transform = shallowRef({ x: 0, y: 0, k: 1 });
let d3ZoomBehavior: ReturnType<typeof d3zoom<HTMLCanvasElement, unknown>> | null = null;

const hoveredPoint = ref<DecodedPoint | null>(null);

function tileKeyStr(t: TileKey): string {
	return `${t.z}/${t.x}/${t.y}`;
}

async function loadTile(grid: GridMetadata, tile: TileKey): Promise<void> {
	const key = tileKeyStr(tile);
	if (tileCache.has(key) || tilesInFlight.has(key) || !pmtiles) return;
	tilesInFlight.add(key);
	try {
		const result = await pmtiles.getZxy(tile.z, tile.x, tile.y);
		if (!result) {
			tileCache.set(key, []);
			return;
		}
		const vt = new VectorTile(new PbfReader(new Uint8Array(result.data)));
		const layer = vt.layers.points;
		const bounds = tileBounds(grid, tile);
		const points: DecodedPoint[] = [];
		if (layer) {
			for (let i = 0; i < layer.length; i++) {
				const feature = layer.feature(i);
				const [[pt]] = feature.loadGeometry();
				const [wx, wy] = tileLocalToWorld(pt.x, pt.y, feature.extent, bounds);
				const props = feature.properties as Record<string, unknown>;
				points.push({
					x: wx,
					y: wy,
					id: Number(props.id),
					topic: String(props.topic ?? ""),
					actor: String(props.actor ?? ""),
					party: String(props.party ?? ""),
					debate: String(props.debate ?? ""),
					soort: String(props.soort ?? ""),
					published_at: String(props.published_at ?? ""),
					text: String(props.text ?? ""),
					cluster: props.cluster == null ? null : Number(props.cluster),
				});
			}
		}
		tileCache.set(key, points);
	} catch {
		tileCache.set(key, []);
	} finally {
		tilesInFlight.delete(key);
		triggerRender();
	}
}

onMounted(async () => {
	try {
		const [gridResponse, clustersResponse] = await Promise.all([
			fetch(`${props.tilesBaseUrl}/plenair-map-grid.json`),
			fetch(`${props.dataBaseUrl}/plenair-map-clusters.json`).catch(() => null),
		]);
		if (!gridResponse.ok) throw new Error(`Status ${gridResponse.status}`);
		gridMeta.value = await gridResponse.json();
		if (clustersResponse && clustersResponse.ok) {
			const clusters = await clustersResponse.json();
			// Twee mogelijke vormen: het oude vaste coarse/fine-formaat
			// (plenair-map-clusters.json) of het nieuwe N-laagse formaat
			// (plenair-map-clusters-full.json, alleen een "levels"-array) --
			// in beide gevallen tonen we hier het grofste niveau.
			const raw: ClusterHullItem[] = Array.isArray(clusters) ? clusters : (clusters.levels?.[0] ?? clusters.coarse ?? []);
			// Hull-/centroid-coördinaten staan nog in ruwe UMAP-ruimte (los
			// bestand, niet via de tile-pyramide gegaan) -- omrekenen naar
			// dezelfde Mercator-ruimte als de punten die uit de tiles komen,
			// anders lopen hulls en punten uit elkaar (zie tiledMapTransform.ts).
			const grid = gridMeta.value!;
			coarseClusters.value = raw.map((cluster) => ({
				...cluster,
				centroid: umapToMercator(cluster.centroid[0], cluster.centroid[1], grid),
				hull: cluster.hull ? cluster.hull.map(([hx, hy]) => umapToMercator(hx, hy, grid)) : null,
			}));
		}
		pmtiles = new PMTiles(`${props.tilesBaseUrl}/plenair-map.pmtiles`);
		await pmtiles.getHeader();
		status.value = "ready";
		updateCanvasDimensions();
		setupZoom();
		triggerRender();
	} catch {
		status.value = "error";
	}
	window.addEventListener("resize", updateCanvasDimensions);
});

onUnmounted(() => {
	window.removeEventListener("resize", updateCanvasDimensions);
});

function updateCanvasDimensions() {
	if (!wrapperEl.value) return;
	const rect = wrapperEl.value.getBoundingClientRect();
	canvasWidth.value = Math.max(200, Math.round(rect.width));
	canvasHeight.value = Math.max(200, Math.round(rect.width / 1.618));
	triggerRender();
}

function setupZoom() {
	if (!canvasRef.value) return;
	const selection = select(canvasRef.value);
	d3ZoomBehavior = d3zoom<HTMLCanvasElement, unknown>()
		.scaleExtent([0.5, 64])
		.on("zoom", (event: D3ZoomEvent<HTMLCanvasElement, unknown>) => {
			transform.value = { x: event.transform.x, y: event.transform.y, k: event.transform.k };
			triggerRender();
		});
	selection.call(d3ZoomBehavior).call(d3ZoomBehavior.transform, zoomIdentity);
	selection.on("pointermove", onPointerMove);
	selection.on("pointerleave", () => {
		hoveredPoint.value = null;
		triggerRender();
	});
}

function currentTileZoom(grid: GridMetadata): number {
	const raw = Math.log2((canvasWidth.value * transform.value.k) / grid.tile_size);
	return Math.max(grid.minzoom, Math.min(grid.maxzoom, Math.round(raw)));
}

function ensureVisibleTilesLoaded(grid: GridMetadata) {
	const screenToWorld = makeScreenToWorld(grid, canvasWidth.value, canvasHeight.value, transform.value);
	const [minx, maxy] = screenToWorld(0, 0);
	const [maxx, miny] = screenToWorld(canvasWidth.value, canvasHeight.value);
	const zoom = currentTileZoom(grid);
	const tiles = tilesForWorldRect(grid, zoom, { minx, miny, maxx, maxy });
	for (const tile of tiles) {
		void loadTile(grid, tile);
	}
	return tiles;
}

let rafHandle: number | null = null;
function triggerRender() {
	if (rafHandle != null) return;
	rafHandle = requestAnimationFrame(() => {
		rafHandle = null;
		render();
	});
}

function render() {
	const canvas = canvasRef.value;
	const grid = gridMeta.value;
	if (!canvas || !grid) return;
	const ctx = canvas.getContext("2d");
	if (!ctx) return;

	const dpr = Math.min(2, window.devicePixelRatio || 1);
	canvas.width = canvasWidth.value * dpr;
	canvas.height = canvasHeight.value * dpr;
	canvas.style.width = `${canvasWidth.value}px`;
	canvas.style.height = `${canvasHeight.value}px`;
	ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
	ctx.fillStyle = paper.value;
	ctx.fillRect(0, 0, canvasWidth.value, canvasHeight.value);

	const worldToScreen = makeWorldToScreen(grid, canvasWidth.value, canvasHeight.value, transform.value);
	const tiles = ensureVisibleTilesLoaded(grid);

	// Cluster-hulls (coarse, altijd getoond -- v1 heeft geen fine/coarse
	// crossfade-logica zoals PlenairMap.vue, puur ter oriëntatie).
	ctx.strokeStyle = muted.value;
	ctx.lineWidth = 1;
	ctx.font = "12px system-ui, sans-serif";
	ctx.fillStyle = muted.value;
	for (const cluster of coarseClusters.value) {
		if (cluster.hull && cluster.hull.length > 2) {
			ctx.beginPath();
			cluster.hull.forEach(([hx, hy], i) => {
				const [sx, sy] = worldToScreen(hx, hy);
				if (i === 0) ctx.moveTo(sx, sy);
				else ctx.lineTo(sx, sy);
			});
			ctx.closePath();
			ctx.stroke();
		}
		const [cx, cy] = worldToScreen(cluster.centroid[0], cluster.centroid[1]);
		ctx.fillText(cluster.name, cx, cy);
	}

	// Punten uit alle momenteel zichtbare (en al gedecodeerde) tiles.
	ctx.globalCompositeOperation = "multiply";
	for (const tile of tiles) {
		const points = tileCache.get(tileKeyStr(tile));
		if (!points) continue;
		for (const point of points) {
			const [sx, sy] = worldToScreen(point.x, point.y);
			ctx.beginPath();
			ctx.fillStyle = TOPIC_COLOR[point.topic] ?? DEFAULT_TOPIC_COLOR;
			ctx.globalAlpha = point === hoveredPoint.value ? 1 : 0.75;
			ctx.arc(sx, sy, point === hoveredPoint.value ? 5 : 2.5, 0, Math.PI * 2);
			ctx.fill();
		}
	}
	ctx.globalCompositeOperation = "source-over";
	ctx.globalAlpha = 1;

	if (hoveredPoint.value) {
		const [sx, sy] = worldToScreen(hoveredPoint.value.x, hoveredPoint.value.y);
		ctx.beginPath();
		ctx.strokeStyle = ink.value;
		ctx.lineWidth = 1.5;
		ctx.arc(sx, sy, 7, 0, Math.PI * 2);
		ctx.stroke();
	}
}

function onPointerMove(event: PointerEvent) {
	const canvas = canvasRef.value;
	const grid = gridMeta.value;
	if (!canvas || !grid) return;
	const rect = canvas.getBoundingClientRect();
	const mx = event.clientX - rect.left;
	const my = event.clientY - rect.top;
	const worldToScreen = makeWorldToScreen(grid, canvasWidth.value, canvasHeight.value, transform.value);

	let nearest: DecodedPoint | null = null;
	let nearestDistSq = 15 * 15;
	for (const points of tileCache.values()) {
		for (const point of points) {
			const [sx, sy] = worldToScreen(point.x, point.y);
			const dx = sx - mx;
			const dy = sy - my;
			const distSq = dx * dx + dy * dy;
			if (distSq < nearestDistSq) {
				nearestDistSq = distSq;
				nearest = point;
			}
		}
	}
	if (nearest !== hoveredPoint.value) {
		hoveredPoint.value = nearest;
		triggerRender();
	}
}
</script>

<template>
	<div ref="wrapperEl" class="tiled-plenair-map">
		<p v-if="status === 'loading'">Kaart laden...</p>
		<p v-else-if="status === 'error'">Kon de kaartdata niet laden.</p>
		<canvas ref="canvasRef" />
		<div v-if="hoveredPoint" class="tooltip">
			<strong>{{ hoveredPoint.actor }}</strong> ({{ hoveredPoint.party }}) -- {{ hoveredPoint.debate }}
			<p>{{ hoveredPoint.text }}</p>
		</div>
	</div>
</template>

<style scoped>
.tiled-plenair-map {
	position: relative;
	width: 100%;
}
canvas {
	display: block;
	touch-action: none;
	cursor: crosshair;
}
.tooltip {
	position: absolute;
	bottom: 0.5rem;
	left: 0.5rem;
	right: 0.5rem;
	background: color-mix(in srgb, canvas 85%, transparent);
	border: 1px solid currentColor;
	padding: 0.5rem 0.75rem;
	font-size: 0.85rem;
	pointer-events: none;
}
</style>
