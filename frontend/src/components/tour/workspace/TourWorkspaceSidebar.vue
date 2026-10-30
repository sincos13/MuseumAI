<script setup>
import { useTour } from '../../../composables/useTour.js'
import { useTourWorkbench } from '../../../composables/useTourWorkbench.js'
import { getHallDisplayName } from '../../../composables/useHallDirectory.js'
import TourIcon from '../TourIcon.vue'
const { currentHall, currentExhibit, personaLabel, leaveHall, loading } = useTour()
const { activeTab } = useTourWorkbench()
defineEmits(['switch-tab'])
</script>
<template>
  <aside class="tour-workspace-sidebar" data-testid="tour-workspace-sidebar">
    <div class="sidebar-roof" aria-hidden="true" />
    <div class="sidebar-landscape" aria-hidden="true" />
    <nav class="sidebar-section sidebar-navigation" aria-label="导览导航">
      <button v-for="tab in [
        { key: 'session', label: '导览会话', icon: 'compass' },
        { key: 'exhibit', label: '展品速览', icon: 'picture' },
        { key: 'settings', label: '导览设置', icon: 'settings' },
      ]" :key="tab.key" type="button" class="sidebar-tab-btn"
        :class="{ active: activeTab === tab.key }" :aria-current="activeTab === tab.key ? 'page' : undefined"
        @click="$emit('switch-tab', tab.key)">
        <TourIcon :name="tab.icon" /><span>{{ tab.label }}</span>
      </button>
    </nav>
    <div class="sidebar-section sidebar-current">
      <h4 class="sidebar-heading">当前信息</h4>
      <dl class="sidebar-info">
        <div class="info-item"><dt>展厅</dt><dd>{{ currentHall ? getHallDisplayName(currentHall) : '-' }}</dd></div>
        <div class="info-item"><dt>展品</dt><dd>{{ currentExhibit?.name || '-' }}</dd></div>
        <div class="info-item"><dt>人设</dt><dd>{{ personaLabel || '-' }}</dd></div>
      </dl>
      <button v-if="currentHall" class="leave-hall-btn" type="button" :disabled="loading?.chat || loading?.session" @click="leaveHall">
        <TourIcon name="exit" /> 离开展厅 <TourIcon name="exit" />
      </button>
    </div>
  </aside>
</template>
<style scoped>
.tour-workspace-sidebar {
  position: relative; isolation: isolate; overflow-y: auto;
  width: calc(368 * var(--tour-u, 1px)); min-width: calc(368 * var(--tour-u, 1px));
  background: #e5ddd0; color: #6b503a; padding: calc(144 * var(--tour-u, 1px)) 0 calc(300 * var(--tour-u, 1px));
  display: flex; flex-direction: column; flex-shrink: 0;
}
.sidebar-roof { position: absolute; z-index: -1; top: 0; left: 0; right: 0; height: calc(144 * var(--tour-u, 1px)); background: url('/tour/sidebar-roof.png') center / 100% 100% no-repeat; }
.sidebar-landscape { position: absolute; z-index: -1; bottom: 0; left: 0; right: 0; height: calc(354 * var(--tour-u, 1px)); background: url('/tour/sidebar-landscape.png') center bottom / 100% 100% no-repeat; mask-image: linear-gradient(transparent, #000 12%); }
.sidebar-section { position: relative; display: flex; flex-direction: column; }
.sidebar-navigation { gap: calc(2 * var(--tour-u, 1px)); padding-right: calc(24 * var(--tour-u, 1px)); }
.sidebar-tab-btn {
  display: flex; align-items: center; gap: calc(24 * var(--tour-u, 1px)); height: calc(72 * var(--tour-u, 1px)); padding: 0 calc(32 * var(--tour-u, 1px));
  border: 0; border-radius: 0 calc(7 * var(--tour-u, 1px)) calc(7 * var(--tour-u, 1px)) 0;
  background: transparent; color: #74563e; font: inherit; font-size: calc(26 * var(--tour-u, 1px)); text-align: left; cursor: pointer;
}
.sidebar-tab-btn .tour-icon { font-size: calc(30 * var(--tour-u, 1px)); color: #9c7d50; }
.sidebar-tab-btn.active { color: #f8f1e5; background: linear-gradient(105deg, #785540, #5e3e2c); }
.sidebar-tab-btn.active .tour-icon { color: #f5eddd; }
.sidebar-tab-btn:hover:not(.active) { background: #d6c5af4d; }
.sidebar-current { margin: calc(14 * var(--tour-u, 1px)) calc(42 * var(--tour-u, 1px)) 0 calc(29 * var(--tour-u, 1px)); padding-top: calc(27 * var(--tour-u, 1px)); border-top: 1px solid #dcd1bf; }
.sidebar-heading { font-size: calc(18 * var(--tour-u, 1px)); font-weight: 600; color: #9a8065; margin: 0 0 calc(15 * var(--tour-u, 1px)); }
.sidebar-info { margin: 0; display: flex; flex-direction: column; gap: calc(16 * var(--tour-u, 1px)); }
.info-item { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; font-size: calc(21 * var(--tour-u, 1px)); line-height: 1.4; }
.info-item dt { color: #9b8166; flex-shrink: 0; }
.info-item dd { margin: 0; text-align: right; color: #302a21; font-weight: 500; overflow-wrap: anywhere; }
.leave-hall-btn { margin-top: calc(36 * var(--tour-u, 1px)); height: calc(60 * var(--tour-u, 1px)); display: flex; align-items: center; justify-content: center; gap: calc(10 * var(--tour-u, 1px)); flex-shrink: 0; border: 1px solid #cbb599; border-radius: 999px; background: #f2ede43b; color: #8c6b47; font: inherit; font-size: calc(21 * var(--tour-u, 1px)); cursor: pointer; }
.leave-hall-btn .tour-icon { color: #aa8b5c; }
.leave-hall-btn:hover { background: #f2eade; }
.leave-hall-btn:disabled { opacity: .5; cursor: wait; }
</style>
