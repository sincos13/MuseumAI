<script setup>
import { computed, ref } from 'vue'
import { api } from '../api/index.js'
import { onMounted } from 'vue'
import { useTour } from '../composables/useTour.js'
import OnboardingQuiz from '../components/tour/OnboardingQuiz.vue'
import VisitorRoute from '../components/tour/VisitorRoute.vue'
import HallSelect from '../components/tour/HallSelect.vue'
import TourWorkspace from '../components/tour/TourWorkspace.vue'
import TourReport from '../components/tour/TourReport.vue'

const { tourStep, restoreSession, setupBeforeUnload } = useTour()
const museumReady = ref(null)

const isImmersiveStep = computed(() =>
  ['onboarding', 'opening', 'hall-select', 'report'].includes(tourStep.value)
)

onMounted(async () => {
  const result = await api.museum.importStatus()
  museumReady.value = result.ok && result.data.status === 'ready'
  if (!museumReady.value) return
  setupBeforeUnload()
  const restored = await restoreSession()
  if (!restored) {
    tourStep.value = 'onboarding'
  }
})
</script>

<template>
  <div class="tour-container" :class="{ 'tour-container--immersive': isImmersiveStep }">
    <div v-if="museumReady === false" class="waiting">
      <h1>馆方资料正在准备中</h1><p>馆方管理员完成资料导入和索引后，即可开启游客导览。</p><a href="/admin/import">前往馆方资料导入</a>
    </div>
    <div v-else-if="museumReady === null" class="waiting">正在检查馆方资料…</div>
    <div v-else class="tour-content">
      <OnboardingQuiz v-if="tourStep === 'onboarding'" />
      <VisitorRoute v-else-if="tourStep === 'opening' || tourStep === 'route'" />
      <HallSelect v-else-if="tourStep === 'hall-select'" />
      <TourWorkspace v-else-if="tourStep === 'tour'" />
      <TourReport v-else-if="tourStep === 'report'" />
    </div>
  </div>
</template>

<style scoped>
.waiting{padding:48px 24px;text-align:center;line-height:2}
.tour-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--color-bg-base);
  color: var(--color-text-primary);
}

.tour-container--immersive {
  background: var(--color-bg-base);
  color: var(--color-text-primary);
}

.tour-content {
  flex: 1;
  overflow-y: auto;
}
</style>
