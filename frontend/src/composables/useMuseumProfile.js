import { computed, isRef, readonly, ref, unref } from 'vue'
import { api } from '../api/index.js'

const profile = ref(null)
const revision = ref(null)
const loading = ref(false)
const error = ref('')
let pending = null

export function formatMuseumText(text, name) {
  return String(text || '').replaceAll('{museum_name}', name || '')
}

// Only public fields enter the shared visitor state, even after an admin saves.
export function publicProfile(envelope) {
  const museum = envelope?.museum
  const codes = museum?.personas?.map((persona) => persona.code).sort().join('')
  if (envelope?.schema_version !== 1 || !Number.isInteger(envelope.revision)
    || !museum?.name || codes !== 'ABCD') {
    throw new Error('馆方配置格式不兼容，请联系管理员检查配置版本。')
  }
  return {
    museum_id: museum.museum_id,
    name: museum.name,
    short_name: museum.short_name,
    description: museum.description,
    logo_url: museum.logo_url,
    language: museum.language,
    timezone: museum.timezone,
    business: publicBusiness(museum.business),
    personas: museum.personas.map(({ code, name, description, icon, report_title, opening_text }) => ({
      code, name, description, icon, report_title, opening_text,
    })),
  }
}

function publicBusiness(business) {
  if (!business || business.version !== 1) {
    throw new Error('馆方业务配置尚未就绪，请联系管理员检查配置。')
  }
  const pick = (value, fields) => Object.fromEntries(fields.map((key) => [key, value?.[key]]))
  const questionnaire = business.questionnaire || {}
  return {
    version: business.version,
    questionnaire: {
      ...pick(questionnaire, ['focus_title', 'persona_title', 'assumption_title']),
      focus_options: (questionnaire.focus_options || []).map((item) => pick(item, ['code', 'label', 'description'])),
      assumption_options: (questionnaire.assumption_options || []).map((item) => pick(item, ['code', 'label', 'description', 'topic'])),
    },
    categories: (business.categories || []).map((item) => pick(item, ['value', 'label'])),
    routes: Object.fromEntries(Object.entries(business.routes || {}).map(([key, route]) => [key, {
      ...pick(route, ['theme', 'summary', 'focus']),
      questions: [...(route.questions || [])], preferred_halls: [...(route.preferred_halls || [])],
    }])),
    route_durations: (business.route_durations || []).map((item) => pick(item, ['max_minutes', 'stops'])),
    rhythms: (business.rhythms || []).map((item) => pick(item, ['value', 'label'])),
    visitor_experience: business.visitor_experience ? JSON.parse(JSON.stringify(business.visitor_experience)) : null,
    reflection: {
      topics: Object.fromEntries(Object.entries(business.reflection?.topics || {}).map(([key, value]) => [key, { label: value.label }])),
      radar_dimensions: Object.fromEntries(Object.entries(business.reflection?.radar_dimensions || {}).map(([key, value]) => [key, { label: value.label }])),
    },
    tts: {
      default_voice: business.tts?.default_voice || '',
      personas: Object.fromEntries(Object.entries(business.tts?.personas || {}).map(([key, voice]) => [key, { voice: voice.voice }])),
    },
  }
}

async function loadProfile() {
  if (pending) return pending
  loading.value = true
  error.value = ''
  pending = (async () => {
    try {
      const result = await api.museum.bootstrap()
      if (!result.ok) throw new Error('无法加载馆方配置，请确认后端服务已启动后重试。')
      profile.value = publicProfile(result.data)
      revision.value = result.data.revision
      return true
    } catch (cause) {
      error.value = cause.message || '馆方配置加载失败，请重试。'
      return false
    } finally {
      loading.value = false
      pending = null
    }
  })()
  return pending
}

export function useMuseumProfile(snapshot = null) {
  const configurationSnapshot = isRef(snapshot) ? snapshot : null
  const selectedProfile = computed(() => unref(configurationSnapshot) ? publicProfile(unref(configurationSnapshot)) : profile.value)
  const museum = computed(() => selectedProfile.value || {
    name: '', short_name: '', description: '', logo_url: '', personas: [], business: null,
  })
  const business = computed(() => museum.value.business)
  const personas = computed(() => museum.value.personas.map((persona) => ({
    ...persona,
    name: formatMuseumText(persona.name, museum.value.name),
    description: formatMuseumText(persona.description, museum.value.name),
    opening_text: formatMuseumText(persona.opening_text, museum.value.name),
    report_title: formatMuseumText(persona.report_title, museum.value.name),
    personaId: persona.code,
    prompt: formatMuseumText(persona.description, museum.value.name),
    reportTitle: formatMuseumText(persona.report_title, museum.value.name),
    routeTitle: business.value?.routes?.[persona.code]?.theme || `${formatMuseumText(persona.name, museum.value.name)}路线`,
    focusTitle: business.value?.routes?.[persona.code]?.focus || formatMuseumText(persona.description, museum.value.name),
  })))
  const personaByCode = computed(() => Object.fromEntries(personas.value.map((persona) => [persona.code, persona])))
  const categories = computed(() => business.value?.categories || [])
  const categoryOptions = computed(() => [{ value: null, label: '全部' }, ...categories.value])
  const getCategoryLabel = (value) => categories.value.find((item) => item.value === value)?.label || value || '未分类'
  return {
    museum: readonly(museum), business: readonly(business),
    personas: readonly(personas), personaByCode: readonly(personaByCode),
    categories: readonly(categories), categoryOptions: readonly(categoryOptions), getCategoryLabel,
    revision: computed(() => unref(configurationSnapshot)?.revision ?? revision.value),
    ready: computed(() => selectedProfile.value !== null),
    loading: readonly(loading), error: readonly(error), loadProfile,
  }
}
