<script setup>
import { computed, ref } from 'vue'
import { useTour } from '../../composables/useTour.js'
import { formatMuseumText, useMuseumProfile } from '../../composables/useMuseumProfile.js'
const { museum, personas, business } = useMuseumProfile()
const { createTourSession, tourStep, error, loading } = useTour()
const step = ref(0)
const answers = ref({ focus: null, rhythm: null, interest: null })
const persona = ref('A')
const skipped = ref(false)
const questions = computed(() => {
  const q = business.value?.questionnaire || {}
  const options = items => (items || []).map(x => ({ value: x.code, label: x.label, desc: x.description }))
  return [
    { key: 'focus', title: formatMuseumText(q.focus_title, museum.value.name), options: options(q.focus_options) },
    { key: 'rhythm', title: '今天想用多少时间探索？', options: [
      { value: 'quick', label: '30 分钟 · 精选速览', desc: '先理解重点展厅和代表展品' },
      { value: 'dialogue', label: '60 分钟 · 边看边聊', desc: '留出观察与提问的时间' },
      { value: 'notebook', label: '90 分钟 · 深入记录', desc: '连接多个展厅，整理观察笔记' },
      { value: 'research', label: '120 分钟 · 专题探索', desc: '比较展品，追问材料和解释边界' },
    ] },
    { key: 'interest', title: formatMuseumText(q.assumption_title, museum.value.name), options: options(q.assumption_options) },
  ]
})
const selectedPersona = computed(() => personas.value.find(p => p.code === persona.value))
function select(value) {
  answers.value[questions.value[step.value].key] = value
  skipped.value = false
  if (step.value === 2) persona.value = business.value?.visitor_experience?.focus_to_persona?.[answers.value.focus] || ({ A: 'B', B: 'A', C: 'C', D: 'D' })[answers.value.focus]
  step.value++
}
function skip() {
  skipped.value = true
  answers.value = { focus: 'B', rhythm: 'dialogue', interest: 'A' }
  persona.value = 'A'
  step.value = 3
}
async function confirm() {
  const session = await createTourSession(answers.value.focus, persona.value, answers.value.interest,
    { rhythm_id: answers.value.rhythm, skipped: skipped.value })
  if (session) tourStep.value = 'opening'
}
</script>
<template>
  <section class="quiz">
    <div class="eyebrow">{{ museum.short_name || museum.name }} · 你的专属导览</div>
    <p v-if="business?.visitor_experience?.disclosure" class="disclosure">{{ business.visitor_experience.disclosure }}</p>
    <template v-if="step < 3">
      <p class="step">参观偏好 {{ step + 1 }} / 3</p>
      <h1>{{ questions[step].title }}</h1>
      <div class="choices">
        <button v-for="option in questions[step].options" :key="option.value" class="choice"
          :aria-pressed="answers[questions[step].key] === option.value" @click="select(option.value)">
          <strong>{{ option.label }}</strong><span>{{ option.desc }}</span><b aria-hidden="true">→</b>
        </button>
      </div>
      <div class="actions"><el-button v-if="step" @click="step--">上一步</el-button><el-button text @click="skip">跳过，使用默认导览</el-button></div>
    </template>
    <template v-else>
      <p class="step">确认 AI 导览身份</p>
      <h1>让 {{ selectedPersona?.name }} 陪你看展</h1>
      <p>{{ skipped ? '你跳过了问卷，以下使用 60 分钟默认方案，可更换身份或返回填写。' : '根据你的参观目的推荐，也可以选择更适合你的讲解方式。' }}</p>
      <div class="personas">
        <button v-for="item in personas" :key="item.code" class="choice" :aria-pressed="persona === item.code" @click="persona = item.code">
          <strong>{{ item.icon }} {{ item.name }}</strong><span>{{ item.description }}</span>
        </button>
      </div>
      <blockquote>{{ selectedPersona?.opening_text }}</blockquote>
      <div class="actions"><el-button :disabled="loading.session" @click="step = 0">修改问卷</el-button><el-button type="primary" :loading="loading.session" @click="confirm">确认身份，查看个性化路线</el-button></div>
    </template>
    <el-alert v-if="error" :title="error" type="error" :closable="false" class="error" />
  </section>
</template>
<style scoped>
.quiz{max-width:800px;margin:auto;padding:48px 24px 64px;color:var(--color-text-primary)}
.eyebrow,.step{color:var(--color-accent);font-weight:600;letter-spacing:.06em}.step{margin:28px 0 12px}
h1{font-size:clamp(24px,3vw,32px);line-height:1.5;margin:12px 0 24px}
.disclosure{font-size:12px;color:var(--color-text-muted);line-height:1.7}.choices{display:grid;gap:14px}
.choice{position:relative;display:flex;flex-direction:column;text-align:left;gap:8px;padding:22px 42px 22px 24px;border:1px solid var(--color-border);border-radius:16px;background:var(--color-bg-elevated);color:inherit;cursor:pointer;font:inherit}
.choice:hover,.choice[aria-pressed=true]{border-color:var(--color-accent);background:var(--color-accent-muted)}
.choice span{font-size:14px;color:var(--color-text-muted);line-height:1.6}.choice b{position:absolute;right:20px;top:25px}
.personas{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:24px}.actions{display:flex;gap:12px;flex-wrap:wrap;margin-top:28px}
blockquote{margin:24px 0;padding:20px;border-left:3px solid var(--color-accent);line-height:1.9;background:var(--color-bg-elevated)}
.error{margin-top:18px}@media(max-width:560px){.personas{grid-template-columns:1fr}.quiz{padding:24px 18px}}
</style>
