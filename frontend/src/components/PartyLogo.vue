<script setup lang="ts">
import { computed } from "vue";
import { partyInitial, partyLogoSimple } from "../lib/parties";

// Vierkante, vereenvoudigde iconenset i.p.v. de officiële wordmarks
// (partyLogo()): die lopen sterk uiteen in verhouding (PVV is 13:1) en
// worden bij dit vaste 18x18-formaat onleesbaar klein/leeg -- de
// vereenvoudigde set is juist voor puntsymbool-gebruik op klein formaat
// gemaakt (zie parties.ts).
const props = defineProps<{ party: string }>();

const logo = computed(() => partyLogoSimple(props.party));
const initial = computed(() => partyInitial(props.party));
</script>

<template>
	<img v-if="logo" :src="logo" :alt="party" class="party-logo" />
	<span v-else class="party-logo party-logo-placeholder" :title="`${party} (geen officieel logo beschikbaar)`">{{ initial }}</span>
</template>
