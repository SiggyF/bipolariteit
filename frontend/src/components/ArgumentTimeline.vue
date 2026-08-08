<script setup lang="ts">
import { computed } from "vue";
import { buildTimeline, yearTicks, type TimelineBucket } from "../lib/timeline";
import { setDateRange, toggleValue } from "../lib/filters";
import { STANCES, TYPOLOGIES, stanceLabel, typologyLabel, type Argument, type Stance, type Typology } from "../lib/types";

// `interactive` staat aan op de topic-pagina (TopicView.vue): daar bestaat een
// FilterBar/filterstore, dus klikken op een staaf om te filteren betekent iets.
// De perspectiefpagina (PerspectiefView.vue) heeft geen filterstore -- daar zou
// klikken alleen de URL wijzigen zonder dat er iets zichtbaars gebeurt, dus
// staat interactive daar uit en toont de tijdlijn puur cijfers.
//
// Wie filtert, filtert vooraf: de topic-pagina rekent zelf `matchesExcept(a,
// [DATE_FROM, DATE_TO])` uit voordat argumentList hier binnenkomt, zodat de
// tijdlijn na een klik alle debatdagen blijft tonen i.p.v. in te klappen tot
// de geselecteerde dag.
const props = withDefaults(defineProps<{ argumentList: Argument[]; interactive?: boolean }>(), { interactive: true });

const timeline = computed(() => buildTimeline(props.argumentList));
const ticks = computed(() => (timeline.value ? yearTicks(timeline.value) : []));

const TRACK_HEIGHT = 140;

// Onder dit totaal is een typologiepercentage schijnnauwkeurig -- zelfde
// ondergrens en redenering als PerspectiefTagHeatmap.vue.
const MIN_TOTAL = 8;

const STANCE_COLORS: Record<Stance, string> = {
	pro: "var(--color-pro)",
	contra: "var(--color-contra)",
	unclear: "var(--color-unclear)",
};

// Gevalideerd 4-slot palet (validate_palette.js, licht + donker, alle zes
// checks PASS) plus --color-unclear als bewust neutrale "Overig"-kleur. De
// slotvolgorde is de CVD-garantie en ligt vast; wijzig hier niet de volgorde
// zonder opnieuw te valideren (zie het plan bij issue #54).
const TYPOLOGY_COLORS: Record<Typology, string> = {
	factual: "#6586c3",
	legal: "#804674",
	economic: "#5c884c",
	moral: "#067396",
	other: "var(--color-unclear)",
};

interface Segment {
	key: string;
	color: string;
	bottom: number;
	height: number;
	label: string;
	n: number;
	pct: number;
}

// Een aandeel van een paar procent zou zonder ondergrens als een lijn van
// minder dan 1px renderen -- geen eigen kleurvlak meer, maar een vage rand
// tussen zijn buren. Zulke segmenten krijgen een leesbare minimumhoogte; de
// ruimte daarvoor komt uit de segmenten die toch al ruim boven het minimum
// zitten (evenredig aan hun eigen aandeel), zodat de stapel nog steeds precies
// de volledige stackHeight vult.
const MIN_SEGMENT_HEIGHT = 6;

function stackSegments(
	shares: { key: string; n: number; pct: number; label: string; color: string }[],
	stackHeight: number,
): Segment[] {
	const aanwezig = shares.filter((s) => s.n > 0);
	const natural = aanwezig.map((s) => (s.pct / 100) * stackHeight);
	const klein = natural.map((h) => h < MIN_SEGMENT_HEIGHT);
	const reserved = klein.filter(Boolean).length * MIN_SEGMENT_HEIGHT;
	const remaining = Math.max(0, stackHeight - reserved);
	const sumGroot = natural.reduce((sum, h, i) => sum + (klein[i] ? 0 : h), 0);

	let bottom = 0;
	const segments: Segment[] = [];
	aanwezig.forEach((share, i) => {
		const height = klein[i] ? MIN_SEGMENT_HEIGHT : sumGroot ? (natural[i] / sumGroot) * remaining : 0;
		segments.push({ key: share.key, color: share.color, bottom, height, label: share.label, n: share.n, pct: share.pct });
		bottom += height;
	});
	return segments;
}

const volumeBars = computed(() => {
	if (!timeline.value) return [];
	const { buckets, maxTotal } = timeline.value;
	return buckets.map((bucket) => {
		const stackHeight = maxTotal ? (bucket.total / maxTotal) * TRACK_HEIGHT : 0;
		const shares = STANCES.map((stance) => ({
			key: stance,
			n: bucket.stance[stance],
			pct: bucket.stance[`${stance}_pct`],
			label: stanceLabel(stance),
			color: STANCE_COLORS[stance],
		}));
		return { bucket, segments: stackSegments(shares, stackHeight) };
	});
});

const typologyBars = computed(() => {
	if (!timeline.value) return [];
	return timeline.value.buckets.map((bucket) => {
		if (bucket.total < MIN_TOTAL) return { bucket, segments: [] as Segment[], onderDrempel: true };
		const shares = bucket.typology.map((t) => ({
			key: t.typology,
			n: t.n,
			pct: t.pct,
			label: typologyLabel(t.typology),
			color: TYPOLOGY_COLORS[t.typology],
		}));
		return { bucket, segments: stackSegments(shares, TRACK_HEIGHT), onderDrempel: false };
	});
});

function volumeTitle(bucket: TimelineBucket): string {
	const datum = bucket.van === bucket.tot ? bucket.van : `${bucket.van} t/m ${bucket.tot}`;
	const delen = STANCES.map((s) => `${stanceLabel(s)}: ${bucket.stance[s]}`).join(", ");
	return `${datum} — ${bucket.total} argumenten (${delen})`;
}

function typologyTitle(bucket: TimelineBucket): string {
	const datum = bucket.van === bucket.tot ? bucket.van : `${bucket.van} t/m ${bucket.tot}`;
	if (bucket.total < MIN_TOTAL) return `${datum} — ${bucket.total} argumenten, te weinig voor een betrouwbaar aandeel`;
	const delen = bucket.typology
		.filter((t) => t.n)
		.map((t) => `${typologyLabel(t.typology)}: ${t.pct}% (${t.n})`)
		.join(", ");
	return `${datum} — ${delen}`;
}

function onBarClick(bucket: TimelineBucket) {
	if (props.interactive) setDateRange(bucket.van, bucket.tot);
}

function onLegendClick(typology: string) {
	if (props.interactive) toggleValue("typologie", typology);
}
</script>

<template>
	<section v-if="timeline" class="stats-panel">
		<h2>Tijdlijn <span class="panel-scope">({{ argumentList.length }} argumenten in selectie)</span></h2>
		<p class="panel-note">
			Argumenten komen uit Kamerdebatten en klonteren dus op debatdagen, niet gelijkmatig verspreid over de tijd. Elke
			staaf is één debatdag; de witruimte ertussen is de tijd zonder debat.
			<template v-if="timeline.zonderDatum">{{ timeline.zonderDatum }} argumenten zonder publicatiedatum blijven buiten
				deze tijdlijn.</template>
		</p>

		<h3>Wanneer werd er gedebatteerd</h3>
		<ul class="chart-legend">
			<li v-for="stance in STANCES" :key="stance">
				<span class="legend-swatch" :style="{ background: STANCE_COLORS[stance] }"></span>{{ stanceLabel(stance) }}
			</li>
		</ul>
		<p v-if="interactive" class="panel-note">Klik op een staaf om op die debatdag te filteren.</p>
		<div class="timeline-panel">
			<div class="timeline-track" :style="{ height: `${TRACK_HEIGHT}px` }">
				<button
					v-for="{ bucket, segments } in volumeBars"
					:key="bucket.key"
					type="button"
					class="timeline-bar"
					:class="{ 'timeline-bar-static': !interactive }"
					:style="{ left: `${bucket.offset * 100}%` }"
					:title="volumeTitle(bucket)"
					@click="onBarClick(bucket)"
				>
					<span
						v-for="segment in segments"
						:key="segment.key"
						class="timeline-segment"
						:class="{ 'timeline-segment-top': segment === segments[segments.length - 1] }"
						:style="{ bottom: `${segment.bottom}px`, height: `${Math.max(1, segment.height - 2)}px`, background: segment.color }"
					></span>
				</button>
			</div>
			<div class="timeline-axis">
				<span v-for="tick in ticks" :key="tick.label" class="timeline-axis-tick" :style="{ left: `${tick.offset * 100}%` }">{{
					tick.label
				}}</span>
			</div>
		</div>

		<h3>Argumentvormen door de tijd</h3>
		<ul class="chart-legend">
			<li v-for="typology in TYPOLOGIES" :key="typology">
				<button v-if="interactive" type="button" class="legend-swatch-btn" @click="onLegendClick(typology)">
					<span class="legend-swatch" :style="{ background: TYPOLOGY_COLORS[typology] }"></span>{{ typologyLabel(typology) }}
				</button>
				<template v-else>
					<span class="legend-swatch" :style="{ background: TYPOLOGY_COLORS[typology] }"></span>{{ typologyLabel(typology) }}
				</template>
			</li>
		</ul>
		<p class="panel-note">
			Aandeel per typologie, genormaliseerd op 100% zodat stijlverschuiving los te zien is van debatvolume. Staven met
			minder dan {{ MIN_TOTAL }} argumenten blijven leeg -- bij minder is een percentage schijnnauwkeurig.
			<template v-if="interactive">Klik op de legenda om op een typologie te filteren.</template>
		</p>
		<div class="timeline-panel">
			<div class="timeline-track" :style="{ height: `${TRACK_HEIGHT}px` }">
				<button
					v-for="{ bucket, segments, onderDrempel } in typologyBars"
					:key="bucket.key"
					type="button"
					class="timeline-bar"
					:class="{ 'timeline-bar-empty': onderDrempel, 'timeline-bar-static': !interactive }"
					:style="{ left: `${bucket.offset * 100}%` }"
					:title="typologyTitle(bucket)"
					@click="onBarClick(bucket)"
				>
					<span
						v-for="segment in segments"
						:key="segment.key"
						class="timeline-segment"
						:class="{ 'timeline-segment-top': segment === segments[segments.length - 1] }"
						:style="{ bottom: `${segment.bottom}px`, height: `${Math.max(1, segment.height - 2)}px`, background: segment.color }"
					></span>
				</button>
			</div>
			<div class="timeline-axis">
				<span v-for="tick in ticks" :key="tick.label" class="timeline-axis-tick" :style="{ left: `${tick.offset * 100}%` }">{{
					tick.label
				}}</span>
			</div>
		</div>

		<div class="table-scroll">
			<table class="party-table">
				<caption class="visually-hidden">Argumenten per debatdag, met posities en typologieaandelen uit de tijdlijn</caption>
				<thead>
					<tr>
						<th>Debatdag</th>
						<th>Argumenten</th>
						<th v-for="stance in STANCES" :key="stance">{{ stanceLabel(stance) }}</th>
						<th v-for="typology in TYPOLOGIES" :key="typology">{{ typologyLabel(typology) }}</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="bucket in timeline.buckets" :key="bucket.key">
						<td>{{ bucket.key }}</td>
						<td>{{ bucket.total }}</td>
						<td v-for="stance in STANCES" :key="stance">{{ bucket.stance[`${stance}_pct`] }}% ({{ bucket.stance[stance] }})</td>
						<td v-for="share in bucket.typology" :key="share.typology">
							<template v-if="bucket.total >= MIN_TOTAL">{{ share.pct }}% ({{ share.n }})</template>
							<template v-else>—</template>
						</td>
					</tr>
				</tbody>
			</table>
		</div>
	</section>
</template>
