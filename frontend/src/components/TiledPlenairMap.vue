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
import { onMounted, onUnmounted, ref, watch } from "vue";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { PMTiles, Protocol } from "pmtiles";
import { VectorTile } from "@mapbox/vector-tile";
import { PbfReader } from "pbf";
import { TileLayer } from "@deck.gl/geo-layers";
import { ScatterplotLayer } from "@deck.gl/layers";
import { MapboxOverlay } from "@deck.gl/mapbox";
import { useTheme } from "../lib/useTheme";
import { DEFAULT_TOPIC_COLOR, TOPIC_COLOR } from "../lib/plenairMapColors";
import {
	mercatorMetersToLngLat,
	tileBoundsMeters,
	tileLocalToLngLat,
	umapToMercator,
	type GridMetadata,
	type TileIndex,
} from "../lib/tiledMapTransform";

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

type DeckPoint = {
	position: [number, number];
	topic: string;
	actor: string;
	party: string;
	debate: string;
	text: string;
};

type HoveredPoint = Pick<DeckPoint, "actor" | "party" | "debate" | "text">;

type FetchStatus = "loading" | "ready" | "error";
const status = ref<FetchStatus>("loading");
const hoveredPoint = ref<HoveredPoint | null>(null);
const mapEl = ref<HTMLDivElement | null>(null);
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
	// "Inkt"-indruk op een lichte achtergrond: result = src * dst (vermenigvuldigen)
	// -- overlappende stippen worden donkerder, niet lichter.
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

function hexToRgba(hex: string, alpha: number): [number, number, number, number] {
	const r = parseInt(hex.slice(1, 3), 16);
	const g = parseInt(hex.slice(3, 5), 16);
	const b = parseInt(hex.slice(5, 7), 16);
	return [r, g, b, Math.round(alpha * 255)];
}

function topicColorRgba(topic: string): [number, number, number, number] {
	const hex = TOPIC_COLOR[topic] ?? DEFAULT_TOPIC_COLOR;
	return hexToRgba(hex, 0.85);
}

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
			position,
			topic: String(p.topic ?? ""),
			actor: String(p.actor ?? ""),
			party: String(p.party ?? ""),
			debate: String(p.debate ?? ""),
			text: String(p.text ?? ""),
		});
	}
	return points;
}

function buildPointsLayer(grid: GridMetadata): TileLayer {
	return new TileLayer<DeckPoint[]>({
		id: "plenair-points",
		getTileData,
		minZoom: grid.minzoom,
		maxZoom: grid.maxzoom,
		tileSize: grid.tile_size,
		renderSubLayers: (subProps) => {
			const zoom = subProps.tile.index.z;
			// Zelfde interpolatie als de eerdere MapLibre-circle-radius (1.2px op
			// het grofste niveau, 3.5px op het fijnste).
			const t = grid.maxzoom > grid.minzoom ? (zoom - grid.minzoom) / (grid.maxzoom - grid.minzoom) : 0;
			const radius = 1.2 + t * (3.5 - 1.2);
			return new ScatterplotLayer<DeckPoint>({
				id: `${subProps.id}-scatter`,
				data: subProps.data,
				getPosition: (d) => d.position,
				getFillColor: (d) => topicColorRgba(d.topic),
				getRadius: radius,
				radiusUnits: "pixels",
				pickable: true,
				parameters: isDark.value ? BLEND_PARAMETERS.dark : BLEND_PARAMETERS.light,
			});
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
			// in beide gevallen tonen we hier het grofste niveau.
			const raw: ClusterHullItem[] = Array.isArray(clusters) ? clusters : (clusters.levels?.[0] ?? clusters.coarse ?? []);
			({ hulls, labels } = buildClusterGeoJSON(raw, grid));
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

		deckOverlay = new MapboxOverlay({
			interleaved: false,
			layers: [buildPointsLayer(grid)],
			getTooltip: () => null,
			onHover: (info) => {
				hoveredPoint.value = (info.object as DeckPoint | undefined) ?? null;
				if (map) map.getCanvas().style.cursor = info.object ? "pointer" : "";
			},
		});
		map.addControl(deckOverlay);

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
			map.setPaintProperty("labels", "text-color", t.muted);
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
