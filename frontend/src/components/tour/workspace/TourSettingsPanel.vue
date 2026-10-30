<script setup>
import { computed } from 'vue'
import { useTour } from '../../../composables/useTour.js'
import { useTourWorkbench } from '../../../composables/useTourWorkbench.js'

const { tourBusiness, tourSession, finishTour, loading } = useTour()
const configuredVoice = computed(() => tourBusiness?.value?.tts?.personas?.[tourSession?.value?.persona || 'default']?.voice || tourBusiness?.value?.tts?.default_voice || '馆方默认声线')

const { uiPreferences, stylePreferences, ttsPreferences, resetPreferences, activeTab } = useTourWorkbench()

const fontScaleOptions = [
  { label: '小', value: 'sm' },
  { label: '中', value: 'md' },
  { label: '大', value: 'lg' },
]

const densityOptions = [
  { label: '紧凑', value: 'compact' },
  { label: '舒适', value: 'comfortable' },
]

const answerLengthOptions = [
  { label: '简短', value: 'brief' },
  { label: '适中', value: 'balanced' },
  { label: '详细', value: 'detailed' },
]

const depthOptions = [
  { label: '入门', value: 'introductory' },
  { label: '标准', value: 'standard' },
  { label: '深入', value: 'deep' },
]

const terminologyOptions = [
  { label: '通俗', value: 'plain' },
  { label: '专业', value: 'professional' },
  { label: '学术', value: 'academic' },
]
</script>

<template>
  <div class="tour-settings-panel">
    <div class="settings-section">
      <h4 class="settings-heading">界面偏好</h4>

      <div class="settings-row">
        <span class="settings-label">字体大小</span>
        <el-select v-model="uiPreferences.fontScale" size="small">
          <el-option v-for="opt in fontScaleOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
        </el-select>
      </div>

      <div class="settings-row">
        <span class="settings-label">消息密度</span>
        <el-select v-model="uiPreferences.messageDensity" size="small">
          <el-option v-for="opt in densityOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
        </el-select>
      </div>

      <div class="settings-row">
        <span class="settings-label">自动滚动</span>
        <el-switch v-model="uiPreferences.autoScroll" />
      </div>

      <div class="settings-row">
        <span class="settings-label">快捷提问</span>
        <el-switch v-model="uiPreferences.showQuickPrompts" />
      </div>

      <div class="settings-row">
        <span class="settings-label">草稿记忆</span>
        <el-switch v-model="uiPreferences.rememberDraft" />
      </div>
    </div>

    <div class="settings-section">
      <h4 class="settings-heading">风格偏好</h4>

      <div class="settings-row">
        <span class="settings-label">启用风格</span>
        <el-switch v-model="stylePreferences.enabled" />
      </div>

      <div class="settings-row">
        <span class="settings-label">回答长度</span>
        <el-select v-model="stylePreferences.answerLength" size="small" :disabled="!stylePreferences.enabled">
          <el-option v-for="opt in answerLengthOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
        </el-select>
      </div>

      <div class="settings-row">
        <span class="settings-label">讲解深浅</span>
        <el-select v-model="stylePreferences.depth" size="small" :disabled="!stylePreferences.enabled">
          <el-option v-for="opt in depthOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
        </el-select>
      </div>

      <div class="settings-row">
        <span class="settings-label">术语难度</span>
        <el-select v-model="stylePreferences.terminology" size="small" :disabled="!stylePreferences.enabled">
          <el-option v-for="opt in terminologyOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
        </el-select>
      </div>
    </div>

    <div class="settings-section tts-section">
      <h4 class="settings-heading">语音朗读</h4>
      <div class="settings-row">
        <span class="settings-label">启用语音朗读</span>
        <el-switch v-model="ttsPreferences.enabled" />
      </div>
      <div class="settings-row" v-if="ttsPreferences.enabled">
        <span class="settings-label">自动播放</span>
        <el-switch v-model="ttsPreferences.autoPlay" />
      </div>
      <div class="settings-row" v-if="ttsPreferences.enabled">
        <span class="settings-label">音色</span>
        <span>{{ configuredVoice }}</span>
      </div>
    </div>

    <div class="settings-section">
      <el-button data-testid="reset-prefs-btn" @click="resetPreferences">
        恢复默认设置
      </el-button>
    </div>
    <div class="settings-section">
      <h4 class="settings-heading">本次参观</h4>
      <div class="tour-actions">
        <el-button @click="activeTab = 'progress'">查看导览进度</el-button>
        <el-button :disabled="loading?.chat || loading?.session" @click="finishTour">结束参观</el-button>
      </div>
      <p class="guide-disclosure">{{ tourBusiness?.visitor_experience?.disclosure || '回答基于馆方资料，资料不足时应保留不确定性。' }}</p>
    </div>
  </div>
</template>

<style scoped>
.tour-actions { display: flex; flex-wrap: wrap; gap: 12px; }
.guide-disclosure { color: var(--color-text-muted); font-size: 13px; line-height: 1.8; }
.tour-settings-panel {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.settings-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.settings-heading {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  padding-bottom: 4px;
  border-bottom: 1px solid var(--color-border);
}

.settings-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
}

.settings-label {
  color: var(--color-text-secondary);
}
</style>
