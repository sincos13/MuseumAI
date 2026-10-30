<script setup>
import { computed } from 'vue'
import { useTour } from '../../../composables/useTour.js'
import { getHallDisplayName } from '../../../composables/useHallDirectory.js'
import { useTourWorkbench } from '../../../composables/useTourWorkbench.js'
const { currentHall, currentExhibit, tourBusiness } = useTour()
const { activeTab } = useTourWorkbench()
const hallName = computed(() => currentHall.value ? getHallDisplayName(currentHall.value) : '博物馆导览')
const title = computed(() => ({ exhibit: '展品速览', settings: '导览设置', progress: '展览信息' }[activeTab.value]
  || currentExhibit.value?.name || '展厅导览'))
const subtitle = computed(() => tourBusiness?.value?.visitor_experience?.hall_taglines?.[currentHall.value]
  || (/营建/.test(hallName.value) ? '一座城的营建，承载着千年的智慧与匠心。' : '循着文物的细节，走进历史深处的故事。'))
</script>
<template>
  <header class="tour-hero">
    <div class="hero-copy">
      <div class="hero-breadcrumb">导览助手 <span>/</span> {{ hallName }}</div>
      <h1>{{ title }}</h1>
      <p>{{ subtitle }}</p>
      <span class="hero-flourish" aria-hidden="true" />
    </div>
  </header>
</template>
<style scoped>
.tour-hero { position: relative; flex: 0 0 calc(282 * var(--tour-u, 1px)); min-height: calc(282 * var(--tour-u, 1px)); overflow: hidden; background: url('/tour/hall-panorama.png') center center / cover no-repeat; }
.tour-hero::before { content: ''; position: absolute; inset: 0; background: linear-gradient(90deg, #ece7df 0%, #ece7dff5 27%, #ece7dfb8 36%, #ece7df3b 48%, transparent 65%); }
.hero-copy { position: relative; padding: calc(45 * var(--tour-u, 1px)) calc(60 * var(--tour-u, 1px)); }
.hero-breadcrumb { color: #a18a71; font-size: calc(23 * var(--tour-u, 1px)); letter-spacing: .025em; }
.hero-breadcrumb span { margin: 0 calc(10 * var(--tour-u, 1px)); }
h1 { margin: calc(13 * var(--tour-u, 1px)) 0 calc(12 * var(--tour-u, 1px)); font-size: calc(48 * var(--tour-u, 1px)); line-height: 1.25; font-weight: 700; letter-spacing: .08em; color: #2b251f; }
p { margin: 0; font-size: calc(24 * var(--tour-u, 1px)); line-height: 1.6; color: #816c55; }
.hero-flourish { display: block; position: relative; margin-top: calc(25 * var(--tour-u, 1px)); width: calc(43 * var(--tour-u, 1px)); height: 1px; background: #ab8960; }
.hero-flourish::after { content: ''; position: absolute; left: 85%; top: 0; width: 90%; height: calc(7 * var(--tour-u, 1px)); border: solid #cbbb9e; border-width: 0 0 1px 1px; transform: skewX(-30deg); opacity: .55; }
@media (max-width: 767px) {
  .tour-hero { flex-basis: 170px; min-height: 170px; background-position: 65% center; }
  .hero-copy { padding: 22px; }
  .hero-breadcrumb { font-size: 14px; }
  h1 { font-size: 29px; max-width: 90%; }
  p { font-size: 14px; max-width: 80%; }
  .hero-flourish { margin-top: 16px; }
  .tour-hero::before { background: linear-gradient(90deg, #ece7dff5, #ece7dfd9 40%, #ece7df33); }
}
</style>
