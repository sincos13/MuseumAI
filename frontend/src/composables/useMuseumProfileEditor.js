import { ref } from 'vue'
import { api } from '../api/index.js'
import { useMuseumProfile } from './useMuseumProfile.js'

const clone = (value) => JSON.parse(JSON.stringify(value))

export function parseMuseumImport(text) {
  let envelope
  try { envelope = JSON.parse(text) } catch { throw new Error('文件不是有效的 JSON，请选择导出的馆方配置文件。') }
  if (envelope?.schema_version !== 1) throw new Error('暂只支持 schema_version 为 1 的馆方配置。')
  const museum = envelope.museum
  if (!museum || typeof museum !== 'object' || Array.isArray(museum)) throw new Error('配置缺少 museum 对象。')
  for (const field of ['museum_id', 'name', 'short_name', 'description', 'language', 'timezone']) {
    if (typeof museum[field] !== 'string' || !museum[field].trim()) throw new Error(`配置中的 ${field} 不能为空。`)
  }
  if (museum.logo_url != null && typeof museum.logo_url !== 'string') throw new Error('Logo 地址必须是文本。')
  if (museum.logo_url && !/^(https?:\/\/|\/(?!\/))/.test(museum.logo_url)) throw new Error('Logo 请使用 http(s) 地址或以 / 开头的本站路径。')
  if (!Array.isArray(museum.personas) || museum.personas.map((item) => item?.code).sort().join('') !== 'ABCD') {
    throw new Error('配置必须恰好包含 A、B、C、D 四种身份，且不能重复。')
  }
  for (const persona of museum.personas) {
    if (typeof persona.icon !== 'string') throw new Error(`身份 ${persona.code} 的 icon 必须是文本（可留空）。`)
    for (const field of ['name', 'description', 'report_title', 'opening_text', 'system_prompt']) {
      if (typeof persona[field] !== 'string' || !persona[field].trim()) throw new Error(`身份 ${persona.code} 的 ${field} 不能为空。`)
    }
  }
  if (!museum.business || museum.business.version !== 1) throw new Error('配置缺少版本 1 的完整业务配置，请使用当前版本导出的配置文件。')
  const business = museum.business
  for (const field of ['questionnaire', 'routes', 'reflection', 'suggestions', 'tts', 'dialogue']) {
    if (!business[field] || typeof business[field] !== 'object' || Array.isArray(business[field])) throw new Error(`业务配置缺少 ${field} 对象。`)
  }
  for (const field of ['focus_options', 'assumption_options']) {
    if (!Array.isArray(business.questionnaire[field]) || business.questionnaire[field].map((item) => item?.code).sort().join('') !== 'ABCD') throw new Error('问卷每道题必须保留 A、B、C、D 四个选项。')
  }
  for (const code of ['A', 'B', 'C', 'D', 'default']) {
    if (!business.routes[code] || !business.reflection.personas?.[code]) throw new Error(`业务配置缺少身份 ${code} 的路线或报告规则。`)
  }
  if (!Array.isArray(business.categories) || !business.categories.length || !Array.isArray(business.route_durations)) throw new Error('业务配置缺少展品分类或路线时长。')
  if (!business.reflection.topics || !business.reflection.radar_dimensions || !business.suggestions.question_templates || !Array.isArray(business.suggestions.description_anchors)) throw new Error('业务配置缺少报告主题、指标或建议问题词表。')
  const parsed = clone(museum)
  parsed.business.tts.personas ||= {}
  for (const code of ['A', 'B', 'C', 'D', 'default']) parsed.business.tts.personas[code] ||= { voice: '', style: '' }
  return parsed
}

function errorMessage(result, fallback) {
  if (result.status === 409) return '配置已被其他管理员更新。你的修改已保留，请先导出草稿，再重新加载最新配置后合并修改。'
  const detail = result.data?.detail
  if (Array.isArray(detail)) return detail.map((item) => `${(item.loc || []).join('.')}: ${item.msg}`).join('；')
  if (typeof detail === 'string') return detail
  return fallback
}

export function useMuseumProfileEditor() {
  const draft = ref(null)
  const revision = ref(null)
  const loading = ref(false)
  const saving = ref(false)
  const error = ref('')
  const message = ref('')
  const imported = ref(false)
  const conflict = ref(false)
  const { loadProfile } = useMuseumProfile()

  async function load() {
    if (loading.value || saving.value) return false
    loading.value = true
    error.value = ''
    try {
      const result = await api.admin.museum.get()
      if (!result.ok) throw new Error(errorMessage(result, '馆方配置读取失败，请重试。'))
      const parsed = parseMuseumImport(JSON.stringify(result.data))
      draft.value = parsed
      revision.value = result.data.revision
      imported.value = false
      conflict.value = false
      message.value = ''
      return true
    } catch (cause) {
      error.value = cause.message
      return false
    } finally { loading.value = false }
  }

  function previewImport(text) {
    error.value = ''
    try {
      const parsed = parseMuseumImport(text)
      draft.value = parsed
      imported.value = true
      message.value = '文件已读入表单，尚未发布。请检查内容，再点击“导入并发布”。'
      return true
    } catch (cause) {
      error.value = cause.message
      return false
    }
  }

  async function save() {
    if (saving.value || loading.value || !draft.value || revision.value == null || conflict.value) return false
    saving.value = true
    error.value = ''
    message.value = ''
    try {
      const museum = parseMuseumImport(JSON.stringify({ schema_version: 1, museum: draft.value }))
      const payload = { schema_version: 1, expected_revision: revision.value, museum }
      const result = imported.value
        ? await api.admin.museum.import(payload)
        : await api.admin.museum.update(payload)
      if (!result.ok) {
        conflict.value = result.status === 409
        throw new Error(errorMessage(result, '保存失败，修改仍保留在表单中。'))
      }
      draft.value = parseMuseumImport(JSON.stringify(result.data))
      revision.value = result.data.revision
      imported.value = false
      const refreshed = await loadProfile()
      message.value = refreshed
        ? '已保存并发布。新导览使用新配置，已有导览保留创建时配置。'
        : '已保存并发布，但当前页面的配置刷新失败；请刷新页面确认显示效果。'
      return true
    } catch (cause) {
      error.value = cause.message
      return false
    } finally { saving.value = false }
  }

  async function exportPublished() {
    error.value = ''
    const result = await api.admin.museum.export()
    if (!result.ok) { error.value = errorMessage(result, '导出失败，请重试。'); return null }
    return result.data
  }

  function exportDraft() {
    return { schema_version: 1, revision: revision.value, museum: clone(draft.value) }
  }

  return { draft, revision, loading, saving, error, message, imported, conflict, load, previewImport, save, exportPublished, exportDraft }
}
