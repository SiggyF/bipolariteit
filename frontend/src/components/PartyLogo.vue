<script setup lang="ts">
import { computed } from "vue";
import { partyInitial, partyLogo } from "../lib/parties";

const props = defineProps<{ party: string }>();

const logo = computed(() => partyLogo(props.party));
const initial = computed(() => partyInitial(props.party));
</script>

<template>
	<img v-if="logo" :src="logo" :alt="party" class="party-logo" />
	<span v-else class="party-logo party-logo-placeholder" :title="`${party} (geen officieel logo beschikbaar)`">{{ initial }}</span>
</template>
