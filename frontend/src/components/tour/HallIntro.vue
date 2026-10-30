<script setup>
import { computed, onMounted } from 'vue'
import { useTour } from '../../composables/useTour.js'

const props = defineProps({ hall: String, hallName: String })
const emit = defineEmits(['done'])

const { personaByCode, tourSession, sendTourMessage, streamingContent, chatMessages, loading } = useTour()

const selectedPersona = computed(() => personaByCode.value[tourSession.value?.persona || 'A'])

onMounted(async () => {
  const persona = selectedPersona.value
  await sendTourMessage(`请以${persona?.name || '导览员'}的身份介绍${props.hallName}。${persona?.description || ''} 请结合本展厅资料说明观察重点和可继续追问的问题，3句话以内。`)
})

function continueTour() { emit('done') }
</script>

<template>
  <div class="hall-intro">
    <h2 class="hall-title">{{ hallName }}</h2>
    <div class="intro-content">
      <template v-if="chatMessages.length > 0">
        <p v-for="msg in chatMessages.filter(m => m.role === 'assistant')" :key="msg.content" class="intro-text">{{ msg.content }}</p>
      </template>
      <p v-if="loading.chat" class="intro-text typing">{{ streamingContent }}<span class="cursor">|</span></p>
    </div>
    <el-button v-if="!loading.chat && chatMessages.length > 0" type="primary" @click="continueTour">开始参观 →</el-button>
  </div>
</template>

<style scoped>
.hall-intro { padding: 40px 24px; text-align: center; max-width: 640px; margin: 0 auto; }
.hall-title { font-size: 24px; color: var(--color-accent); margin-bottom: 24px; }
.intro-content { margin-bottom: 32px; }
.intro-text { font-size: 16px; line-height: 2; color: var(--color-text-primary); text-align: left; white-space: pre-wrap; }
.cursor { animation: blink 0.8s infinite; color: var(--color-accent); }
@keyframes blink { 0%,50%{opacity:1} 51%,100%{opacity:0} }
</style>
