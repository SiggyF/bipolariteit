<script setup lang="ts">
import { computed } from "vue";
import { stanceLabel, stanceDescription, type Stance } from "../lib/types";
import { standpuntModifier } from "../lib/standpunt";

// Glyph + woord voor pro/contra/onduidelijk (issue #220, Vloei): de enige
// toegestane manier om een standpunt te tonen. Vervangt .stance-dot en
// .stance-badge, die alleen met kleur onderscheidden -- zie
// docs/design/vloei/README.md. `groot` is voor kolomkoppen/samenvattingen
// (.vl-standpunt.is-groot in main.css).
const props = withDefaults(defineProps<{ stance: Stance; groot?: boolean }>(), { groot: false });

const modifier = computed(() => standpuntModifier(props.stance));
</script>

<template>
	<span class="vl-standpunt" :class="[`is-${modifier}`, { 'is-groot': groot }]" :title="stanceDescription(stance)">
		<svg viewBox="0 0 32 20" aria-hidden="true">
			<ellipse class="l" cx="11" cy="10" rx="9" ry="5.5" transform="rotate(-15 11 10)" />
			<ellipse class="r" cx="21" cy="10" rx="9" ry="5.5" transform="rotate(15 21 10)" />
			<circle cx="16" cy="10" r="2.2" />
		</svg>
		{{ stanceLabel(stance) }}
	</span>
</template>
