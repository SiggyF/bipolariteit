<script setup lang="ts">
// Zoekveld met keuzelijst voor de contourkeuze (issue #261). Eigen component
// i.p.v. <input list="..."> + <datalist>: de ingebouwde suggestielijst filtert
// op wat al in het veld staat, dus met een gekozen naam (bv. "D66") toonde hij
// alleen die ene naam en kon je niet meer wisselen. Hier toont focus altijd de
// hele lijst en filtert pas wat je daarna typt.
import { computed, ref, useId } from "vue";

const props = defineProps<{
	label: string;
	placeholder: string;
	options: { name: string; n: number }[];
	modelValue: string | null;
	disabled?: boolean;
}>();
const emit = defineEmits<{
	(e: "update:modelValue", value: string | null): void;
	(e: "open"): void;
}>();

const id = useId();
const listId = `${id}-lijst`;
const open = ref(false);
const typing = ref(false);
const query = ref("");
const activeIndex = ref(0);

// Zonder diakrieten en hoofdletters vergelijken ("Jetten", "jétten").
function normalize(text: string): string {
	return text.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

const filtered = computed(() => {
	if (!typing.value || !query.value.trim()) return props.options;
	const needle = normalize(query.value.trim());
	return props.options.filter((o) => normalize(o.name).includes(needle));
});

const inputValue = computed(() => (typing.value ? query.value : (props.modelValue ?? "")));

function openList() {
	if (props.disabled) return;
	open.value = true;
	typing.value = false;
	const current = props.options.findIndex((o) => o.name === props.modelValue);
	activeIndex.value = Math.max(current, 0);
	emit("open");
}

function close() {
	open.value = false;
	typing.value = false;
}

function choose(name: string | null) {
	emit("update:modelValue", name);
	close();
}

function onInput(event: Event) {
	typing.value = true;
	query.value = (event.target as HTMLInputElement).value;
	open.value = true;
	activeIndex.value = 0;
}

function onKeydown(event: KeyboardEvent) {
	if (event.key === "ArrowDown") {
		event.preventDefault();
		if (!open.value) openList();
		else activeIndex.value = Math.min(activeIndex.value + 1, filtered.value.length - 1);
	} else if (event.key === "ArrowUp") {
		event.preventDefault();
		activeIndex.value = Math.max(activeIndex.value - 1, 0);
	} else if (event.key === "Enter") {
		event.preventDefault();
		const option = filtered.value[activeIndex.value];
		if (open.value && option) choose(option.name);
	} else if (event.key === "Escape") {
		close();
	}
}

// Het veld leegmaken en de focus verlaten wist de keuze; een half getypte,
// onbekende naam laat de huidige keuze staan.
function onBlur() {
	if (typing.value && !query.value.trim()) emit("update:modelValue", null);
	close();
}
</script>

<template>
	<div class="contour-combobox">
		<label :for="id" class="contour-label">{{ label }}</label>
		<div class="contour-combobox-wrap">
			<input
				:id="id"
				type="text"
				role="combobox"
				aria-autocomplete="list"
				:aria-expanded="open"
				:aria-controls="listId"
				:aria-activedescendant="open && filtered[activeIndex] ? `${id}-${activeIndex}` : undefined"
				:placeholder="placeholder"
				:disabled="disabled"
				:value="inputValue"
				autocomplete="off"
				spellcheck="false"
				@focus="openList"
				@click="openList"
				@input="onInput"
				@keydown="onKeydown"
				@blur="onBlur"
			/>
			<button v-if="modelValue" type="button" class="contour-clear" :aria-label="`${label} wissen`" @mousedown.prevent @click="choose(null)">
				&times;
			</button>
			<ul v-show="open" :id="listId" role="listbox" class="contour-options">
				<li v-if="!filtered.length" class="contour-empty">Geen resultaten</li>
				<li
					v-for="(option, index) in filtered"
					:id="`${id}-${index}`"
					:key="option.name"
					role="option"
					:aria-selected="option.name === modelValue"
					:class="{ active: index === activeIndex, selected: option.name === modelValue }"
					@mousedown.prevent
					@click="choose(option.name)"
					@mousemove="activeIndex = index"
				>
					<span>{{ option.name }}</span>
					<span class="contour-option-n">{{ option.n.toLocaleString("nl-NL") }}</span>
				</li>
			</ul>
		</div>
	</div>
</template>

<style scoped>
.contour-combobox {
	display: flex;
	flex-direction: column;
	gap: 0.2rem;
	min-width: 0;
	flex: 1 1 12rem;
	max-width: 18rem;
}
.contour-label {
	font-family: var(--font-kop);
	font-variation-settings: "wdth" 85;
	font-size: 0.7rem;
	font-weight: 600;
	letter-spacing: 0.04em;
	text-transform: uppercase;
	opacity: 0.7;
}
.contour-combobox-wrap {
	position: relative;
}
input {
	box-sizing: border-box;
	width: 100%;
	font: inherit;
	font-size: 0.85rem;
	padding: 0.3rem 1.8rem 0.3rem 0.5rem;
	color: inherit;
	background: transparent;
	border: 1px solid color-mix(in srgb, currentColor 25%, transparent);
	border-radius: 4px;
	min-width: 0;
}
input:focus-visible {
	outline: 2px solid color-mix(in srgb, currentColor 60%, transparent);
	outline-offset: 1px;
}
.contour-clear {
	position: absolute;
	top: 50%;
	right: 0.3rem;
	transform: translateY(-50%);
	font: inherit;
	font-size: 1.1rem;
	line-height: 1;
	padding: 0 0.3rem;
	color: inherit;
	background: transparent;
	border: 0;
	opacity: 0.6;
	cursor: pointer;
}
.contour-clear:hover {
	opacity: 1;
}
.contour-options {
	position: absolute;
	z-index: 20;
	top: calc(100% + 2px);
	left: 0;
	right: 0;
	max-height: 16rem;
	margin: 0;
	padding: 0.2rem;
	overflow-y: auto;
	list-style: none;
	background: var(--blad);
	border: 1px solid color-mix(in srgb, currentColor 25%, transparent);
	border-radius: 4px;
	box-shadow: 0 6px 18px rgba(0, 0, 0, 0.25);
}
.contour-options li {
	display: flex;
	justify-content: space-between;
	gap: 0.75rem;
	padding: 0.3rem 0.5rem;
	font-size: 0.85rem;
	border-radius: 3px;
	cursor: pointer;
}
.contour-options li.active {
	background: color-mix(in srgb, currentColor 12%, transparent);
}
.contour-options li.selected span:first-child {
	font-weight: 700;
}
.contour-option-n {
	opacity: 0.55;
	font-variant-numeric: tabular-nums;
}
.contour-empty {
	opacity: 0.6;
	cursor: default;
}
</style>
