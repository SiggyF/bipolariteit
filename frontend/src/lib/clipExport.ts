import { buildOverlayState } from "./videoOverlayState";
import { renderOverlaySvg, svgToDataUrl } from "./svgOverlayRenderer";
import type { Argument } from "./types";

// Lokale clip-export (issue #180, plan B uit de PoC): canvas.captureStream()
// i.p.v. een serverside component, want die hebben we niet (geen backend,
// geen video-opslag). Overlay wordt als SVG getekend (issue #179) i.p.v.
// losse divs, want een <div> kan sowieso niet naar een MediaStream/canvas
// gerasterd worden -- captureStream() bestaat alleen op canvas/video/audio.

export interface ClipExportResult {
	blob: Blob;
	mimeType: string;
}

const MIME_CANDIDATES = ["video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm"];

function pickSupportedMimeType(): string {
	return MIME_CANDIDATES.find((m) => MediaRecorder.isTypeSupported(m)) ?? "";
}

/** Neemt `durationSeconds` op vanaf het huidige afspeelpunt van `video`,
 * overlay (badges/naamplaatje/titelkaart) inbegrepen, en levert een
 * afspeelbare WebM-blob op. Vereist dat `video` CORS-schoon is
 * (crossorigin="anonymous" + de bron stuurt Access-Control-Allow-Origin),
 * anders raakt het tussenliggende canvas "tainted" en gooit captureStream()
 * een SecurityError. */
export async function recordClip(
	video: HTMLVideoElement,
	args: Argument[],
	isVisible: (tag: { perspectief: string }) => boolean,
	durationSeconds: number,
): Promise<ClipExportResult> {
	const width = video.videoWidth || 640;
	const height = video.videoHeight || 360;
	const canvas = document.createElement("canvas");
	canvas.width = width;
	canvas.height = height;
	const ctx = canvas.getContext("2d");
	if (!ctx) throw new Error("kon geen 2D-canvascontext aanmaken");

	const stream = canvas.captureStream(30);
	if (typeof video.captureStream === "function") {
		try {
			video.captureStream().getAudioTracks().forEach((track) => stream.addTrack(track));
		} catch {
			// Geen audiotrack beschikbaar (bv. gedempte/geen-audio bron) -- de
			// clip blijft dan stil, geen harde eis voor deze PoC-afgeleide functie.
		}
	}

	const mimeType = pickSupportedMimeType();
	const chunks: Blob[] = [];
	const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
	recorder.ondataavailable = (e) => {
		if (e.data.size > 0) chunks.push(e.data);
	};
	const stopped = new Promise<void>((resolve) => {
		recorder.onstop = () => resolve();
	});

	const img = new Image();
	let currentSvgUrl: string | null = null;

	function drawFrame() {
		ctx!.drawImage(video, 0, 0, width, height);
		const state = buildOverlayState(args, video.currentTime, isVisible);
		const url = svgToDataUrl(renderOverlaySvg(state, width, height));
		if (url !== currentSvgUrl) {
			img.src = url;
			currentSvgUrl = url;
		}
		if (img.complete && img.naturalWidth > 0) {
			ctx!.drawImage(img, 0, 0, width, height);
		}
	}

	recorder.start();
	const start = performance.now();
	let raf = 0;
	await new Promise<void>((resolve) => {
		function loop() {
			drawFrame();
			if (performance.now() - start < durationSeconds * 1000) {
				raf = requestAnimationFrame(loop);
			} else {
				cancelAnimationFrame(raf);
				recorder.stop();
				resolve();
			}
		}
		loop();
	});
	await stopped;

	return { blob: new Blob(chunks, { type: mimeType || "video/webm" }), mimeType: mimeType || "video/webm" };
}

/** Triggert een lokale download van de clip -- geen upload, geen server. */
export function downloadClip(result: ClipExportResult, filename: string) {
	const url = URL.createObjectURL(result.blob);
	const a = document.createElement("a");
	a.href = url;
	a.download = filename;
	a.click();
	URL.revokeObjectURL(url);
}
