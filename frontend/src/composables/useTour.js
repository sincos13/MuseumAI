import { computed, ref } from 'vue'
import { api } from '../api/index.js'
import { getHallDisplayName, useHallDirectory } from './useHallDirectory.js'
import { useMuseumProfile } from './useMuseumProfile.js'
import { useAuth } from './useAuth.js'
import { useTourWorkbench } from './useTourWorkbench.js'
import { useTTSPlayer } from './useTTSPlayer.js'

const tourSession = ref(null), sessionToken = ref(null), tourStep = ref('onboarding')
const currentHall = ref(null), currentExhibit = ref(null), hallExhibits = ref([]), exhibitIndex = ref(0)
const streamingContent = ref(''), suggestedActions = ref(null), questionSuggestions = ref([]), chatMessages = ref([])
const guideChoices = ref([]), openingPending = ref(false)
const loading = ref({ session: false, chat: false, report: false }), error = ref(null), tourReport = ref(null), visitorRoute = ref(null)
const { halls, hallsLoading, hallsError, fetchHalls, findHall } = useHallDirectory()
let eventBuffer = [], eventFlushTimer = null, exhibitStartTime = null, hallStartTime = null
let flushPromise = null, lifecycleInstalled = false, streamGeneration = 0
let streamController = null
const viewedIds = new Set()
const SESSION = 'tour_session_id', TOKEN = 'tour_session_token', EVENTS = 'tour_pending_events'
const EVENT_METADATA_LIMITS = {
  started_at: 64, client_event_id: 120, question_client_event_id: 120,
  exhibit_name: 255, view_source: 64, message: 2000, question: 2000,
  answer: 4000, trace_id: 120, exhibit_kind: 100,
}
const EVENT_TYPES = new Set(['exhibit_view', 'exhibit_question', 'exhibit_deep_dive', 'hall_enter', 'hall_leave', 'assistant_answer', 'tour_start'])
function normalizeBufferedEvent(event) {
  if (!event || !EVENT_TYPES.has(event.event_type)) return null
  const { hall, exhibit_id, duration_seconds, ...details } = event.metadata || {}
  const metadata = {}
  for (const [key, limit] of Object.entries(EVENT_METADATA_LIMITS)) {
    if (typeof details[key] === 'string') metadata[key] = details[key].slice(0, limit)
  }
  if (typeof details.is_ceramic_question === 'boolean') metadata.is_ceramic_question = details.is_ceramic_question
  if (event.event_type === 'tour_start' && !metadata.started_at) return null
  metadata.client_event_id ||= crypto.randomUUID()
  return { event_type: event.event_type, hall: event.hall ?? hall, exhibit_id: event.exhibit_id ?? exhibit_id,
    duration_seconds: event.duration_seconds ?? duration_seconds, metadata }
}
function persistSession() {
  if (!tourSession.value) return
  localStorage.setItem(SESSION, tourSession.value.id)
  localStorage.setItem(TOKEN, sessionToken.value || '')
}
function persistEvents() { localStorage.setItem(EVENTS, JSON.stringify(eventBuffer)) }

export function useTour() {
  const { revision: publishedRevision } = useMuseumProfile()
  const museumConfiguration = computed(() => tourSession.value?.museum_configuration || null)
  const { personaByCode, museum: tourMuseum, business: tourBusiness } = useMuseumProfile(museumConfiguration)
  const { isAuthenticated, user } = useAuth()
  const { ttsPreferences, activeTab } = useTourWorkbench()
  const { isPlaying: ttsPlaying, feedChunk, stop: stopTTS } = useTTSPlayer()
  const busy = () => loading.value.chat || loading.value.session
  function welcome(hall) {
    return tourBusiness.value?.visitor_experience?.hall_openings?.[hall]
      || ('欢迎来到' + getHallDisplayName(hall) + '。选择下方话题，或点“看展品”，围绕具体展品继续提问。')
  }
  function fail(result, fallback) {
    error.value = typeof result?.data?.detail === 'string' ? result.data.detail : fallback
    return false
  }
  async function createTourSession(focus, persona, assumption, preferences = {}) {
    if (loading.value.session) return null
    loading.value.session = true
    error.value = null
    const questionnaire = { focus_id: focus, persona_id: persona, assumption }
    if (publishedRevision.value != null) questionnaire.config_revision = publishedRevision.value
    if (preferences.rhythm_id) questionnaire.rhythm_id = preferences.rhythm_id
    if (preferences.skipped) questionnaire.skipped = true
    try {
      const existing = tourSession.value
      const canRetry = existing?.status === 'onboarding' && existing.persona === persona
        && existing.assumption === assumption && existing.questionnaire?.focus_id === focus
        && existing.questionnaire?.rhythm_id === questionnaire.rhythm_id
        && existing.questionnaire?.config_revision === questionnaire.config_revision
      if (!canRetry) {
        const result = await api.tour.createSession({
          interest_type: persona, persona, assumption, questionnaire,
          guest_id: isAuthenticated.value ? null : 'guest-' + crypto.randomUUID(),
        })
        if (!result?.ok) {
          const messages = { 0: '无法连接导览服务，请确认后端已启动后重试。', 401: '登录已过期，请刷新页面后重新登录，或使用游客导览。',
            409: '馆方问卷已更新，请刷新页面后重新作答。', 422: '提交信息未通过校验，请刷新页面后重试。', 429: '操作太频繁，请稍后重试。' }
          error.value = messages[result?.status] || result?.data?.detail || '创建导览失败，请稍后重试。'
          return null
        }
        tourSession.value = result.data
        sessionToken.value = result.data.session_token
        persistSession()
      }
      const result = await api.tour.updateSession(tourSession.value.id, { status: 'opening' }, sessionToken.value)
      if (!result?.ok) { fail(result, '导览准备失败，请重试。'); return null }
      tourSession.value = result.data || tourSession.value
      visitorRoute.value = null
      return result.data
    } catch { error.value = '导览准备失败，请检查网络后重试；若仍失败，请刷新页面。'; return null }
    finally { loading.value.session = false }
  }
  async function restoreSession() {
    const id = localStorage.getItem(SESSION), token = localStorage.getItem(TOKEN)
    if (!id) return false
    const result = await api.tour.getSession(id, token)
    if (!result?.ok) {
      if (result?.status === 0 || result?.status >= 500) {
        error.value = '暂时无法恢复导览，请恢复网络后刷新。'
        return true
      }
      resetTour(); return false
    }
    if (isAuthenticated.value && result.data.user_id && String(result.data.user_id) !== String(user.value?.id)) {
      resetTour(); return false
    }
    tourSession.value = result.data
    sessionToken.value = token
    try {
      const pending = JSON.parse(localStorage.getItem(EVENTS) || '[]')
      eventBuffer = Array.isArray(pending) ? pending.map(normalizeBufferedEvent).filter(Boolean) : []
    } catch { eventBuffer = [] }
    persistEvents()
    startTimer()
    if (result.data.status === 'completed') tourStep.value = 'report'
    else if (result.data.status === 'touring') {
      await fetchHalls()
      if (!findHall(result.data.current_hall)) {
        tourStep.value = 'hall-select'
        if (result.data.current_hall) error.value = hallsError.value || '上次参观的展厅已不可用，请重新选择展厅'
        return true
      }
      currentHall.value = result.data.current_hall
      await loadExhibits()
      currentExhibit.value = hallExhibits.value.find(e => e.id === result.data.current_exhibit_id) || null
      hallStartTime = Date.now()
      exhibitStartTime = currentExhibit.value ? Date.now() : null
      await restoreMessages()
      await fetchSuggestions()
      tourStep.value = 'tour'
      if (currentExhibit.value && !chatMessages.value.some(m => !m.isWelcome)) await startExhibitOpening()
    } else tourStep.value = result.data.status === 'opening' ? 'opening' : 'onboarding'
    return true
  }
  async function loadExhibits() {
    const result = await api.exhibits.list({ hall: currentHall.value, limit: 100 })
    if (result?.ok) hallExhibits.value = result.data.exhibits || []
    else fail(result, '展品加载失败，请重新进入展厅。')
  }
  async function selectHall(slug) {
    if (!tourSession.value || busy()) return false
    loading.value.session = true
    error.value = null
    try {
      await fetchHalls()
      const hall = findHall(slug)
      if (!hall) { error.value = hallsError.value || '这个展厅不存在或已关闭，请选择其他展厅'; return false }
      const result = await api.tour.updateSession(tourSession.value.id,
        { current_hall: hall.slug, current_exhibit_id: null, status: 'touring' }, sessionToken.value)
      if (!result?.ok) return fail(result, '无法进入展厅，请刷新后重试')
      checkpointVisit()
      currentHall.value = hall.slug
      currentExhibit.value = null
      exhibitStartTime = null
      hallStartTime = Date.now()
      hallExhibits.value = []
      exhibitIndex.value = 0
      streamingContent.value = ''
      suggestedActions.value = null
      chatMessages.value = [{ role: 'assistant', content: welcome(hall.slug), isWelcome: true }]
      tourSession.value = result.data || tourSession.value
      tourSession.value.visited_exhibit_ids = [...viewedIds]
      persistSession()
      await loadExhibits()
      bufferEvent('hall_enter', { hall: hall.slug })
      activeTab.value = 'session'
      await fetchSuggestions()
      return true
    } finally { loading.value.session = false }
  }
  async function enterExhibit(exhibit) {
    if (!tourSession.value || busy()) return false
    loading.value.session = true
    try {
      const result = await api.tour.updateSession(tourSession.value.id,
        { current_exhibit_id: exhibit?.id || null }, sessionToken.value)
      if (!result?.ok) return fail(result, '无法切换展品，请重试。')
      checkpointVisit()
      tourSession.value = result.data || tourSession.value
      tourSession.value.visited_exhibit_ids = [...viewedIds]
      currentExhibit.value = exhibit || null
      exhibitStartTime = exhibit ? Date.now() : null
      streamingContent.value = ''
      error.value = null
      chatMessages.value = []
      if (exhibit) bufferEvent('exhibit_view', { exhibit_id: exhibit.id, exhibit_name: exhibit.name, duration_seconds: 0 })
      if (exhibit && !tourSession.value.visited_exhibit_ids?.includes(exhibit.id)) {
        viewedIds.add(exhibit.id)
        tourSession.value.visited_exhibit_ids = [...(tourSession.value.visited_exhibit_ids || []), exhibit.id]
      }
      await restoreMessages()
      loading.value.session = false
      if (exhibit) activeTab.value = 'session'
      if (exhibit && !chatMessages.value.some(m => !m.isWelcome)) await startExhibitOpening()
      else await fetchSuggestions()
      return true
    } finally { loading.value.session = false }
  }
  async function startExhibitOpening() {
    if (!currentExhibit.value || busy()) return
    chatMessages.value = chatMessages.value.filter(m => !m.isWelcome && !(m.isOpening && m.saved === false))
    openingPending.value = true
    const generation = streamGeneration + 1
    try { await sendTourMessage('开始展品带看', true, null, { action: 'opening' }) }
    finally { if (generation === streamGeneration) openingPending.value = false }
  }
  async function sendTourMessage(message, skipUserPush = false, style = null, options = {}) {
    if (!tourSession.value || busy() || tourSession.value.status === 'completed') return
    const rawMessage = String(message || '').trim()
    if (!rawMessage) return
    loading.value.chat = true
    error.value = null
    const generation = ++streamGeneration, clientEventId = crypto.randomUUID()
    const controller = new AbortController()
    streamController = controller
    let completed = false, sources = []
    if (!skipUserPush) chatMessages.value.push({ role: 'user', content: rawMessage })
    streamingContent.value = ''
    suggestedActions.value = null
    try {
      for await (const event of api.tour.chatStream(tourSession.value.id, rawMessage,
        sessionToken.value, currentExhibit.value?.id, style,
        { tts: ttsPreferences.value.enabled, clientEventId, ...options, signal: controller.signal })) {
        if (generation !== streamGeneration) return
        if (event.event === 'sources') sources = event.data?.sources || []
        else if (event.event === 'chunk' && event.data?.content) streamingContent.value += event.data.content
        else if (event.event === 'done') {
          chatMessages.value.push({ role: 'assistant', content: streamingContent.value, sources,
            isOpening: options.action === 'opening', saved: event.saved !== false })
          completed = true
          streamingContent.value = ''
          suggestedActions.value = event.suggested_actions || {}
          if (event.state_version) tourSession.value.state_version = event.state_version
        } else if (event.event === 'error' || event.event === 'warning') error.value = event.data?.message || 'AI 导览暂时不可用'
        else if (event.event === 'audio_chunk' && ttsPreferences.value.enabled && ttsPreferences.value.autoPlay) feedChunk(event.data)
      }
      if (generation === streamGeneration && !completed && !error.value) error.value = '回答未完成，请重试。'
    } catch { if (generation === streamGeneration) error.value = '连接中断，请重试' }
    finally {
      if (generation === streamGeneration) {
        streamController = null
        streamingContent.value = ''
        loading.value.chat = false
        await fetchSuggestions()
      }
    }
  }
  function stopTourResponse() {
    ++streamGeneration
    streamController?.abort()
    streamController = null
    if (streamingContent.value || openingPending.value) chatMessages.value.push({ role: 'assistant', content: streamingContent.value || '开场已停止，你可以继续提问或重试开场。',
      isOpening: openingPending.value, saved: false, interrupted: true })
    streamingContent.value = ''
    loading.value.chat = false
    openingPending.value = false
    stopTTS()
  }
  function startTimer() {
    if (!eventFlushTimer) eventFlushTimer = setInterval(() => { checkpointVisit(); void flushEvents() }, 30000)
  }
  function bufferEvent(type, metadata = {}) {
    const { hall, exhibit_id, duration_seconds, ...details } = metadata
    const event = normalizeBufferedEvent({ event_type: type, hall: hall ?? currentHall.value,
      exhibit_id: exhibit_id ?? currentExhibit.value?.id, duration_seconds,
      metadata: { client_event_id: crypto.randomUUID(), ...details } })
    if (!event) return
    eventBuffer.push(event)
    persistEvents()
    startTimer()
  }
  function checkpointVisit() {
    if (tourSession.value?.status === 'completed') return
    const now = Date.now()
    const seconds = start => Math.min(86400, Math.max(0, Math.floor((now - start) / 1000)))
    if (currentExhibit.value && exhibitStartTime) {
      bufferEvent('exhibit_view', { exhibit_id: currentExhibit.value.id, exhibit_name: currentExhibit.value.name, duration_seconds: seconds(exhibitStartTime) })
      exhibitStartTime = now
    }
    if (currentHall.value && hallStartTime) {
      bufferEvent('hall_leave', { hall: currentHall.value, duration_seconds: seconds(hallStartTime) })
      hallStartTime = now
    }
  }
  async function flushEvents() {
    if (flushPromise) return flushPromise
    if (!eventBuffer.length || !tourSession.value) return true
    const id = tourSession.value.id
    flushPromise = (async () => {
      while (eventBuffer.length && tourSession.value?.id === id) {
        const events = eventBuffer.slice(0, 100)
        try {
          const result = await api.tour.recordEvents(id, events, sessionToken.value)
          if (!result?.ok || tourSession.value?.id !== id) return false
          eventBuffer.splice(0, events.length)
          persistEvents()
        } catch { return false }
      }
      return true
    })()
    try { return await flushPromise } finally { flushPromise = null }
  }
  async function completeHall() {
    if (!tourSession.value || busy()) return null
    checkpointVisit()
    if (!await flushEvents()) { error.value = '参观记录尚未保存，请重试。'; return null }
    const result = await api.tour.completeHall(tourSession.value.id, sessionToken.value)
    if (!result?.ok) { fail(result, '无法完成当前展厅，请重试。'); return result }
    if (result.data.all_halls_visited) await finishTour()
    else await leaveHall()
    return result
  }
  async function leaveHall() {
    if (!tourSession.value || busy()) return null
    checkpointVisit()
    if (!await flushEvents()) { error.value = '参观记录尚未保存，请重试。'; return null }
    const result = await api.tour.updateSession(tourSession.value.id,
      { current_hall: null, current_exhibit_id: null, status: 'touring' }, sessionToken.value)
    if (!result?.ok) { fail(result, '离开展厅失败，请重试。'); return result }
    tourSession.value = result.data
    tourStep.value = 'hall-select'
    currentHall.value = null
    currentExhibit.value = null
    hallStartTime = null
    exhibitStartTime = null
    hallExhibits.value = []
    exhibitIndex.value = 0
    streamingContent.value = ''
    suggestedActions.value = null
    chatMessages.value = []
    stopTTS()
    return result
  }
  async function finishTour() {
    if (!tourSession.value || busy()) return false
    checkpointVisit()
    if (!await flushEvents()) { error.value = '参观记录尚未保存，请重试。'; return false }
    const result = await api.tour.updateSession(tourSession.value.id, { status: 'completed' }, sessionToken.value)
    if (!result?.ok) return fail(result, '结束参观失败，请重试。')
    tourSession.value = result.data
    hallStartTime = null
    exhibitStartTime = null
    stopTTS()
    tourStep.value = 'report'
    return true
  }
  async function generateReport() {
    if (!tourSession.value || loading.value.report) return
    if (!await flushEvents()) { error.value = '参观记录尚未保存，请重试。'; return }
    loading.value.report = true
    error.value = null
    try {
      const result = await api.tour.generateReport(tourSession.value.id, sessionToken.value)
      if (result?.ok) tourReport.value = result.data
      else fail(result, '报告生成失败，请重试。')
      return result
    } finally { loading.value.report = false }
  }
  async function loadRoute() {
    if (!tourSession.value) return
    error.value = null
    const result = await api.tour.getRoute(tourSession.value.id, sessionToken.value)
    if (result?.ok) visitorRoute.value = result.data
    else fail(result, '路线加载失败，请重试。')
    return result
  }
  async function fetchSuggestions() {
    const id = tourSession.value?.id, exhibitId = currentExhibit.value?.id, hall = currentHall.value
    questionSuggestions.value = []
    guideChoices.value = []
    if (!id || !hall) return
    try {
      const result = await api.tour.getSuggestions(id, sessionToken.value, { hall_id: hall, ...(exhibitId ? { exhibit_id: exhibitId } : {}) })
      if (result?.ok && tourSession.value?.id === id && currentHall.value === hall && currentExhibit.value?.id === exhibitId) {
        questionSuggestions.value = result.data.suggestions || []
        guideChoices.value = result.data.choices || []
      }
    } catch { /* Curated topic chips remain usable. */ }
  }
  async function restoreMessages() {
    const result = await api.tour.getEvents(tourSession.value.id, sessionToken.value)
    const messages = []
    for (const e of result?.data?.events || []) {
      if (e.event_type === 'exhibit_view' && e.exhibit_id) viewedIds.add(e.exhibit_id)
      if (e.hall !== currentHall.value || !['assistant_answer', 'guide_opening'].includes(e.event_type) || !e.metadata?.server_authored) continue
      if ((e.exhibit_id || null) !== (currentExhibit.value?.id || null)) continue
      if (e.event_type !== 'guide_opening') messages.push({ role: 'user', content: e.metadata.question })
      messages.push({ role: 'assistant', content: e.metadata.answer, sources: e.metadata.sources || [], isOpening: e.event_type === 'guide_opening' })
    }
    tourSession.value.visited_exhibit_ids = [...viewedIds]
    chatMessages.value = messages.length ? messages : [{ role: 'assistant', content: welcome(currentHall.value), isWelcome: true }]
  }
  function resetTour() {
    streamController?.abort()
    streamController = null
    ++streamGeneration
    tourSession.value = null
    sessionToken.value = null
    tourStep.value = 'onboarding'
    currentHall.value = null
    currentExhibit.value = null
    hallExhibits.value = []
    exhibitIndex.value = 0
    streamingContent.value = ''
    suggestedActions.value = null
    questionSuggestions.value = []
    guideChoices.value = []
    openingPending.value = false
    chatMessages.value = []
    tourReport.value = null
    visitorRoute.value = null
    error.value = null
    loading.value = { session: false, chat: false, report: false }
    eventBuffer = []
    viewedIds.clear()
    exhibitStartTime = null
    hallStartTime = null
    for (const key of [SESSION, TOKEN, EVENTS]) localStorage.removeItem(key)
    if (eventFlushTimer) { clearInterval(eventFlushTimer); eventFlushTimer = null }
    stopTTS()
  }
  function setupBeforeUnload() {
    if (lifecycleInstalled) return
    lifecycleInstalled = true
    window.addEventListener('pagehide', () => {
      checkpointVisit()
      if (eventBuffer.length && tourSession.value) {
        fetch('/api/v1/tour/sessions/' + tourSession.value.id + '/events', {
          method: 'POST', keepalive: true,
          headers: { 'Content-Type': 'application/json', 'X-Session-Token': sessionToken.value || '' },
          body: JSON.stringify({ events: eventBuffer.slice(0, 100) }),
        }).catch(() => {})
      }
    })
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) { checkpointVisit(); hallStartTime = null; exhibitStartTime = null; void flushEvents() }
      else if (currentHall.value && tourSession.value?.status === 'touring') {
        hallStartTime = Date.now()
        exhibitStartTime = currentExhibit.value ? Date.now() : null
      }
    })
  }
  const personaLabel = computed(() => personaByCode.value[tourSession.value?.persona]?.name || '')
  const reportThemeTitle = computed(() => personaByCode.value[tourSession.value?.persona]?.reportTitle || '')
  return {
    tourSession, sessionToken, tourStep, currentHall, currentExhibit, hallExhibits, exhibitIndex,
    streamingContent, suggestedActions, questionSuggestions, chatMessages, loading, error,
    tourReport, visitorRoute, halls, hallsLoading, hallsError, personaLabel, personaByCode,
    tourMuseum, tourBusiness, reportThemeTitle, ttsPlaying, createTourSession, restoreSession,
    fetchHalls, selectHall, enterExhibit, sendTourMessage, bufferEvent, flushEvents, completeHall,
    leaveHall, finishTour, generateReport, loadRoute, resetTour, setupBeforeUnload,
    guideChoices, openingPending, startExhibitOpening, stopTourResponse,
  }
}
