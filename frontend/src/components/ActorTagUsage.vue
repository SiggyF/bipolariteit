<script setup lang="ts">
import { computed } from "vue";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import "../lib/echartsSetup";
import { CanvasRenderer } from "echarts/renderers";
import { BarChart, CustomChart } from "echarts/charts";
import { TooltipComponent, GridComponent } from "echarts/components";
import { useTheme } from "../lib/useTheme";
import { displayPartyName } from "../lib/parties";
import { deriveTagUsage, bucketSmallCounts } from "../lib/aggregate";
import { slugify } from "../lib/slug";
import { PERSPECTIEVEN } from "../lib/tagIcons.generated";
import { tagIconPath, tagIconDataUri } from "../lib/tagIcon";
import { perspectiefKleur, themaNaam, VLOEI } from "../lib/vloeiChart";
import PartyLogo from "./PartyLogo.vue";
import ArgumentCard from "./ArgumentCard.vue";
import FilterBar from "./FilterBar.vue";
import { initFiltersFromUrl, matches } from "../lib/filters";
import type { Argument } from "../lib/types";
import type { TagSignaal } from "../lib/tagSignalen";

use([CanvasRenderer, BarChart, CustomChart, TooltipComponent, GridComponent]);

export interface TopicTaggedArgument extends Argument {
	topicSlug: string;
	topicName: string;
}

export interface TagSignaalWeergave extends TagSignaal {
	beschrijving?: string;
	accentColor?: string;
	title: string;
	detail: string;
}

const props = defineProps<{
	name: string;
	mode: "partij" | "persoon";
	argumentList: TopicTaggedArgument[];
	/** Top-N favoriete/minst favoriete tags -- al berekend door de aanroepende
	 * pagina (zie lib/tagSignalen.ts), want dat vergt het volledige corpus
	 * over alle personen heen, niet alleen deze persoon z'n argumentList. */
	favorieteTags?: TagSignaalWeergave[];
	minstFavorieteTags?: TagSignaalWeergave[];
	/** Per tag: mediaan van het gebruik over alle personen/partijen heen
	 * (afhankelijk van `mode`) -- al berekend door de aanroepende pagina,
	 * zelfde reden als favorieteTags. Getoond als een tik bovenop de eigen
	 * balk. */
	tagMedian?: Record<string, number>;
	/** Persoonspagina alleen: mediaan van het gebruik over alleen de
	 * partijgenoten van deze spreker. Laat zien of iemand ook binnen de eigen
	 * fractie op- of onderscheidt, niet alleen t.o.v. de volledige Kamer. */
	tagPartyMedian?: Record<string, number>;
	/** Ruwe, kleurloze SVG-markup van het partijlogo (zie lib/partyIconMono.ts,
	 * alleen server-side leesbaar) -- de kleur wordt hier pas toegevoegd zodat
	 * die met het thema (licht/donker) mee kan schakelen. */
	partyIconSvgRaw?: string | null;
}>();

initFiltersFromUrl(props.argumentList);

const filteredList = computed(() => props.argumentList.filter(matches));

// Zie issue #5: bij deze taggingvolumes heeft een individuele spreker vaak
// maar 1-3 toekenningen van een tag. Op persoonsniveau vouwen we die samen
// i.p.v. ze als ranglijst te tonen -- op partijniveau is het volume hoog
// genoeg dat dat niet nodig is.
const PERSON_TAG_THRESHOLD = 3;

const tagRows = computed(() => {
	const rows = deriveTagUsage(filteredList.value);
	return props.mode === "persoon" ? bucketSmallCounts(rows, PERSON_TAG_THRESHOLD) : rows;
});

// Groepeer op perspectief (in de volgorde van de taxonomie, config/tags.toml)
// i.p.v. kaal op aantal -- zo staan gelijkgekleurde tags bij elkaar en oogt de
// grafiek als vier blokken in plaats van willekeurig door elkaar gehusselde
// kleuren. Binnen een perspectief blijft aantal-aflopend de sortering.
const PERSPECTIEF_VOLGORDE = new Map(PERSPECTIEVEN.map((p, i) => [p.naam, i]));
const gegroepeerdeRows = computed(() => {
	const rows = [...tagRows.value];
	rows.sort((a, b) => {
		const volgordeA = PERSPECTIEF_VOLGORDE.get(a.perspectief) ?? PERSPECTIEVEN.length;
		const volgordeB = PERSPECTIEF_VOLGORDE.get(b.perspectief) ?? PERSPECTIEVEN.length;
		return volgordeA - volgordeB || b.count - a.count;
	});
	return rows;
});

// Ascending so each perspectief-blok reads top-down by count on ECharts' bottom-up axis.
const chartRows = computed(() => [...gegroepeerdeRows.value].reverse());

const isDark = useTheme();
const modus = computed(() => (isDark.value ? "dark" : "light"));

// Kleur per perspectief uit het Vloei-grafiekthema (grafiek.md) i.p.v. de
// tag-styles.json-kleuren: die lagen met #4C7C7A en #B15E4A te dicht op
// pro/contra, en standpuntkleuren zijn voorbehouden aan standpunten. Dezelfde
// bron als de correspondentiekaart (TagCorrespondenceMap.vue), zodat een
// perspectief overal op de site dezelfde kleur draagt. De "overig"-rij
// (bucketSmallCounts) heeft geen perspectief en valt terug op `rand`.

// Mediaan-tik per tag (issue #202): mediaan van het gebruik van díe tag over
// alle personen/partijen heen, bovenop de eigen balk -- zo zie je per tag of
// deze persoon/partij daar boven- of ondergemiddeld op zit, i.p.v. alleen
// één referentielijn voor de hele grafiek. `tagMedian` ontbreekt op een
// `overig`-rij (bucketSmallCounts heeft geen eigen sleutel) en wordt dan
// overgeslagen.
const medianRows = computed(() => {
	if (!props.tagMedian) return [];
	return chartRows.value
		.map((r, i) => {
			const waarde = props.tagMedian![r.sleutel];
			return waarde === undefined ? null : [i, waarde];
		})
		.filter((row): row is number[] => row !== null);
});

// Mediaan-streep in galnoot (de tekstkleur): de enige donkere lijn in de
// grafiek, zoals de middenas in de gespiegelde standpuntbalk (grafiek.md).

// Zelfde plafond als de balken zelf (barMaxWidth hieronder) -- op smalle
// balken (weinig rijen, dus brede category-band) mag de tik/het icoontje niet
// breder uitvallen dan de balk ooit zelf wordt.
const BAR_MAX_WIDTH = 22;

function barHalfHoogte(api: any): number {
	const bandHeight = api.size!([0, 1])[1] as number;
	return Math.min(bandHeight, BAR_MAX_WIDTH) / 2;
}

function renderMedianTik(_params: any, api: any) {
	const idx = api.value(0) as number;
	const med = api.value(1) as number;

	// Afgerond op de pixelgrid: bij een even lineWidth (2px) moet het midden
	// op een heel pixel liggen, anders valt de rand tussen twee pixels en
	// anti-aliast canvas 'm wazig in plaats van scherp.
	const y = Math.round(api.coord([0, idx])[1]);
	const xMed = Math.round(api.coord([med, idx])[0]);
	const capHalf = Math.round(barHalfHoogte(api));
	const color = VLOEI[modus.value].galnoot;

	// Mediaan-tik als "I": een verticale streep met korte dwarsstreepjes aan
	// de uiteinden, zoals een foutbalk/mediaanmarkering in statistiekgrafieken
	// -- geen gloed meer. Die hoorde bij de rode radiotuner-naald
	// (VideoTimeline.vue) tegen een "plastic glas"-achtergrond; in vlakke
	// inkt oogde diezelfde vorm alleen nog als een onverklaarde wazige balk.
	const capWidth = 4;
	const line = { stroke: color, lineWidth: 2, opacity: 0.75 };
	return {
		type: "group",
		children: [
			{ type: "line", shape: { x1: xMed, y1: y - capHalf, x2: xMed, y2: y + capHalf }, style: line },
			{ type: "line", shape: { x1: xMed - capWidth / 2, y1: y - capHalf, x2: xMed + capWidth / 2, y2: y - capHalf }, style: line },
			{ type: "line", shape: { x1: xMed - capWidth / 2, y1: y + capHalf, x2: xMed + capWidth / 2, y2: y + capHalf }, style: line },
		],
	};
}

function medianTooltip(params: any) {
	const [idx, waarde] = params.value as number[];
	const sleutel = chartRows.value[idx]?.sleutel ?? "";
	const over = props.mode === "persoon" ? "alle sprekers" : "alle partijen";
	return `<strong>${sleutel}</strong><br/>mediaan over ${over}: ${Math.round(waarde * 100)}%`;
}

// Partijgenoten-mediaan als klein grijstinten partijicoontje i.p.v. een tik
// (issue #202-vervolg): alleen op de persoonspagina, als losstaand symbool
// naast de tik voor het Kamerbrede mediaan zodat de twee referentiepunten uit
// elkaar te houden zijn. De grijswaarden zitten al in partyIconSvgRaw (zie
// lib/partyIconMono.ts) -- hier alleen base64-encoderen, geen kleur meer
// toevoegen, want dat zou het per-laag contrast dat de leesbaarheid van het
// silhouet geeft weer plat zetten.
const partyIconUri = computed(() =>
	props.partyIconSvgRaw ? `data:image/svg+xml;base64,${btoa(props.partyIconSvgRaw)}` : null,
);

const partyMedianRows = computed(() => {
	if (!props.tagPartyMedian || !partyIconUri.value) return [];
	return chartRows.value
		.map((r, i) => {
			const waarde = props.tagPartyMedian![r.sleutel];
			return waarde === undefined ? null : [i, waarde];
		})
		.filter((row): row is number[] => row !== null);
});

function renderPartyIcon(_params: any, api: any) {
	const idx = api.value(0) as number;
	const waarde = api.value(1) as number;

	const y = api.coord([0, idx])[1];
	const x = api.coord([waarde, idx])[0];
	// Iets kleiner dan de volle balkhoogte (i.p.v. dezelfde maat als de
	// mediaan-streep) -- zo blijft de streep zelf altijd zichtbaar naast/
	// door het icoon heen, ook als ze bijna op dezelfde plek vallen.
	const size = barHalfHoogte(api) * 2 * 0.8;

	return { type: "image", style: { image: partyIconUri.value!, x: x - size / 2, y: y - size / 2, width: size, height: size } };
}

function partyMedianTooltip(params: any) {
	const [idx, waarde] = params.value as number[];
	const sleutel = chartRows.value[idx]?.sleutel ?? "";
	return `<strong>${sleutel}</strong><br/>mediaan over fractiegenoten: ${Math.round(waarde * 100)}%`;
}

// Tagicoontje voor de as-labels: ECharts' as-labels zijn tekst + optionele
// rich-text-afbeeldingen, geen losse SVG-elementen -- vandaar de data-URI
// (tagIconDataUri) i.p.v. het <svg><path> patroon dat de rest van de site
// gebruikt (bv. TagSignaalBadge.astro). Rich-stijlen zijn een vaste set
// sleutel->stijl, dus één stijl per tagsleutel (niet per rij-index) zodat
// dezelfde tag op andere pagina's dezelfde stijlsleutel hergebruikt.
function richKeyFor(sleutel: string): string {
	return `icon_${sleutel.replace(/[^a-zA-Z0-9]/g, "_")}`;
}

const yAxisRich = computed(() => {
	const rich: Record<string, any> = {};
	const color = VLOEI[modus.value].galnoot;
	for (const r of chartRows.value) {
		const key = richKeyFor(r.sleutel);
		if (rich[key]) continue;
		const uri = tagIconDataUri(r.sleutel, color);
		if (uri) rich[key] = { height: 12, width: 12, backgroundColor: { image: uri } };
	}
	return rich;
});

const chartOption = computed(() => ({
	tooltip: { trigger: "item" },
	grid: { left: 90, right: 24, top: 8, bottom: 16 },
	xAxis: {
		type: "value",
		axisLabel: { formatter: (waarde: number) => `${Math.round(waarde * 100)}%` },
	},
	yAxis: {
		type: "category",
		data: chartRows.value.map((r) => r.sleutel),
		axisLabel: {
			formatter: (sleutel: string) => (tagIconPath(sleutel) ? `{${richKeyFor(sleutel)}|}  ${sleutel}` : sleutel),
			rich: yAxisRich.value,
		},
	},
	series: [
		{
			type: "bar",
			data: chartRows.value.map((r) => ({
				value: taggedArgumentCount.value ? r.count / taggedArgumentCount.value : 0,
				count: r.count,
				itemStyle: { color: perspectiefKleur(r.perspectief, modus.value) },
			})),
			barMaxWidth: BAR_MAX_WIDTH,
			tooltip: {
				formatter: (params: any) =>
					`<strong>${params.name}</strong><br/>${Math.round(params.value * 100)}% (${params.data.count} van ${taggedArgumentCount.value} getagde argumenten)`,
			},
		},
		// z: het partij-icoontje (breder) tekent ónder de mediaan-streep, niet
		// erboven -- anders verdwijnt de dunne streep volledig als beide zo goed
		// als samenvallen (partijgebruik ~ Kamerbreed gebruik voor die tag).
		...(partyMedianRows.value.length
			? [
					{
						type: "custom",
						z: 10,
						data: partyMedianRows.value,
						encode: { x: [1], y: 0 },
						renderItem: renderPartyIcon,
						tooltip: { formatter: partyMedianTooltip },
					},
				]
			: []),
		...(medianRows.value.length
			? [
					{
						type: "custom",
						z: 11,
						data: medianRows.value,
						encode: { x: [1], y: 0 },
						renderItem: renderMedianTik,
						tooltip: { formatter: medianTooltip },
					},
				]
			: []),
	],
}));

const chartHeight = computed(() => `${Math.max(160, chartRows.value.length * 28 + 24)}px`);

const totalArguments = computed(() => filteredList.value.length);

// Noemer voor de tag-percentages in de taghistogram (issue #202): alleen
// argumenten met minstens één LLM-tag, niet alle argumenten -- bijna de helft
// heeft er geen (te kort, buiten de taxonomie, ...), en die als nul
// meetellen zou elk percentage verdunnen t.o.v. wat er in de mediaan-
// berekening (server-side, dezelfde definitie) gebeurt.
const taggedArgumentCount = computed(
	() => filteredList.value.filter((a) => a.tags.some((t) => t.created_by === "llm")).length,
);

const perTopic = computed(() => {
	const byTopic = new Map<string, { topicSlug: string; topicName: string; count: number }>();
	for (const argument of filteredList.value) {
		const existing = byTopic.get(argument.topicSlug);
		if (existing) existing.count += 1;
		else byTopic.set(argument.topicSlug, { topicSlug: argument.topicSlug, topicName: argument.topicName, count: 1 });
	}
	return [...byTopic.values()].sort((a, b) => b.count - a.count);
});

function topicLink(topicSlug: string): string {
	const param = props.mode === "partij" ? "partij" : "persoon";
	return `/onderwerpen/${topicSlug}/?${param}=${encodeURIComponent(props.name)}`;
}

const persons = computed(() => {
	if (props.mode !== "partij") return [];
	const counts = new Map<string, number>();
	for (const argument of filteredList.value) counts.set(argument.actor.name, (counts.get(argument.actor.name) ?? 0) + 1);
	return [...counts.entries()].map(([person, count]) => ({ person, count })).sort((a, b) => b.count - a.count);
});

const exampleArguments = computed(() =>
	[...filteredList.value]
		.sort((a, b) => (b.document.published_at ?? "").localeCompare(a.document.published_at ?? ""))
		.slice(0, 5),
);

// Zelfde ster voor favoriet/minst-favoriet, gevuld vs. omlijnd -- zie
// TagSignaalBadge.astro (de Astro-tegenhanger op de personenlijst) voor de
// volledige toelichting.
const ICOON_STER = "M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 21 12 17.77 5.82 21 7 14.14l-5-4.87 6.91-1.01L12 2z";
</script>

<template>
	<section class="actor-tag-usage">
		<header class="actor-header">
			<PartyLogo v-if="mode === 'partij'" :party="name" />
			<h1>{{ mode === "partij" ? displayPartyName(name) : name }}</h1>
		</header>

		<FilterBar :argumentList="argumentList" :matchCount="filteredList.length" />

		<section v-if="(favorieteTags && favorieteTags.length) || (minstFavorieteTags && minstFavorieteTags.length)" class="stats-panel">
			<h2>
				Favoriete tags
				<a href="/over/#favoriete-tags-methode" class="info-link" title="Hoe favoriet/minst favoriet bepaald wordt" aria-label="Uitleg: hoe favoriet en minst favoriet bepaald worden">?</a>
			</h2>
			<div class="tag-signalen-kolommen">
				<div>
					<h3>Top 3 favoriet</h3>
					<p v-if="!favorieteTags || !favorieteTags.length" class="panel-note">
						Geen tag met minstens 5% aandeel van de eigen getagde argumenten.
					</p>
					<ul v-else class="tag-signalen-lijst">
						<li v-for="signaal in favorieteTags" :key="signaal.sleutel">
							<span class="tag-signaal tag-signaal-favoriet" :style="{ '--tag-signaal-accent': signaal.accentColor }" :title="signaal.title">
								<svg class="tag-signaal-icoon" viewBox="0 0 24 24" width="12" height="12" fill="currentColor" stroke="none">
									<path :d="ICOON_STER" />
								</svg>
								<span class="tag-signaal-sleutel">{{ signaal.sleutel }}</span>
								<svg v-if="tagIconPath(signaal.sleutel)" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
									<path :d="tagIconPath(signaal.sleutel)!" />
								</svg>
							</span>
							<span class="tag-signalen-lijst-beschrijving">{{ signaal.beschrijving }}</span>
							<span class="tag-signalen-lijst-detail">{{ signaal.detail }}</span>
						</li>
					</ul>
				</div>
				<div>
					<h3>Top 3 minst favoriet</h3>
					<ul class="tag-signalen-lijst">
						<li v-for="signaal in minstFavorieteTags" :key="signaal.sleutel">
							<span class="tag-signaal tag-signaal-minst-favoriet" :title="signaal.title">
								<svg class="tag-signaal-icoon" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="1.75">
									<path :d="ICOON_STER" />
								</svg>
								<span class="tag-signaal-sleutel">{{ signaal.sleutel }}</span>
								<svg v-if="tagIconPath(signaal.sleutel)" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
									<path :d="tagIconPath(signaal.sleutel)!" />
								</svg>
							</span>
							<span class="tag-signalen-lijst-beschrijving">{{ signaal.beschrijving }}</span>
							<span class="tag-signalen-lijst-detail">{{ signaal.detail }}</span>
						</li>
					</ul>
				</div>
			</div>
		</section>

		<p v-if="!filteredList.length" class="no-results">
			Geen argumenten voldoen aan dit filter. Verwijder een filter hierboven om er meer te zien.
		</p>

		<template v-else>
			<p class="panel-note">{{ totalArguments }} argumenten in totaal, over {{ perTopic.length }} onderwerp(en).</p>

			<section class="stats-panel">
				<h2>
					Tags
					<a v-if="medianRows.length" href="/over/#tag-mediaan-methode" class="info-link" title="Wat betekent de tik boven een balk?" aria-label="Uitleg: wat de mediaan-tik boven een balk betekent">?</a>
				</h2>
				<p class="panel-note">
					In hoeveel procent van de getagde argumenten van {{ mode === "persoon" ? "deze spreker" : "deze partij" }}
					elke tag voorkomt (argumenten zonder enige LLM-tag tellen niet mee in de noemer). Drie
					labelgroepen die automatisch uit metadata volgen (bv. wie iemand is, in welke setting het gezegd
					werd) staan er niet bij -- die zeggen niets over de eigen argumentatiestijl, alleen door het
					taalmodel zelf herkende tags tellen mee.
					<template v-if="mode === 'persoon'">
						Tags met minder dan {{ PERSON_TAG_THRESHOLD }} toekenningen zijn samengevoegd tot "overig" -- bij deze
						volumes zegt een enkele toekenning weinig.
					</template>
				</p>
				<ul class="vl-legenda">
					<li v-for="perspectief in PERSPECTIEVEN" :key="perspectief.key">
						<span class="vl-swatch" :style="{ '--kleur': perspectiefKleur(perspectief.naam, modus) }" />
						{{ perspectief.naam }}
					</li>
					<li v-if="medianRows.length">
						<span class="vl-swatch is-lijn" :style="{ '--kleur': VLOEI[modus].galnoot }" />
						mediaan over {{ mode === "persoon" ? "alle sprekers" : "alle partijen" }}
					</li>
					<li v-if="partyMedianRows.length">
						<img :src="partyIconUri!" width="12" height="12" alt="" />
						mediaan over fractiegenoten
					</li>
				</ul>
				<p v-if="!tagRows.length" class="panel-note">Geen getagde argumenten.</p>
				<div v-else class="vl-grafiek">
					<VChart
						class="tag-usage-chart"
						:option="chartOption"
						:theme="themaNaam(isDark)"
						:style="{ height: chartHeight }"
						autoresize
					/>
				</div>
			</section>

			<section class="stats-panel">
				<h2>Per onderwerp</h2>
				<ul class="card-grid">
					<li v-for="topic in perTopic" :key="topic.topicSlug">
						<a :href="topicLink(topic.topicSlug)" class="card-tile">
							<span class="card-tile-name">{{ topic.topicName }}</span>
							<span class="card-tile-count">{{ topic.count }} argumenten</span>
						</a>
					</li>
				</ul>
			</section>

			<section v-if="mode === 'partij'" class="stats-panel">
				<h2>Personen</h2>
				<ul class="topic-breakdown">
					<li v-for="row in persons" :key="row.person">
						<a :href="`/personen/${slugify(row.person)}/`">{{ row.person }}</a>
						<span class="topic-count">{{ row.count }} argumenten</span>
					</li>
				</ul>
			</section>

			<!-- Server-gerenderde Astro-slot (bv. tekststatistieken op de
			     persoonspagina) -- géén prop, zodat de onderliggende data nooit
			     in de client-JS-bundle van dit client:only-eiland belandt. -->
			<slot name="voor-argumentlijst" />

			<section class="stats-panel">
				<h2>Voorbeeldargumenten</h2>
				<ArgumentCard v-for="argument in exampleArguments" :key="argument.id" :argument="argument" :topic-slug="argument.topicSlug" />
			</section>
		</template>
	</section>
</template>
