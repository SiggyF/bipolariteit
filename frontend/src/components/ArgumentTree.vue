<template>
	<div class="argument-tree">
		<div class="argument-tree-charts">
			<div v-for="block in visibleStances" :key="block.stance" class="argument-tree-chart-wrap">
				<h3 class="argument-tree-chart-title">
					{{ stanceLabel(block.stance) }} <span class="argument-tree-count">({{ block.argument_count }})</span>
				</h3>
				<VChart
					class="argument-tree-chart"
					:option="chartOption(block)"
					:style="{ height: chartHeight(block) }"
					autoresize
					@click="onNodeClick"
				/>
			</div>
		</div>

		<!-- Altijd zichtbaar (sticky), ook zonder selectie: boom en kaart moeten
		     tegelijk in beeld blijven i.p.v. dat je naar een los blok eronder
		     moet scrollen zodra je iets aanklikt. -->
		<div class="argument-tree-detail">
			<template v-if="selectedArgument">
				<button type="button" class="argument-tree-detail-close" aria-label="Sluiten" @click="selectedArgumentId = null">
					×
				</button>
				<blockquote>&ldquo;{{ selectedArgument.quote_text }}&rdquo;</blockquote>
				<p class="argument-tree-detail-meta">
					— {{ selectedArgument.actor_name
					}}<template v-if="selectedArgument.actor_party"> ({{ selectedArgument.actor_party }})</template>
					· typologie: {{ selectedArgument.typology }}
				</p>
				<ul v-if="selectedArgument.tags.length" class="argument-tree-detail-tags">
					<li v-for="tag in selectedArgument.tags" :key="tag">{{ tag }}</li>
				</ul>
				<div
					v-if="selectedArgument.tweedekamer_activiteit_url || selectedArgument.speaker_video_url"
					class="argument-tree-detail-links"
				>
					<a
						v-if="selectedArgument.tweedekamer_activiteit_url"
						:href="selectedArgument.tweedekamer_activiteit_url"
						target="_blank"
						rel="noopener"
						title="Officiële tweedekamer.nl-pagina van dit debat (Verslag/Handelingen + video)"
						>bekijk in de Tweede Kamer</a
					>
					<a
						v-if="selectedArgument.speaker_video_url"
						:href="selectedArgument.speaker_video_url"
						target="_blank"
						rel="noopener"
						title="Springt naar het moment dat deze spreker begint in het debat"
						>video (dit moment)</a
					>
				</div>
				<div v-if="selectedOppositions.length" class="argument-tree-detail-oppositions">
					<p class="argument-tree-detail-oppositions-label">Weerlegd door:</p>
					<ul>
						<li v-for="opp in selectedOppositions" :key="opp.id">
							&ldquo;{{ truncate(opp.quote_text) }}&rdquo; — {{ opp.actor_name
							}}<template v-if="opp.actor_party"> ({{ opp.actor_party }})</template>
						</li>
					</ul>
				</div>
			</template>
			<p v-else class="argument-tree-detail-placeholder">Klik op een argument in de boom voor het volledige citaat.</p>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { SVGRenderer } from "echarts/renderers";
import { TreeChart } from "echarts/charts";
import { TooltipComponent } from "echarts/components";
import { useTheme } from "../lib/useTheme";

use([SVGRenderer, TreeChart, TooltipComponent]);

interface TreeArgument {
	id: number;
	quote_text: string;
	typology: string;
	actor_name: string;
	actor_party: string | null;
	tags: string[];
	tweedekamer_activiteit_url: string | null;
	speaker_video_url: string | null;
}

interface GroupMember {
	argument_id: number;
	gist: string;
}

type TreeNode =
	| { argument_id: number; gist: string; children?: TreeNode[] }
	| { label: string; arguments: GroupMember[]; children?: TreeNode[] };

interface StanceBlock {
	stance: "pro" | "contra" | "unclear";
	argument_count: number;
	nodes: TreeNode[];
}

interface Opposition {
	argument_a_id: number;
	argument_b_id: number;
	confidence: number | null;
}

interface ArgumentTreeData {
	slug: string;
	name: string;
	stances: StanceBlock[];
	arguments: Record<string, TreeArgument>;
	oppositions: Opposition[];
}

const props = defineProps<{ tree: ArgumentTreeData }>();

const STANCE_LABELS: Record<string, string> = { pro: "Pro", contra: "Contra", unclear: "Onduidelijk" };

// "Ink & Rust" -- mirrors --color-pro/--color-contra/--color-unclear in
// main.css (ECharts can't read CSS custom properties, so this stays a
// manual mirror, same pattern as StatsPanel.vue).
const COLORS = {
	light: { pro: "#1f6f66", contra: "#9c3b32", unclear: "#948a79" },
	dark: { pro: "#4fa89b", contra: "#cf6b5f", unclear: "#a89e8c" },
};
const GROUP_COLOR = { light: "#948a79", dark: "#a89e8c" };

const isDark = useTheme();
const colors = computed(() => (isDark.value ? COLORS.dark : COLORS.light));
const groupColor = computed(() => (isDark.value ? GROUP_COLOR.dark : GROUP_COLOR.light));

const visibleStances = computed(() => props.tree.stances.filter((block) => block.nodes.length > 0));

// Oppositions (direct_rebuttal) kunnen geen boom-edge zijn -- het zijn per
// definitie links tussen twee verschillende standpunt-bomen. In plaats van
// een losse graph-overlay te bouwen, tonen we ze als tekst in het
// detailpaneel van het argument dat weerlegd wordt.
const oppositionsByArgument = computed(() => {
	const map = new Map<number, number[]>();
	for (const opp of props.tree.oppositions ?? []) {
		if (!map.has(opp.argument_a_id)) map.set(opp.argument_a_id, []);
		if (!map.has(opp.argument_b_id)) map.set(opp.argument_b_id, []);
		map.get(opp.argument_a_id)!.push(opp.argument_b_id);
		map.get(opp.argument_b_id)!.push(opp.argument_a_id);
	}
	return map;
});

function stanceLabel(stance: string): string {
	return STANCE_LABELS[stance] ?? stance;
}

function truncate(text: string, maxLength = 60): string {
	return text.length <= maxLength ? text : `${text.slice(0, maxLength).trimEnd()}…`;
}

// Node-label is de door de LLM aangeleverde `gist` (max. 3-4 woorden, zie
// pipeline/prompts/argument_tree.md + _validate_gist in build_argument_tree.py)
// i.p.v. de volledige quote -- die was op deze schaal onleesbaar in de
// vorige, d2-gebaseerde weergave. De volledige tekst staat in het
// detailpaneel na een klik, en als tooltip on hover (zie `fullName`).
function argumentNode(argumentId: number, gist: string, children: TreeNode[], stanceColor: string): Record<string, unknown> {
	const arg = props.tree.arguments[String(argumentId)];
	return {
		name: gist,
		fullName: arg.quote_text,
		argumentId,
		itemStyle: { color: stanceColor },
		children: children.map((child) => toEchartsNode(child, stanceColor)),
	};
}

function toEchartsNode(node: TreeNode, stanceColor: string): Record<string, unknown> {
	if ("argument_id" in node) {
		return argumentNode(node.argument_id, node.gist, node.children ?? [], stanceColor);
	}
	return {
		name: `${truncate(node.label, 38)} (${node.arguments.length})`,
		fullName: node.label,
		itemStyle: { color: groupColor.value },
		children: [
			...node.arguments.map((member) => argumentNode(member.argument_id, member.gist, [], stanceColor)),
			...(node.children ?? []).map((child) => toEchartsNode(child, stanceColor)),
		],
	};
}

// Genoeg verticale ruimte per node zodat siblings (nu onder elkaar i.p.v.
// naast elkaar, zie orient: "LR" hieronder) niet overlappen. Schaalt met het
// aantal TOP-LEVEL knopen (wat je standaard ziet, initialTreeDepth: 1), niet
// met het totaal aantal argumenten -- dat laatste gaf bij bv. 25 argumenten
// in 5 groepen een veel te hoge, grotendeels lege box. Bij het uitklappen
// van een tak herschikt ECharts zelf binnen deze hoogte (desnoods dichter op
// elkaar); roam laat je dan in-/uitzoomen.
function chartHeight(block: StanceBlock): string {
	return `${Math.max(200, block.nodes.length * 46)}px`;
}

function chartOption(block: StanceBlock) {
	const stanceColor = colors.value[block.stance] ?? colors.value.unclear;
	return {
		tooltip: {
			trigger: "item",
			// Labels zijn afgekapt (zie truncate() in toEchartsNode/shortLabel)
			// zodat ze nooit buiten de plot kunnen vallen -- de tooltip toont de
			// volledige tekst on hover, zonder de layout te verstoren.
			formatter: (params: { data?: { fullName?: string; name?: string } }) =>
				(params.data?.fullName ?? params.data?.name ?? "").replace(/\n/g, "<br/>"),
		},
		series: [
			{
				type: "tree",
				data: [
					{
						name: stanceLabel(block.stance),
						itemStyle: { color: stanceColor },
						children: block.nodes.map((node) => toEchartsNode(node, stanceColor)),
					},
				],
				// Links-rechts i.p.v. boven-onder: bij tekstzware labels (citaten,
				// groep-namen) geeft dat elke laag zijn eigen kolom, en staan
				// broer/zus-nodes onder elkaar (verticale ruimte schaalt mee met het
				// aantal nodes) i.p.v. naast elkaar in een vaste breedte, waar
				// labels bij >5 siblings al over elkaar heen vielen.
				orient: "LR",
				layout: "orthogonal",
				top: "3%",
				bottom: "3%",
				// Vaste pixelmarges i.p.v. percentages: Pro/Contra staan side-by-side
				// (zie .argument-tree-chart-wrap), dus de containerbreedte -- en
				// daarmee een %-marge -- varieert nogal, terwijl de labelbreedte dat
				// niet doet (een gist is per definitie maar 3-4 woorden). Alleen
				// blad-labels (leaves.label.position "right") vallen binnen de
				// rechtermarge -- niet-blad-labels staan links van hun eigen node,
				// dus al binnen de plot-area.
				left: 70,
				right: 240,
				roam: true,
				initialTreeDepth: 1,
				expandAndCollapse: true,
				symbol: "circle",
				symbolSize: 9,
				label: { fontSize: 12, position: "left", verticalAlign: "middle", align: "right", lineHeight: 14 },
				leaves: { label: { position: "right", verticalAlign: "middle", align: "left" } },
				emphasis: { focus: "descendant" },
				animationDurationUpdate: 300,
			},
		],
	};
}

const selectedArgumentId = ref<number | null>(null);

const selectedArgument = computed(() =>
	selectedArgumentId.value === null ? null : (props.tree.arguments[String(selectedArgumentId.value)] ?? null)
);

const selectedOppositions = computed(() => {
	if (selectedArgumentId.value === null) return [];
	const ids = oppositionsByArgument.value.get(selectedArgumentId.value) ?? [];
	return ids.map((id) => props.tree.arguments[String(id)]).filter((arg): arg is TreeArgument => Boolean(arg));
});

function onNodeClick(params: { data?: { argumentId?: number } }) {
	if (typeof params?.data?.argumentId === "number") {
		selectedArgumentId.value = params.data.argumentId;
	}
}
</script>

<style scoped>
/* Twee kolommen: boom(en) links, detailkaart rechts, sticky -- zo blijven
   structuur en kaart altijd samen in beeld i.p.v. dat je naar een blok
   onderaan moet scrollen zodra je iets aanklikt. Op smalle schermen valt
   dit terug naar één kolom (kaart onder de boom, niet meer sticky). */
.argument-tree {
	display: grid;
	grid-template-columns: 1fr minmax(260px, 340px);
	gap: var(--space-3);
	align-items: start;
}

@media (max-width: 860px) {
	.argument-tree {
		grid-template-columns: 1fr;
	}
}

.argument-tree-charts {
	display: flex;
	flex-wrap: wrap;
	gap: var(--space-3);
}

.argument-tree-chart-wrap {
	flex: 1 1 320px;
	min-width: 0;
}

.argument-tree-chart-title {
	margin: 0 0 var(--space-1);
	font-size: var(--step-0);
}

.argument-tree-count {
	color: var(--color-muted);
	font-weight: normal;
}

.argument-tree-chart {
	width: 100%;
	height: 480px;
	border: 1px solid var(--color-border);
	background: var(--color-bg);
}

.argument-tree-detail {
	position: sticky;
	top: var(--space-3);
	padding: var(--space-3);
	background: var(--color-card-bg);
	border: 1px solid var(--color-border);
	border-left: 4px solid var(--color-accent);
}

@media (max-width: 860px) {
	.argument-tree-detail {
		position: static;
	}
}

.argument-tree-detail-placeholder {
	margin: 0;
	color: var(--color-muted);
	font-size: var(--step--1);
}

.argument-tree-detail blockquote {
	margin: 0 0 var(--space-1);
	font-size: var(--step-0);
}

.argument-tree-detail-meta {
	margin: 0 0 var(--space-1);
	color: var(--color-muted);
	font-size: var(--step--1);
}

.argument-tree-detail-tags {
	list-style: none;
	display: flex;
	flex-wrap: wrap;
	gap: var(--space-1);
	padding: 0;
	margin: 0 0 var(--space-1);
}

.argument-tree-detail-tags li {
	border: 1px solid var(--color-border);
	padding: 0 0.4em;
	font-size: var(--step--1);
}

.argument-tree-detail-links {
	display: flex;
	gap: 0.75rem;
	font-size: 0.8rem;
	margin: 0 0 var(--space-1);
}

.argument-tree-detail-links a {
	color: var(--color-accent);
}

.argument-tree-detail-oppositions {
	margin-top: var(--space-1);
	padding-top: var(--space-1);
	border-top: 1px dashed var(--color-border);
}

.argument-tree-detail-oppositions-label {
	margin: 0 0 var(--space-1);
	color: var(--color-contra);
	font-weight: bold;
	font-size: var(--step--1);
}

.argument-tree-detail-oppositions ul {
	margin: 0;
	padding-left: 1.2em;
	font-size: var(--step--1);
}

.argument-tree-detail-close {
	position: absolute;
	top: var(--space-1);
	right: var(--space-1);
	border: none;
	background: none;
	font-size: 1.4em;
	line-height: 1;
	cursor: pointer;
	color: var(--color-muted);
}
</style>
