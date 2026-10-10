<script setup lang="ts">
// Benchmark-/debugpagina voor de tiled plenaire kaart (issue #390): rendert
// TiledPlenairMap.vue exact zoals in productie, vangt de trace-events van de
// kaart op en zet ze naast netwerk-timings en een paar scripted scenario's
// (zoom-sweep, geanimeerd zoomen, pannen). Uitkomsten zijn als JSON te
// downloaden om voor/na-runs te vergelijken.
//
// De meetpunten volgen de Mapbox GL JS-prestatiehandleiding
// (docs.mapbox.com/help/troubleshooting/mapbox-gl-js-performance/): aantal
// bronnen/lagen, vertexaantallen van de GeoJSON-bronnen, tegelgroottes en
// framekosten. De debugvlaggen (collision boxes, tile boundaries, repaint) zijn
// MapLibre's eigen.
import { computed, onMounted, onUnmounted, ref, shallowRef, triggerRef } from "vue";
import type maplibregl from "maplibre-gl";
import TiledPlenairMap from "./TiledPlenairMap.vue";
import { BLEND_DEFAULT_STRENGTH, DEFAULT_POINT_STYLE, type DarkBlend, type LightBlend, type PointStyle } from "../lib/pointStyle";
import {
	firstOccurrences,
	groupResources,
	percentile,
	summarizeTiles,
	type ResourceGroup,
	type ResourceSample,
	type TileStat,
	type TraceEvent,
} from "../lib/tileTrace";

const props = defineProps<{ tilesBaseUrl: string }>();

// Doel uit issue #390: top-level zoom (startaanzicht) binnen 0,3 s zichtbaar.
const TARGET_FIRST_VIEW_MS = 300;
const SCENARIO_TIMEOUT_MS = 10_000;

const events = shallowRef<TraceEvent[]>([]);
const mapRef = ref<InstanceType<typeof TiledPlenairMap> | null>(null);
const resources = shallowRef<ResourceSample[]>([]);
const mountedAt = ref<number | null>(null);

type ScenarioRow = {
	scenario: string;
	label: string;
	loadMs: number | null;
	tiles: number | null;
	points: number | null;
	represented: number | null;
	frames: number | null;
	frameP50: number | null;
	frameP95: number | null;
	frameMax: number | null;
	timedOut: boolean;
};
const scenarioRows = ref<ScenarioRow[]>([]);
const running = ref<string | null>(null);

// Puntgrootte/-kleursterkte, live bij te stellen (geen herlaad nodig).
const pointStyle = ref<PointStyle>({ ...DEFAULT_POINT_STYLE });
const STYLE_SLIDERS: { key: keyof PointStyle; label: string; min: number; max: number; step: number }[] = [
	{ key: "targetOverlap", label: "Doeloverlap licht thema (schijven per pixel, druk punt)", min: 0.2, max: 4, step: 0.05 },
	{ key: "darkTargetOverlap", label: "Doeloverlap donker thema", min: 0.2, max: 4, step: 0.05 },
	{ key: "radiusMin", label: "Minimale straal (px)", min: 0.3, max: 4, step: 0.05 },
	{ key: "radiusMax", label: "Maximale straal (px)", min: 1, max: 10, step: 0.1 },
	{ key: "strength", label: "Kleursterkte of dekking (licht thema)", min: 0.05, max: 1, step: 0.01 },
	{ key: "darkStrength", label: "Helderheid (donker thema)", min: 0.05, max: 1, step: 0.01 },
];
const BLEND_CHOICES = {
	blendLight: [
		{ value: "multiply", label: "Multiply (inkt)" },
		{ value: "mix", label: "Mix (alpha-over)" },
	],
	blendDark: [
		{ value: "max", label: "Max" },
		{ value: "screen", label: "Screen" },
	],
} as const;
const pointStyleJson = computed(() => JSON.stringify(pointStyle.value));
// Een andere blend-modus krijgt meteen de passende sterkte (zie
// BLEND_DEFAULT_STRENGTH); daarna is die met de slider bij te stellen.
function setBlendLight(mode: LightBlend) {
	pointStyle.value.blendLight = mode;
	pointStyle.value.strength = BLEND_DEFAULT_STRENGTH[mode];
}
function setBlendDark(mode: DarkBlend) {
	pointStyle.value.blendDark = mode;
	pointStyle.value.darkStrength = BLEND_DEFAULT_STRENGTH[mode];
}
function resetPointStyle() {
	pointStyle.value = { ...DEFAULT_POINT_STYLE };
}

const flags = ref({ collisionBoxes: false, tileBoundaries: false, repaint: false });

const viewportWaiters: ((event: TraceEvent) => void)[] = [];

function onTrace(event: TraceEvent) {
	if (event.name === "component:mounted") mountedAt.value = event.t;
	events.value.push(event);
	triggerRef(events);
	if (event.name === "viewport:loaded") {
		for (const waiter of viewportWaiters.splice(0)) waiter(event);
	}
}

function getMap(): maplibregl.Map | null {
	return (mapRef.value?.getMap() as maplibregl.Map | null | undefined) ?? null;
}

// --- Milestones ---

const MILESTONES: { name: string; label: string }[] = [
	{ name: "component:mounted", label: "Vue-component gemount (na hydratatie)" },
	{ name: "data:grid+clusters-fetched", label: "grid.json + clusters-full.json opgehaald" },
	{ name: "data:clusters-built", label: "Cluster-hullen/-labels omgerekend" },
	{ name: "map:creating", label: "PMTiles-instantie klaar, MapLibre wordt aangemaakt" },
	{ name: "map:constructed", label: "MapLibre-kaart aangemaakt" },
	{ name: "map:first-render", label: "Eerste render" },
	{ name: "map:load", label: "MapLibre 'load'" },
	{ name: "tile:decoded", label: "Eerste puntentegel gedecodeerd" },
	{ name: "viewport:loaded", label: "Alle tegels in beeld geladen (deck.gl)" },
	{ name: "map:idle", label: "MapLibre 'idle' (alles geladen, stil)" },
	{ name: "data:contours-fetched", label: "Contouren opgehaald" },
];

const milestoneRows = computed(() => {
	const first = firstOccurrences(events.value);
	return MILESTONES.map((m) => ({ ...m, t: first.get(m.name) ?? null })).sort((a, b) => (a.t ?? Infinity) - (b.t ?? Infinity));
});

const firstViewMs = computed(() => firstOccurrences(events.value).get("viewport:loaded") ?? null);
const firstViewSinceMountMs = computed(() => (firstViewMs.value !== null && mountedAt.value !== null ? firstViewMs.value - mountedAt.value : null));

// --- Tegels ---

const tileStats = computed<TileStat[]>(() =>
	events.value.filter((e) => e.name === "tile:decoded").map((e) => e.detail as unknown as TileStat),
);
const zoomSummary = computed(() => summarizeTiles(tileStats.value));
const tileErrors = computed(() => events.value.filter((e) => e.name === "tile:error").length);

// --- Bronnen en kaartconfiguratie ---

const configRows = computed(() => {
	const detail = (name: string) => events.value.find((e) => e.name === name)?.detail;
	const built = detail("data:clusters-built");
	const contours = events.value.filter((e) => e.name === "data:contours-fetched");
	const constructed = detail("map:load");
	const creating = detail("map:creating");
	const gridFetched = detail("data:grid+clusters-fetched");
	const cacheEvents = events.value.filter((e) => e.name === "pmtiles:cache");
	const rows: { key: string; value: string }[] = [];
	if (gridFetched) rows.push({ key: "Ink-tabel in grid.json", value: gridFetched.ink === "grid" ? "ja, uit grid.json" : "nee, ingebouwde meting (pas publiceren na make tiles-full)" });
	if (cacheEvents.length) {
		const hits = cacheEvents.filter((e) => e.detail?.hit).length;
		const bytesHit = cacheEvents.filter((e) => e.detail?.hit).reduce((sum, e) => sum + Number(e.detail?.length ?? 0), 0);
		rows.push({
			key: "Tegelcache: treffers / missers (bytes uit cache)",
			value: `${hits} / ${cacheEvents.length - hits} (${(bytesHit / 1024).toFixed(0)} kB)`,
		});
	}
	if (creating) rows.push({ key: "Puntentegel px (render / pyramide)", value: `${creating.tileSize} / ${creating.gridTileSize}` });
	if (constructed && constructed.layers !== null) rows.push({ key: "MapLibre-lagen / -bronnen", value: `${constructed.layers} / ${constructed.sources}` });
	if (built) {
		rows.push({ key: "Clusters (niveau 0)", value: String(built.clusters) });
		rows.push({ key: "Hull-vertices (GeoJSON-bron)", value: String(built.hullVertices) });
		rows.push({ key: "Labels", value: String(built.labels) });
	}
	for (const e of contours) {
		const d = e.detail as { kind: string; features: number; vertices: number };
		rows.push({ key: `Contouren ${d.kind}: features / vertices`, value: `${d.features} / ${d.vertices}` });
	}
	rows.push({ key: "devicePixelRatio", value: String(window.devicePixelRatio) });
	const canvas = getMap()?.getCanvas();
	if (canvas) rows.push({ key: "Canvas (px)", value: `${canvas.width} x ${canvas.height}` });
	return rows;
});

const glRenderer = ref("");
function readGlRenderer() {
	const gl = getMap()?.getCanvas().getContext("webgl2") ?? getMap()?.getCanvas().getContext("webgl");
	const ext = gl?.getExtension("WEBGL_debug_renderer_info");
	glRenderer.value = gl && ext ? String(gl.getParameter(ext.UNMASKED_RENDERER_WEBGL)) : "onbekend";
}

// --- Netwerk ---

let observer: PerformanceObserver | null = null;
const resourceGroups = computed<ResourceGroup[]>(() => groupResources(resources.value));

function collectResources(entries: PerformanceEntryList) {
	const kept: ResourceSample[] = [];
	for (const entry of entries as PerformanceResourceTiming[]) {
		if (entry.initiatorType !== "fetch" && entry.initiatorType !== "xmlhttprequest") continue;
		kept.push({
			name: entry.name,
			startTime: entry.startTime,
			responseEnd: entry.responseEnd,
			duration: entry.duration,
			transferSize: entry.transferSize,
			encodedBodySize: entry.encodedBodySize,
		});
	}
	if (kept.length) resources.value = [...resources.value, ...kept];
}

// --- Debugvlaggen ---

function applyFlags() {
	const map = getMap();
	if (!map) return;
	map.showCollisionBoxes = flags.value.collisionBoxes;
	map.showTileBoundaries = flags.value.tileBoundaries;
	map.repaint = flags.value.repaint;
}

// --- Scenario's ---

function waitForViewport(): Promise<TraceEvent | null> {
	return new Promise((resolve) => {
		const timer = window.setTimeout(() => resolve(null), SCENARIO_TIMEOUT_MS);
		viewportWaiters.push((event) => {
			window.clearTimeout(timer);
			resolve(event);
		});
	});
}

// Verzamelt render-tijdstippen tijdens `during()`; de intervallen daartussen
// zijn de frametijden (MapLibre rendert alleen als er iets verandert, dus dit
// meet alleen echte frames tijdens een animatie of laadgolf).
async function measureFrames(map: maplibregl.Map, during: () => Promise<void>) {
	const stamps: number[] = [];
	const onRender = () => stamps.push(performance.now());
	map.on("render", onRender);
	try {
		await during();
	} finally {
		map.off("render", onRender);
	}
	const deltas = stamps.slice(1).map((t, i) => t - stamps[i]);
	return {
		frames: stamps.length,
		frameP50: deltas.length ? percentile(deltas, 50) : null,
		frameP95: deltas.length ? percentile(deltas, 95) : null,
		frameMax: deltas.length ? Math.max(...deltas) : null,
	};
}

const nextFrame = () => new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));

async function runScenario(name: string, body: (map: maplibregl.Map) => Promise<void>) {
	const map = getMap();
	if (!map || running.value) return;
	running.value = name;
	const center = map.getCenter();
	const zoom = map.getZoom();
	try {
		await body(map);
	} finally {
		map.jumpTo({ center, zoom });
		running.value = null;
	}
}

async function runZoomSweep() {
	await runScenario("zoom-sweep", async (map) => {
		const from = Math.ceil(map.getMinZoom());
		const to = Math.floor(map.getMaxZoom());
		for (let z = from; z <= to; z++) {
			const started = performance.now();
			let loaded: TraceEvent | null = null;
			const frames = await measureFrames(map, async () => {
				const waiting = waitForViewport();
				map.jumpTo({ zoom: z });
				loaded = await waiting;
			});
			const detail = (loaded as TraceEvent | null)?.detail as { tiles: number; points: number; represented: number } | undefined;
			scenarioRows.value.push({
				scenario: "zoom-sweep",
				label: `zoom ${z}`,
				loadMs: loaded ? (loaded as TraceEvent).t - started : null,
				tiles: detail?.tiles ?? null,
				points: detail?.points ?? null,
				represented: detail?.represented ?? null,
				timedOut: loaded === null,
				...frames,
			});
		}
	});
}

async function runAnimatedZoom() {
	await runScenario("animated-zoom", async (map) => {
		const start = Math.ceil(map.getMinZoom());
		map.jumpTo({ zoom: start });
		await waitForViewport();
		const frames = await measureFrames(map, async () => {
			const done = new Promise<void>((resolve) => map.once("moveend", () => resolve()));
			map.easeTo({ zoom: Math.min(start + 4, map.getMaxZoom()), duration: 3000 });
			await done;
		});
		scenarioRows.value.push({
			scenario: "animated-zoom",
			label: `zoom ${start} naar ${Math.min(start + 4, map.getMaxZoom())} in 3 s`,
			loadMs: null,
			tiles: null,
			points: null,
			represented: null,
			timedOut: false,
			...frames,
		});
	});
}

async function runPan() {
	await runScenario("pan", async (map) => {
		const z = Math.min(Math.ceil(map.getMinZoom()) + 3, map.getMaxZoom());
		map.jumpTo({ zoom: z });
		await waitForViewport();
		const frames = await measureFrames(map, async () => {
			for (let i = 0; i < 20; i++) {
				map.panBy([(i % 2 ? -1 : 1) * 180, 60], { duration: 0 });
				await nextFrame();
				await nextFrame();
			}
			await waitForViewport();
		});
		scenarioRows.value.push({
			scenario: "pan",
			label: `20 pan-stappen op zoom ${z}`,
			loadMs: null,
			tiles: null,
			points: null,
			represented: null,
			timedOut: false,
			...frames,
		});
	});
}

// --- Export ---

function downloadJson() {
	const payload = {
		takenAt: new Date().toISOString(),
		userAgent: navigator.userAgent,
		devicePixelRatio: window.devicePixelRatio,
		glRenderer: glRenderer.value,
		firstViewMs: firstViewMs.value,
		firstViewSinceMountMs: firstViewSinceMountMs.value,
		milestones: milestoneRows.value,
		zoomSummary: zoomSummary.value,
		resources: resourceGroups.value,
		scenarios: scenarioRows.value,
		pointStyle: pointStyle.value,
		config: configRows.value,
		events: events.value,
	};
	const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
	const link = document.createElement("a");
	link.href = URL.createObjectURL(blob);
	link.download = `tiled-layer-benchmark-${payload.takenAt.replace(/[:.]/g, "-")}.json`;
	link.click();
	URL.revokeObjectURL(link.href);
}

function reloadCold() {
	window.location.reload();
}

// --- Opmaak ---

const ms = (value: number | null, digits = 0) => (value === null ? "n.v.t." : `${value.toFixed(digits)} ms`);
const kb = (bytes: number) => (bytes ? `${(bytes / 1024).toFixed(0)} kB` : "n.v.t.");
const recentEvents = computed(() => events.value.slice(-200));

onMounted(() => {
	if (typeof PerformanceObserver === "undefined") return;
	collectResources(performance.getEntriesByType("resource"));
	observer = new PerformanceObserver((list) => collectResources(list.getEntries()));
	observer.observe({ type: "resource", buffered: false });
	// getMap() is pas na de async init van de kaart gevuld; zodra MapLibre
	// 'load' meldt weten we dat de GL-context er is.
	const poll = window.setInterval(() => {
		if (getMap()) {
			window.clearInterval(poll);
			readGlRenderer();
			applyFlags();
		}
	}, 200);
});

onUnmounted(() => observer?.disconnect());
</script>

<template>
	<div class="tlb">
		<header class="tlb-header">
			<h1>Tiled-laag benchmark</h1>
			<p class="tlb-sub">
				Dezelfde <code>TiledPlenairMap</code> als op <code>/onderwerpen/</code>, met meetpunten. Doel (issue #390): startaanzicht binnen
				{{ TARGET_FIRST_VIEW_MS }} ms zichtbaar.
			</p>
			<p v-if="firstViewMs !== null" class="tlb-verdict" :class="firstViewSinceMountMs !== null && firstViewSinceMountMs <= TARGET_FIRST_VIEW_MS ? 'ok' : 'slow'">
				Startaanzicht compleet na {{ ms(firstViewMs) }} sinds navigatiestart, {{ ms(firstViewSinceMountMs) }} sinds mount van de component.
			</p>
		</header>

		<TiledPlenairMap ref="mapRef" :tiles-base-url="props.tilesBaseUrl" :point-style="pointStyle" @trace="onTrace" />

		<section class="tlb-section">
			<h2>Puntstijl</h2>
			<p class="tlb-note">
				De straal volgt uit de gemeten inktdichtheid per zoomniveau (<code>ink</code> in grid.json); zonder die tabel gebruikt de kaart een
				ingebouwde meting van de huidige pyramide. Alleen het lichte thema gebruikt de kleursterkte; het donkere thema tekent altijd de volle
				kleur (zie #373). Het resultaat gaat mee in de JSON-download.
			</p>
			<div class="tlb-sliders">
				<label v-for="slider in STYLE_SLIDERS" :key="slider.key">
					<span>{{ slider.label }}: <strong>{{ pointStyle[slider.key].toFixed(2) }}</strong></span>
					<input v-model.number="pointStyle[slider.key]" type="range" :min="slider.min" :max="slider.max" :step="slider.step" />
				</label>
			</div>
			<div class="tlb-blend">
				<div>
					<span class="tlb-blend-title">Blend licht thema</span>
					<button
						v-for="choice in BLEND_CHOICES.blendLight"
						:key="choice.value"
						:class="{ active: pointStyle.blendLight === choice.value }"
						@click="setBlendLight(choice.value)"
					>
						{{ choice.label }}
					</button>
				</div>
				<div>
					<span class="tlb-blend-title">Blend donker thema</span>
					<button
						v-for="choice in BLEND_CHOICES.blendDark"
						:key="choice.value"
						:class="{ active: pointStyle.blendDark === choice.value }"
						@click="setBlendDark(choice.value)"
					>
						{{ choice.label }}
					</button>
				</div>
			</div>
			<p class="tlb-note"><button @click="resetPointStyle">Terug naar standaard</button> <code>{{ pointStyleJson }}</code></p>
		</section>

		<section class="tlb-section">
			<h2>Acties</h2>
			<div class="tlb-actions">
				<button :disabled="!!running" @click="runZoomSweep">Zoom-sweep</button>
				<button :disabled="!!running" @click="runAnimatedZoom">Geanimeerd zoomen</button>
				<button :disabled="!!running" @click="runPan">Pannen</button>
				<button @click="reloadCold">Herlaad (koude start)</button>
				<button @click="downloadJson">Download JSON</button>
				<span v-if="running" class="tlb-running">Bezig: {{ running }}</span>
			</div>
			<div class="tlb-flags">
				<label><input v-model="flags.collisionBoxes" type="checkbox" @change="applyFlags" /> Collision boxes</label>
				<label><input v-model="flags.tileBoundaries" type="checkbox" @change="applyFlags" /> Tegelgrenzen (alleen MapLibre-lagen)</label>
				<label><input v-model="flags.repaint" type="checkbox" @change="applyFlags" /> Continu hertekenen</label>
			</div>
		</section>

		<section class="tlb-section">
			<h2>Opstart</h2>
			<table>
				<thead>
					<tr><th>Mijlpaal</th><th class="num">Sinds navigatiestart</th><th class="num">Sinds mount</th></tr>
				</thead>
				<tbody>
					<tr v-for="row in milestoneRows" :key="row.name">
						<td>{{ row.label }}</td>
						<td class="num">{{ ms(row.t) }}</td>
						<td class="num">{{ row.t !== null && mountedAt !== null ? ms(row.t - mountedAt) : "n.v.t." }}</td>
					</tr>
				</tbody>
			</table>
		</section>

		<section class="tlb-section">
			<h2>Tegels per zoomniveau</h2>
			<p class="tlb-note">
				Punten = getekende punten; vertegenwoordigd = som van <code>point_count</code>. Bij een goed gebalanceerde uitdunning hoort
				<em>vertegenwoordigd</em> per zoomniveau ongeveer gelijk te blijven aan het totaal.
				<span v-if="tileErrors">{{ tileErrors }} tegelfout(en).</span>
			</p>
			<table>
				<thead>
					<tr>
						<th>Zoom</th><th class="num">Tegels</th><th class="num">Punten</th><th class="num">Vertegenw.</th><th class="num">Grootte</th>
						<th class="num">Fetch p50 / p95</th><th class="num">Decode p50 / p95</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="row in zoomSummary" :key="row.z">
						<td>{{ row.z }}</td>
						<td class="num">{{ row.tiles }}</td>
						<td class="num">{{ row.points.toLocaleString("nl-NL") }}</td>
						<td class="num">{{ row.represented.toLocaleString("nl-NL") }}</td>
						<td class="num">{{ kb(row.bytes) }}</td>
						<td class="num">{{ row.fetchP50.toFixed(0) }} / {{ row.fetchP95.toFixed(0) }} ms</td>
						<td class="num">{{ row.decodeP50.toFixed(1) }} / {{ row.decodeP95.toFixed(1) }} ms</td>
					</tr>
				</tbody>
			</table>
		</section>

		<section v-if="scenarioRows.length" class="tlb-section">
			<h2>Scenario's</h2>
			<table>
				<thead>
					<tr>
						<th>Scenario</th><th>Stap</th><th class="num">Tot geladen</th><th class="num">Tegels</th><th class="num">Punten</th>
						<th class="num">Vertegenw.</th><th class="num">Frames</th><th class="num">Frame p50 / p95 / max</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="(row, i) in scenarioRows" :key="i" :class="{ timeout: row.timedOut }">
						<td>{{ row.scenario }}</td>
						<td>{{ row.label }}<span v-if="row.timedOut"> (timeout)</span></td>
						<td class="num">{{ ms(row.loadMs) }}</td>
						<td class="num">{{ row.tiles ?? "n.v.t." }}</td>
						<td class="num">{{ row.points?.toLocaleString("nl-NL") ?? "n.v.t." }}</td>
						<td class="num">{{ row.represented?.toLocaleString("nl-NL") ?? "n.v.t." }}</td>
						<td class="num">{{ row.frames ?? "n.v.t." }}</td>
						<td class="num">
							{{ row.frameP50 === null ? "n.v.t." : `${row.frameP50.toFixed(1)} / ${row.frameP95?.toFixed(1)} / ${row.frameMax?.toFixed(1)} ms` }}
						</td>
					</tr>
				</tbody>
			</table>
		</section>

		<section class="tlb-section">
			<h2>Netwerk (fetch/XHR)</h2>
			<p class="tlb-note">Een pmtiles-bestand verschijnt als veel range-verzoeken onder dezelfde naam. Cross-origin zonder Timing-Allow-Origin geeft geen groottes.</p>
			<table>
				<thead>
					<tr><th>Bestand</th><th class="num">Verzoeken</th><th class="num">Overdracht</th><th class="num">Langste</th><th class="num">Eerste start</th><th class="num">Laatste klaar</th></tr>
				</thead>
				<tbody>
					<tr v-for="g in resourceGroups" :key="g.file">
						<td>{{ g.file }}</td>
						<td class="num">{{ g.requests }}</td>
						<td class="num">{{ kb(g.transferBytes) }}</td>
						<td class="num">{{ g.maxDurationMs.toFixed(0) }} ms</td>
						<td class="num">{{ g.firstStartMs.toFixed(0) }} ms</td>
						<td class="num">{{ g.lastEndMs.toFixed(0) }} ms</td>
					</tr>
				</tbody>
			</table>
		</section>

		<section class="tlb-section">
			<h2>Kaartconfiguratie</h2>
			<table>
				<tbody>
					<tr v-for="row in configRows" :key="row.key"><td>{{ row.key }}</td><td class="num">{{ row.value }}</td></tr>
					<tr><td>WebGL-renderer</td><td class="num">{{ glRenderer || "n.v.t." }}</td></tr>
				</tbody>
			</table>
		</section>

		<section class="tlb-section">
			<details>
				<summary>Ruwe events (laatste {{ recentEvents.length }} van {{ events.length }})</summary>
				<pre class="tlb-log">{{ recentEvents.map((e) => `${e.t.toFixed(0).padStart(6)} ms  ${e.name}${e.detail ? "  " + JSON.stringify(e.detail) : ""}`).join("\n") }}</pre>
			</details>
		</section>
	</div>
</template>

<style scoped>
.tlb {
	display: flex;
	flex-direction: column;
	gap: 1.25rem;
	margin: 0 auto;
	max-width: 1200px;
	padding: 1.5rem 1rem;
}
.tlb-sub,
.tlb-note {
	margin: 0.35rem 0 0;
	font-size: 0.9rem;
	color: var(--galnoot-zacht);
}
.tlb-verdict {
	margin: 0.5rem 0 0;
	padding: 0.4rem 0.7rem;
	border: 1px solid var(--lijn);
	border-radius: 6px;
	font-weight: 600;
}
.tlb-verdict.ok {
	border-color: #2e7d32;
}
.tlb-verdict.slow {
	border-color: #c62828;
}
.tlb-section h2 {
	font-size: 1.05rem;
	margin: 0 0 0.5rem;
}
.tlb-sliders {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
	gap: 0.6rem 1.25rem;
}
.tlb-blend {
	display: flex;
	flex-wrap: wrap;
	gap: 0.6rem 1.5rem;
	margin-top: 0.75rem;
}
.tlb-blend-title {
	margin-right: 0.5rem;
	font-size: 0.88rem;
}
.tlb-blend button.active {
	font-weight: 700;
	outline: 2px solid currentColor;
}
.tlb-sliders label {
	display: flex;
	flex-direction: column;
	gap: 0.15rem;
	font-size: 0.88rem;
}
.tlb-actions,
.tlb-flags {
	display: flex;
	flex-wrap: wrap;
	gap: 0.6rem;
	align-items: center;
	margin-bottom: 0.5rem;
}
.tlb-running {
	font-style: italic;
}
table {
	width: 100%;
	border-collapse: collapse;
	font-size: 0.88rem;
}
th,
td {
	text-align: left;
	padding: 0.3rem 0.5rem;
	border-bottom: 1px solid var(--lijn);
}
.num {
	text-align: right;
	font-variant-numeric: tabular-nums;
}
tr.timeout td {
	color: #c62828;
}
.tlb-log {
	max-height: 360px;
	overflow: auto;
	font-size: 0.78rem;
	background: var(--color-surface);
	border: 1px solid var(--lijn);
	border-radius: 6px;
	padding: 0.5rem;
}
</style>
