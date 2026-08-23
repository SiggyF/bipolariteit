<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { scaleThreshold } from "d3-scale";
import { select } from "d3-selection";
import { zoom as d3zoom, zoomIdentity, type D3ZoomEvent } from "d3-zoom";
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
	topicIdx: number;
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

const props = withDefaults(
	defineProps<{
		dataBaseUrl?: string;
	}>(),
	{
		dataBaseUrl: "/data",
	}
);

type RenderMethod = "echarts" | "webgl" | "canvas2d" | "css_transform" | "hybrid" | "d3_canvas";
const selectedMethod = ref<RenderMethod>("hybrid");

const status = ref<"loading" | "ready" | "error">("loading");
const pointsData = ref<RawExport>({ topics: [], actors: [], parties: [], debates: [], soorten: [], points: [] });
const clustersData = ref<ClustersExport | null>(null);

const TOPIC_COLOR: Record<string, string> = {
	stikstof: "#4a7a4a",
	abortus: "#a64d5f",
	asiel: "#c07a2e",
	energietransitie: "#3d6e8f",
	plenair: "#a89e8c",
};

const TOPIC_RGB: Record<string, [number, number, number]> = {
	stikstof: [74 / 255, 122 / 255, 74 / 255],
	abortus: [166 / 255, 77 / 255, 95 / 255],
	asiel: [192 / 255, 122 / 255, 46 / 255],
	energietransitie: [61 / 255, 110 / 255, 143 / 255],
	plenair: [168 / 255, 158 / 255, 140 / 255],
};

const pointLimit = ref<number>(40000);
const hullMode = ref<"none" | "coarse" | "fine" | "semantic">("semantic");
const showLabels = ref(true);

const isDark = useTheme();
const ink = computed(() => (isDark.value ? "#f2ede3" : "#221f1b"));

// Canvas Viewport State (Zoom & Pan)
const zoom = ref(1);
const panX = ref(0);
const panY = ref(0);

// CSS Transform temporary interaction state
const gestureTranslateX = ref(0);
const gestureTranslateY = ref(0);
const gestureScale = ref(1);
const isGestureActive = ref(false);
let settleTimer: any = null;

// Performance Metrics
const fps = ref(60);
const frameTimeMs = ref(0);
const avgFrameTimeMs = ref(0);
const p95FrameTimeMs = ref(0);
const frameHistory: number[] = [];
let perfAnimationFrameId: number | null = null;
let lastPerfTime = performance.now();

// Automated Stress Test state
const isRunningStressTest = ref(false);
const stressTestReport = ref<string | null>(null);

const wrapperEl = ref<HTMLElement | null>(null);
const webglCanvasRef = ref<HTMLCanvasElement | null>(null);
const canvas2dRef = ref<HTMLCanvasElement | null>(null);
const d3CanvasRef = ref<HTMLCanvasElement | null>(null);
const hybridWebglCanvasRef = ref<HTMLCanvasElement | null>(null);
const chartRef = ref<any>(null);
let d3ZoomBehavior: any = null;

const canvasWidth = ref(800);
const canvasHeight = ref(500);
const canvasAspectRatio = computed(() => (canvasHeight.value > 0 ? canvasWidth.value / canvasHeight.value : 1.618));

// Data Decoding
onMounted(async () => {
	try {
		const [pointsResponse, clustersResponse] = await Promise.all([
			fetch(`${props.dataBaseUrl}/plenair-map.json`),
			fetch(`${props.dataBaseUrl}/plenair-map-clusters.json`),
		]);
		if (!pointsResponse.ok || !clustersResponse.ok) throw new Error("Fetch error");
		pointsData.value = await pointsResponse.json();
		clustersData.value = await clustersResponse.json();
		status.value = "ready";
	} catch {
		status.value = "error";
	}
});

const decodedPoints = computed<PlenairPoint[]>(() => {
	const raw = pointsData.value;
	if (!raw.points.length) return [];
	const limit = Math.min(raw.points.length, pointLimit.value);
	const xScale = canvasAspectRatio.value > 0 ? canvasAspectRatio.value : 1.618;
	const pts: PlenairPoint[] = new Array(limit);

	for (let i = 0; i < limit; i++) {
		const [id, x, y, topicIdx, actorIdx, partyIdx, debateIdx, soortIdx, published_at, text, cluster] = raw.points[i];
		pts[i] = {
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
		};
	}
	return pts;
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

// Coarse & Fine Clusters with X-scaling
function scaleClusterX(items: ClusterHullItem[], xScale: number): ClusterHullItem[] {
	return items.map((c) => ({
		...c,
		centroid: [c.centroid[0] * xScale, c.centroid[1]] as [number, number],
		hull: c.hull ? c.hull.map(([hx, hy]) => [hx * xScale, hy] as [number, number]) : null,
	}));
}

const coarseClusters = computed<ClusterHullItem[]>(() => {
	if (!clustersData.value || !clustersData.value.coarse) return [];
	return scaleClusterX(clustersData.value.coarse, canvasAspectRatio.value);
});

const fineClusters = computed<ClusterHullItem[]>(() => {
	if (!clustersData.value || !clustersData.value.fine) return [];
	return scaleClusterX(clustersData.value.fine, canvasAspectRatio.value);
});

// Coordinate projection helper for Canvas2D / SVG overlay
function worldToScreen(wx: number, wy: number): [number, number] {
	const b = rawBounds.value;
	const w = canvasWidth.value;
	const h = canvasHeight.value;

	// Center normalized: [-1, 1]
	const nx = (wx - b.cx) / (b.spanX / 2);
	const ny = (wy - b.cy) / (b.spanY / 2);

	// Apply Zoom and Pan
	const sx = w / 2 + nx * (w / 2) * zoom.value + panX.value;
	const sy = h / 2 - ny * (h / 2) * zoom.value + panY.value; // inverted Y
	return [sx, sy];
}

function screenToWorld(sx: number, sy: number): [number, number] {
	const b = rawBounds.value;
	const w = canvasWidth.value;
	const h = canvasHeight.value;

	const nx = (sx - w / 2 - panX.value) / ((w / 2) * zoom.value);
	const ny = -(sy - h / 2 - panY.value) / ((h / 2) * zoom.value);

	const wx = b.cx + nx * (b.spanX / 2);
	const wy = b.cy + ny * (b.spanY / 2);
	return [wx, wy];
}

// -------------------------------------------------------------
// Performance Monitoring Loop
// -------------------------------------------------------------
function startPerfMonitoring() {
	let frames = 0;
	let lastSecond = performance.now();

	function loop(time: number) {
		const delta = time - lastPerfTime;
		lastPerfTime = time;

		frameTimeMs.value = Math.round(delta * 10) / 10;
		frameHistory.push(delta);
		if (frameHistory.length > 120) frameHistory.shift();

		frames++;
		if (time - lastSecond >= 500) {
			fps.value = Math.round((frames * 1000) / (time - lastSecond));
			frames = 0;
			lastSecond = time;

			if (frameHistory.length > 0) {
				const sum = frameHistory.reduce((a, b) => a + b, 0);
				avgFrameTimeMs.value = Math.round((sum / frameHistory.length) * 10) / 10;
				const sorted = [...frameHistory].sort((a, b) => a - b);
				const p95Idx = Math.floor(sorted.length * 0.95);
				p95FrameTimeMs.value = Math.round(sorted[p95Idx] * 10) / 10;
			}
		}

		perfAnimationFrameId = requestAnimationFrame(loop);
	}
	perfAnimationFrameId = requestAnimationFrame(loop);
}

onMounted(() => {
	startPerfMonitoring();
	updateCanvasDimensions();
	window.addEventListener("resize", updateCanvasDimensions);
});

onUnmounted(() => {
	if (perfAnimationFrameId != null) cancelAnimationFrame(perfAnimationFrameId);
	window.removeEventListener("resize", updateCanvasDimensions);
});

function updateCanvasDimensions() {
	if (wrapperEl.value) {
		const rect = wrapperEl.value.getBoundingClientRect();
		canvasWidth.value = Math.max(300, rect.width);
		canvasHeight.value = Math.max(300, rect.height || 520);
	}
}

// -------------------------------------------------------------
// METHOD 2 & 5: WebGL Point Renderer Engine
// -------------------------------------------------------------
const VS_SOURCE = `
attribute vec2 a_position;
attribute vec3 a_color;
attribute float a_size;
uniform mat3 u_matrix;
varying vec3 v_color;

void main() {
    vec3 pos = u_matrix * vec3(a_position, 1.0);
    gl_Position = vec4(pos.xy, 0.0, 1.0);
    gl_PointSize = a_size;
    v_color = a_color;
}
`;

const FS_SOURCE = `
precision mediump float;
varying vec3 v_color;

void main() {
    vec2 coord = gl_PointCoord - vec2(0.5);
    if (length(coord) > 0.5) {
        discard;
    }
    gl_FragColor = vec4(v_color, 0.75);
}
`;

let glContext: WebGLRenderingContext | null = null;
let glProgram: WebGLProgram | null = null;
let glBuffer: WebGLBuffer | null = null;
let glPointCount = 0;

let hybridGlContext: WebGLRenderingContext | null = null;
let hybridGlProgram: WebGLProgram | null = null;
let hybridGlBuffer: WebGLBuffer | null = null;
let hybridGlPointCount = 0;

function initWebGL(canvas: HTMLCanvasElement): { gl: WebGLRenderingContext; prog: WebGLProgram; buf: WebGLBuffer } | null {
	const gl = canvas.getContext("webgl", { antialias: true, alpha: true });
	if (!gl) return null;

	const vs = gl.createShader(gl.VERTEX_SHADER)!;
	gl.shaderSource(vs, VS_SOURCE);
	gl.compileShader(vs);

	const fs = gl.createShader(gl.FRAGMENT_SHADER)!;
	gl.shaderSource(fs, FS_SOURCE);
	gl.compileShader(fs);

	const prog = gl.createProgram()!;
	gl.attachShader(prog, vs);
	gl.attachShader(prog, fs);
	gl.linkProgram(prog);

	gl.enable(gl.BLEND);
	gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

	const buf = gl.createBuffer()!;
	return { gl, prog, buf };
}

function updateWebGLData(gl: WebGLRenderingContext, prog: WebGLProgram, buf: WebGLBuffer, pts: PlenairPoint[], isHybrid = false) {
	const stride = 6; // x, y, r, g, b, size
	const filterPts = isHybrid ? pts.filter((p) => p.topic === "plenair") : pts;
	const count = filterPts.length;
	const data = new Float32Array(count * stride);
	const b = rawBounds.value;

	for (let i = 0; i < count; i++) {
		const p = filterPts[i];
		// Normalize to [-1, 1] relative to center
		const nx = (p.x - b.cx) / (b.spanX / 2);
		const ny = (p.y - b.cy) / (b.spanY / 2);
		const rgb = TOPIC_RGB[p.topic] || TOPIC_RGB.plenair;
		const sz = p.topic === "plenair" ? 4.5 : 8.5;

		const idx = i * stride;
		data[idx] = nx;
		data[idx + 1] = ny;
		data[idx + 2] = rgb[0];
		data[idx + 3] = rgb[1];
		data[idx + 4] = rgb[2];
		data[idx + 5] = sz;
	}

	gl.bindBuffer(gl.ARRAY_BUFFER, buf);
	gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
	return count;
}

function renderWebGL(gl: WebGLRenderingContext, prog: WebGLProgram, buf: WebGLBuffer, count: number) {
	if (!gl || !prog || count === 0) return;
	gl.viewport(0, 0, gl.canvas.width, gl.canvas.height);
	gl.clearColor(0, 0, 0, 0);
	gl.clear(gl.COLOR_BUFFER_BIT);

	gl.useProgram(prog);
	gl.bindBuffer(gl.ARRAY_BUFFER, buf);

	const stride = 6 * 4; // 6 floats of 4 bytes
	const aPos = gl.getAttribLocation(prog, "a_position");
	const aCol = gl.getAttribLocation(prog, "a_color");
	const aSize = gl.getAttribLocation(prog, "a_size");

	gl.enableVertexAttribArray(aPos);
	gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, stride, 0);

	gl.enableVertexAttribArray(aCol);
	gl.vertexAttribPointer(aCol, 3, gl.FLOAT, false, stride, 2 * 4);

	gl.enableVertexAttribArray(aSize);
	gl.vertexAttribPointer(aSize, 1, gl.FLOAT, false, stride, 5 * 4);

	// Pan & Zoom Matrix in WebGL NDC space
	const ndcPanX = panX.value / (canvasWidth.value / 2);
	const ndcPanY = -panY.value / (canvasHeight.value / 2);
	const z = zoom.value;

	// Mat3 2D Transform (Column-major)
	const uMatrix = gl.getUniformLocation(prog, "u_matrix");
	const matrix = new Float32Array([z, 0, 0, 0, z, 0, ndcPanX, ndcPanY, 1]);
	gl.uniformMatrix3fv(uMatrix, false, matrix);

	gl.drawArrays(gl.POINTS, 0, count);
}

// -------------------------------------------------------------
// METHOD 3 & 4: Canvas2D Optimized Batch Renderer Engine
// -------------------------------------------------------------
function renderCanvas2D(canvas: HTMLCanvasElement) {
	const ctx = canvas.getContext("2d");
	if (!ctx) return;

	const w = canvas.width;
	const h = canvas.height;
	ctx.clearRect(0, 0, w, h);

	// Viewport bounds in world coords for culling
	const [wMinX, wMaxY] = screenToWorld(0, 0);
	const [wMaxX, wMinY] = screenToWorld(w, h);

	// Group points by topic for batched Path2D / arc calls
	const groups: Record<string, PlenairPoint[]> = {
		plenair: [],
		stikstof: [],
		abortus: [],
		asiel: [],
		energietransitie: [],
	};

	const pts = decodedPoints.value;
	for (let i = 0; i < pts.length; i++) {
		const p = pts[i];
		// Viewport culling
		if (p.x < wMinX || p.x > wMaxX || p.y < wMinY || p.y > wMaxY) continue;
		if (groups[p.topic]) {
			groups[p.topic].push(p);
		} else {
			groups.plenair.push(p);
		}
	}

	const basePlenairRadius = Math.max(1.5, Math.min(4, 1.8 * Math.sqrt(zoom.value)));
	const baseTopicRadius = Math.max(3, Math.min(8, 3.5 * Math.sqrt(zoom.value)));

	// Batch draw per topic
	for (const [topic, topicPts] of Object.entries(groups)) {
		if (topicPts.length === 0) continue;
		const isPlenair = topic === "plenair";
		ctx.fillStyle = TOPIC_COLOR[topic] || TOPIC_COLOR.plenair;
		ctx.globalAlpha = isPlenair ? (isDark.value ? 0.35 : 0.25) : 0.75;
		const r = isPlenair ? basePlenairRadius : baseTopicRadius;

		ctx.beginPath();
		for (let i = 0; i < topicPts.length; i++) {
			const p = topicPts[i];
			const [sx, sy] = worldToScreen(p.x, p.y);
			ctx.moveTo(sx + r, sy);
			ctx.arc(sx, sy, r, 0, Math.PI * 2);
		}
		ctx.fill();
	}
	ctx.globalAlpha = 1.0;
}

// -------------------------------------------------------------
// METHOD 6: D3 Canvas + d3-zoom Engine
// -------------------------------------------------------------
function initD3Zoom() {
	if (!d3CanvasRef.value) return;
	const canvas = d3CanvasRef.value;
	const sel = select(canvas);

	d3ZoomBehavior = d3zoom<HTMLCanvasElement, unknown>()
		.scaleExtent([0.8, 12])
		.on("zoom", (event: D3ZoomEvent<HTMLCanvasElement, unknown>) => {
			const transform = event.transform;
			const w = canvasWidth.value;
			const h = canvasHeight.value;

			zoom.value = transform.k;
			panX.value = transform.x + (transform.k - 1) * (w / 2);
			panY.value = transform.y + (transform.k - 1) * (h / 2);

			if (d3CanvasRef.value) {
				renderCanvas2D(d3CanvasRef.value);
			}
		});

	sel.call(d3ZoomBehavior);
}

// -------------------------------------------------------------
// Interactive Pointer & Gesture Handlers (Pan & Wheel Zoom)
// -------------------------------------------------------------
const activePointers = new Map<number, { x: number; y: number }>();
let initialPinchDist = 0;
let initialPinchZoom = 1;
let initialPinchPanX = 0;
let initialPinchPanY = 0;
let pinchCenter = { x: 0, y: 0 };

function onPointerDown(e: PointerEvent) {
	if (selectedMethod.value === "echarts" || selectedMethod.value === "d3_canvas") return;
	(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
	activePointers.set(e.pointerId, { x: e.clientX, y: e.clientY });

	if (activePointers.size === 1) {
		isDragging.value = true;
		dragStart.value = {
			x: e.clientX,
			y: e.clientY,
			panX: panX.value,
			panY: panY.value,
		};
	} else if (activePointers.size === 2) {
		// Start Pinch gesture
		const [p1, p2] = Array.from(activePointers.values());
		initialPinchDist = Math.hypot(p2.x - p1.x, p2.y - p1.y);
		initialPinchZoom = zoom.value;
		initialPinchPanX = panX.value;
		initialPinchPanY = panY.value;

		const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
		pinchCenter = {
			x: (p1.x + p2.x) / 2 - rect.left,
			y: (p1.y + p2.y) / 2 - rect.top,
		};
	}
}

function onPointerMove(e: PointerEvent) {
	if (selectedMethod.value === "echarts" || selectedMethod.value === "d3_canvas") return;
	if (!activePointers.has(e.pointerId)) return;
	activePointers.set(e.pointerId, { x: e.clientX, y: e.clientY });

	if (activePointers.size === 1 && isDragging.value) {
		const dx = e.clientX - dragStart.value.x;
		const dy = e.clientY - dragStart.value.y;

		if (selectedMethod.value === "css_transform") {
			isGestureActive.value = true;
			gestureTranslateX.value = dx;
			gestureTranslateY.value = dy;

			clearTimeout(settleTimer);
			settleTimer = setTimeout(() => {
				panX.value = dragStart.value.panX + dx;
				panY.value = dragStart.value.panY + dy;
				gestureTranslateX.value = 0;
				gestureTranslateY.value = 0;
				isGestureActive.value = false;
				triggerRender();
			}, 80);
		} else {
			panX.value = dragStart.value.panX + dx;
			panY.value = dragStart.value.panY + dy;
			triggerRender();
		}
	} else if (activePointers.size === 2 && initialPinchDist > 0) {
		// Pinch to Zoom centered around two fingers
		const [p1, p2] = Array.from(activePointers.values());
		const dist = Math.hypot(p2.x - p1.x, p2.y - p1.y);
		const scaleChange = dist / initialPinchDist;
		const newZoom = Math.max(0.8, Math.min(12, initialPinchZoom * scaleChange));

		const w = canvasWidth.value;
		const h = canvasHeight.value;
		const cx = pinchCenter.x - w / 2;
		const cy = pinchCenter.y - h / 2;

		const zRatio = newZoom / initialPinchZoom;
		panX.value = cx - (cx - initialPinchPanX) * zRatio;
		panY.value = cy - (cy - initialPinchPanY) * zRatio;
		zoom.value = newZoom;

		triggerRender();
	}
}

function onPointerUp(e: PointerEvent) {
	if (selectedMethod.value === "echarts" || selectedMethod.value === "d3_canvas") return;
	activePointers.delete(e.pointerId);
	try {
		(e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
	} catch {}

	if (activePointers.size === 0) {
		isDragging.value = false;
		if (selectedMethod.value === "css_transform" && isGestureActive.value) {
			const dx = e.clientX - dragStart.value.x;
			const dy = e.clientY - dragStart.value.y;
			panX.value = dragStart.value.panX + dx;
			panY.value = dragStart.value.panY + dy;
			gestureTranslateX.value = 0;
			gestureTranslateY.value = 0;
			isGestureActive.value = false;
			triggerRender();
		}
	} else if (activePointers.size === 1) {
		// Re-initialize single finger drag
		const remaining = Array.from(activePointers.values())[0];
		dragStart.value = {
			x: remaining.x,
			y: remaining.y,
			panX: panX.value,
			panY: panY.value,
		};
	}
}

function onWheel(e: WheelEvent) {
	if (selectedMethod.value === "echarts" || selectedMethod.value === "d3_canvas") return;
	e.preventDefault();

	const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
	const mouseX = e.clientX - rect.left;
	const mouseY = e.clientY - rect.top;

	const zoomFactorDelta = e.deltaY < 0 ? 1.15 : 0.87;
	const oldZoom = zoom.value;
	const newZoom = Math.max(0.8, Math.min(12, oldZoom * zoomFactorDelta));

	const w = canvasWidth.value;
	const h = canvasHeight.value;

	// Center-relative mouse coordinates
	const cx = mouseX - w / 2;
	const cy = mouseY - h / 2;

	// Invariant: screen point under cursor stays motionless
	const scaleRatio = newZoom / oldZoom;
	panX.value = cx - (cx - panX.value) * scaleRatio;
	panY.value = cy - (cy - panY.value) * scaleRatio;
	zoom.value = newZoom;

	triggerRender();
}

function resetView() {
	zoom.value = 1;
	panX.value = 0;
	panY.value = 0;
	if (selectedMethod.value === "d3_canvas" && d3CanvasRef.value && d3ZoomBehavior) {
		select(d3CanvasRef.value).call(d3ZoomBehavior.transform, zoomIdentity);
	}
	triggerRender();
}

function triggerRender() {
	if (selectedMethod.value === "webgl" && webglCanvasRef.value) {
		if (!glContext && webglCanvasRef.value) {
			const res = initWebGL(webglCanvasRef.value);
			if (res) {
				glContext = res.gl;
				glProgram = res.prog;
				glBuffer = res.buf;
				glPointCount = updateWebGLData(glContext, glProgram, glBuffer, decodedPoints.value);
			}
		}
		if (glContext && glProgram && glBuffer) {
			renderWebGL(glContext, glProgram, glBuffer, glPointCount);
		}
	} else if ((selectedMethod.value === "canvas2d" || selectedMethod.value === "css_transform") && canvas2dRef.value) {
		renderCanvas2D(canvas2dRef.value);
	} else if (selectedMethod.value === "d3_canvas" && d3CanvasRef.value) {
		renderCanvas2D(d3CanvasRef.value);
	} else if (selectedMethod.value === "hybrid" && hybridWebglCanvasRef.value) {
		if (!hybridGlContext && hybridWebglCanvasRef.value) {
			const res = initWebGL(hybridWebglCanvasRef.value);
			if (res) {
				hybridGlContext = res.gl;
				hybridGlProgram = res.prog;
				hybridGlBuffer = res.buf;
				hybridGlPointCount = updateWebGLData(hybridGlContext, hybridGlProgram, hybridGlBuffer, decodedPoints.value, true);
			}
		}
		if (hybridGlContext && hybridGlProgram && hybridGlBuffer) {
			renderWebGL(hybridGlContext, hybridGlProgram, hybridGlBuffer, hybridGlPointCount);
		}
	}
}

watch(
	[selectedMethod, decodedPoints, canvasWidth, canvasHeight, isDark],
	() => {
		setTimeout(() => {
			if (webglCanvasRef.value) {
				const res = initWebGL(webglCanvasRef.value);
				if (res) {
					glContext = res.gl;
					glProgram = res.prog;
					glBuffer = res.buf;
					glPointCount = updateWebGLData(glContext, glProgram, glBuffer, decodedPoints.value);
				}
			}
			if (hybridWebglCanvasRef.value) {
				const res = initWebGL(hybridWebglCanvasRef.value);
				if (res) {
					hybridGlContext = res.gl;
					hybridGlProgram = res.prog;
					hybridGlBuffer = res.buf;
					hybridGlPointCount = updateWebGLData(hybridGlContext, hybridGlProgram, hybridGlBuffer, decodedPoints.value, true);
				}
			}
			if (selectedMethod.value === "d3_canvas" && d3CanvasRef.value) {
				initD3Zoom();
			}
			triggerRender();
		}, 20);
	},
	{ immediate: true }
);

// -------------------------------------------------------------
// Automated Stress Tests
// -------------------------------------------------------------
type BenchmarkResult = {
	method: string;
	label: string;
	avgMs: number;
	p50Ms: number;
	p95Ms: number;
	maxMs: number;
	fps: number;
	droppedFrames16: number;
	droppedFrames33: number;
};

const allResults = ref<BenchmarkResult[]>([]);
const formattedMarkdownOutput = ref<string>("");
const isCopied = ref(false);

async function runZoomStressTest() {
	if (isRunningStressTest.value) return;
	isRunningStressTest.value = true;
	stressTestReport.value = "Stresstest draait: 60 zoom-stappen...";

	const frameTimes: number[] = [];
	const originalZoom = zoom.value;
	const originalPanX = panX.value;
	const originalPanY = panY.value;

	const steps = 60;
	for (let i = 0; i < steps; i++) {
		const t = i / (steps / 2);
		const currentZ = 1 + Math.sin(t * Math.PI) * 4;
		zoom.value = Math.max(1, currentZ);

		const t0 = performance.now();
		triggerRender();
		// Wait for next animation frame
		await new Promise((r) => requestAnimationFrame(r));
		const t1 = performance.now();
		frameTimes.push(t1 - t0);
	}

	zoom.value = originalZoom;
	panX.value = originalPanX;
	panY.value = originalPanY;
	triggerRender();

	isRunningStressTest.value = false;
	const avgTime = Math.round((frameTimes.reduce((a, b) => a + b, 0) / frameTimes.length) * 10) / 10;
	const maxTime = Math.round(Math.max(...frameTimes) * 10) / 10;
	stressTestReport.value = `Test voltooid voor ${selectedMethod.value.toUpperCase()}: Gem. frametijd = ${avgTime}ms, Piek = ${maxTime}ms (${fps.value} FPS).`;
}

async function runAllBenchmarks() {
	if (isRunningStressTest.value) return;
	isRunningStressTest.value = true;
	allResults.value = [];
	formattedMarkdownOutput.value = "";

	const methodsToTest: { id: RenderMethod; label: string }[] = [
		{ id: "echarts", label: "1. ECharts Baseline" },
		{ id: "webgl", label: "2. Raw WebGL" },
		{ id: "canvas2d", label: "3. Fast Canvas2D" },
		{ id: "css_transform", label: "4. CSS Transform" },
		{ id: "hybrid", label: "5. Hybride (WebGL + SVG)" },
		{ id: "d3_canvas", label: "6. D3 Canvas (d3-zoom)" },
	];

	const results: BenchmarkResult[] = [];

	for (const m of methodsToTest) {
		selectedMethod.value = m.id;
		stressTestReport.value = `Bezig met benchmarken van ${m.label}...`;
		await new Promise((r) => setTimeout(r, 250));

		const frameTimes: number[] = [];
		const originalZoom = zoom.value;
		const originalPanX = panX.value;
		const originalPanY = panY.value;

		const steps = 60;
		for (let i = 0; i < steps; i++) {
			const t = i / (steps / 2);
			const currentZ = 1 + Math.sin(t * Math.PI) * 3.5;
			zoom.value = Math.max(1, currentZ);
			panX.value = Math.sin(t * 2 * Math.PI) * 60;
			panY.value = Math.cos(t * 2 * Math.PI) * 40;

			const t0 = performance.now();
			if (m.id === "echarts" && chartRef.value) {
				chartRef.value.dispatchAction?.({
					type: "dataZoom",
					dataZoomIndex: 0,
					start: Math.max(0, 50 - 50 / zoom.value),
					end: Math.min(100, 50 + 50 / zoom.value),
				});
			} else {
				triggerRender();
			}
			await new Promise((r) => requestAnimationFrame(r));
			const t1 = performance.now();
			frameTimes.push(t1 - t0);
		}

		zoom.value = originalZoom;
		panX.value = originalPanX;
		panY.value = originalPanY;
		triggerRender();

		const sorted = [...frameTimes].sort((a, b) => a - b);
		const avg = frameTimes.reduce((a, b) => a + b, 0) / frameTimes.length;
		const p50 = sorted[Math.floor(sorted.length * 0.5)];
		const p95 = sorted[Math.floor(sorted.length * 0.95)];
		const max = Math.max(...frameTimes);
		const dropped16 = frameTimes.filter((t) => t > 16.7).length;
		const dropped33 = frameTimes.filter((t) => t > 33.3).length;
		const effectiveFps = Math.min(60, Math.round(1000 / Math.max(1, avg)));

		results.push({
			method: m.id,
			label: m.label,
			avgMs: Math.round(avg * 10) / 10,
			p50Ms: Math.round(p50 * 10) / 10,
			p95Ms: Math.round(p95 * 10) / 10,
			maxMs: Math.round(max * 10) / 10,
			fps: effectiveFps,
			droppedFrames16: dropped16,
			droppedFrames33: dropped33,
		});
	}

	allResults.value = results;
	isRunningStressTest.value = false;
	stressTestReport.value = `Alle 6 benchmarks voltooid. Klik hieronder om de tabel te kopiëren.`;

	let md = `### Benchmark Resultaten Plenaire Kaart (${decodedPoints.value.length.toLocaleString("nl-NL")} punten)\n\n`;
	md += `| Methode | Gem. Frametijd (ms) | P50 (ms) | P95 (ms) | Max (ms) | Effectieve FPS | Dropped (>16ms) | Dropped (>33ms) |\n`;
	md += `|---|---|---|---|---|---|---|---|\n`;
	for (const r of results) {
		md += `| **${r.label}** | ${r.avgMs} ms | ${r.p50Ms} ms | ${r.p95Ms} ms | ${r.maxMs} ms | ${r.fps} FPS | ${r.droppedFrames16}/60 | ${r.droppedFrames33}/60 |\n`;
	}
	formattedMarkdownOutput.value = md;
}

function copyResultsToClipboard() {
	if (!formattedMarkdownOutput.value) return;
	navigator.clipboard.writeText(formattedMarkdownOutput.value);
	isCopied.value = true;
	setTimeout(() => {
		isCopied.value = false;
	}, 2500);
}

// -------------------------------------------------------------
// ECharts Option for Baseline comparison
// -------------------------------------------------------------
const echartsPlenairPts = computed(() => {
	const pts = decodedPoints.value;
	return pts.filter((p) => p.topic === "plenair").map((p) => [p.x, p.y]);
});

const echartsTopicPts = computed(() => {
	const pts = decodedPoints.value;
	return pts.filter((p) => p.topic !== "plenair").map((p) => [p.x, p.y]);
});

const curatedTopicPoints = computed(() => {
	return decodedPoints.value.filter((p) => p.topic !== "plenair");
});

const echartsOption = computed(() => {
	const b = rawBounds.value;

	return {
		backgroundColor: "transparent",
		animation: false,
		grid: { top: 16, left: 16, right: 16, bottom: 16, containLabel: false },
		dataZoom: [
			{ type: "inside", xAxisIndex: 0, filterMode: "none", throttle: 16 },
			{ type: "inside", yAxisIndex: 0, filterMode: "none", throttle: 16 },
		],
		xAxis: { type: "value", min: b.cx - b.spanX / 2, max: b.cx + b.spanX / 2, show: false },
		yAxis: { type: "value", min: b.cy - b.spanY / 2, max: b.cy + b.spanY / 2, show: false },
		series: [
			{
				name: "overig plenair",
				type: "scatter",
				symbolSize: 4,
				large: true,
				largeThreshold: 1000,
				itemStyle: { color: TOPIC_COLOR.plenair, opacity: 0.25 },
				data: echartsPlenairPts.value,
			},
			{
				name: "topics",
				type: "scatter",
				symbolSize: 7,
				itemStyle: { color: "#3d6e8f", opacity: 0.8 },
				data: echartsTopicPts.value,
			},
		],
	};
});

// SVG Polygon points formatter for Hulls
function formatHullPoints(hull: [number, number][] | null): string {
	if (!hull || hull.length < 3) return "";
	return hull.map(([hx, hy]) => worldToScreen(hx, hy).join(",")).join(" ");
}

// Semantic zoom visibility rule for hulls
const showCoarseInOverlay = computed(() => {
	if (hullMode.value === "none") return false;
	if (hullMode.value === "coarse") return true;
	if (hullMode.value === "semantic") return zoom.value < 2.5;
	return false;
});

const showFineInOverlay = computed(() => {
	if (hullMode.value === "none") return false;
	if (hullMode.value === "fine") return true;
	if (hullMode.value === "semantic") return zoom.value >= 1.8;
	return false;
});
</script>

<template>
	<div class="benchmark-container">
		<header class="benchmark-header">
			<div>
				<h1>Plenaire Kaart: Render- & Interactie Benchmark</h1>
				<p class="benchmark-subtitle">
					Vergelijk performance, framerates en interactievloeiendheid van 5 renderingtechnieken op {{ decodedPoints.length.toLocaleString("nl-NL") }} spreekbeurten.
				</p>
			</div>

			<!-- Live Metric Badges -->
			<div class="perf-stats-card">
				<div class="stat-box">
					<span class="stat-label">FPS</span>
					<span class="stat-value" :class="{ 'stat-good': fps >= 55, 'stat-warn': fps < 55 && fps >= 30, 'stat-bad': fps < 30 }">
						{{ fps }}
					</span>
				</div>
				<div class="stat-box">
					<span class="stat-label">Frametijd</span>
					<span class="stat-value">{{ frameTimeMs }} <small>ms</small></span>
				</div>
				<div class="stat-box">
					<span class="stat-label">Gem. / P95</span>
					<span class="stat-value">{{ avgFrameTimeMs }} / {{ p95FrameTimeMs }} <small>ms</small></span>
				</div>
				<div class="stat-box">
					<span class="stat-label">Zoom</span>
					<span class="stat-value">{{ zoom.toFixed(2) }}x</span>
				</div>
			</div>
		</header>

		<!-- Control Toolbar -->
		<div class="controls-panel">
			<div class="control-group">
				<label class="control-heading">Methode:</label>
				<div class="button-group">
					<button
						:class="{ active: selectedMethod === 'd3_canvas' }"
						@click="selectedMethod = 'd3_canvas'"
						title="Canvas2D met d3-zoom gesture handling"
					>
						6. D3 (Canvas + d3-zoom)
					</button>
					<button
						:class="{ active: selectedMethod === 'hybrid' }"
						@click="selectedMethod = 'hybrid'"
						title="Achtergrond op WebGL + Hulls/Labels in SVG overlay"
					>
						5. Hybride (WebGL + SVG)
					</button>
					<button
						:class="{ active: selectedMethod === 'webgl' }"
						@click="selectedMethod = 'webgl'"
						title="Alle punten via pure GPU WebGL point-shader"
					>
						2. Raw WebGL
					</button>
					<button
						:class="{ active: selectedMethod === 'css_transform' }"
						@click="selectedMethod = 'css_transform'"
						title="Hardware CSS-transform tijdens interactie, redraw op rust"
					>
						4. CSS Transform
					</button>
					<button
						:class="{ active: selectedMethod === 'canvas2d' }"
						@click="selectedMethod = 'canvas2d'"
						title="Canvas2D met viewport culling & topic batching"
					>
						3. Fast Canvas2D
					</button>
					<button
						:class="{ active: selectedMethod === 'echarts' }"
						@click="selectedMethod = 'echarts'"
						title="Huidige ECharts canvas implementatie"
					>
						1. ECharts Baseline
					</button>
				</div>
			</div>

			<div class="control-group">
				<label class="control-heading">Hulls & Hiërarchie:</label>
				<div class="button-group">
					<button :class="{ active: hullMode === 'semantic' }" @click="hullMode = 'semantic'">
						Semantische Zoom
					</button>
					<button :class="{ active: hullMode === 'coarse' }" @click="hullMode = 'coarse'">
						Domeinen (Coarse)
					</button>
					<button :class="{ active: hullMode === 'fine' }" @click="hullMode = 'fine'">
						Thema's (Fine)
					</button>
					<button :class="{ active: hullMode === 'none' }" @click="hullMode = 'none'">
						Geen
					</button>
				</div>
			</div>

			<div class="control-group actions-group">
				<button class="action-btn" :disabled="isRunningStressTest" @click="runAllBenchmarks">
					Run alle benchmarks
				</button>
				<button class="action-btn secondary" :disabled="isRunningStressTest" @click="runZoomStressTest">
					Test huidige methode
				</button>
				<button class="action-btn secondary" @click="resetView">
					Reset Weergave
				</button>
			</div>
		</div>

		<div v-if="stressTestReport" class="stress-report-banner">
			{{ stressTestReport }}
		</div>

		<!-- Benchmark Results Summary Box & Clipboard Export -->
		<div v-if="formattedMarkdownOutput" class="benchmark-results-box">
			<div class="results-box-header">
				<h3>Benchmark Resultaten</h3>
				<button class="action-btn copy-btn" @click="copyResultsToClipboard">
					{{ isCopied ? 'Gekopieerd naar klembord!' : 'Kopieer Markdown' }}
				</button>
			</div>

			<div class="results-table-wrapper">
				<table class="results-table">
					<thead>
						<tr>
							<th>Methode</th>
							<th>Gem. (ms)</th>
							<th>P50 (ms)</th>
							<th>P95 (ms)</th>
							<th>Max (ms)</th>
							<th>Effectieve FPS</th>
							<th>Dropped (&gt;16ms)</th>
							<th>Dropped (&gt;33ms)</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="r in allResults" :key="r.method">
							<td><strong>{{ r.label }}</strong></td>
							<td>{{ r.avgMs }} ms</td>
							<td>{{ r.p50Ms }} ms</td>
							<td>{{ r.p95Ms }} ms</td>
							<td>{{ r.maxMs }} ms</td>
							<td><span :class="r.fps >= 55 ? 'stat-good' : r.fps >= 30 ? 'stat-warn' : 'stat-bad'">{{ r.fps }} FPS</span></td>
							<td>{{ r.droppedFrames16 }} / 60</td>
							<td>{{ r.droppedFrames33 }} / 60</td>
						</tr>
					</tbody>
				</table>
			</div>

			<div class="markdown-preview-block">
				<label class="block-label">Markdown export (klaar om te plakken):</label>
				<textarea readonly class="markdown-textarea" rows="8" :value="formattedMarkdownOutput" @click="($event.target as HTMLTextAreaElement).select()"></textarea>
			</div>
		</div>

		<!-- Main Viewport Canvas Container -->
		<div
			ref="wrapperEl"
			class="map-viewport"
			@pointerdown="onPointerDown"
			@pointermove="onPointerMove"
			@pointerup="onPointerUp"
			@pointercancel="onPointerUp"
			@wheel="onWheel"
		>
			<p v-if="status === 'loading'" class="loading-overlay">Puntenwolk en clusters laden&hellip;</p>

			<!-- 1. ECharts Baseline -->
			<VChart
				v-if="selectedMethod === 'echarts' && status === 'ready'"
				ref="chartRef"
				class="echarts-view"
				:option="echartsOption"
				autoresize
			/>

			<!-- 2. Raw WebGL Point Cloud -->
			<canvas
				v-show="selectedMethod === 'webgl'"
				ref="webglCanvasRef"
				class="render-canvas"
				:width="canvasWidth"
				:height="canvasHeight"
			/>

			<!-- 3 & 4. Canvas2D & CSS Transform Mode -->
			<div
				v-show="selectedMethod === 'canvas2d' || selectedMethod === 'css_transform'"
				class="canvas2d-wrapper"
				:style="
					selectedMethod === 'css_transform' && isGestureActive
						? { transform: `translate3d(${gestureTranslateX}px, ${gestureTranslateY}px, 0)` }
						: {}
				"
			>
				<canvas
					ref="canvas2dRef"
					class="render-canvas"
					:width="canvasWidth"
					:height="canvasHeight"
				/>
			</div>

			<!-- 5. Hybrid: WebGL Background Canvas -->
			<canvas
				v-show="selectedMethod === 'hybrid'"
				ref="hybridWebglCanvasRef"
				class="render-canvas"
				:width="canvasWidth"
				:height="canvasHeight"
			/>

			<!-- 6. D3 Canvas (with d3-zoom) -->
			<canvas
				v-show="selectedMethod === 'd3_canvas'"
				ref="d3CanvasRef"
				class="render-canvas"
				:width="canvasWidth"
				:height="canvasHeight"
			/>

			<!-- SVG Overlay for Hulls, Labels & Thematic Highlights (Methods 1-6) -->
			<svg
				v-if="status === 'ready'"
				class="overlay-svg"
				:width="canvasWidth"
				:height="canvasHeight"
			>
				<!-- Thematic topic points for Hybrid mode (on top of WebGL background) -->
				<g v-if="selectedMethod === 'hybrid'" class="hybrid-topics-layer">
					<circle
						v-for="p in curatedTopicPoints"
						:key="'topic-' + p.id"
						:cx="worldToScreen(p.x, p.y)[0]"
						:cy="worldToScreen(p.x, p.y)[1]"
						:r="Math.max(3, Math.min(8, 3.5 * Math.sqrt(zoom)))"
						:fill="TOPIC_COLOR[p.topic] || TOPIC_COLOR.plenair"
						opacity="0.85"
					/>
				</g>

				<!-- Coarse Hulls -->
				<g v-if="showCoarseInOverlay" class="coarse-hulls-layer">
					<polygon
						v-for="c in coarseClusters"
						:key="'coarse-' + c.cluster_id"
						:points="formatHullPoints(c.hull)"
						class="coarse-polygon"
					/>
				</g>

				<!-- Fine Hulls -->
				<g v-if="showFineInOverlay" class="fine-hulls-layer">
					<polygon
						v-for="c in fineClusters"
						:key="'fine-' + c.cluster_id"
						:points="formatHullPoints(c.hull)"
						class="fine-polygon"
					/>
				</g>

				<!-- Thematic Labels with Semantic LOD -->
				<g v-if="showLabels" class="labels-layer">
					<!-- Coarse Labels (Overview) -->
					<template v-if="showCoarseInOverlay">
						<text
							v-for="c in coarseClusters"
							:key="'label-c-' + c.cluster_id"
							:x="worldToScreen(c.centroid[0], c.centroid[1])[0]"
							:y="worldToScreen(c.centroid[0], c.centroid[1])[1]"
							class="coarse-label-text"
							text-anchor="middle"
						>
							{{ c.name }}
						</text>
					</template>

					<!-- Fine Labels (Zoomed In) -->
					<template v-if="showFineInOverlay">
						<text
							v-for="c in fineClusters"
							:key="'label-f-' + c.cluster_id"
							:x="worldToScreen(c.centroid[0], c.centroid[1])[0]"
							:y="worldToScreen(c.centroid[0], c.centroid[1])[1]"
							class="fine-label-text"
							text-anchor="middle"
						>
							{{ c.name }}
						</text>
					</template>
				</g>
			</svg>
		</div>

		<!-- Explanation and Observations Footer -->
		<div class="benchmark-info-card">
			<h3>Hoe verhouden deze methodes zich?</h3>
			<div class="info-grid">
				<div class="info-item">
					<strong>1. ECharts Baseline:</strong>
					<p>Volledig geïntegreerd in het huidige framework. Echter, door canvas herbouw op de main thread kan de frametijd bij continue zoom pieken naar 100-300ms.</p>
				</div>
				<div class="info-item">
					<strong>2. Raw WebGL:</strong>
					<p>Rendert alle 40k punten direct op de GPU in &lt;1ms per frame. 60 FPS gegarandeerd tijdens zoomen en pannen.</p>
				</div>
				<div class="info-item">
					<strong>3. Fast Canvas2D:</strong>
					<p>Tekent direct naar Canvas2D met viewport culling. Verbruikt minder geheugen dan ECharts, maar is trager dan GPU WebGL bij zware zoomacties.</p>
				</div>
				<div class="info-item">
					<strong>4. CSS Transform:</strong>
					<p>Transformeert de bestaande buffer direct via GPU CSS matrix. Biedt directe respons zonder CPU framing tijdens het slepen.</p>
				</div>
				<div class="info-item">
					<strong>5. Hybride (Aanbevolen):</strong>
					<p>Combineert WebGL voor de 33.000 statische achtergrondpunten met een interactieve SVG/Canvas overlay voor themaclusters, convex/concave hulls en tooltips.</p>
				</div>
				<div class="info-item">
					<strong>6. D3 Canvas (d3-zoom):</strong>
					<p>Gebruikt d3-zoom met native event-handling en transformaties op een 2D canvas. Vloeiende inertie en gestandaardiseerd d3-ecosysteem.</p>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.benchmark-container {
	display: flex;
	flex-direction: column;
	gap: 1.25rem;
	margin: 0 auto;
	max-width: 1200px;
	padding: 1.5rem 1rem;
}

.benchmark-header {
	display: flex;
	justify-content: space-between;
	align-items: flex-start;
	flex-wrap: wrap;
	gap: 1rem;
}

.benchmark-subtitle {
	margin: 0.35rem 0 0;
	font-size: 0.95rem;
	color: var(--color-muted, #736b5e);
}

.perf-stats-card {
	display: flex;
	gap: 0.75rem;
	background: var(--color-surface, #f9f8f6);
	border: 1px solid var(--color-border, #e5e0d8);
	border-radius: 8px;
	padding: 0.5rem 0.85rem;
}

.stat-box {
	display: flex;
	flex-direction: column;
	align-items: center;
	min-width: 65px;
}

.stat-label {
	font-size: 0.7rem;
	text-transform: uppercase;
	font-weight: 600;
	color: var(--color-muted, #736b5e);
}

.stat-value {
	font-size: 1.15rem;
	font-weight: 700;
	font-family: monospace;
}

.stat-good {
	color: #2e7d32;
}
.stat-warn {
	color: #ed6c02;
}
.stat-bad {
	color: #d32f2f;
}

.controls-panel {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	justify-content: space-between;
	gap: 1rem;
	background: var(--color-surface, #f9f8f6);
	border: 1px solid var(--color-border, #e5e0d8);
	border-radius: 8px;
	padding: 0.75rem 1rem;
}

.control-group {
	display: flex;
	align-items: center;
	gap: 0.5rem;
}

.control-heading {
	font-size: 0.85rem;
	font-weight: 600;
}

.button-group {
	display: inline-flex;
	border: 1px solid var(--color-border, #e5e0d8);
	border-radius: 6px;
	overflow: hidden;
}

.button-group button {
	background: var(--color-bg, #ffffff);
	border: none;
	border-right: 1px solid var(--color-border, #e5e0d8);
	padding: 0.4rem 0.75rem;
	font-size: 0.82rem;
	cursor: pointer;
	transition: background 0.15s, color 0.15s;
}

.button-group button:last-child {
	border-right: none;
}

.button-group button.active {
	background: var(--color-ink, #221f1b);
	color: var(--color-bg, #ffffff);
	font-weight: 600;
}

.actions-group {
	display: flex;
	gap: 0.5rem;
}

.action-btn {
	background: var(--color-accent, #2563eb);
	color: #fff;
	border: none;
	border-radius: 6px;
	padding: 0.45rem 0.85rem;
	font-size: 0.82rem;
	font-weight: 600;
	cursor: pointer;
	transition: opacity 0.15s;
}

.action-btn:hover {
	opacity: 0.9;
}

.action-btn:disabled {
	opacity: 0.5;
	cursor: not-allowed;
}

.action-btn.secondary {
	background: var(--color-surface, #e5e0d8);
	color: var(--color-ink, #221f1b);
}

.stress-report-banner {
	background: #eff6ff;
	color: #1e40af;
	border: 1px solid #bfdbfe;
	border-radius: 6px;
	padding: 0.6rem 1rem;
	font-size: 0.85rem;
	font-weight: 500;
}

.map-viewport {
	position: relative;
	width: 100%;
	height: 540px;
	background: var(--color-surface, #f9f8f6);
	border: 1px solid var(--color-border, #e5e0d8);
	border-radius: 8px;
	overflow: hidden;
	user-select: none;
	touch-action: none;
	cursor: grab;
}

.map-viewport:active {
	cursor: grabbing;
}

.echarts-view,
.render-canvas,
.canvas2d-wrapper,
.overlay-svg {
	position: absolute;
	top: 0;
	left: 0;
	width: 100%;
	height: 100%;
}

.overlay-svg {
	pointer-events: none;
}

.coarse-polygon {
	fill: rgba(0, 0, 0, 0.03);
	stroke: rgba(0, 0, 0, 0.25);
	stroke-width: 1.5;
	stroke-dasharray: 6 4;
}

.fine-polygon {
	fill: rgba(0, 0, 0, 0.015);
	stroke: rgba(0, 0, 0, 0.3);
	stroke-width: 1.2;
}

.coarse-label-text {
	font-family: system-ui, sans-serif;
	font-size: 13px;
	font-weight: bold;
	fill: var(--color-ink, #221f1b);
	paint-order: stroke fill;
	stroke: rgba(255, 255, 255, 0.85);
	stroke-width: 3px;
}

.fine-label-text {
	font-family: system-ui, sans-serif;
	font-size: 11px;
	font-weight: 600;
	fill: var(--color-ink, #221f1b);
	paint-order: stroke fill;
	stroke: rgba(255, 255, 255, 0.85);
	stroke-width: 2px;
}

.loading-overlay {
	position: absolute;
	top: 50%;
	left: 50%;
	transform: translate(-50%, -50%);
	font-size: 0.95rem;
	color: var(--color-muted, #736b5e);
}

.benchmark-results-box {
	background: var(--color-surface, #f9f8f6);
	border: 2px solid var(--color-accent, #2563eb);
	border-radius: 8px;
	padding: 1.25rem;
	display: flex;
	flex-direction: column;
	gap: 1rem;
}

.results-box-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	flex-wrap: wrap;
	gap: 0.5rem;
}

.results-box-header h3 {
	margin: 0;
	font-size: 1.05rem;
}

.copy-btn {
	background: #16a34a;
}

.results-table-wrapper {
	overflow-x: auto;
}

.results-table {
	width: 100%;
	border-collapse: collapse;
	font-size: 0.85rem;
	text-align: left;
}

.results-table th,
.results-table td {
	padding: 0.5rem 0.65rem;
	border-bottom: 1px solid var(--color-border, #e5e0d8);
}

.results-table th {
	background: rgba(0, 0, 0, 0.03);
	font-weight: 600;
}

.markdown-preview-block {
	display: flex;
	flex-direction: column;
	gap: 0.35rem;
}

.block-label {
	font-size: 0.78rem;
	font-weight: 600;
	color: var(--color-muted, #736b5e);
}

.markdown-textarea {
	width: 100%;
	font-family: monospace;
	font-size: 0.8rem;
	padding: 0.6rem;
	border: 1px solid var(--color-border, #e5e0d8);
	border-radius: 6px;
	background: var(--color-bg, #ffffff);
	color: var(--color-ink, #221f1b);
	resize: vertical;
}

.benchmark-info-card {
	background: var(--color-surface, #f9f8f6);
	border: 1px solid var(--color-border, #e5e0d8);
	border-radius: 8px;
	padding: 1.25rem;
}

.benchmark-info-card h3 {
	margin-top: 0;
	margin-bottom: 0.75rem;
	font-size: 1rem;
}

.info-grid {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
	gap: 1rem;
}

.info-item {
	font-size: 0.82rem;
	line-height: 1.4;
}

.info-item strong {
	display: block;
	margin-bottom: 0.25rem;
}

.info-item p {
	margin: 0;
	color: var(--color-muted, #736b5e);
}
</style>

