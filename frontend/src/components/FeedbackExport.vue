<script setup lang="ts">
import { ref, onMounted } from "vue";
import { feedbackCount, exportFeedback } from "../lib/feedback";

const count = ref(0);
onMounted(() => {
	count.value = feedbackCount();
});
</script>

<template>
	<div class="feedback-export">
		<button type="button" @click="exportFeedback" :disabled="!count">
			Feedback exporteren ({{ count }})
		</button>
	</div>
</template>
