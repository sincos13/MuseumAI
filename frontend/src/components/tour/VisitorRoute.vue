<script setup>
import { onMounted } from 'vue'
import { useTour } from '../../composables/useTour.js'
const { visitorRoute, loadRoute, personaLabel, tourSession, tourBusiness, selectHall, tourStep, loading, error, finishTour } = useTour()
async function enter(slug) { if (await selectHall(slug)) tourStep.value = 'tour' }
onMounted(loadRoute)
</script>
<template>
  <section class="route">
    <p class="kicker">{{ personaLabel }} · {{ tourSession?.questionnaire?.skipped ? '默认参观方案' : '个性化参观方案' }}</p>
    <h1>{{ visitorRoute?.theme || '正在准备路线…' }}</h1>
    <p>{{ visitorRoute?.summary }}</p>
    <p v-if="tourBusiness?.visitor_experience?.disclosure" class="muted">{{ tourBusiness.visitor_experience.disclosure }}</p>
    <el-alert v-if="error" :title="error" type="error" :closable="false"><el-button @click="loadRoute">重新加载</el-button></el-alert>
    <template v-if="visitorRoute">
      <div class="budget"><strong>{{ visitorRoute.planned_minutes }} 分钟</strong><span>{{ visitorRoute.interest_label }}</span><span>含开场、换厅、回顾与预留时间</span></div>
      <p class="muted">{{ visitorRoute.notice }}</p>
      <ol>
        <li v-for="(stop, i) in visitorRoute.steps" :key="stop.hall_slug">
          <span class="number">{{ i + 1 }}</span>
          <div class="stop"><h2>{{ stop.hall_name }} <small>{{ stop.minutes }} 分钟</small></h2>
            <p>{{ stop.task }}</p><p class="exhibits">{{ stop.exhibits.map(e => e.name).join(' · ') }}</p>
            <el-button type="primary" plain :disabled="loading.session" @click="enter(stop.hall_slug)">{{ i ? '进入这个展厅' : '按路线开始参观' }}</el-button>
          </div>
        </li>
      </ol>
      <div class="actions"><el-button @click="tourStep = 'hall-select'">自主选择展厅</el-button><el-button text :disabled="loading.session" @click="finishTour">结束并查看记录</el-button></div>
    </template>
  </section>
</template>
<style scoped>
.route{max-width:900px;margin:auto;padding:40px 24px;color:var(--color-text-primary)}.kicker{color:var(--color-accent);font-weight:600}h1{font-size:30px;line-height:1.5;margin:16px 0}p{line-height:1.8}.muted{color:var(--color-text-muted);font-size:13px}.budget{display:flex;gap:18px;flex-wrap:wrap;align-items:center;padding:20px 0}.budget strong{font-size:24px;color:var(--color-accent)}ol{list-style:none;padding:0;margin:24px 0}li{display:flex;gap:20px;margin-bottom:18px;padding:24px;border:1px solid var(--color-border);border-radius:18px;background:var(--color-bg-elevated)}.number{font-size:24px;color:var(--color-accent)}.stop{flex:1;min-width:0}h2{font-size:20px;margin:0}small{font-size:13px;font-weight:400;margin-left:12px;color:var(--color-text-muted)}.exhibits{font-size:14px;color:var(--color-text-muted)}.actions{display:flex;gap:12px;flex-wrap:wrap}
</style>
