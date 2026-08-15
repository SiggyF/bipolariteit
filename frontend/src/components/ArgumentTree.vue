<template>
	<div class="confrontatie">
		<div class="confrontatie-main">
			<header class="confrontatie-header">
				<div>
					<div class="confrontatie-kicker">Argumentenboom · {{ tree.name }}</div>
					<h1 class="confrontatie-title">{{ tree.name }}</h1>
				</div>
				<p v-if="tree.topic_description" class="confrontatie-intro">{{ introSentence }}</p>
			</header>

			<div class="confrontatie-legend">
				<div class="confrontatie-legend-item">
					<span class="confrontatie-swatch confrontatie-swatch-pro"></span><span>Pro</span>
				</div>
				<div class="confrontatie-legend-item">
					<span class="confrontatie-swatch confrontatie-swatch-contra"></span><span>Contra</span>
				</div>
				<div class="confrontatie-legend-item">
					<span class="confrontatie-legend-dash"></span><span>onderbouwing (&ldquo;A, want B&rdquo;)</span>
				</div>
				<div class="confrontatie-legend-item">
					<span class="confrontatie-legend-medallion">↔</span><span>weerlegging over de as heen</span>
				</div>
				<div class="confrontatie-legend-stats">
					{{ tree.stats.aantal_geselecteerd }} van {{ tree.stats.totaal_argumenten }} argumenten ·
					{{ tree.stats.aantal_pro }} pro / {{ tree.stats.aantal_contra }} contra
				</div>
			</div>

			<div class="confrontatie-toggles">
				<label><input v-model="toonCitaten" type="checkbox" /> citaten tonen</label>
				<label><input v-model="toonOnderbouwing" type="checkbox" /> onderbouwing tonen</label>
				<label v-if="!officieel"><input v-model="toonTwijfel" type="checkbox" /> twijfelachtige classificaties tonen</label>
			</div>

			<div class="confrontatie-colheader">
				<div class="confrontatie-colheader-pro">Pro</div>
				<div class="confrontatie-colheader-mid">thema</div>
				<div class="confrontatie-colheader-contra">Contra</div>
			</div>

			<div class="confrontatie-bands-wrap" ref="wrapRef">
				<svg class="confrontatie-svg" width="100%" height="100%">
					<line
						v-for="rail in kidsRails"
						:key="rail.key"
						:x1="rail.x"
						:y1="rail.y1"
						:x2="rail.x"
						:y2="rail.y2"
						stroke="var(--confrontatie-muted-2)"
						stroke-width="1"
						stroke-dasharray="4 4"
					/>
					<g v-for="l in links" :key="l.key">
						<path :d="l.d" fill="none" :stroke="l.stroke" :stroke-width="l.w" stroke-dasharray="6 5" />
						<circle :cx="l.mx" :cy="l.my" r="11" class="confrontatie-medallion-bg" :stroke="l.stroke" :stroke-width="l.w" />
						<text
							:x="l.mx"
							:y="l.my"
							text-anchor="middle"
							dominant-baseline="central"
							:fill="l.stroke"
							class="confrontatie-medallion-glyph"
							>↔</text
						>
					</g>
				</svg>

				<div v-for="band in tree.bands" :key="band.nummer" class="confrontatie-band">
					<div class="confrontatie-band-row">
						<div class="confrontatie-band-side confrontatie-band-side-pro">
							<ArgumentConfrontatieKaart
								v-if="band.pro?.type === 'node'"
								variant="hoofd"
								side="pro"
								:argument="argumentFor(band.pro.id)"
								:selected="selectedId === band.pro.id"
								:linked="isLinked(band.pro.id)"
								:show-citaat="toonCitaten"
								:opp-gist="oppositionGist(band.pro.id)"
								@select="selectArgument"
								@hover="hoverId = $event"
								@unhover="hoverId = null"
							/>
							<ArgumentConfrontatieKaart
								v-else-if="band.pro?.type === 'ref'"
								variant="ref"
								side="pro"
								:ref-id="band.pro.ref_id"
								:ref-band-nummer="band.pro.band_nummer"
								@select="selectArgument"
							/>
							<div v-if="toonOnderbouwing && band.pro?.type === 'node' && band.pro.kids.length" class="confrontatie-kids confrontatie-kids-pro">
								<ArgumentConfrontatieKaart
									v-for="kid in band.pro.kids"
									:key="kid"
									variant="kid"
									side="pro"
									:argument="argumentFor(kid)"
									:selected="selectedId === kid"
									:linked="isLinked(kid)"
									:show-citaat="toonCitaten"
									:opp-gist="oppositionGist(kid)"
									@select="selectArgument"
									@hover="hoverId = $event"
									@unhover="hoverId = null"
								/>
							</div>
						</div>

						<div class="confrontatie-band-mid">
							<div class="confrontatie-band-rule"></div>
							<div class="confrontatie-band-theme">
								<div class="confrontatie-band-no">Thema {{ String(band.nummer).padStart(2, "0") }}</div>
								<div class="confrontatie-band-label">{{ band.thema }}</div>
							</div>
							<div class="confrontatie-band-rule"></div>
						</div>

						<div class="confrontatie-band-side confrontatie-band-side-contra">
							<ArgumentConfrontatieKaart
								v-if="band.contra?.type === 'node'"
								variant="hoofd"
								side="contra"
								:argument="argumentFor(band.contra.id)"
								:selected="selectedId === band.contra.id"
								:linked="isLinked(band.contra.id)"
								:show-citaat="toonCitaten"
								:opp-gist="oppositionGist(band.contra.id)"
								@select="selectArgument"
								@hover="hoverId = $event"
								@unhover="hoverId = null"
							/>
							<ArgumentConfrontatieKaart
								v-else-if="band.contra?.type === 'ref'"
								variant="ref"
								side="contra"
								:ref-id="band.contra.ref_id"
								:ref-band-nummer="band.contra.band_nummer"
								@select="selectArgument"
							/>
							<div v-if="toonOnderbouwing && band.contra?.type === 'node' && band.contra.kids.length" class="confrontatie-kids confrontatie-kids-contra">
								<ArgumentConfrontatieKaart
									v-for="kid in band.contra.kids"
									:key="kid"
									variant="kid"
									side="contra"
									:argument="argumentFor(kid)"
									:selected="selectedId === kid"
									:linked="isLinked(kid)"
									:show-citaat="toonCitaten"
									:opp-gist="oppositionGist(kid)"
									@select="selectArgument"
									@hover="hoverId = $event"
									@unhover="hoverId = null"
								/>
							</div>
						</div>
					</div>
					<div class="confrontatie-band-divider"></div>
				</div>
			</div>

			<section v-if="losseGroepenPro.length || losseGroepenContra.length || losseArgumentenPro.length || losseArgumentenContra.length" class="confrontatie-losse">
				<div class="confrontatie-losse-header">
					<h2>Buiten de confrontatie</h2>
					<span>argumenten uit de selectie zonder scherpe tegenhanger, geen weerlegging over de as</span>
				</div>
				<div class="confrontatie-losse-row">
					<div class="confrontatie-band-side confrontatie-band-side-pro">
						<div v-for="groep in losseGroepenPro" :key="groep.label" class="confrontatie-losse-groep">
							<div class="confrontatie-losse-groep-label">coördinatief · {{ groep.label }}</div>
							<div v-if="groep.samenvatting" class="confrontatie-losse-groep-samenvatting">{{ groep.samenvatting }}</div>
							<ArgumentConfrontatieKaart
								v-for="id in groep.member_ids"
								:key="id"
								variant="los"
								side="pro"
								:argument="argumentFor(id)"
								:selected="selectedId === id"
								:linked="isLinked(id)"
								@select="selectArgument"
								@hover="hoverId = $event"
								@unhover="hoverId = null"
							/>
						</div>
						<ArgumentConfrontatieKaart
							v-for="id in losseArgumentenPro"
							:key="id"
							variant="hoofd"
							side="pro"
							:argument="argumentFor(id)"
							:selected="selectedId === id"
							:linked="isLinked(id)"
							@select="selectArgument"
							@hover="hoverId = $event"
							@unhover="hoverId = null"
						/>
					</div>
					<div class="confrontatie-band-mid">
						<div class="confrontatie-band-rule"></div>
						<div class="confrontatie-band-theme confrontatie-losse-mid-label">zonder tegenhanger<br />in deze selectie</div>
						<div class="confrontatie-band-rule"></div>
					</div>
					<div class="confrontatie-band-side confrontatie-band-side-contra">
						<div v-for="groep in losseGroepenContra" :key="groep.label" class="confrontatie-losse-groep">
							<div class="confrontatie-losse-groep-label">coördinatief · {{ groep.label }}</div>
							<div v-if="groep.samenvatting" class="confrontatie-losse-groep-samenvatting">{{ groep.samenvatting }}</div>
							<ArgumentConfrontatieKaart
								v-for="id in groep.member_ids"
								:key="id"
								variant="los"
								side="contra"
								:argument="argumentFor(id)"
								:selected="selectedId === id"
								:linked="isLinked(id)"
								@select="selectArgument"
								@hover="hoverId = $event"
								@unhover="hoverId = null"
							/>
						</div>
						<ArgumentConfrontatieKaart
							v-for="id in losseArgumentenContra"
							:key="id"
							variant="hoofd"
							side="contra"
							:argument="argumentFor(id)"
							:selected="selectedId === id"
							:linked="isLinked(id)"
							@select="selectArgument"
							@hover="hoverId = $event"
							@unhover="hoverId = null"
						/>
					</div>
				</div>
			</section>

			<section v-if="toonTwijfel && tree.twijfelachtige_classificaties.length" class="confrontatie-twijfel">
				<div class="confrontatie-twijfel-header">
					<h2>Twijfelachtige classificaties</h2>
					<span>gemarkeerd tijdens het structureren, niet in de boom opgenomen</span>
				</div>
				<div class="confrontatie-twijfel-grid">
					<div v-for="t in tree.twijfelachtige_classificaties" :key="t.argument_id" class="confrontatie-twijfel-item">
						<div class="confrontatie-twijfel-kicker">
							<span class="confrontatie-muted-2">#{{ t.argument_id }}</span><span>nu gelabeld: {{ t.huidige_stance }}</span>
						</div>
						<div class="confrontatie-twijfel-reden">{{ t.reden }}</div>
					</div>
				</div>
			</section>

			<footer class="confrontatie-footer">
				Bron: argumentexport {{ tree.name }}, {{ tree.stats.totaal_argumenten }} argumenten ({{ tree.stats.aantal_pro }}
				pro / {{ tree.stats.aantal_contra }} contra). Boomstructuur uit Gemini's structurering: ruwe, ongevalideerde
				output. Pro/contra-labels komen uit een eerdere automatische classificatie; het citaat is leidend, niet het
				label.
			</footer>
		</div>

		<Transition name="confrontatie-panel">
			<div v-if="selectedArgument" ref="panelRef" class="confrontatie-detail">
				<div class="confrontatie-detail-head">
					<div class="confrontatie-detail-kicker">
						{{ selectedArgument.stance === "pro" ? "Pro" : "Contra" }} · {{ typeNl(selectedArgument.typologie) }} ·
						#{{ selectedArgument.id }}
					</div>
					<button type="button" class="confrontatie-detail-close" @click="selectedId = null">sluiten ×</button>
				</div>
				<div class="confrontatie-detail-gist">{{ selectedArgument.gist }}</div>
				<div class="confrontatie-detail-speaker">
					{{ selectedArgument.spreker }}<template v-if="selectedArgument.partij"> ({{ selectedArgument.partij }})</template>
				</div>
				<div class="confrontatie-detail-quote">&ldquo;{{ selectedArgument.citaat }}&rdquo;</div>
				<div v-if="selectedArgument.claims.length" class="confrontatie-detail-block">
					<div class="confrontatie-detail-label">Genoemde claims</div>
					<div v-for="(claim, i) in selectedArgument.claims" :key="i" class="confrontatie-detail-claim">
						{{ claim.claim_text }}<template v-if="claim.attributed_source_text"> (bron: {{ claim.attributed_source_text }})</template>
					</div>
				</div>
				<div v-if="selectedOppositionId" class="confrontatie-detail-block">
					<div class="confrontatie-detail-label">Weerlegging</div>
					<div class="confrontatie-detail-oppositielink" @click="selectArgument(selectedOppositionId)">
						↔ #{{ selectedOppositionId }}: {{ argumentFor(selectedOppositionId)?.gist }}
					</div>
				</div>
				<div v-if="selectedArgument.tags.length" class="confrontatie-detail-block">
					<div class="confrontatie-detail-label">Tags</div>
					<div class="confrontatie-detail-tags">
						<span v-for="tag in selectedArgument.tags" :key="tag">{{ tag }}</span>
					</div>
				</div>
				<div
					v-if="selectedArgument.tweedekamer_activiteit_url || selectedArgument.speaker_video_url"
					class="confrontatie-detail-links"
				>
					<a v-if="selectedArgument.tweedekamer_activiteit_url" :href="selectedArgument.tweedekamer_activiteit_url" target="_blank" rel="noopener">bekijk in de Tweede Kamer</a>
					<a v-if="selectedArgument.speaker_video_url" :href="selectedArgument.speaker_video_url" target="_blank" rel="noopener">video (dit moment)</a>
				</div>
			</div>
		</Transition>
	</div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import ArgumentConfrontatieKaart from "./ArgumentConfrontatieKaart.vue";

interface ExportArgument {
	id: number;
	citaat: string;
	typologie: string;
	stance: "pro" | "contra";
	spreker: string;
	partij: string | null;
	tags: string[];
	claims: { claim_text: string; attributed_source_text: string | null }[];
	tweedekamer_activiteit_url: string | null;
	speaker_video_url: string | null;
	gist: string;
	samenvatting: string | null;
}

interface BandSlot {
	type: "node" | "ref";
	id?: number;
	kids?: number[];
	ref_id?: number;
	band_nummer?: number;
}

interface Band {
	nummer: number;
	thema: string;
	pro: BandSlot | null;
	contra: BandSlot | null;
	oppositie: { argument_a_id: number; argument_b_id: number; relation_type: string } | null;
}

interface LosseGroep {
	kind: "group";
	label: string;
	samenvatting: string | null;
	member_ids: number[];
}

interface Twijfel {
	argument_id: number;
	huidige_stance: string;
	reden: string;
}

interface ConfrontatieExport {
	slug: string;
	name: string;
	topic_description: string | null;
	stats: { totaal_argumenten: number; aantal_pro: number; aantal_contra: number; aantal_geselecteerd: number };
	arguments: Record<string, ExportArgument>;
	bands: Band[];
	losse_groepen: LosseGroep[];
	losse_argumenten: number[];
	twijfelachtige_classificaties: Twijfel[];
}

const props = defineProps<{ tree: ConfrontatieExport }>();

const TYPE_NL: Record<string, string> = {
	factual: "feitelijk",
	moral: "moreel",
	legal: "juridisch",
	economic: "economisch",
	other: "overig",
};
function typeNl(t: string): string {
	return TYPE_NL[t] ?? t;
}

function argumentFor(id: number | undefined): ExportArgument | undefined {
	if (id === undefined) return undefined;
	return props.tree.arguments[String(id)];
}

// Alleen de eerste zin van de topic-description (het PRO=/CONTRA=-narratief
// staat er in detail, maar dat hoort in het detailpaneel/de brondocumentatie
// thuis, niet in de introalinea van de boom zelf).
const introSentence = computed(() => {
	const text = props.tree.topic_description ?? "";
	const firstParagraph = text.split("\n\n")[0] ?? text;
	return firstParagraph.trim();
});

const toonCitaten = ref(false);
const toonOnderbouwing = ref(true);
const toonTwijfel = ref(false);

// Zelfde vlag als de ontwikkelbalk (SiteNav.astro): fail-open, dus zichtbaar
// tenzij een build zichzelf expliciet als officieel bestempelt. Twijfelachtige
// classificaties zijn ruwe, ongefilterde LLM-output -- geschikt om tijdens
// ontwikkeling te inspecteren, niet om in de officiële publicatie te tonen.
const officieel = import.meta.env.PUBLIC_RELEASE_OFFICIEEL === "true";

const selectedId = ref<number | null>(null);
const hoverId = ref<number | null>(null);

const selectedArgument = computed(() => (selectedId.value === null ? undefined : argumentFor(selectedId.value)));

function selectArgument(id: number) {
	selectedId.value = selectedId.value === id ? null : id;
}

// Het detailpaneel is een los, zwevend paneel (geen vaste kolom die altijd
// ruimte inneemt, zie ArgumentTree.vue-geschiedenis) -- klik erbuiten of
// Escape sluit het weer dicht. Een klik op een kaart zelf telt niet als
// "erbuiten": die heeft al zijn eigen @click (selectArgument) dat de
// selectie verandert i.p.v. het paneel te sluiten. Zelfde patroon als
// FilterBar.vue.
const panelRef = ref<HTMLElement | null>(null);

function onDocumentPointerDown(e: PointerEvent) {
	if (selectedId.value === null) return;
	const target = e.target as Node;
	if (panelRef.value?.contains(target)) return;
	if (target instanceof Element && target.closest("[data-arg]")) return;
	selectedId.value = null;
}

function onKeydown(e: KeyboardEvent) {
	if (e.key !== "Escape") return;
	selectedId.value = null;
}

const oppositionPartners = computed(() => {
	const map = new Map<number, number[]>();
	for (const band of props.tree.bands) {
		const opp = band.oppositie;
		if (!opp) continue;
		const { argument_a_id: a, argument_b_id: b } = opp;
		if (!map.has(a)) map.set(a, []);
		if (!map.has(b)) map.set(b, []);
		map.get(a)!.push(b);
		map.get(b)!.push(a);
	}
	return map;
});

function isLinked(id: number): boolean {
	if (hoverId.value === null && selectedId.value === null) return false;
	const active = hoverId.value ?? selectedId.value;
	if (active === id) return false;
	return (oppositionPartners.value.get(id) ?? []).includes(active as number);
}

function oppositionGist(id: number): string | null {
	const partners = oppositionPartners.value.get(id);
	if (!partners || partners.length === 0) return null;
	const partner = argumentFor(partners[0]);
	return partner ? `#${partners[0]} ${partner.gist}` : null;
}

const selectedOppositionId = computed(() => {
	if (selectedId.value === null) return null;
	const partners = oppositionPartners.value.get(selectedId.value);
	return partners && partners.length ? partners[0] : null;
});

const losseGroepenPro = computed(() => props.tree.losse_groepen.filter((g) => argumentFor(g.member_ids[0])?.stance === "pro"));
const losseGroepenContra = computed(() => props.tree.losse_groepen.filter((g) => argumentFor(g.member_ids[0])?.stance === "contra"));
const losseArgumentenPro = computed(() => props.tree.losse_argumenten.filter((id) => argumentFor(id)?.stance === "pro"));
const losseArgumentenContra = computed(() => props.tree.losse_argumenten.filter((id) => argumentFor(id)?.stance === "contra"));

// --- Weerleggingslijnen: live gemeten kaartposities i.p.v. vaste
// coördinaten, zodat lijnen blijven kloppen als citaten/onderbouwing
// aan- of uitgezet worden (zie ontwerpgids §4). Zelfde aanpak als het
// .dc.html-prototype (measure() + buildLinks()), hier als Vue computed
// over een reactieve `rects`-snapshot.
const wrapRef = ref<HTMLElement | null>(null);
const rects = ref<Record<number, { x: number; y: number; w: number; h: number; anchorY: number }>>({});
const wrapWidth = ref(0);
const wrapHeight = ref(0);
const spineX = ref(0);

function measure() {
	const el = wrapRef.value;
	if (!el) return;
	const base = el.getBoundingClientRect();
	wrapWidth.value = base.width;
	wrapHeight.value = base.height;
	// Spine = het echte midden van de "thema"-kolom, niet wrapWidth/2:
	// die twee zijn alleen gelijk als .confrontatie-bands-wrap precies zo
	// breed is als de 3-koloms band-rij zelf, wat afhankelijk van
	// paginabreedte/scroll niet altijd klopt.
	const mid = el.querySelector(".confrontatie-band-mid");
	if (mid) {
		const midBox = mid.getBoundingClientRect();
		spineX.value = Math.round(midBox.left + midBox.width / 2 - base.left);
	}
	const next: Record<number, { x: number; y: number; w: number; h: number; anchorY: number }> = {};
	el.querySelectorAll("[data-arg]").forEach((node) => {
		const id = Number(node.getAttribute("data-arg"));
		if (Number.isNaN(id)) return;
		const b = node.getBoundingClientRect();
		// Verankeren op het verticale midden van de kicker-regel (typologie +
		// #id) i.p.v. een gegokt vast offset vanaf de kaartrand -- zo blijft de
		// lijn kloppen ongeacht kaartvariant/padding/lettergrootte, i.p.v. uit
		// de pas te lopen zodra de kaartstijl verandert.
		const kicker = node.querySelector(".ack-kicker");
		const anchorRect = kicker ? kicker.getBoundingClientRect() : b;
		next[id] = {
			x: Math.round(b.left - base.left),
			y: Math.round(b.top - base.top),
			w: Math.round(b.width),
			h: Math.round(b.height),
			anchorY: Math.round(anchorRect.top + anchorRect.height / 2 - base.top),
		};
	});
	rects.value = next;
}

let measureTimer: ReturnType<typeof setTimeout> | undefined;
function scheduleMeasure() {
	clearTimeout(measureTimer);
	measureTimer = setTimeout(measure, 80);
}

let resizeObserver: ResizeObserver | null = null;

onMounted(() => {
	window.addEventListener("resize", scheduleMeasure);
	if (window.ResizeObserver && wrapRef.value) {
		resizeObserver = new ResizeObserver(scheduleMeasure);
		resizeObserver.observe(wrapRef.value);
	}
	measure();
	setTimeout(measure, 400);
	if (document.fonts?.ready) document.fonts.ready.then(measure);
	document.addEventListener("pointerdown", onDocumentPointerDown);
	document.addEventListener("keydown", onKeydown);
});

onUnmounted(() => {
	window.removeEventListener("resize", scheduleMeasure);
	resizeObserver?.disconnect();
	clearTimeout(measureTimer);
	document.removeEventListener("pointerdown", onDocumentPointerDown);
	document.removeEventListener("keydown", onKeydown);
});

watch([toonCitaten, toonOnderbouwing, toonTwijfel], () => nextTick(scheduleMeasure));

interface LinkPath {
	key: string;
	d: string;
	stroke: string;
	w: number;
	mx: number;
	my: number;
}

const MARGIN = 14;
const CORNER = 8;

interface KidsRail {
	key: string;
	x: number;
	y1: number;
	y2: number;
}

// De verticale rail naast een reeks onderbouwing-kaarten getekend als
// gemeten SVG-lijn i.p.v. een CSS `border-right/-left` op de wrapper-div:
// een CSS-border loopt altijd tot de onderkant van die div (= onderkant van
// de laatste kaart), niet tot het laatste verbindingsstreepje (dat op
// `anchorY` van de kicker-regel zit, ruim boven de kaart-onderkant) -- dat
// gaf een rail die zichtbaar doorliep na de laatste aftakking. Hier stopt
// hij precies bij de anchorY van de eerste/laatste kid, wat de knikpunten
// van de individuele verbindingsstreepjes (zie ArgumentConfrontatieKaart.vue)
// ook daadwerkelijk zijn.
const kidsRails = computed<KidsRail[]>(() => {
	const r = rects.value;
	const out: KidsRail[] = [];
	for (const band of props.tree.bands) {
		for (const sideKey of ["pro", "contra"] as const) {
			const slot = band[sideKey];
			if (!slot || slot.type !== "node" || slot.id === undefined) continue;
			const kids = slot.kids ?? [];
			if (!kids.length) continue;
			const hoofd = r[slot.id];
			if (!hoofd) continue;
			const kidYs = kids.map((id) => r[id]?.anchorY).filter((y): y is number => y !== undefined);
			if (!kidYs.length) continue;
			// Start bij de hoofdkaart zelf (niet pas bij de eerste kid): dat
			// laat in één lijn zien dat de hele tak -- hoofdargument mét
			// onderbouwing -- samenhangt, i.p.v. een los stukje rail dat pas
			// begint bij de eerste aftakking.
			out.push({
				key: `${band.nummer}-${sideKey}`,
				x: sideKey === "pro" ? hoofd.x + hoofd.w : hoofd.x,
				y1: Math.min(hoofd.anchorY, ...kidYs),
				y2: Math.max(hoofd.anchorY, ...kidYs),
			});
		}
	}
	return out;
});

const links = computed<LinkPath[]>(() => {
	const r = rects.value;
	const spine = spineX.value;
	const out: LinkPath[] = [];

	for (const band of props.tree.bands) {
		const opp = band.oppositie;
		if (!opp) continue;
		const aArg = argumentFor(opp.argument_a_id);
		if (!aArg) continue;
		const proId = aArg.stance === "pro" ? opp.argument_a_id : opp.argument_b_id;
		const contraId = proId === opp.argument_a_id ? opp.argument_b_id : opp.argument_a_id;
		const ra = r[proId];
		const rb = r[contraId];
		if (!ra || !rb) continue;

		const live = hoverId.value === proId || hoverId.value === contraId || selectedId.value === proId || selectedId.value === contraId;
		const stroke = live ? "var(--confrontatie-accent-strong)" : "var(--confrontatie-accent-soft)";
		const w = live ? 2 : 1;
		const ay = ra.anchorY;
		const by = rb.anchorY;
		const key = `${proId}-${contraId}`;

		const sameBand = band.pro?.type === "node" && band.contra?.type === "node";
		if (sameBand) {
			const ax = ra.x + ra.w;
			const bx = rb.x;
			const flat = Math.abs(ay - by) < 6;
			const d = flat
				? `M ${ax} ${ay} H ${bx}`
				: `M ${ax} ${ay} H ${spine - 24} C ${spine} ${ay}, ${spine} ${by}, ${spine + 24} ${by} H ${bx}`;
			const my = flat ? ay : (ay + by) / 2;
			out.push({ key, d, stroke, w, mx: spine, my });
			continue;
		}

		// Cross-band: de kaart die hier "ontbreekt" (verwijskaart) staat
		// elders op de pagina. We routeren om de buitenmarge heen -- links als
		// het de pro-kant betreft (pro-kolom ligt links), rechts voor contra.
		const my = (ay + by) / 2;
		if (band.pro?.type === "ref") {
			const gx = MARGIN;
			const dir = ay < by ? CORNER : -CORNER;
			const d = `M ${ra.x} ${ay} H ${gx + CORNER} Q ${gx} ${ay} ${gx} ${ay + dir} V ${by - dir} Q ${gx} ${by} ${gx + CORNER} ${by} H ${rb.x}`;
			out.push({ key, d, stroke, w, mx: gx, my });
		} else {
			const gx = wrapWidth.value - MARGIN;
			const dir = ay < by ? CORNER : -CORNER;
			const ax = ra.x + ra.w;
			const d = `M ${ax} ${ay} H ${gx - CORNER} Q ${gx} ${ay} ${gx} ${ay + dir} V ${by - dir} Q ${gx} ${by} ${gx - CORNER} ${by} H ${rb.x + rb.w}`;
			out.push({ key, d, stroke, w, mx: gx, my });
		}
	}
	return out;
});
</script>

<style scoped>
/* Hergebruikt de bestaande site-tokens (main.css, "Ink & Rust") 1-op-1 --
   geen los kleuren-/font-systeem naast de rest van bipolariteit.nl. Deze
   laag van namen blijft alleen bestaan zodat de regels hieronder leesbaar
   verwijzen naar een rol (`--confrontatie-accent-text`) i.p.v. steeds
   `var(--color-accent)` te herhalen; de dark-mode-variant komt vanzelf mee
   omdat --color-* zelf al omslaat via :root[data-theme="dark"] in main.css
   -- geen aparte donkere-thema-override hier nodig. Zie
   docs/design/argumentenboom/ voor de (niet meer gebruikte) Classical-
   ontwerpreferentie van de designer.
   `.confrontatie` heeft bewust geen eigen achtergrond/padding: die komt al
   van de omringende `.argument-tree-section` in topics/[slug].astro. */
.confrontatie {
	--confrontatie-text: var(--color-text);
	--confrontatie-muted: var(--color-muted);
	--confrontatie-muted-2: var(--color-muted);
	--confrontatie-divider: var(--color-border);
	--confrontatie-surface: var(--color-bg);
	--confrontatie-accent: var(--color-accent);
	--confrontatie-accent-text: var(--color-accent);
	--confrontatie-accent-soft: var(--color-border);
	--confrontatie-accent-strong: var(--color-accent);
	--confrontatie-font-heading: var(--font-heading);
	--confrontatie-font-body: var(--font-body);

	/* Geen vaste sidebar-kolom meer -- die nam altijd ruimte in, ook zonder
	   selectie, en drukte het diagram onnodig smal. Het detailpaneel is nu
	   een zwevend paneel (zie .confrontatie-detail hieronder) dat alleen
	   verschijnt bij een selectie. */
	color: var(--confrontatie-text);
	font-family: var(--confrontatie-font-body);
}

/* Alleen dit brede binnenwerk (kop t/m voetnoot) scrollt bij een smal
   scherm horizontaal -- de confrontatie-as heeft nu eenmaal een harde
   minimumbreedte (vaste kaartbreedtes, zie ontwerpgids §9). Het paneel
   ernaast (sticky, 300px) blijft daardoor altijd gewoon in beeld, in
   plaats van dat je er met de hele pagina naartoe moet scrollen. */
.confrontatie-main {
	min-width: 0;
	overflow-x: auto;
}

.confrontatie-header {
	display: grid;
	grid-template-columns: minmax(320px, 1fr) 320px;
	gap: var(--space-4);
	align-items: end;
	padding-bottom: var(--space-3);
	border-bottom: 1px solid var(--confrontatie-text);
}

.confrontatie-kicker {
	font-size: 0.7rem;
	letter-spacing: 0.18em;
	text-transform: uppercase;
	color: var(--confrontatie-muted);
	margin-bottom: 0.9rem;
}

.confrontatie-title {
	font-family: var(--confrontatie-font-heading);
	font-weight: 400;
	/* Herhaalt (bewust) het onderwerp uit de topic-header erboven, als
	   context bij de as -- daarom bescheiden, geen tweede paginatitel. */
	font-size: var(--step-2);
	line-height: 1.15;
	margin: 0;
}

.confrontatie-intro {
	font-size: 0.85rem;
	line-height: 1.55;
	color: var(--confrontatie-text-soft);
	text-align: justify;
	hyphens: auto;
	margin: 0;
}

.confrontatie-legend {
	display: flex;
	flex-wrap: wrap;
	gap: 1rem 2rem;
	padding: 0.9rem 0 1.6rem;
	border-bottom: 1px solid var(--confrontatie-divider);
	align-items: center;
	font-size: 0.75rem;
	color: var(--confrontatie-text-soft);
}

.confrontatie-legend-item {
	display: flex;
	align-items: center;
	gap: 0.5rem;
}

.confrontatie-swatch {
	display: block;
	width: 22px;
	height: 2px;
}

.confrontatie-swatch-pro {
	background: var(--color-pro);
}

.confrontatie-swatch-contra {
	background: var(--color-contra);
}

.confrontatie-legend-dash {
	display: block;
	width: 22px;
	border-top: 1px dashed var(--confrontatie-muted-2);
}

.confrontatie-legend-medallion {
	font-family: var(--confrontatie-font-heading);
	color: var(--confrontatie-accent-text);
	font-size: 0.8rem;
	border: 1px solid var(--confrontatie-accent-soft);
	border-radius: 50%;
	width: 19px;
	height: 19px;
	display: flex;
	align-items: center;
	justify-content: center;
}

.confrontatie-legend-stats {
	margin-left: auto;
	font-feature-settings: "tnum";
	color: var(--confrontatie-muted);
}

.confrontatie-toggles {
	display: flex;
	gap: 1.5rem;
	padding: 0.7rem 0;
	font-size: 0.75rem;
	color: var(--confrontatie-muted);
}

.confrontatie-toggles label {
	display: flex;
	align-items: center;
	gap: 0.4rem;
	cursor: pointer;
}

.confrontatie-colheader {
	display: grid;
	grid-template-columns: minmax(370px, 1fr) 196px minmax(370px, 1fr);
	padding: 1rem 0 0.5rem;
	align-items: center;
}

.confrontatie-colheader-pro,
.confrontatie-colheader-contra {
	font-family: var(--confrontatie-font-heading);
	font-size: 1.15rem;
	letter-spacing: 0.02em;
}

.confrontatie-colheader-pro {
	text-align: right;
	color: var(--color-pro);
}

.confrontatie-colheader-contra {
	color: var(--color-contra);
}

.confrontatie-colheader-mid {
	text-align: center;
	font-size: 0.65rem;
	letter-spacing: 0.16em;
	text-transform: uppercase;
	color: var(--confrontatie-muted-2);
}

.confrontatie-bands-wrap {
	position: relative;
}

.confrontatie-svg {
	position: absolute;
	left: 0;
	top: 0;
	overflow: visible;
	pointer-events: none;
}

.confrontatie-medallion-bg {
	/* Moet de daadwerkelijke achtergrond erachter matchen (--color-card-bg
	   van .argument-tree-section in topics/[slug].astro, niet de losse
	   paginategel) zodat de gestippelde lijn er zichtbaar "achter" loopt. */
	fill: var(--color-card-bg);
}

.confrontatie-medallion-glyph {
	font-size: 13px;
	font-family: var(--confrontatie-font-heading);
}

.confrontatie-band-row {
	display: grid;
	grid-template-columns: minmax(370px, 1fr) 196px minmax(370px, 1fr);
	align-items: stretch;
}

.confrontatie-band-side {
	display: flex;
	flex-direction: column;
	gap: 0.75rem;
	padding: 1.6rem 0 2.1rem;
}

.confrontatie-band-side-pro {
	align-items: flex-end;
}

.confrontatie-band-side-contra {
	align-items: flex-start;
}

/* Zelfde breedte als de hoofdkaart (336px, zie .ack-hoofd in
   ArgumentConfrontatieKaart.vue) en dezelfde uitlijnkant als
   .confrontatie-band-side-* hierboven -- zo valt de buitenrand van deze
   wrapper altijd exact samen met de buitenrand van de hoofdkaart erboven,
   ongeacht kaartbreedte. De 288px kid-kaart zelf uitlijnen op diezelfde
   buitenrand (flex-start voor pro=links, flex-end voor contra=rechts) laat
   het verschil (336-288=48px) automatisch aan de kant van de as over, waar
   de rail + het verbindingsstreepje (zie ArgumentConfrontatieKaart.vue)
   horen. */
.confrontatie-kids {
	display: flex;
	flex-direction: column;
	gap: 0.6rem;
	width: 336px;
	max-width: 100%;
	box-sizing: border-box;
	margin-top: -0.75rem;
	padding-top: 0.75rem;
}

.confrontatie-kids-pro {
	align-items: flex-start;
}

.confrontatie-kids-contra {
	align-items: flex-end;
}

.confrontatie-band-mid {
	display: flex;
	flex-direction: column;
	align-items: center;
	padding: 0 0.9rem;
}

.confrontatie-band-rule {
	flex: 1;
	width: 1px;
	background: var(--confrontatie-divider);
	min-height: 22px;
}

.confrontatie-band-theme {
	padding: 0.75rem 0;
	text-align: center;
}

.confrontatie-band-no {
	font-family: var(--confrontatie-font-heading);
	font-size: 0.7rem;
	letter-spacing: 0.14em;
	text-transform: uppercase;
	color: var(--confrontatie-accent-text);
	font-feature-settings: "tnum";
}

.confrontatie-band-label {
	/* Was italic, bedoeld voor een korte titel ("Vergunningverlening"); de
	   inhoud hier is nu een hele (mechanisch samengestelde) zin uit de twee
	   gists van het weersproken paar, en leest schuin over meerdere regels
	   onprettig. */
	font-family: var(--confrontatie-font-heading);
	font-size: 0.95rem;
	line-height: 1.3;
	margin-top: 0.35rem;
	color: var(--confrontatie-text-soft);
}

/* Iets steviger dan een gewone --confrontatie-divider-lijn (zelfde kleur als
   de rail-streepjes, --confrontatie-muted-2): de rechterrand van de
   volgende band se hoofdkaart valt toevallig op precies dezelfde x als de
   rail hierboven (beide rechts uitgelijnd op dezelfde kolomrand) -- zonder
   duidelijke horizontale stop leest dat als één doorlopende verticale lijn
   i.p.v. twee losse dingen in twee aparte banden. */
.confrontatie-band-divider {
	height: 1px;
	background: var(--confrontatie-muted-2);
}

.confrontatie-losse {
	padding-top: 2.3rem;
}

.confrontatie-losse-header,
.confrontatie-twijfel-header {
	display: flex;
	align-items: baseline;
	gap: 1rem;
	padding-bottom: 0.85rem;
	border-bottom: 1px solid var(--confrontatie-text);
}

.confrontatie-losse-header h2,
.confrontatie-twijfel-header h2 {
	font-family: var(--confrontatie-font-heading);
	font-weight: 400;
	font-size: 1.8rem;
	margin: 0;
	line-height: 1;
}

.confrontatie-losse-header span,
.confrontatie-twijfel-header span {
	font-size: 0.75rem;
	color: var(--confrontatie-muted);
}

.confrontatie-losse-row {
	display: grid;
	grid-template-columns: minmax(370px, 1fr) 196px minmax(370px, 1fr);
	align-items: start;
	padding-top: 1rem;
}

.confrontatie-losse-groep {
	display: flex;
	flex-direction: column;
	gap: 0.6rem;
}

.confrontatie-band-side-pro .confrontatie-losse-groep {
	align-items: flex-end;
}

.confrontatie-band-side-contra .confrontatie-losse-groep {
	align-items: flex-start;
}

.confrontatie-losse-groep-label {
	font-family: var(--confrontatie-font-heading);
	font-style: italic;
	font-size: 0.9rem;
	color: var(--confrontatie-text-soft);
	margin-bottom: 0.2rem;
}

.confrontatie-losse-groep-samenvatting {
	font-size: 0.8rem;
	line-height: 1.5;
	color: var(--confrontatie-text-soft);
	margin-bottom: 0.4rem;
	max-width: 336px;
}

.confrontatie-losse-mid-label {
	font-family: var(--confrontatie-font-heading);
	font-style: italic;
	font-size: 0.9rem;
	color: var(--confrontatie-muted);
	text-align: center;
}

.confrontatie-twijfel {
	margin-top: 3.5rem;
	padding-top: 1.3rem;
	border-top: 1px solid var(--confrontatie-text);
}

.confrontatie-twijfel-grid {
	display: grid;
	grid-template-columns: repeat(3, minmax(0, 1fr));
	gap: 0 2.5rem;
	margin-top: 1.1rem;
}

.confrontatie-twijfel-item {
	padding: 1rem 0;
	border-top: 1px solid var(--confrontatie-divider);
}

.confrontatie-twijfel-kicker {
	display: flex;
	gap: 0.75rem;
	font-size: 0.65rem;
	letter-spacing: 0.1em;
	text-transform: uppercase;
	color: var(--confrontatie-muted);
	font-feature-settings: "tnum";
	margin-bottom: 0.45rem;
}

.confrontatie-muted-2 {
	color: var(--confrontatie-muted-2);
}

.confrontatie-twijfel-reden {
	font-size: 0.8rem;
	line-height: 1.55;
	color: var(--confrontatie-text-soft);
	text-align: justify;
	hyphens: auto;
}

.confrontatie-footer {
	margin-top: 3.5rem;
	padding-top: 1.1rem;
	border-top: 1px solid var(--confrontatie-divider);
	font-size: 0.7rem;
	line-height: 1.6;
	color: var(--confrontatie-muted);
	max-width: 48rem;
	text-align: justify;
	hyphens: auto;
}

/* Zwevend paneel i.p.v. een vaste kolom: neemt geen ruimte in zolang er
   niets geselecteerd is, en drukt het diagram dus nooit onnodig smal. Zelfde
   sluitgedrag (Escape, klik erbuiten) als de mobiele filtersheet in
   FilterBar.vue. */
.confrontatie-detail {
	position: fixed;
	top: var(--space-4);
	right: var(--space-3);
	z-index: 25;
	width: min(360px, calc(100vw - 2 * var(--space-3)));
	max-height: calc(100vh - 2 * var(--space-4));
	overflow: auto;
	border: 1px solid var(--confrontatie-divider);
	border-top: 2px solid var(--confrontatie-accent);
	background: var(--confrontatie-surface);
	box-shadow: 0 6px 20px rgba(0, 0, 0, 0.16);
	padding: 1.35rem 1.35rem 1.6rem;
}

.confrontatie-panel-enter-active,
.confrontatie-panel-leave-active {
	transition: opacity 0.15s ease, transform 0.15s ease;
}

.confrontatie-panel-enter-from,
.confrontatie-panel-leave-to {
	opacity: 0;
	transform: translateY(-6px);
}

.confrontatie-detail-head {
	display: flex;
	justify-content: space-between;
	align-items: baseline;
	gap: 0.75rem;
	margin-bottom: 0.9rem;
}

.confrontatie-detail-kicker {
	font-size: 0.65rem;
	letter-spacing: 0.14em;
	text-transform: uppercase;
	color: var(--confrontatie-muted-2);
	font-feature-settings: "tnum";
}

.confrontatie-detail-close {
	font-size: 0.7rem;
	color: var(--confrontatie-muted-2);
	background: none;
	border: none;
	cursor: pointer;
	padding: 0;
}

.confrontatie-detail-close:hover {
	color: var(--confrontatie-accent-text);
}

.confrontatie-detail-gist {
	font-family: var(--confrontatie-font-heading);
	font-size: 1.55rem;
	line-height: 1.15;
	margin-bottom: 0.25rem;
}

.confrontatie-detail-speaker {
	font-size: 0.78rem;
	color: var(--confrontatie-muted);
	padding-bottom: 0.9rem;
	border-bottom: 1px solid var(--confrontatie-divider);
}

.confrontatie-detail-quote {
	font-family: var(--confrontatie-font-heading);
	font-size: 1.02rem;
	line-height: 1.5;
	margin: 1rem 0 0.25rem;
	text-align: justify;
	hyphens: auto;
}

.confrontatie-detail-block {
	margin-top: 1.25rem;
	padding-top: 0.9rem;
	border-top: 1px solid var(--confrontatie-divider);
}

.confrontatie-detail-label {
	font-size: 0.65rem;
	letter-spacing: 0.14em;
	text-transform: uppercase;
	color: var(--confrontatie-muted-2);
	margin-bottom: 0.55rem;
}

.confrontatie-detail-claim {
	font-size: 0.78rem;
	line-height: 1.5;
	color: var(--confrontatie-text-soft);
	padding: 0.4rem 0 0.4rem 0.85rem;
	border-left: 1px solid var(--confrontatie-accent-soft);
}

.confrontatie-detail-oppositielink {
	font-size: 0.8rem;
	line-height: 1.5;
	color: var(--confrontatie-accent-text);
	cursor: pointer;
	font-feature-settings: "tnum";
}

.confrontatie-detail-oppositielink:hover {
	text-decoration: underline;
}

.confrontatie-detail-tags {
	display: flex;
	flex-wrap: wrap;
	gap: 0.4rem;
}

.confrontatie-detail-tags span {
	font-size: 0.65rem;
	letter-spacing: 0.04em;
	padding: 0.2rem 0.5rem;
	border: 1px solid var(--confrontatie-divider);
	color: var(--confrontatie-text-soft);
}

.confrontatie-detail-links {
	display: flex;
	gap: 0.75rem;
	font-size: 0.75rem;
	margin-top: 1rem;
}

.confrontatie-detail-links a {
	color: var(--confrontatie-accent-text);
}
</style>
