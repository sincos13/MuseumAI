<script setup>
import { computed, onUnmounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../../api/index.js'
import { useMuseumProfile } from '../../composables/useMuseumProfile.js'
const { personas, museum, business, loadProfile, loading } = useMuseumProfile()
const previewLoading = ref(false)
const previewAudioUrl = ref('')
const selectedPersona = ref('A')
const voiceSample = computed(() => `欢迎来到${museum.value.name}。我们从眼前这件展品开始，结合馆方资料探索历史。`)
const rows = computed(() => personas.value.map((persona) => ({
  ...persona, voice: business.value?.tts.personas?.[persona.code]?.voice || business.value?.tts.default_voice || '',
})))
onUnmounted(() => { if (previewAudioUrl.value) URL.revokeObjectURL(previewAudioUrl.value) })
async function previewVoice() {
  previewLoading.value = true
  try {
    const result = await api.tts.synthesize(voiceSample.value, null, null, selectedPersona.value)
    const audio = result.data?.audio
    if (!result.ok || !audio) throw new Error(typeof result.data?.detail === 'string' ? result.data.detail : '试听生成失败，请检查语音服务配置。')
    const bytes = Uint8Array.from(atob(audio), (char) => char.charCodeAt(0))
    if (previewAudioUrl.value) URL.revokeObjectURL(previewAudioUrl.value)
    previewAudioUrl.value = URL.createObjectURL(new Blob([bytes], { type: result.data?.mime_type || 'audio/wav' }))
  } catch (cause) { ElMessage.error(cause.message || '试听失败，请稍后重试。') }
  finally { previewLoading.value = false }
}
</script>
<template>
  <div class="tts-persona-manager">
    <header class="admin-hero"><div><span class="kicker">馆方语音配置</span><h2>语音角色与试听</h2><p>声线与播报风格统一在馆方配置中维护。新导览使用已发布版本，已有导览保留创建时的语音配置。</p><RouterLink to="/admin/museum">前往馆方配置修改语音</RouterLink></div><el-button :loading="loading" @click="loadProfile">刷新配置</el-button></header>
    <section class="voice-contract"><h3>默认声线：{{ business?.tts.default_voice || '未配置' }}</h3><blockquote>{{ voiceSample }}</blockquote><div class="preview-row"><el-select v-model="selectedPersona"><el-option v-for="persona in personas" :key="persona.code" :value="persona.code" :label="persona.name" /></el-select><el-button type="primary" :loading="previewLoading" @click="previewVoice">试听该身份</el-button><audio v-if="previewAudioUrl" :src="previewAudioUrl" controls autoplay /></div></section>
    <el-table :data="rows" class="persona-table"><el-table-column prop="name" label="导览身份" /><el-table-column prop="voice" label="配置声线" /><el-table-column prop="description" label="导览角度" min-width="260" /></el-table>
  </div>
</template>

<style scoped>
.tts-persona-manager {
  min-height: 100%;
  padding: 28px 34px 56px;
  background: linear-gradient(180deg, #fffdf9 0%, #f8f2ea 100%);
}

.admin-hero,
.voice-contract,
.persona-table {
  border-radius: 16px;
  box-shadow: 0 14px 36px rgba(77, 49, 31, 0.07);
}

.admin-hero {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 18px;
  padding: 24px;
  border: 1px solid rgba(126, 91, 65, 0.16);
  background: #fffaf3;
}

.kicker {
  color: #c57548;
  font-size: 13px;
  font-weight: 700;
}

.admin-hero h2 {
  margin: 8px 0;
  color: #2f2118;
  font-size: 28px;
}

.admin-hero p {
  max-width: 760px;
  margin: 0;
  color: #7e6a59;
  line-height: 1.7;
}

.hero-actions {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.voice-contract {
  margin-bottom: 18px;
  padding: 22px;
  border: 1px solid rgba(126, 91, 65, 0.16);
  background: rgba(255, 252, 247, 0.92);
}

.voice-card {
  display: grid;
  grid-template-columns: 76px 1fr;
  gap: 18px;
}

.voice-icon {
  display: grid;
  place-items: center;
  width: 76px;
  height: 76px;
  border-radius: 18px;
  background: #f2e4d2;
  font-size: 34px;
}

.voice-card h3 {
  margin: 6px 0;
  color: #2f2118;
  font-size: 23px;
}

.voice-card p {
  margin: 0;
  color: #756252;
  line-height: 1.7;
}

blockquote {
  margin: 14px 0 0;
  padding: 12px 14px;
  border-left: 3px solid #c57548;
  background: #f7efe6;
  color: #3b2b20;
}

.preview-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 14px;
}

.preview-row audio {
  width: 360px;
  max-width: 100%;
}

.persona-table {
  overflow: hidden;
}

.persona-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.persona-cell span {
  font-size: 28px;
}

.persona-cell strong,
.persona-cell em {
  display: block;
}

.persona-cell strong {
  color: #2f2118;
}

.persona-cell em {
  margin-top: 2px;
  color: #987d67;
  font-size: 13px;
  font-style: normal;
}
</style>
