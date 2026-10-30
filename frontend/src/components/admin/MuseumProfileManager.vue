<script setup>
import { onMounted, ref, watch } from 'vue'
import MuseumBusinessEditor from './MuseumBusinessEditor.vue'
import { useMuseumProfileEditor } from '../../composables/useMuseumProfileEditor.js'

const { draft, revision, loading, saving, error, message, imported, conflict, load, previewImport, save, exportPublished, exportDraft } = useMuseumProfileEditor()
const fileInput = ref(null)
const activePersona = ref('A')
const importError = ref('')
const businessValid = ref(true)
const editorGeneration = ref(0)
watch(draft, () => { businessValid.value = true; editorGeneration.value += 1 })
async function publish() { if (businessValid.value) await save() }

onMounted(load)

async function readImport(event) {
  const file = event.target.files?.[0]
  if (!file) return
  importError.value = ''
  try {
    if (file.size > 512 * 1024) throw new Error('配置文件超过 512 KB，请确认选择的是馆方配置 JSON。')
    previewImport(await file.text())
  } catch (cause) { importError.value = cause.message || '文件读取失败。' }
  event.target.value = ''
}

function download(envelope, suffix) {
  if (!envelope) return
  const url = window.URL.createObjectURL(new window.Blob([JSON.stringify(envelope, null, 2)], { type: 'application/json' }))
  const link = document.createElement('a')
  link.href = url
  link.download = `museum-profile-${suffix}.json`
  link.click()
  window.setTimeout(() => window.URL.revokeObjectURL(url), 1000)
}

async function downloadPublished() { download(await exportPublished(), 'published') }
function downloadDraft() { download(exportDraft(), 'draft') }
function reload() {
  if (!draft.value || window.confirm('重新加载会替换当前未保存的表单。需要保留时，请先导出草稿。确定重新加载？')) load()
}
</script>

<template>
  <div class="museum-profile-manager">
    <header class="profile-hero">
      <div>
        <p class="eyebrow">馆方配置</p>
        <h1>让导览呈现你的博物馆</h1>
        <p>统一维护馆方资料、问卷、身份路线、展品分类、报告规则与语音。保存后立即发布，无需重新打包前端。</p>
      </div>
      <span v-if="revision !== null" class="revision">已发布版本 {{ revision }}</span>
    </header>

    <p v-if="loading" role="status">正在读取馆方配置…</p>
    <el-alert v-if="error || importError" :title="error || importError" type="error" :closable="false" show-icon role="alert" />
    <el-alert v-if="message" :title="message" type="success" :closable="false" show-icon role="status" />
    <div class="toolbar">
      <el-button :disabled="loading || saving" @click="reload">{{ conflict ? '重新加载最新配置' : '重新加载' }}</el-button>
      <el-button :disabled="!draft || loading || saving" @click="downloadPublished">导出已发布配置</el-button>
      <el-button :disabled="!draft || loading || saving" @click="downloadDraft">导出当前草稿</el-button>
      <el-button :disabled="!draft || loading || saving" @click="fileInput?.click()">选择 JSON 导入</el-button>
      <input ref="fileInput" type="file" accept=".json,application/json" hidden @change="readImport" />
    </div>

    <el-form v-if="draft" :model="draft" label-position="top" :disabled="loading || saving" @submit.prevent="publish">
      <section class="form-card">
        <h2>博物馆资料</h2>
        <div class="field-grid">
          <el-form-item label="博物馆标识（使用小写英文、数字、连字符或下划线）"><el-input v-model="draft.museum_id" maxlength="64" /></el-form-item>
          <el-form-item label="馆名"><el-input v-model="draft.name" maxlength="100" data-testid="museum-name" /></el-form-item>
          <el-form-item label="馆名简称"><el-input v-model="draft.short_name" maxlength="50" /></el-form-item>
          <el-form-item label="Logo 地址（可留空）"><el-input v-model="draft.logo_url" placeholder="https://… 或 /images/logo.png" maxlength="2048" /></el-form-item>
        </div>
        <el-form-item label="博物馆简介"><el-input v-model="draft.description" type="textarea" :rows="3" maxlength="4000" show-word-limit /></el-form-item>
        <div class="field-grid">
          <el-form-item label="语言"><el-input v-model="draft.language" placeholder="zh-CN" maxlength="35" /></el-form-item>
          <el-form-item label="时区"><el-input v-model="draft.timezone" placeholder="Asia/Shanghai" maxlength="64" /></el-form-item>
        </div>
      </section>

      <section class="form-card">
        <h2>四种导览身份</h2>
        <p class="help-text">A / B / C / D 是稳定的身份编号。可调整展示名称、文案和讲解方式；在文案中使用 <code>{museum_name}</code> 可自动代入馆名。</p>
        <el-tabs v-model="activePersona">
          <el-tab-pane v-for="persona in draft.personas" :key="persona.code" :name="persona.code" :label="`${persona.code} · ${persona.name}`">
            <div class="field-grid">
              <el-form-item label="身份名称"><el-input v-model="persona.name" maxlength="100" /></el-form-item>
              <el-form-item label="身份图标（文字或 Emoji）"><el-input v-model="persona.icon" maxlength="32" /></el-form-item>
            </div>
            <el-form-item label="身份简介"><el-input v-model="persona.description" type="textarea" :rows="2" maxlength="1000" /></el-form-item>
            <el-form-item label="开场白"><el-input v-model="persona.opening_text" type="textarea" :rows="4" maxlength="2000" /></el-form-item>
            <el-form-item label="报告标题"><el-input v-model="persona.report_title" maxlength="100" /></el-form-item>
            <el-form-item label="讲解风格指令（仅管理员可见，支持 {museum_name} 和 {persona_name}）"><el-input v-model="persona.system_prompt" type="textarea" :rows="5" maxlength="8000" /></el-form-item>
            <template v-if="persona.guide">
              <p class="help-text">以下设置与身份一起保存，控制展品快捷引导与报告小结。开场和连续回应遵循上方身份指令。</p>
              <el-form-item label="带看方法（怎样邀请游客参与）"><el-input v-model="persona.guide.method" type="textarea" :rows="2" maxlength="800" /></el-form-item>
              <el-form-item label="身份小结名称"><el-input v-model="persona.guide.takeaway_title" maxlength="80" /></el-form-item>
              <el-form-item label="报告优先保留什么"><el-input v-model="persona.guide.takeaway_instruction" type="textarea" :rows="3" maxlength="1200" /></el-form-item>
              <div class="field-grid"><el-form-item v-for="(_, i) in persona.guide.section_labels" :key="i" :label="`小结栏目 ${i + 1}`"><el-input v-model="persona.guide.section_labels[i]" maxlength="50" /></el-form-item></div>
              <div v-for="shortcut in persona.guide.shortcuts" :key="shortcut.id" class="field-grid">
                <el-form-item label="快捷按钮名称"><el-input v-model="shortcut.label" maxlength="40" /></el-form-item>
                <el-form-item label="点击后发送的问题（{exhibit} 代入展品名）"><el-input v-model="shortcut.question" maxlength="300" /></el-form-item>
                <el-form-item label="资料关键词（可选，匹配任一个才展示）"><el-select v-model="shortcut.requires_any" multiple filterable allow-create default-first-option><el-option v-for="word in shortcut.requires_any" :key="word" :label="word" :value="word" /></el-select></el-form-item>
                <el-form-item label="已问过的表达（游客说过后不再推荐）"><el-select v-model="shortcut.asked_phrases" multiple filterable allow-create default-first-option><el-option v-for="phrase in shortcut.asked_phrases || []" :key="phrase" :label="phrase" :value="phrase" /></el-select></el-form-item>
              </div>
            </template>
          </el-tab-pane>
        </el-tabs>
      </section>

      <MuseumBusinessEditor v-if="draft.business" :key="editorGeneration" v-model="draft.business" @validity="businessValid = $event" />

      <footer class="publish-bar">
        <p>发布后新导览使用新配置。已有导览保留创建时的问卷、身份、路线和报告规则；展厅开放状态仍实时更新。导入文件只填入表单，点击此按钮才发布。</p>
        <el-button type="primary" :loading="saving" :disabled="loading || conflict || !businessValid" native-type="submit" data-testid="publish-profile">{{ imported ? '导入并发布' : '保存并发布' }}</el-button>
      </footer>
    </el-form>
  </div>
</template>

<style scoped>
.museum-profile-manager { max-width: 1100px; margin: 0 auto; padding: 28px 32px 56px; }
.profile-hero { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; margin-bottom: 24px; }
.eyebrow { color: var(--color-accent); font-weight: 700; margin: 0 0 8px; }
.profile-hero h1 { font-size: 28px; margin: 0 0 12px; }
.profile-hero p, .help-text, .publish-bar p { line-height: 1.7; color: var(--color-text-secondary); }
.revision { white-space: nowrap; padding: 8px 12px; background: var(--color-bg-elevated); border-radius: 8px; }
.toolbar { display: flex; flex-wrap: wrap; gap: 10px; margin: 20px 0; }
.toolbar .el-button { margin-left: 0; }
.form-card { padding: 24px; margin-bottom: 20px; border: 1px solid var(--color-border); border-radius: 12px; background: var(--color-bg-elevated); }
.form-card h2 { font-size: 20px; margin: 0 0 20px; }
.field-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 20px; }
.publish-bar { display: flex; align-items: center; justify-content: space-between; gap: 24px; }
.publish-bar p { max-width: 700px; margin: 0; }
.el-alert + .el-alert { margin-top: 12px; }
@media (max-width: 767px) { .museum-profile-manager { padding: 20px 16px; } .field-grid { grid-template-columns: 1fr; } .profile-hero, .publish-bar { flex-direction: column; } .form-card { padding: 18px; } }
</style>
