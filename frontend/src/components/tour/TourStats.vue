<script setup>
import { getHallDisplayName } from '../../composables/useHallDirectory.js'
defineProps({ report: Object, persona: String })

</script>

<template>
  <div class="tour-stats">
    <div class="stat-item">
      <p class="stat-text">本次会话历时 {{ Number(report?.total_duration_minutes || 0).toFixed(1) }} 分钟。</p>
    </div>
    <div v-if="report?.most_viewed_exhibit_id" class="stat-item">
      <p class="stat-text">你关注最多的展品：{{ report.most_viewed_exhibit_name || report.most_viewed_exhibit_id }}。</p>
    </div>
    <div v-if="report?.longest_hall" class="stat-item">
      <p class="stat-text">你在 {{ report.hall_names?.[report.longest_hall] || getHallDisplayName(report.longest_hall) }} 的页面停留了 {{ ((report.longest_hall_duration || 0) / 60).toFixed(1) }} 分钟。</p>
    </div>
    <div v-if="report?.halls_visited?.length" class="stat-item" data-testid="visited-halls">
      <p class="stat-text">已探索 {{ report.halls_visited.length }} 个展厅</p>
      <ul>
        <li v-for="hall in report.halls_visited" :key="hall">
          {{ report.hall_names?.[hall] || getHallDisplayName(hall) }}
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.tour-stats { margin-bottom: 32px; }
.stat-item { padding: 16px; background: var(--color-bg-subtle); border-radius: 8px; margin-bottom: 12px; }
.stat-text { font-size: 15px; line-height: 1.8; color: var(--color-text-primary); }
</style>
