<script setup>
import { computed } from 'vue'
const props = defineProps({ text: { type: String, default: '' } })
// Render emphasis as Vue text nodes. Model output is never interpreted as HTML.
const parts = computed(() => props.text.split(/(\*\*[^*]+\*\*)/g).map(text => ({
  bold: text.startsWith('**') && text.endsWith('**') && text.length > 4,
  text,
})))
</script>
<template>
  <span class="answer-text"><template v-for="(part, i) in parts" :key="i"><strong v-if="part.bold">{{ part.text.slice(2, -2) }}</strong><template v-else>{{ part.text }}</template></template></span>
</template>
<style scoped>
.answer-text{white-space:pre-wrap;overflow-wrap:anywhere}
</style>
