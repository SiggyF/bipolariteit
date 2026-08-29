<script setup lang="ts">
import { computed } from "vue";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { BarChart, CustomChart } from "echarts/charts";
import { TooltipComponent, GridComponent } from "echarts/components";
import { useTheme } from "../lib/useTheme";
import { displayPartyName } from "../lib/parties";
import { deriveTagUsage, bucketSmallCounts } from "../lib/aggregate";
import { slugify } from "../lib/slug";
import { PERSPECTIEVEN } from "../lib/tagIcons.generated";
import { tagIconPath, tagIconDataUri } from "../lib/tagIcon";
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

// Groepeer op perspectief (in de volgorde van de taxonomie, data/tags.toml)
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

// Kleur per perspectief i.p.v. één vaste kleur -- zelfde bron als de
// correspondentiekaart (TagCorrespondenceMap.vue), zodat een perspectief
// overal op de site dezelfde kleur draagt. De "overig"-rij (bucketSmallCounts)
// heeft geen perspectief en valt terug op de gedempte kleur.
const PERSPECTIEF_KLEUR = new Map(PERSPECTIEVEN.map((p) => [p.naam, p.kleur]));
const ONBEKENDE_KLEUR = "#6f6558";

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

const MEDIAAN_KLEUR = { light: "#221f1b", dark: "#f2ede3" };
const MEDIAAN_RGB = { light: "34, 31, 27", dark: "242, 237, 227" };

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

	const y = api.coord([0, idx])[1];
	const xMed = api.coord([med, idx])[0];
	const capHalf = barHalfHoogte(api);
	const color = isDark.value ? MEDIAAN_KLEUR.dark : MEDIAAN_KLEUR.light;
	const rgb = isDark.value ? MEDIAAN_RGB.dark : MEDIAAN_RGB.light;

	// Zachte gloed achter de streep i.p.v. een harde lijn -- zelfde
	// "radiotuner-naald"-idee als de video-afspeelkop (VideoTimeline.vue),
	// maar dan met de vervaging alleen links-rechts, niet omhoog-omlaag (op
	// verzoek). `shadowBlur` blurt altijd rondom (isotroop), dus i.p.v.
	// daarvan een losse band achter de streep met een horizontale
	// kleur-naar-transparant gradient -- exact zo hoog als de streep zelf,
	// dus geen verticale vervaging.
	const glowHalfWidth = 4;
	return {
		type: "group",
		children: [
			{
				type: "rect",
				shape: { x: xMed - glowHalfWidth, y: y - capHalf, width: glowHalfWidth * 2, height: capHalf * 2 },
				style: {
					fill: {
						type: "linear",
						x: 0,
						y: 0,
						x2: 1,
						y2: 0,
						colorStops: [
							{ offset: 0, color: `rgba(${rgb}, 0)` },
							{ offset: 0.5, color: `rgba(${rgb}, 0.55)` },
							{ offset: 1, color: `rgba(${rgb}, 0)` },
						],
					},
				},
				silent: true,
			},
			{ type: "line", shape: { x1: xMed, y1: y - capHalf, x2: xMed, y2: y + capHalf }, style: { stroke: color, lineWidth: 2 } },
		],
	};
}

function medianTooltip(params: any) {
	const [idx, waarde] = params.value as number[];
	const sleutel = chartRows.value[idx]?.sleutel ?? "";
	const over = props.mode === "persoon" ? "alle sprekers" : "alle partijen";
	return `<strong>${sleutel}</strong><br/>mediaan over ${over}: ${waarde.toFixed(1)}`;
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
	return `<strong>${sleutel}</strong><br/>mediaan over fractiegenoten: ${waarde.toFixed(1)}`;
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
	const color = isDark.value ? "#f2ede3" : "#221f1b";
	for (const r of chartRows.value) {
		const key = richKeyFor(r.sleutel);
		if (rich[key]) continue;
		const uri = tagIconDataUri(r.sleutel, color);
		if (uri) rich[key] = { height: 12, width: 12, backgroundColor: { image: uri } };
	}
	return rich;
});

const chartOption = computed(() => ({
	backgroundColor: "transparent",
	textStyle: { fontFamily: "inherit" },
	tooltip: { trigger: "item" },
	grid: { left: 90, right: 24, top: 8, bottom: 16 },
	xAxis: {
		type: "value",
		axisLabel: { color: isDark.value ? "#a89e8c" : "#6f6558" },
		splitLine: { lineStyle: { color: isDark.value ? "#453f36" : "#ddd5c4" } },
	},
	yAxis: {
		type: "category",
		data: chartRows.value.map((r) => r.sleutel),
		axisLabel: {
			color: isDark.value ? "#f2ede3" : "#221f1b",
			formatter: (sleutel: string) => (tagIconPath(sleutel) ? `{${richKeyFor(sleutel)}|}  ${sleutel}` : sleutel),
			rich: yAxisRich.value,
		},
	},
	series: [
		{
			type: "bar",
			data: chartRows.value.map((r) => ({
				value: r.count,
				itemStyle: { color: PERSPECTIEF_KLEUR.get(r.perspectief) ?? ONBEKENDE_KLEUR },
			})),
			barMaxWidth: BAR_MAX_WIDTH,
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
					Hoeveel argumenten van {{ mode === "persoon" ? "deze spreker" : "deze partij" }} elke tag toegekend
					kregen. Drie labelgroepen die automatisch uit metadata volgen (bv. wie iemand is, in welke setting
					het gezegd werd) staan er niet bij -- die zeggen niets over de eigen argumentatiestijl, alleen
					door het taalmodel zelf herkende tags tellen mee.
					<template v-if="mode === 'persoon'">
						Tags met minder dan {{ PERSON_TAG_THRESHOLD }} toekenningen zijn samengevoegd tot "overig" -- bij deze
						volumes zegt een enkele toekenning weinig.
					</template>
				</p>
				<ul v-if="medianRows.length || partyMedianRows.length" class="chart-legend">
					<li v-if="medianRows.length">
						<svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
							<line x1="6" y1="1" x2="6" y2="11" stroke="currentColor" stroke-width="2" />
						</svg>
						mediaan over {{ mode === "persoon" ? "alle sprekers" : "alle partijen" }}
					</li>
					<li v-if="partyMedianRows.length">
						<img :src="partyIconUri!" width="12" height="12" alt="" />
						mediaan over fractiegenoten
					</li>
				</ul>
				<p v-if="!tagRows.length" class="panel-note">Geen getagde argumenten.</p>
				<VChart v-else class="tag-usage-chart" :option="chartOption" :style="{ height: chartHeight }" autoresize />
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
