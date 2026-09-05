// Lokale clip-export (issue #180): canvas.captureStream() i.p.v. een
// serverside component, want die hebben we niet (geen backend, geen
// video-opslag).
//
// Overlay-rendering: de ECHTE, ongewijzigde VideoOverlay.vue-DOM (incl. zijn
// bestaande, door een designer gemaakte CSS) wordt elk frame gekloond en via
// een SVG <foreignObject> op hetzelfde canvas getekend als het videoframe.
// Eerder werd de overlay apart herbouwd als losstaande SVG-vormen
// (svgOverlayRenderer.ts/VideoOverlaySvg.vue) -- dat gaf onvermijdelijk
// twee implementaties van dezelfde vormgeving uit de pas (titelmarges,
// naam-wrap, badge-uitlijning, tag-hover, ...). Deze aanpak hergebruikt de
// live DOM 1:1, dus geen tweede plek om diezelfde vormgeving te
// onderhouden.
//
// <foreignObject> met echte HTML tainted het canvas NIET in Chromium
// (empirisch geverifieerd, zie PR #267) -- wel drie dingen die eerst
// opgelost moesten worden:
//  1. XML staat geen "--" toe binnen een <!-- -->-comment, maar dit project
//     schrijft toelichtingen consequent met "--" als gedachtestreepje, ook in
//     de Vue-templates zelf -- die commentaarnodes staan gewoon in de DOM en
//     moeten eruit vóór XMLSerializer (zie memory:
//     project_dutch_comments_break_xml_serialization.md).
//  2. Csstekst (via document.styleSheets) kan ongeëscapete "&"/"<" bevatten
//     (bv. Google Fonts-@import-URL's met "&family=...") -- moet in een
//     CDATA-sectie.
//  3. <img>'s met een gewoon (zelfs absoluut) src-attribuut laden binnen de
//     foreignObject niet betrouwbaar op tijd: de buitenste SVG->Image()
//     rasterisatie wacht niet altijd op geneste, asynchrone resources, dus
//     het partijlogo bleef op het eerste frame een kapot-plaatje-icoon
//     (empirisch bevestigd: dezelfde absolute URL laadt prima als los
//     element, maar niet betrouwbaar als geneste foreignObject-resource).
//     Oplossing: elke <img> vooraf naar een data:-URI omzetten (fetch +
//     base64, gecachet) zodat er geen resource meer op te halen valt op het
//     moment dat de browser de SVG rasterizeert.

/** Verwijdert alle commentaarnodes (Vue-placeholders én de letterlijke
 * toelichtingen uit de templates) uit een gekloonde subtree -- noodzakelijk
 * vóór XMLSerializer, zie moduledocstring punt 1. */
function stripComments(root: Node) {
	const walker = document.createTreeWalker(root, NodeFilter.SHOW_COMMENT);
	const comments: Comment[] = [];
	let node: Node | null;
	while ((node = walker.nextNode())) comments.push(node as Comment);
	comments.forEach((c) => c.remove());
}

const imageDataUrlCache = new Map<string, string>();

async function fetchAsDataUrl(url: string): Promise<string> {
	const cached = imageDataUrlCache.get(url);
	if (cached) return cached;
	const blob = await (await fetch(url)).blob();
	const dataUrl = await new Promise<string>((resolve, reject) => {
		const reader = new FileReader();
		reader.onload = () => resolve(reader.result as string);
		reader.onerror = reject;
		reader.readAsDataURL(blob);
	});
	imageDataUrlCache.set(url, dataUrl);
	return dataUrl;
}

/** Vervangt elke <img src="..."> door een data:-URI (zie moduledocstring
 * punt 3) -- gecachet op absolute URL, dus een partijlogo dat al eerder in
 * deze opname voorbijkwam kost geen nieuwe fetch. Async: bedoeld om één keer
 * vooraf te "warmen" op de dan zichtbare sprekers. */
async function inlineImages(root: Element): Promise<void> {
	const images = Array.from(root.querySelectorAll("img"));
	await Promise.all(
		images.map(async (img) => {
			const src = img.getAttribute("src");
			if (!src || src.startsWith("data:")) return;
			try {
				img.setAttribute("src", await fetchAsDataUrl(new URL(src, location.href).href));
			} catch {
				// Logo niet op te halen (bv. netwerkfout) -- geen harde eis,
				// de rest van de overlay blijft gewoon zichtbaar.
			}
		}),
	);
}

/** Synchrone tegenhanger voor de per-frame renderlus: gebruikt alleen wat al
 * in de cache zit (geen await mogelijk in een requestAnimationFrame-loop).
 * Een spreker die pas halverwege de opname in beeld komt, mist zijn logo dan
 * een enkel frame terwijl de fetch op de achtergrond loopt -- daarna is 'm
 * gecachet en klopt elk volgend frame weer. */
function inlineImagesSync(root: Element): void {
	for (const img of root.querySelectorAll("img")) {
		const src = img.getAttribute("src");
		if (!src || src.startsWith("data:")) continue;
		const absolute = new URL(src, location.href).href;
		const cached = imageDataUrlCache.get(absolute);
		if (cached) {
			img.setAttribute("src", cached);
		} else {
			img.removeAttribute("src"); // liever geen logo dan een kapot-plaatje-icoon
			void fetchAsDataUrl(absolute).catch(() => {});
		}
	}
}

/** Alle CSS-regeltekst van de pagina (main.css + Vue's scoped
 * component-stylesheets) -- éénmalig verzameld, niet per frame: de
 * stylesheets veranderen niet tijdens een 10s-opname. */
function collectStylesheetText(): string {
	let css = "";
	for (const sheet of Array.from(document.styleSheets)) {
		try {
			for (const rule of Array.from(sheet.cssRules)) css += rule.cssText + "\n";
		} catch {
			// Cross-origin stylesheet (bv. een Google Fonts <link>) --
			// cssRules is dan niet leesbaar, maar het lettertype is al
			// geladen/gecachet door de browser en rendert alsnog correct.
		}
	}
	return css;
}

function serializeOverlaySvg(overlayEl: Element, width: number, height: number, css: string): string {
	const clone = overlayEl.cloneNode(true) as Element;
	stripComments(clone);
	inlineImagesSync(clone);
	const html = new XMLSerializer().serializeToString(clone);
	// container-type: inline-size op de wrapper -- VideoOverlay.vue's eigen
	// @container-regels (compacte badge-labels) reageren op de breedte van
	// déze wrapper, dus die moet zelf een container zijn, niet enkel de
	// (hier ontbrekende) .video-stage-ouder uit de echte pagina.
	return (
		`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}">` +
		`<foreignObject width="${width}" height="${height}">` +
		`<div xmlns="http://www.w3.org/1999/xhtml" style="position:relative;width:${width}px;height:${height}px;container-type:inline-size;">` +
		`<style>${`<![CDATA[${css}]]>`}</style>` +
		html +
		`</div></foreignObject></svg>`
	);
}

function svgToDataUrl(svg: string): string {
	return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
}

export interface ClipExportResult {
	blob: Blob;
	mimeType: string;
}

const MIME_CANDIDATES = ["video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm"];

function pickSupportedMimeType(): string {
	return MIME_CANDIDATES.find((m) => MediaRecorder.isTypeSupported(m)) ?? "";
}

// Bovengrens voor de exportbreedte: de bronvideo is vaak 1080p, maar
// full-res per frame tekenen (canvas + overlay-redraw) én tegelijk
// VP9-encoden bleek in de praktijk te haperen. Een clip is voor delen
// bedoeld, geen archiefkwaliteit -- 640px breed is ruim genoeg en scheelt
// zowel canvas-tekenwerk als encodetijd per frame.
const MAX_WIDTH = 640;

// Duck-typed i.p.v. hls.js' eigen Hls-type importeren: clipExport.ts hoeft
// verder niets van hls.js te weten, en dit blijft ook bruikbaar als
// VideoPlayer.vue ooit een ander HLS-type zou gebruiken.
export interface HlsLike {
	levels: { width: number }[];
	currentLevel: number;
}

/** Kiest de HLS-kwaliteitslaag die qua breedte het dichtst bij `targetWidth`
 * zit i.p.v. altijd de (vaak 1080p) laag die hls.js toevallig al gekozen
 * had -- decoderen op volle resolutie en dan via canvas downschalen naar
 * MAX_WIDTH bleek in de praktijk merkbaar te haperen. Geeft de vorige laag
 * terug zodat de kijker na de opname weer terug kan naar de kwaliteit die
 * hls.js zelf (adaptief, op bandbreedte) had gekozen. */
function selectExportQuality(hls: HlsLike, targetWidth: number): number {
	const previousLevel = hls.currentLevel;
	if (hls.levels.length === 0) return previousLevel;
	let bestIndex = 0;
	let bestDiff = Infinity;
	hls.levels.forEach((level, i) => {
		const diff = Math.abs(level.width - targetWidth);
		if (diff < bestDiff) {
			bestDiff = diff;
			bestIndex = i;
		}
	});
	hls.currentLevel = bestIndex;
	return previousLevel;
}

/** Neemt `durationSeconds` op vanaf het huidige afspeelpunt van `video`,
 * overlay (badges/naamplaatje/titelkaart, de echte VideoOverlay.vue-DOM)
 * inbegrepen, en levert een afspeelbare WebM-blob op. Vereist dat `video`
 * CORS-schoon is (crossorigin="anonymous" + de bron stuurt
 * Access-Control-Allow-Origin), anders raakt het tussenliggende canvas
 * "tainted" en gooit captureStream() een SecurityError. `hls` is optioneel:
 * zonder HLS (bv. Safari's native afspeelpad) wordt gewoon op de huidige
 * decoderesolutie opgenomen. */
export async function recordClip(
	video: HTMLVideoElement,
	overlayEl: Element,
	durationSeconds: number,
	onProgress?: (fraction: number) => void,
	hls?: HlsLike | null,
): Promise<ClipExportResult> {
	const sourceWidth = video.videoWidth || 640;
	const sourceHeight = video.videoHeight || 360;
	const scale = Math.min(1, MAX_WIDTH / sourceWidth);
	const width = Math.round(sourceWidth * scale);
	const height = Math.round(sourceHeight * scale);

	const previousLevel = hls ? selectExportQuality(hls, width) : null;
	// Korte marge zodat hls.js het eerste segment van de nieuwe laag kan
	// laden vóór de opname begint -- anders tonen de eerste frames nog de
	// oude (hogere) resolutie terwijl de rest al is omgeschakeld.
	if (hls) await new Promise((resolve) => setTimeout(resolve, 400));

	// video.currentTime moet daadwerkelijk lopen tijdens het opnemen -- een
	// gepauzeerde video zou hetzelfde frame durationSeconds lang herhalen.
	if (video.paused) await video.play().catch(() => {});

	try {
		return await recordFrames(video, overlayEl, durationSeconds, width, height, onProgress);
	} finally {
		if (hls && previousLevel !== null) hls.currentLevel = previousLevel;
	}
}

async function recordFrames(
	video: HTMLVideoElement,
	overlayEl: Element,
	durationSeconds: number,
	width: number,
	height: number,
	onProgress?: (fraction: number) => void,
): Promise<ClipExportResult> {
	// Logo('s) van de nu al zichtbare spreker vast ophalen/cachen (zie
	// inlineImages/inlineImagesSync): zonder deze warmronde zou zelfs de
	// eerste spreker van de clip zijn logo missen totdat de achtergrondfetch
	// in de renderlus is aangeslagen.
	await inlineImages(overlayEl.cloneNode(true) as Element);

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
			// clip blijft dan stil, geen harde eis voor deze functie.
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

	const css = collectStylesheetText();
	const img = new Image();
	let currentSvgUrl: string | null = null;

	function drawFrame() {
		ctx!.drawImage(video, 0, 0, width, height);
		const url = svgToDataUrl(serializeOverlaySvg(overlayEl, width, height, css));
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
			const elapsed = performance.now() - start;
			onProgress?.(Math.min(1, elapsed / (durationSeconds * 1000)));
			if (elapsed < durationSeconds * 1000) {
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
