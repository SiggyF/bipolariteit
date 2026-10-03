<script setup lang="ts">
import { computed } from "vue";
import { stanceLabel, stanceDescription, type Stance } from "../lib/types";
import { standpuntModifier } from "../lib/standpunt";

// Glyph voor pro/contra/onduidelijk (issue #220, Vloei): de enige toegestane
// manier om een standpunt te tonen. Vervangt .stance-dot en .stance-badge,
// die alleen met kleur onderscheidden -- zie docs/design/vloei/README.md. Het
// woord zelf staat er (via title + een visueel verborgen span) nog steeds
// bij voor screenreaders/tooltip, maar is zichtbaar niet meer nodig: de glyph
// codeert zelf al met vorm (linkerlob/rechterlob/open+stip), zie puntenlijst
// in het README onder "Kleurblindheid". `groot` is voor kolomkoppen/
// samenvattingen (.vl-standpunt.is-groot in main.css).
const props = withDefaults(defineProps<{ stance: Stance; groot?: boolean }>(), { groot: false });

const modifier = computed(() => standpuntModifier(props.stance));
</script>

<template>
	<!-- viewBox verticaal precies rond de inkt (ellipsbbox bij 15 graden rotatie
	     + halve strokewidth), niet de volle 0-20 van de ongeroteerde geometrie --
	     anders blijft er onder/boven de vorm lege ruimte in de svg-box staan en
	     lijnt geen enkele vertical-align de onderkant van de vorm uit met de
	     tekstbaseline (bv. naast een actornaam in ClaimsHighlights.vue). -->
	<span class="vl-standpunt" :class="[`is-${modifier}`, { 'is-groot': groot }]" :title="stanceDescription(stance)">
		<svg viewBox="0 3.3 32 13.4" aria-hidden="true">
			<ellipse class="l" cx="11" cy="10" rx="9" ry="5.5" transform="rotate(-15 11 10)" />
			<ellipse class="r" cx="21" cy="10" rx="9" ry="5.5" transform="rotate(15 21 10)" />
			<circle cx="16" cy="10" r="2.2" />
		</svg>
		<span class="visually-hidden">{{ stanceLabel(stance) }}</span>
	</span>
</template>
