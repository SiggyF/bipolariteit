<script setup lang="ts">
// Alternatief renderpad naast PlenairMap.vue (die ongewijzigd blijft, zie
// issue #215/#253): leest dezelfde brondata niet als één platte JSON, maar
// als een vector-tile-pyramide (.pmtiles, gebouwd door
// `pipeline.tiling.build_pyramid`) op de volle dataset (issue #293/#259).
//
// MapLibre GL i.p.v. een eigen Canvas2D-renderer (v2, zie git-historie voor
// de eerdere eigen d3-zoom/@mapbox-vector-tile-opzet): die had geen
// zoom-debounce (een doorlopend zoomgebaar deed elk tussenliggend
// zoomniveau een eigen volledige tegelronde ophalen) en geen "toon het
// vorige niveau tot het nieuwe geladen is"-gedrag (leeg canvas tijdens het
// laden). MapLibre lost beide al standaard op, plus WebGL-rendering i.p.v.
// canvas-arcs per punt.
import { onMounted, onUnmounted, ref, watch } from "vue";
import maplibregl, { type CircleLayerSpecification, type MapGeoJSONFeature } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { Protocol } from "pmtiles";
import { useTheme } from "../lib/useTheme";
import { DEFAULT_TOPIC_COLOR, TOPIC_COLOR } from "../lib/plenairMapColors";
import { mercatorMetersToLngLat, umapToMercator, type GridMetadata } from "../lib/tiledMapTransform";

const props = defineProps<{
	// pmtiles + grid-metadata + cluster-hulls komen van Hugging Face (volle
	// dataset, zie lib/dataBaseUrl.ts, issue #316/#293) -- deze component
	// gebruikt geen jsDelivr-databasis.
	tilesBaseUrl: string;
}>();

type ClusterHullItem = {
	cluster_id: number;
	name: string;
	centroid: [number, number];
	hull: [number, number][] | null;
};

type HoveredPoint = {
	actor: string;
	party: string;
	debate: string;
	text: string;
};

type FetchStatus = "loading" | "ready" | "error";
const status = ref<FetchStatus>("loading");
const hoveredPoint = ref<HoveredPoint | null>(null);
const mapEl = ref<HTMLDivElement | null>(null);
let map: maplibregl.Map | null = null;

const isDark = useTheme();

// pmtiles://-protocol is proces-breed (maplibregl.addProtocol), niet per
// component-instantie -- dubbel registreren bij een tweede mount (bv.
// Astro view-transition) zou een harmloze maar overbodige herregistratie
// zijn, dit voorkomt dat.
let protocolRegistered = false;
function ensurePmtilesProtocol() {
	if (protocolRegistered) return;
	const protocol = new Protocol();
	maplibregl.addProtocol("pmtiles", protocol.tile);
	protocolRegistered = true;
}

function circlePaint(dark: boolean): CircleLayerSpecification["paint"] {
	return {
		"circle-radius": ["interpolate", ["linear"], ["zoom"], 0, 1.2, 8, 3.5],
		"circle-color": ["match", ["get", "topic"], ...Object.entries(TOPIC_COLOR).flat(), DEFAULT_TOPIC_COLOR],
		// MapLibre's circle-layer ondersteunt geen echte GL-blendmode
		// (screen/multiply) -- benaderd met opaciteit + blur, zelfde truc als
		// het overwogen debugvoorbeeld: donker thema iets lager/wazig (licht
		// laten "oplichten" bij overlap), licht thema steviger/scherp (een
		// "inkt"-indruk van overlappende stippen).
		"circle-opacity": dark ? 0.55 : 0.8,
		"circle-blur": dark ? 0.35 : 0,
	};
}

const THEME_COLOR = {
	light: { bg: "#f7f3ea", muted: "#6f6558" },
	dark: { bg: "#221f1b", muted: "#a89e8c" },
};

function buildClusterGeoJSON(clusters: ClusterHullItem[], grid: GridMetadata) {
	const hullFeatures: GeoJSON.Feature[] = [];
	const labelFeatures: GeoJSON.Feature[] = [];
	for (const cluster of clusters) {
		if (cluster.hull && cluster.hull.length > 2) {
			const ring = cluster.hull.map(([hx, hy]) => mercatorMetersToLngLat(...umapToMercator(hx, hy, grid)));
			ring.push(ring[0]);
			hullFeatures.push({
				type: "Feature",
				properties: { name: cluster.name },
				geometry: { type: "Polygon", coordinates: [ring] },
			});
		}
		labelFeatures.push({
			type: "Feature",
			properties: { name: cluster.name },
			geometry: { type: "Point", coordinates: mercatorMetersToLngLat(...umapToMercator(cluster.centroid[0], cluster.centroid[1], grid)) },
		});
	}
	return {
		hulls: { type: "FeatureCollection", features: hullFeatures } as GeoJSON.FeatureCollection,
		labels: { type: "FeatureCollection", features: labelFeatures } as GeoJSON.FeatureCollection,
	};
}

function toHoveredPoint(feature: MapGeoJSONFeature): HoveredPoint {
	const p = feature.properties as Record<string, unknown>;
	return {
		actor: String(p.actor ?? ""),
		party: String(p.party ?? ""),
		debate: String(p.debate ?? ""),
		text: String(p.text ?? ""),
	};
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
			// in beide gevallen tonen we hier het grofste niveau.
			const raw: ClusterHullItem[] = Array.isArray(clusters) ? clusters : (clusters.levels?.[0] ?? clusters.coarse ?? []);
			({ hulls, labels } = buildClusterGeoJSON(raw, grid));
		}

		if (!mapEl.value) return;
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
					points: {
						type: "vector",
						url: `pmtiles://${props.tilesBaseUrl}/plenair-map-full.pmtiles`,
						maxzoom: grid.maxzoom,
					},
					hulls: { type: "geojson", data: hulls },
					labels: { type: "geojson", data: labels },
				},
				layers: [
					{ id: "bg", type: "background", paint: { "background-color": theme.bg } },
					{ id: "hulls", type: "line", source: "hulls", paint: { "line-color": theme.muted, "line-width": 1 } },
					{ id: "points", type: "circle", source: "points", "source-layer": "points", paint: circlePaint(isDark.value) },
					{
						id: "labels",
						type: "symbol",
						source: "labels",
						layout: {
							"text-field": ["get", "name"],
							"text-font": ["Noto Sans Regular"],
							"text-size": 11,
							"text-anchor": "top",
							"text-allow-overlap": false,
						},
						paint: { "text-color": theme.muted },
					},
				],
			},
			center: [0, 0],
			zoom: 0,
			minZoom: grid.minzoom,
			maxZoom: grid.maxzoom,
			attributionControl: false,
		});
		map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");

		map.on("load", () => {
			status.value = "ready";
		});
		map.on("error", (e) => {
			console.error("TiledPlenairMap MapLibre error", e.error);
			status.value = "error";
		});
		map.on("mousemove", "points", (e) => {
			const feature = e.features?.[0];
			if (!feature) return;
			hoveredPoint.value = toHoveredPoint(feature);
			map!.getCanvas().style.cursor = "pointer";
		});
		map.on("mouseleave", "points", () => {
			hoveredPoint.value = null;
			map!.getCanvas().style.cursor = "";
		});
	} catch (err) {
		console.error("TiledPlenairMap init failed", err);
		status.value = "error";
	}
});

onUnmounted(() => {
	map?.remove();
	map = null;
});

watch(isDark, (dark) => {
	if (!map) return;
	const theme = dark ? THEME_COLOR.dark : THEME_COLOR.light;
	map.setPaintProperty("bg", "background-color", theme.bg);
	map.setPaintProperty("hulls", "line-color", theme.muted);
	map.setPaintProperty("labels", "text-color", theme.muted);
	const paint = circlePaint(dark)!;
	map.setPaintProperty("points", "circle-opacity", paint["circle-opacity"]);
	map.setPaintProperty("points", "circle-blur", paint["circle-blur"]);
});
</script>

<template>
	<div class="tiled-plenair-map">
		<p v-if="status === 'loading'">Kaart laden...</p>
		<p v-else-if="status === 'error'">Kon de kaartdata niet laden.</p>
		<div ref="mapEl" class="map-el" />
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
.map-el {
	width: 100%;
	aspect-ratio: 1.618;
	min-height: 320px;
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
	z-index: 1;
}
</style>
