<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  Document,
  MapLocation,
  Monitor,
  Refresh,
  Search,
} from '@element-plus/icons-vue'
import { api } from '../../api/index.js'
import { useMuseumProfile } from '../../composables/useMuseumProfile.js'

import { normalizeHallRecords } from '../../utils/halls.js'

const { personas, business } = useMuseumProfile()

const router = useRouter()
const loading = ref(false)
const fetchErrors = ref([])

const halls = ref([])
const exhibits = ref([])
const prompts = ref([])
const ttsPersonas = ref([])
const healthStatus = ref('unknown')
const readyStatus = ref('unknown')

const expectedHalls = computed(() => normalizeHallRecords(halls.value, { includeInactive: true }))
const activeHalls = computed(() => expectedHalls.value.filter((hall) => hall.is_active))

const personaContract = computed(() => personas.value.map((persona) => ({
  code: persona.code,
  personaId: persona.personaId,
  label: persona.name,
  report: persona.reportTitle,
  route: persona.routeTitle,
})))

const expectedTtsKeys = ['a', 'b', 'c', 'd'].map((code) => `tour_tts_persona_${code}`)

const hasConfiguredVoice = computed(() => {
  if (!hasExactTtsPersonas.value) return false
  return Boolean(business.value?.tts.default_voice)
})

const hasExactTtsPersonas = computed(() => {
  const keys = ttsPersonas.value.map((item) => item.key).sort()
  return keys.length === expectedTtsKeys.length
    && expectedTtsKeys.every((key, index) => keys[index] === key)
})

const dashboardStats = computed(() => [
  {
    label: '后端服务',
    value: healthStatus.value === 'ok' ? '正常' : '待检查',
    desc: readyStatus.value === 'ok' ? 'health / ready 均可用' : 'ready 状态未确认',
    type: healthStatus.value === 'ok' ? 'success' : 'warning',
  },
  {
    label: '开放展厅',
    value: `${activeHalls.value.length}/${expectedHalls.value.length}`,
    desc: '按本馆数据库目录统计',
    type: activeHalls.value.length ? 'success' : 'warning',
  },
  {
    label: '展品数据',
    value: String(exhibits.value.length),
    desc: '影响展品浏览、搜展品和 OCR fallback',
    type: exhibits.value.length ? 'success' : 'warning',
  },
  {
    label: '提示词',
    value: String(prompts.value.length),
    desc: '覆盖 RAG、策展、报告与语音人设',
    type: prompts.value.length ? 'success' : 'warning',
  },
])

const flowRows = computed(() => [
  {
    name: '入口问卷与四身份',
    miniapp: 'onboarding -> persona-reveal -> route',
    backend: '/tour/sessions, persona A/B/C/D',
    control: '提示词管理、语音角色管理',
    status: hasExactTtsPersonas.value ? 'ok' : 'warn',
    note: hasExactTtsPersonas.value ? '四身份 TTS key 与小程序 A/B/C/D 完全一致' : 'TTS 身份必须只保留 tour_tts_persona_a/b/c/d',
    actions: [
      { label: '提示词', path: '/admin/prompts' },
      { label: '语音角色', path: '/admin/tts-personas' },
    ],
  },
  {
    name: 'AI 策展路线',
    miniapp: 'route 页先有可用路线，再接入 AI plan',
    backend: '/curator/plan-tour',
    control: '路线管理、提示词管理、LLM 调用追踪',
    status: healthStatus.value === 'ok' ? 'ok' : 'warn',
    note: '路线管理展示当前开放展厅顺序；AI plan 使用馆方可用展厅生成路线',
    actions: [
      { label: '路线管理', path: '/admin/tour-paths' },
      { label: '调用追踪', path: '/admin/llm-traces' },
    ],
  },
  {
    name: '展厅选择与到访统计',
    miniapp: 'hall 选择、有效互动事件、report halls_visited',
    backend: '/tour/halls, /tour/sessions/:id/events, /report',
    control: '展厅设置',
    status: activeHalls.value.length ? 'ok' : 'warn',
    note: activeHalls.value.length ? '目录来自馆方数据；hall_enter 不单独计入到访统计' : '当前没有开放展厅，请先维护目录',
    actions: [{ label: '展厅设置', path: '/admin/halls' }],
  },
  {
    name: '展品搜索与拍照识别',
    miniapp: 'exhibit-scan 文字搜索/OCR 匹配 -> exhibit-detail',
    backend: '/exhibits, /exhibits/:id',
    control: '展品管理、知识库管理',
    status: exhibits.value.length ? 'ok' : 'warn',
    note: exhibits.value.length ? '展品 API 有数据可供搜索和 OCR 匹配' : '当前未读取到展品数据',
    actions: [
      { label: '展品管理', path: '/admin/exhibits' },
      { label: '知识库', path: '/admin/documents' },
    ],
  },
  {
    name: '建议条与 AI 回答',
    miniapp: 'tour suggestions Phase1/Phase2, SSE Markdown',
    backend: '/tour/sessions/:id/chat/stream, RAG prompts',
    control: '提示词管理、LLM 调用追踪',
    status: prompts.value.length ? 'ok' : 'warn',
    note: '建议问题词表与模板由馆方配置维护；回答依据与检索结果可通过调用追踪排查',
    actions: [
      { label: '提示词', path: '/admin/prompts' },
      { label: 'LLM 追踪', path: '/admin/llm-traces' },
    ],
  },
  {
    name: '报告与 Reflection Engine',
    miniapp: 'report 渲染 halls_visited / highlights / reflection / record_notes，并合并本地记录摘要',
    backend: '/tour/sessions/:id/report',
    control: '提示词管理、LLM 调用追踪',
    status: healthStatus.value === 'ok' ? 'ok' : 'warn',
    note: '报告由有效互动事件、展厅、展品、规则式 reflection 与小程序本地 TOUR_RECORD_SUMMARY 共同组成',
    actions: [
      { label: '提示词', path: '/admin/prompts' },
      { label: '调用追踪', path: '/admin/llm-traces' },
    ],
  },
  {
    name: 'TTS 手动播报',
    miniapp: 'tour 页手动播放 AI 回复语音',
    backend: '/tts/synthesize',
    control: '语音角色管理',
    status: hasConfiguredVoice.value ? 'ok' : 'warn',
    note: hasConfiguredVoice.value ? '声线由已发布馆方配置维护' : '请检查馆方语音配置与服务状态',
    actions: [{ label: '语音角色', path: '/admin/tts-personas' }],
  },
])

const syncRows = [
  {
    area: '展品管理',
    runtime: '小程序通过 /exhibits 和 /exhibits/:id 实时读取后端展品库',
    effect: '保存后立即影响搜展品、展品详情、OCR fallback 和报告展品统计',
    note: '需要绑定 canonical hall slug；未绑定展厅会被小程序筛选、报告和 OCR 逻辑漏掉。',
  },
  {
    area: '展厅设置',
    runtime: '游客展厅目录通过 /tour/halls 读取本馆数据库',
    effect: '保存后游客刷新页面即可读取最新名称、排序和开放状态',
    note: '展厅标识创建后保持稳定；旧名称和简称可通过别名映射。',
  },
  {
    area: '提示词与 TTS',
    runtime: 'AI 回答、报告和 TTS 播报由后端接口读取提示词缓存和 TTS persona',
    effect: '提示词按现有缓存机制生效；语音采用馆方配置中各身份的声线',
    note: '提示词不会自动改小程序页面文案，但会影响后端生成内容和播报风格。',
  },
  {
    area: '路线管理',
    runtime: '路线服务通过 /curator/plan-tour 生成路线，管理端按实际目录展示参考顺序',
    effect: 'AI plan 由后端服务实时返回；展厅目录变动后刷新页面生效',
    note: '路线主题、优先展厅、观察重点与建议问题可在馆方配置中编辑。',
  },
]

const quickActions = [
  { title: '维护展厅顺序', desc: '同步小程序选择页、路线页和报告统计使用的 canonical slug。', icon: MapLocation, path: '/admin/halls' },
  { title: '维护展品与 OCR 匹配', desc: '展品名称、分类、展厅归属会直接影响搜展品和拍照识别结果。', icon: Search, path: '/admin/exhibits' },
  { title: '调整导览提示词', desc: '控制 AI 回答风格、RAG 解释方式和报告文本边界。', icon: Document, path: '/admin/prompts' },
  { title: '排查线上回答', desc: '按调用记录查看 route、tour、report 的模型输入输出和错误。', icon: Monitor, path: '/admin/llm-traces' },
]

async function safeLoad(label, loader) {
  try {
    const result = await loader()
    if (!result?.ok) {
      fetchErrors.value.push(`${label}: ${result?.data?.detail || result?.status || '失败'}`)
      return null
    }
    return result.data
  } catch (err) {
    fetchErrors.value.push(`${label}: ${err instanceof Error ? err.message : '失败'}`)
    return null
  }
}

async function fetchDashboard() {
  loading.value = true
  fetchErrors.value = []
  try {
    const [health, ready, hallData, exhibitData, promptData, ttsData] = await Promise.all([
      safeLoad('健康检查', () => api.health()),
      safeLoad('就绪检查', () => api.ready()),
      safeLoad('展厅设置', () => api.admin.listHalls({ include_inactive: 'true' })),
      safeLoad('展品数据', () => api.admin.listExhibits({ limit: 200 })),
      safeLoad('提示词', () => api.admin.prompts.list({ include_inactive: 'true' })),
      safeLoad('语音角色', () => api.admin.ttsPersonas.list()),
    ])

    healthStatus.value = health ? 'ok' : 'error'
    readyStatus.value = ready ? 'ok' : 'error'
    halls.value = hallData?.halls || []
    exhibits.value = exhibitData?.exhibits || []
    prompts.value = promptData?.prompts || []
    ttsPersonas.value = ttsData?.personas || []
  } finally {
    loading.value = false
  }
}

function go(path) {
  router.push(path)
}

function flowTagType(status) {
  return status === 'ok' ? 'success' : 'warning'
}

function flowTagText(status) {
  return status === 'ok' ? '已对齐' : '需检查'
}

function hallContractStatus(row) {
  return row.is_active === false
    ? { type: 'warning', text: '未启用' }
    : { type: 'success', text: '启用' }
}

onMounted(fetchDashboard)
</script>

<template>
  <div class="mini-program-control" v-loading="loading">
    <section class="control-header">
      <div>
        <p class="eyebrow">MuseAI 管理端</p>
        <h1>小程序闭环控制台</h1>
        <p class="subtitle">
          按小程序实际链路检查后台控制点：问卷、路线、展厅、展品、建议条、TTS、报告与 Reflection Engine。
        </p>
      </div>
      <el-button type="primary" @click="fetchDashboard">
        <el-icon><Refresh /></el-icon>
        刷新状态
      </el-button>
    </section>

    <el-alert
      v-if="fetchErrors.length"
      type="warning"
      :closable="false"
      show-icon
      class="status-alert"
    >
      <template #title>
        有 {{ fetchErrors.length }} 项状态未读取成功，通常是登录权限、后端服务或网络问题。
      </template>
      <div class="error-list">
        <span v-for="item in fetchErrors" :key="item">{{ item }}</span>
      </div>
    </el-alert>

    <section class="stat-grid">
      <article v-for="stat in dashboardStats" :key="stat.label" class="stat-card">
        <div class="stat-label">{{ stat.label }}</div>
        <div class="stat-value">{{ stat.value }}</div>
        <el-tag size="small" :type="stat.type">{{ stat.desc }}</el-tag>
      </article>
    </section>

    <section class="panel-section">
      <div class="section-title">
        <div>
          <h2>闭环能力对齐</h2>
          <p>小程序端每个功能都需要能在后台找到对应的数据、配置或排查入口。</p>
        </div>
      </div>

      <div class="flow-list">
        <article v-for="row in flowRows" :key="row.name" class="flow-card">
          <div class="flow-card-head">
            <h3>{{ row.name }}</h3>
            <el-tag :type="flowTagType(row.status)" size="small">{{ flowTagText(row.status) }}</el-tag>
          </div>
          <div class="flow-grid">
            <div class="flow-field">
              <span>小程序链路</span>
              <p>{{ row.miniapp }}</p>
            </div>
            <div class="flow-field">
              <span>后端契约</span>
              <p>{{ row.backend }}</p>
            </div>
            <div class="flow-field">
              <span>管理端控制点</span>
              <p>{{ row.control }}</p>
            </div>
            <div class="flow-field flow-note">
              <span>说明</span>
              <p>{{ row.note }}</p>
            </div>
          </div>
          <div class="action-group">
            <el-button
              v-for="action in row.actions"
              :key="action.path + action.label"
              size="small"
              @click="go(action.path)"
            >
              {{ action.label }}
            </el-button>
          </div>
        </article>
      </div>
    </section>

    <section class="panel-section">
      <div class="section-title">
        <div>
          <h2>管理同步边界</h2>
          <p>这里区分“保存后立即影响小程序”和“需要发布小程序代码”的配置。</p>
        </div>
      </div>
      <div class="sync-list">
        <article v-for="row in syncRows" :key="row.area" class="sync-card">
          <h3>{{ row.area }}</h3>
          <div class="sync-grid">
            <div class="flow-field">
              <span>小程序读取方式</span>
              <p>{{ row.runtime }}</p>
            </div>
            <div class="flow-field">
              <span>生效方式</span>
              <p>{{ row.effect }}</p>
            </div>
            <div class="flow-field">
              <span>说明</span>
              <p>{{ row.note }}</p>
            </div>
          </div>
        </article>
      </div>
    </section>

    <section class="two-column">
      <div class="panel-section">
        <div class="section-title compact">
          <div>
            <h2>四身份契约</h2>
            <p>与小程序 persona、报告标题和路线主题保持一致。</p>
          </div>
          <el-button text type="primary" @click="go('/admin/tts-personas')">
            管理语音角色
          </el-button>
        </div>
        <div class="contract-list">
          <article v-for="row in personaContract" :key="row.code" class="contract-card">
            <div class="contract-main">
              <strong>{{ row.label }}</strong>
              <span>{{ row.report }}</span>
            </div>
            <div class="contract-meta">
              <span>后端 {{ row.code }}</span>
              <span>前端 {{ row.personaId }}</span>
              <span>{{ row.route }}</span>
            </div>
          </article>
        </div>
      </div>

      <div class="panel-section">
        <div class="section-title compact">
          <div>
            <h2>本馆展厅目录</h2>
            <p>报告统计、路线、展品筛选共用馆方配置的展厅标识。</p>
          </div>
          <el-button text type="primary" @click="go('/admin/halls')">
            管理展厅
          </el-button>
        </div>
        <div class="contract-list hall-contract-list">
          <article v-for="row in expectedHalls" :key="row.slug" class="contract-card hall-card">
            <div class="contract-main">
              <strong>{{ row.name }}</strong>
              <span>{{ row.slug }}</span>
            </div>
            <div class="contract-meta">
              <span>{{ row.type }}</span>
              <span>{{ row.zone }}</span>
              <el-tag :type="hallContractStatus(row).type" size="small">
                {{ hallContractStatus(row).text }}
              </el-tag>
            </div>
          </article>
        </div>
      </div>
    </section>

    <section class="quick-grid">
      <button
        v-for="item in quickActions"
        :key="item.title"
        type="button"
        class="quick-card"
        @click="go(item.path)"
      >
        <el-icon><component :is="item.icon" /></el-icon>
        <span class="quick-title">{{ item.title }}</span>
        <span class="quick-desc">{{ item.desc }}</span>
      </button>
    </section>
  </div>
</template>

<style scoped>
.mini-program-control {
  display: grid;
  gap: 18px;
  min-height: 100%;
  padding: 24px;
  background: var(--el-bg-color-page);
}

.control-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.eyebrow {
  margin: 0 0 6px;
  color: var(--el-color-primary);
  font-size: 13px;
  font-weight: 600;
}

h1,
h2 {
  margin: 0;
  color: var(--el-text-color-primary);
}

h1 {
  font-size: 26px;
  line-height: 1.25;
}

h2 {
  font-size: 17px;
}

.subtitle,
.section-title p {
  margin: 6px 0 0;
  color: var(--el-text-color-secondary);
  line-height: 1.55;
}

.status-alert {
  border-radius: 8px;
}

.error-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 6px;
}

.error-list span {
  font-size: 12px;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.stat-card,
.panel-section {
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  box-shadow: var(--el-box-shadow-lighter);
}

.stat-card {
  display: grid;
  gap: 8px;
  padding: 16px;
}

.stat-label {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.stat-value {
  color: var(--el-text-color-primary);
  font-size: 24px;
  font-weight: 700;
}

.panel-section {
  min-width: 0;
  padding: 16px;
}

.section-title {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.section-title.compact {
  align-items: center;
}

.action-group {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.flow-list,
.sync-list,
.contract-list {
  display: grid;
  gap: 12px;
}

.flow-card,
.sync-card,
.contract-card {
  min-width: 0;
  padding: 14px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: var(--el-fill-color-extra-light);
}

.flow-card-head,
.contract-card {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.flow-card h3,
.sync-card h3 {
  margin: 0;
  color: var(--el-text-color-primary);
  font-size: 16px;
  line-height: 1.35;
}

.flow-grid,
.sync-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin: 12px 0;
}

.sync-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-bottom: 0;
}

.flow-field {
  min-width: 0;
}

.flow-field span {
  display: block;
  margin-bottom: 4px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  font-weight: 700;
}

.flow-field p {
  margin: 0;
  color: var(--el-text-color-primary);
  line-height: 1.6;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.flow-note {
  grid-column: auto;
}

.contract-list {
  max-height: 390px;
  overflow-y: auto;
  padding-right: 4px;
}

.contract-main {
  display: grid;
  min-width: 0;
  gap: 4px;
}

.contract-main strong {
  color: var(--el-text-color-primary);
  line-height: 1.4;
}

.contract-main span,
.contract-meta {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.contract-meta {
  display: flex;
  flex: 0 1 58%;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px 10px;
}

.contract-meta span {
  min-width: 0;
  overflow-wrap: anywhere;
}

.two-column {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.15fr);
  gap: 18px;
}

.quick-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.quick-card {
  display: grid;
  gap: 8px;
  min-height: 112px;
  padding: 16px;
  color: var(--el-text-color-primary);
  text-align: left;
  cursor: pointer;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.quick-card:hover {
  border-color: var(--el-color-primary);
  box-shadow: var(--el-box-shadow-light);
}

.quick-card .el-icon {
  color: var(--el-color-primary);
  font-size: 22px;
}

.quick-title {
  font-weight: 700;
}

.quick-desc {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  line-height: 1.5;
}

@media (max-width: 1180px) {
  .stat-grid,
  .quick-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .two-column {
    grid-template-columns: 1fr;
  }

  .flow-grid,
  .sync-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .mini-program-control {
    padding: 16px;
  }

  .control-header,
  .section-title {
    flex-direction: column;
  }

  .stat-grid,
  .quick-grid {
    grid-template-columns: 1fr;
  }

  .flow-grid,
  .sync-grid {
    grid-template-columns: 1fr;
  }

  .flow-card-head,
  .contract-card {
    flex-direction: column;
  }

  .contract-meta {
    justify-content: flex-start;
    flex-basis: auto;
  }
}
</style>
