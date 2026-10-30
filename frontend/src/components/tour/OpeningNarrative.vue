<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useTour } from '../../composables/useTour.js'
import { useTourWorkbench } from '../../composables/useTourWorkbench.js'
import { useTTSPlayer } from '../../composables/useTTSPlayer.js'
import { api } from '../../api/index.js'

const { personaByCode, tourSession, sessionToken, tourStep, fetchHalls } = useTour()
const { ttsPreferences } = useTourWorkbench()
const { feedChunk, stop: stopTTS } = useTTSPlayer()

const displayedText = ref('')
const isTyping = ref(true)
const ttsPlaying = ref(false)

const selectedPersona = computed(() => personaByCode.value[tourSession.value?.persona || 'A'])
const fullText = computed(() => selectedPersona.value?.opening_text || '')
const personaBadge = computed(() => `${selectedPersona.value?.icon || ''} ${selectedPersona.value?.name || ''}`)
let timer
onUnmounted(() => { window.clearInterval(timer); stopTTS() })

onMounted(() => {
  let index = 0
  timer = window.setInterval(() => {
    if (index < fullText.value.length) {
      displayedText.value += fullText.value[index]
      index++
    } else {
      isTyping.value = false
      window.clearInterval(timer)
      // Auto-play TTS when typewriter finishes
      if (ttsPreferences.value.enabled && ttsPreferences.value.autoPlay) {
        playOpeningTTS()
      }
    }
  }, 30)
})

async function playOpeningTTS() {
  if (ttsPlaying.value) {
    stopTTS()
    ttsPlaying.value = false
    return
  }

  ttsPlaying.value = true
  try {
    const persona = tourSession.value?.persona || 'A'
    const result = await api.tts.synthesize(fullText.value, null, null, persona, tourSession.value?.id, sessionToken.value)
    if (result.ok && result.data?.audio) {
      stopTTS()
      feedChunk(result.data.audio)
      ttsPlaying.value = false
    } else {
      ttsPlaying.value = false
    }
  } catch (err) {
    console.error('Opening TTS error:', err)
    ttsPlaying.value = false
  }
}

async function startExplore() {
  await fetchHalls()
  tourStep.value = 'hall-select'
}
</script>

<template>
  <div class="opening">
    <div class="opening-inner">
      <div class="persona-badge">
        {{ personaBadge }}
      </div>
      <button
        v-if="!isTyping && ttsPreferences.enabled"
        class="tts-play-btn"
        :class="{ playing: ttsPlaying }"
        title="语音播放"
        @click="playOpeningTTS"
      >
        <svg v-if="!ttsPlaying" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/></svg>
        <svg v-else xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>
        <span>{{ ttsPlaying ? '暂停' : '播放' }}</span>
      </button>
      <div class="narrative-text">
        {{ displayedText }}
        <span v-if="isTyping" class="cursor">|</span>
      </div>
      <el-button
        v-if="!isTyping"
        type="primary"
        size="large"
        class="start-btn"
        @click="startExplore"
      >
        开始探索 →
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.opening {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100%;
  padding: 40px 20px;
}

.opening-inner {
  max-width: 640px;
  width: 100%;
  text-align: center;
}

.persona-badge {
  display: inline-block;
  padding: 8px 24px;
  background: var(--color-accent-muted);
  border: 1px solid var(--color-accent);
  border-radius: 20px;
  color: var(--color-accent);
  font-size: 16px;
  margin-bottom: 32px;
}

.narrative-text {
  font-size: 17px;
  line-height: 2;
  text-align: left;
  color: var(--color-text-primary);
  white-space: pre-wrap;
}

.cursor {
  animation: blink 0.8s infinite;
  color: var(--color-accent);
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.start-btn {
  margin-top: 40px;
  padding: 14px 48px;
  font-size: 18px;
  border-radius: 24px;
  background: var(--color-accent);
  border-color: var(--color-accent);
}

.start-btn:hover {
  background: var(--color-accent-soft);
}

.tts-play-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 20px;
  margin-bottom: 24px;
  background: var(--color-accent-muted);
  border: 1px solid var(--color-accent);
  border-radius: 20px;
  color: var(--color-accent);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.tts-play-btn:hover {
  background: var(--color-accent-muted);
  border-color: var(--color-accent);
}

.tts-play-btn.playing {
  background: var(--color-accent-muted);
  border-color: var(--color-accent);
}
</style>
