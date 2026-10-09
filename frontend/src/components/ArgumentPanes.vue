<template>
	<section ref="rootEl" class="ap" :data-level="level" aria-label="Argumentenboom in panelen">
		<!-- Niveau 1: overzicht. Op een smal scherm de startpagina, op een breed scherm het linkerpaneel. -->
		<div class="ap-pane ap-overview">
			<div class="ap-pane-body">
				<p class="ap-kicker">Argumentenboom · {{ tree.name }}</p>
				<p class="ap-intro">{{ introText }}</p>

				<div class="ap-totals" role="group" aria-label="Alle uitgelichte argumenten">
					<div class="ap-totals-bar" aria-hidden="true">
						<span class="ap-totals-pro" :style="{ flexGrow: totals.pro }"></span>
						<span class="ap-totals-contra" :style="{ flexGrow: totals.contra }"></span>
					</div>
					<div class="ap-totals-buttons">
						<button type="button" class="ap-total ap-total-pro" :class="{ 'is-active': scope === 'all' && side === 'pro' }" @click="openList('pro', 'all')">
							<span class="ap-total-count">{{ totals.pro }}</span>
							<span class="ap-total-label">Voor</span>
						</button>
						<button type="button" class="ap-total ap-total-contra" :class="{ 'is-active': scope === 'all' && side === 'contra' }" @click="openList('contra', 'all')">
							<span class="ap-total-count">{{ totals.contra }}</span>
							<span class="ap-total-label">Tegen</span>
						</button>
					</div>
				</div>

				<h3 v-if="summaries.length" class="ap-label">Deelthema's</h3>
				<div v-for="band in summaries" :key="band.nummer" class="ap-band" :class="{ 'is-active': scope === band.nummer }">
					<div class="ap-band-head">
						<span class="ap-band-no">Deelthema {{ band.nummer }}</span>
						<span class="ap-band-thema">{{ band.thema }}</span>
					</div>
					<div class="ap-band-sides">
						<button type="button" class="ap-band-side ap-band-side-pro" :disabled="band.proCount === 0" @click="openList('pro', band.nummer)">
							<span class="ap-band-count">{{ band.proCount }}</span> voor
						</button>
						<button type="button" class="ap-band-side ap-band-side-contra" :disabled="band.contraCount === 0" @click="openList('contra', band.nummer)">
							<span class="ap-band-count">{{ band.contraCount }}</span> tegen
						</button>
					</div>
				</div>

				<button v-if="loose > 0" type="button" class="ap-loose" :class="{ 'is-active': scope === 'loose' }" @click="openList(side, 'loose')">
					<span>Argumenten zonder tegenhanger</span>
					<span class="ap-loose-count">{{ loose }}</span>
				</button>
			</div>
		</div>

		<!-- Niveau 2: de lijst met argumenten van één kant. -->
		<div class="ap-pane ap-list">
			<div class="ap-pane-body">
				<header class="ap-list-head" :data-side="side">
					<h3 class="ap-list-title">{{ SIDE_LABEL[side] }}</h3>
					<span class="ap-list-scope">{{ scopeLabel }}</span>
				</header>
				<p v-if="groups.length === 0" class="ap-empty">Geen argumenten aan deze kant{{ scope === "all" ? "" : " in dit onderdeel" }}.</p>
				<section v-for="group in groups" :key="group.key" class="ap-group">
					<h4 class="ap-group-title">
						<span v-if="group.nummer !== null" class="ap-group-no">{{ group.nummer }} ·</span> {{ group.title }}
					</h4>
					<p v-if="group.summary" class="ap-group-summary">{{ group.summary }}</p>
					<ul class="ap-entries">
						<li v-for="entry in group.entries" :key="`${entry.kind}-${entry.id}`" class="ap-entry" :class="`ap-entry-${entry.kind}`">
							<button type="button" class="ap-row" :data-side="side" :aria-current="selectedId === entry.id ? 'true' : undefined" @click="selectArgument(entry.id)">
								<span class="ap-row-text">
									<span v-if="entry.kind === 'kid'" class="ap-row-tag">Onderbouwing</span>
									<span v-else-if="entry.kind === 'ref'" class="ap-row-tag">Onderbouwing in deelthema {{ entry.refBand }}</span>
									<span class="ap-row-gist">{{ argumentById(tree, entry.id)?.gist }}</span>
									<span class="ap-row-meta">{{ speakerLine(entry.id) }}</span>
								</span>
								<svg class="ap-chevron" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 5l7 7-7 7" /></svg>
							</button>
						</li>
					</ul>
				</section>
			</div>
			<div class="ap-bar">
				<button type="button" class="ap-back" @click="backToOverview">
					<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 5l-7 7 7 7" /></svg>
					Overzicht
				</button>
				<div class="ap-toggle" role="group" aria-label="Kant">
					<button type="button" class="ap-toggle-pro" :aria-pressed="side === 'pro'" @click="switchSide('pro')">Voor</button>
					<button type="button" class="ap-toggle-contra" :aria-pressed="side === 'contra'" @click="switchSide('contra')">Tegen</button>
				</div>
			</div>
		</div>

		<!-- Niveau 3: het volledige argument. -->
		<div class="ap-pane ap-detail">
			<div v-if="selected" class="ap-pane-body" :data-side="selected.stance">
				<p class="ap-context">
					{{ tree.name }} · {{ SIDE_LABEL[selected.stance] }}<template v-if="selectedBand"> · Deelthema {{ selectedBand.nummer }}</template>
				</p>
				<p v-if="selectedBand" class="ap-context-thema">{{ selectedBand.thema }}</p>

				<p class="ap-detail-kicker">{{ SIDE_LABEL[selected.stance] }} · {{ typeNl(selected.typologie) }} · #{{ selected.id }}</p>
				<h3 class="ap-detail-gist">{{ selected.gist }}</h3>
				<p v-if="selected.samenvatting" class="ap-detail-summary">{{ selected.samenvatting }}</p>

				<blockquote class="ap-quote">
					<p>&ldquo;{{ selected.citaat }}&rdquo;</p>
					<footer>{{ selected.spreker }}<template v-if="selected.partij"> ({{ selected.partij }})</template></footer>
				</blockquote>

				<div v-if="selected.claims.length" class="ap-block">
					<h4 class="ap-label">Genoemde claims</h4>
					<p v-for="(claim, i) in selected.claims" :key="i" class="ap-claim">
						{{ claim.claim_text }}<template v-if="claim.attributed_source_text"> (bron: {{ claim.attributed_source_text }})</template>
					</p>
				</div>

				<div v-if="parent" class="ap-block">
					<h4 class="ap-label ap-label-support">Onderbouwt</h4>
					<button type="button" class="ap-link-row" @click="selectArgument(parent.id)">
						<span class="ap-link-row-text">
							<span class="ap-link-row-gist">{{ parent.gist }}</span>
							<span class="ap-row-meta">{{ speakerLine(parent.id) }}</span>
						</span>
						<svg class="ap-chevron" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 5l7 7-7 7" /></svg>
					</button>
				</div>

				<div v-if="kids.length" class="ap-block">
					<h4 class="ap-label ap-label-support">Onderbouwing</h4>
					<button v-for="kid in kids" :key="kid.id" type="button" class="ap-link-row" @click="selectArgument(kid.id)">
						<span class="ap-link-row-text">
							<span class="ap-link-row-gist">{{ kid.gist }}</span>
							<span class="ap-row-meta">{{ speakerLine(kid.id) }}</span>
						</span>
						<svg class="ap-chevron" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 5l7 7-7 7" /></svg>
					</button>
				</div>

				<div v-if="partner" class="ap-block">
					<h4 class="ap-label ap-label-opposed" :data-side="partner.stance">Tegenover</h4>
					<button type="button" class="ap-link-row ap-partner" :data-side="partner.stance" @click="selectArgument(partner.id)">
						<span class="ap-link-row-text">
							<span class="ap-link-row-gist">{{ partner.gist }}</span>
							<span class="ap-row-meta">{{ speakerLine(partner.id) }}</span>
							<span class="ap-partner-quote">&ldquo;{{ partner.citaat }}&rdquo;</span>
						</span>
						<svg class="ap-chevron" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 5l7 7-7 7" /></svg>
					</button>
				</div>

				<div v-if="selected.tags.length" class="ap-block">
					<h4 class="ap-label">Tags</h4>
					<div class="ap-tags">
						<span v-for="tag in selected.tags" :key="tag">{{ tag }}</span>
					</div>
				</div>

				<div v-if="links.length" class="ap-links">
					<a
						v-for="link in links"
						:key="link.key"
						:href="link.href"
						:target="link.external ? '_blank' : undefined"
						:rel="link.external ? 'noopener' : undefined"
						:title="link.title"
						><img v-if="link.external" src="/icons/tk.svg" alt="" class="ap-link-icon" />{{ link.label }}</a
					>
				</div>
			</div>
			<p v-else class="ap-hint">Kies een argument in de lijst om het volledige citaat te zien.</p>

			<div v-if="selected" class="ap-bar ap-detail-bar">
				<button type="button" class="ap-back" @click="backToList">
					<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 5l-7 7 7 7" /></svg>
					Lijst {{ SIDE_LABEL[selected.stance].toLowerCase() }}
				</button>
			</div>
		</div>
	</section>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import {
	argumentById,
	bandSummaries,
	kidIdsOf,
	listGroups,
	looseCount,
	oppositionPartners,
	parentOf,
	scopeOf,
	sideTotals,
	typeNl,
	type ConfrontatieExport,
	type ExportArgument,
	type Scope,
	type Side,
} from "../lib/argumentTree";
import { externalArgumentLinks, internalVideoLink, type ArgumentLink } from "../lib/argumentLinks";

const props = defineProps<{ tree: ConfrontatieExport }>();

const SIDE_LABEL: Record<Side, string> = { pro: "Voor", contra: "Tegen" };

// Eén toestand voor alle breedtes. Op een smal scherm is er steeds één
// niveau zichtbaar (overzicht, lijst of detail) en volgt `level` uit deze
// toestand; op een breed scherm staan de drie panelen naast elkaar en bepaalt
// alleen `side`/`scope`/`selectedId` wat erin staat. Dat verschil is puur CSS.
const side = ref<Side>("pro");
const scope = ref<Scope>("all");
const listOpen = ref(false);
const selectedId = ref<number | null>(null);

const level = computed<"overview" | "list" | "detail">(() => {
	if (selectedId.value !== null) return "detail";
	return listOpen.value ? "list" : "overview";
});

const totals = computed(() => sideTotals(props.tree));
const summaries = computed(() => bandSummaries(props.tree));
const loose = computed(() => looseCount(props.tree));
const partners = computed(() => oppositionPartners(props.tree));
const parents = computed(() => parentOf(props.tree));

const introText = computed(() => {
	const selected = totals.value.pro + totals.value.contra;
	const bands = props.tree.bands.length;
	const count = `${selected} uitgelichte argumenten uit ${props.tree.stats.totaal_argumenten}.`;
	if (bands === 0) return count;
	const themes = bands === 1 ? "Eén deelthema waar" : `${bands} deelthema's waar`;
	return `${count} ${themes} een voor- en een tegenargument tegenover elkaar staan.`;
});

// Verwijzingen naar argumenten die in de export ontbreken worden overgeslagen
// i.p.v. een lege rij te tonen.
const groups = computed(() =>
	listGroups(props.tree, side.value, scope.value)
		.map((group) => ({ ...group, entries: group.entries.filter((entry) => argumentById(props.tree, entry.id)) }))
		.filter((group) => group.entries.length > 0),
);

const scopeLabel = computed(() => {
	if (scope.value === "all") return "Alle deelthema's";
	if (scope.value === "loose") return "Zonder tegenhanger";
	return `Deelthema ${scope.value}`;
});

const selected = computed(() => argumentById(props.tree, selectedId.value));

const selectedBand = computed(() => {
	if (selectedId.value === null) return null;
	const where = scopeOf(props.tree, selectedId.value);
	return typeof where === "number" ? (props.tree.bands.find((band) => band.nummer === where) ?? null) : null;
});

const parent = computed<ExportArgument | null>(() => {
	if (selectedId.value === null) return null;
	return argumentById(props.tree, parents.value.get(selectedId.value)) ?? null;
});

const kids = computed<ExportArgument[]>(() => {
	if (selectedId.value === null) return [];
	return kidIdsOf(props.tree, selectedId.value)
		.map((id) => argumentById(props.tree, id))
		.filter((kid): kid is ExportArgument => kid !== undefined);
});

// Zoals in ArgumentTree.vue: bij meerdere tegenhangers de eerste.
const partner = computed<ExportArgument | null>(() => {
	if (selectedId.value === null) return null;
	return argumentById(props.tree, partners.value.get(selectedId.value)?.[0]) ?? null;
});

// Zelfde regelset als ArgumentCard.vue en ArgumentTree.vue (issue #173).
const links = computed<ArgumentLink[]>(() => {
	const a = selected.value;
	if (!a) return [];
	const result = externalArgumentLinks({
		tweedekamer_activiteit_url: a.tweedekamer_activiteit_url,
		document_url: null,
		speaker_video_url: null,
		video_url: null,
	});
	const player = internalVideoLink(a.raw_video_url, a.start_seconds);
	if (player) result.push(player);
	return result;
});

function speakerLine(id: number): string {
	const a = argumentById(props.tree, id);
	if (!a) return "";
	const speaker = a.partij ? `${a.spreker} (${a.partij})` : a.spreker;
	return `${speaker} · ${typeNl(a.typologie)}`;
}

function openList(nextSide: Side, nextScope: Scope) {
	side.value = nextSide;
	scope.value = nextScope;
	selectedId.value = null;
	listOpen.value = true;
}

// Een argument kan van de andere kant zijn dan de lijst (via "Tegenover" of
// "Onderbouwt"): de lijst springt dan mee, zodat de selectie altijd zichtbaar
// is. Bij "alle deelthema's" blijft het bereik zoals het was.
function selectArgument(id: number) {
	const target = argumentById(props.tree, id);
	if (!target) return;
	side.value = target.stance;
	if (scope.value !== "all") scope.value = scopeOf(props.tree, id);
	selectedId.value = id;
	listOpen.value = true;
}

function switchSide(next: Side) {
	side.value = next;
	selectedId.value = null;
}

function backToList() {
	selectedId.value = null;
}

function backToOverview() {
	selectedId.value = null;
	listOpen.value = false;
}

// Op een smal scherm vervangt elk niveau het vorige op dezelfde plek in de
// pagina; zonder terugscrollen blijf je halverwege de nieuwe inhoud staan.
// Op een breed scherm blijft de pagina staan.
const rootEl = ref<HTMLElement | null>(null);
watch(level, async () => {
	if (!window.matchMedia("(max-width: 900px)").matches) return;
	await nextTick();
	rootEl.value?.scrollIntoView({ block: "start" });
});
</script>

<style scoped>
/* Site-tokens uit main.css ("Ink & Rust"), dus het donkere thema komt vanzelf
   mee. Ontwerp: issue #251 (drie niveaus: overzicht, lijst, detail). Smal
   scherm: één niveau tegelijk, de terugbalk plakt onderin binnen duimbereik.
   Breed scherm (> 900px, zelfde breekpunt als main.css): drie panelen
   naast elkaar op de hoogte van één scherm, alleen het paneel scrolt. */
.ap {
	display: flex;
	flex-direction: column;
	background: var(--vloei);
	border: 1px solid var(--lijn);
	color: var(--galnoot);
	font-family: var(--font-tekst);
	scroll-margin-top: var(--space-2);
}

.ap-pane {
	display: none;
	min-width: 0;
	flex-direction: column;
}

.ap[data-level="overview"] .ap-overview,
.ap[data-level="list"] .ap-list,
.ap[data-level="detail"] .ap-detail {
	display: flex;
}

.ap-pane-body {
	display: flex;
	flex-direction: column;
	gap: var(--space-2);
	padding: var(--space-3) var(--space-2);
	min-width: 0;
}

/* Anders krimpen de kinderen in het scrollende paneel i.p.v. dat het scrolt. */
.ap-pane-body > * {
	flex-shrink: 0;
}

.ap button {
	font: inherit;
	color: inherit;
}

/* Kleine hoofdletterlabels (kicker, sectiekoppen). */
.ap-kicker,
.ap-label,
.ap-band-no,
.ap-group-title,
.ap-context,
.ap-detail-kicker {
	font-family: var(--font-kop);
	font-size: 0.72rem;
	font-weight: 600;
	letter-spacing: 0.08em;
	text-transform: uppercase;
	color: var(--galnoot-zacht);
	margin: 0;
}

.ap-intro {
	margin: 0;
	font-size: 0.95rem;
	line-height: 1.45;
	color: var(--galnoot-zacht);
}

/* --- Overzicht --- */
.ap-totals {
	display: flex;
	flex-direction: column;
	gap: var(--space-1);
}

.ap-totals-bar {
	display: flex;
	gap: 2px;
	height: 8px;
	border-radius: var(--hoek-rond);
	overflow: hidden;
	background: var(--was);
}

.ap-totals-pro {
	flex-basis: 0;
	background: var(--pro);
}

.ap-totals-contra {
	flex-basis: 0;
	background: var(--contra);
}

.ap-totals-buttons {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(7.5rem, 1fr));
	gap: var(--space-1);
}

.ap-total {
	display: flex;
	align-items: center;
	gap: 0.6rem;
	min-width: 0;
	min-height: 4rem;
	padding: 0.6rem 0.9rem;
	background: var(--blad);
	border: 1px solid var(--lijn);
	border-radius: var(--hoek-m);
	cursor: pointer;
	text-align: left;
}

.ap-total-count {
	font-family: var(--font-kop);
	font-size: 2rem;
	font-weight: 700;
	line-height: 1;
	font-variant-numeric: tabular-nums;
}

.ap-total-label {
	font-family: var(--font-kop);
	font-size: 1.05rem;
	font-weight: 600;
}

.ap-total-pro {
	color: var(--pro);
}

.ap-total-contra {
	color: var(--contra);
}

.ap-band {
	background: var(--blad);
	border: 1px solid var(--lijn);
	border-radius: var(--hoek-m);
	overflow: hidden;
}

.ap-band-head {
	display: flex;
	flex-direction: column;
	gap: 0.25rem;
	padding: 0.8rem var(--space-2) 0.7rem;
}

.ap-band-thema {
	font-size: 1rem;
	font-weight: 500;
	line-height: 1.35;
}

.ap-band-sides {
	display: grid;
	grid-template-columns: 1fr 1fr;
	border-top: 1px solid var(--lijn);
}

.ap-band-side {
	min-height: 3rem;
	background: transparent;
	border: 0;
	cursor: pointer;
	font-family: var(--font-kop);
	font-size: 0.95rem;
	font-weight: 600;
}

.ap-band-side + .ap-band-side {
	border-left: 1px solid var(--lijn);
}

.ap-band-side:disabled {
	cursor: default;
	opacity: 0.45;
}

.ap-band-count {
	font-size: 1.35rem;
	font-variant-numeric: tabular-nums;
	margin-right: 0.15rem;
}

.ap-band-side-pro {
	color: var(--pro);
}

.ap-band-side-contra {
	color: var(--contra);
}

.ap-loose {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: var(--space-2);
	min-height: 3rem;
	padding: 0 var(--space-2);
	background: transparent;
	border: 1px dashed var(--rand);
	border-radius: var(--hoek-m);
	cursor: pointer;
	text-align: left;
	color: var(--galnoot-zacht);
}

.ap-loose-count {
	font-family: var(--font-kop);
	font-weight: 600;
	font-variant-numeric: tabular-nums;
}

/* --- Terug-/navigatiebalk --- */
.ap-bar {
	position: sticky;
	bottom: 0;
	z-index: 1;
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: var(--space-1);
	min-height: 4rem;
	padding: 0 0.75rem;
	background: var(--blad);
	border-top: 1px solid var(--lijn);
}

.ap-back {
	display: inline-flex;
	align-items: center;
	gap: 0.35rem;
	min-height: 3rem;
	padding: 0 0.75rem;
	background: transparent;
	border: 0;
	cursor: pointer;
	font-family: var(--font-kop);
	font-size: 0.95rem;
	font-weight: 600;
}

.ap-toggle {
	display: flex;
	border: 1px solid var(--lijn);
	border-radius: var(--hoek-rond);
	overflow: hidden;
	font-family: var(--font-kop);
	font-size: 0.9rem;
	font-weight: 600;
}

.ap-toggle button {
	min-height: 2.75rem;
	padding: 0 1.1rem;
	background: transparent;
	border: 0;
	cursor: pointer;
	color: var(--galnoot-zacht);
}

.ap-toggle button[aria-pressed="true"].ap-toggle-pro {
	background: var(--pro-was);
	color: var(--pro);
}

.ap-toggle button[aria-pressed="true"].ap-toggle-contra {
	background: var(--contra-was);
	color: var(--contra);
}

/* --- Lijst --- */
.ap-list-head {
	display: flex;
	align-items: baseline;
	gap: var(--space-1);
	padding-top: 0.6rem;
	border-top: 3px solid var(--rand);
	padding-bottom: 0.25rem;
}

.ap-list-head[data-side="pro"] {
	border-top-color: var(--pro);
}

.ap-list-head[data-side="contra"] {
	border-top-color: var(--contra);
}

.ap-list-title {
	margin: 0;
	font-family: var(--font-kop);
	font-size: 1.6rem;
	font-weight: 700;
	line-height: 1.1;
}

.ap-list-head[data-side="pro"] .ap-list-title {
	color: var(--pro);
}

.ap-list-head[data-side="contra"] .ap-list-title {
	color: var(--contra);
}

.ap-list-scope {
	font-size: 0.9rem;
	color: var(--galnoot-zacht);
}

.ap-empty,
.ap-hint {
	margin: 0;
	padding: var(--space-3) var(--space-2);
	color: var(--galnoot-zacht);
	font-size: 0.95rem;
}

.ap-group {
	display: flex;
	flex-direction: column;
	gap: 0.5rem;
}

.ap-group-summary {
	margin: 0;
	font-size: 0.9rem;
	line-height: 1.4;
	color: var(--galnoot-zacht);
}

.ap-entries {
	display: flex;
	flex-direction: column;
	margin: 0;
	padding: 0;
	list-style: none;
}

.ap-row,
.ap-link-row {
	display: flex;
	align-items: center;
	gap: 0.75rem;
	width: 100%;
	min-height: 3.5rem;
	padding: 0.7rem 0.9rem;
	background: var(--blad);
	border: 1px solid var(--lijn);
	border-radius: var(--hoek-m);
	cursor: pointer;
	text-align: left;
}

.ap-row-text,
.ap-link-row-text {
	display: flex;
	flex: 1;
	flex-direction: column;
	gap: 0.2rem;
	min-width: 0;
}

.ap-row-gist,
.ap-link-row-gist {
	font-size: 1.02rem;
	font-weight: 500;
	line-height: 1.3;
}

.ap-row-meta {
	font-size: 0.82rem;
	color: var(--galnoot-zacht);
}

.ap-row-tag {
	font-family: var(--font-kop);
	font-size: 0.68rem;
	font-weight: 600;
	letter-spacing: 0.08em;
	text-transform: uppercase;
	color: var(--onderbouwing);
}

.ap-chevron {
	flex: none;
	color: var(--rand);
}

.ap-row[aria-current="true"][data-side="pro"] {
	border-color: var(--pro);
	box-shadow: inset 4px 0 0 var(--pro);
}

.ap-row[aria-current="true"][data-side="contra"] {
	border-color: var(--contra);
	box-shadow: inset 4px 0 0 var(--contra);
}

/* Onderbouwing: ingesprongen aan een gestippelde tak, één niveau diep. */
.ap-entry-kid,
.ap-entry-ref {
	position: relative;
	padding-left: 1.75rem;
	margin-top: 0.5rem;
}

.ap-entry-kid::before,
.ap-entry-ref::before {
	content: "";
	position: absolute;
	left: 0.85rem;
	top: -0.5rem;
	height: calc(50% + 0.5rem);
	width: 0.8rem;
	border-left: 2px dotted var(--onderbouwing);
	border-bottom: 2px dotted var(--onderbouwing);
	border-bottom-left-radius: 8px;
}

.ap-entry-kid .ap-row,
.ap-entry-ref .ap-row {
	background: transparent;
}

.ap-entry + .ap-entry-node {
	margin-top: 0.5rem;
}

/* --- Detail --- */
.ap-context-thema {
	margin: 0;
	font-size: 0.9rem;
	line-height: 1.4;
	color: var(--galnoot-zacht);
}

.ap-detail-kicker {
	margin-top: var(--space-1);
}

.ap-pane-body[data-side="pro"] .ap-detail-kicker {
	color: var(--pro);
}

.ap-pane-body[data-side="contra"] .ap-detail-kicker {
	color: var(--contra);
}

.ap-detail-gist {
	margin: 0;
	font-family: var(--font-kop);
	font-size: 1.6rem;
	font-weight: 700;
	line-height: 1.15;
}

.ap-detail-summary {
	margin: 0;
	font-size: 1rem;
	line-height: 1.5;
}

.ap-quote {
	margin: 0;
	padding: 0.9rem 1rem;
	background: var(--blad);
	border: 1px solid var(--lijn);
	border-radius: var(--hoek-m);
}

.ap-quote p {
	margin: 0 0 0.5rem;
	font-style: italic;
	font-size: 0.95rem;
	line-height: 1.5;
}

.ap-quote footer {
	font-size: 0.82rem;
	color: var(--galnoot-zacht);
}

.ap-block {
	display: flex;
	flex-direction: column;
	gap: 0.5rem;
}

.ap-label-support {
	color: var(--onderbouwing);
}

.ap-label-opposed[data-side="pro"] {
	color: var(--pro);
}

.ap-label-opposed[data-side="contra"] {
	color: var(--contra);
}

.ap-claim {
	margin: 0;
	font-size: 0.92rem;
	line-height: 1.45;
}

.ap-partner[data-side="pro"] {
	border-left: 3px solid var(--pro);
}

.ap-partner[data-side="contra"] {
	border-left: 3px solid var(--contra);
}

/* Het citaat van de tegenhanger past op een smal scherm niet naast de rest. */
.ap-partner-quote {
	display: none;
	margin-top: 0.3rem;
	font-size: 0.88rem;
	font-style: italic;
	line-height: 1.45;
}

.ap-tags {
	display: flex;
	flex-wrap: wrap;
	gap: 0.4rem;
}

.ap-tags span {
	padding: 0.15rem 0.55rem;
	background: var(--was);
	border-radius: var(--hoek-rond);
	font-size: 0.78rem;
	color: var(--galnoot-zacht);
}

.ap-links {
	display: flex;
	flex-wrap: wrap;
	gap: var(--space-1) var(--space-2);
	font-size: 0.9rem;
}

.ap-link-icon {
	width: 1rem;
	height: 1rem;
	margin-right: 0.3rem;
	vertical-align: -0.15em;
}

.ap button:focus-visible,
.ap a:focus-visible {
	outline: 2px solid var(--galnoot);
	outline-offset: 2px;
}

/* --- Breed scherm: drie panelen naast elkaar --- */
@media (min-width: 901px) {
	.ap {
		display: grid;
		grid-template-columns: minmax(230px, 290px) minmax(290px, 400px) minmax(0, 1fr);
		height: min(80vh, 880px);
		min-height: 520px;
	}

	.ap .ap-pane {
		display: flex;
		min-height: 0;
	}

	/* Wat de lijst nu toont staat in het overzicht gemarkeerd. Op een smal
	   scherm is er geen lijst naast het overzicht, dus daar geen markering. */
	.ap-total-pro.is-active {
		background: var(--pro-was);
		border-color: var(--pro);
	}

	.ap-total-contra.is-active {
		background: var(--contra-was);
		border-color: var(--contra);
	}

	.ap-band.is-active {
		border-color: var(--rand);
	}

	.ap-loose.is-active {
		background: var(--blad);
	}

	.ap-pane + .ap-pane {
		border-left: 1px solid var(--lijn);
	}

	.ap-pane-body {
		flex: 1;
		overflow-y: auto;
		padding: var(--space-3);
	}

	/* De navigatiebalk wordt een werkbalk bovenin; terugknoppen hebben geen nut
	   als alle niveaus al zichtbaar zijn. */
	.ap-bar {
		position: static;
		order: -1;
		min-height: 3.25rem;
		border-top: 0;
		border-bottom: 1px solid var(--lijn);
		justify-content: flex-end;
	}

	.ap-back,
	.ap-detail-bar {
		display: none;
	}

	.ap-partner-quote {
		display: block;
	}

	.ap-detail .ap-pane-body {
		max-width: 46rem;
	}
}
</style>
