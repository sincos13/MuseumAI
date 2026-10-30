import { log, warn, error as logError } from '../utils/logger.js'

const BASE_URL = '/api/v1'

function clearAuthState() {
  localStorage.removeItem('user')
  localStorage.removeItem('user_role')
  localStorage.removeItem('auth_token')
  localStorage.removeItem('tour_session_id')
  localStorage.removeItem('tour_session_token')
  localStorage.removeItem('tour_pending_events')
}

function getAuthToken() {
  return localStorage.getItem('auth_token')
}

function normalizeNetworkError(error) {
  const detail = error instanceof Error ? error.message : 'Network error'
  return { ok: false, status: 0, data: { detail } }
}

async function request(path, options = {}) {
  const { publicRequest = false, ...fetchOptions } = options
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  }

  const authToken = getAuthToken()
  if (authToken && !publicRequest) {
    headers['Authorization'] = `Bearer ${authToken}`
  }

  log(`[API] ${options.method || 'GET'} ${path}`, options.body || '')

  let response
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...fetchOptions,
      headers,
    })
  } catch (error) {
    logError(`[API] Network error for ${path}:`, error)
    return normalizeNetworkError(error)
  }

  const data = await response.json().catch(() => ({}))
  log(`[API] Response for ${path}:`, { status: response.status, ok: response.ok, data })

  if (response.status === 401 && !publicRequest) {
    clearAuthState()
  }

  return {
    ok: response.ok,
    status: response.status,
    data,
  }
}

function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

async function requestWithRetry(path, options = {}, config = { retries: 0, baseDelayMs: 150 }) {
  let attempt = 0
  while (true) {
    const result = await request(path, options)
    const retryable = result.status === 0 || result.status >= 500 || result.status === 429

    if (!retryable || attempt >= config.retries) {
      return result
    }

    attempt += 1
    await wait(config.baseDelayMs * attempt)
  }
}

export const api = {
  museum: {
    importStatus: () => request('/museum/import-status', { publicRequest: true }),
    bootstrap: () => request('/museum/bootstrap', { publicRequest: true, cache: 'no-store' }),
  },
  // Health endpoints (public) - idempotent, safe to retry
  health: () => requestWithRetry('/health', {}, { retries: 1, baseDelayMs: 150 }),
  ready: () => requestWithRetry('/ready', {}, { retries: 1, baseDelayMs: 150 }),

  // Auth endpoints
  auth: {
    register: (email, password) => requestWithRetry('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }, { retries: 1 }),
    login: (email, password) => requestWithRetry('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }, { retries: 1 }),
    logout: () => request('/auth/logout', {
      method: 'POST',
    }),
  },

  documents: {
    list: () => request('/documents'),
    get: (id) => request(`/documents/${id}`),
    status: (id) => request(`/documents/${id}/status`),
    delete: (id) => request(`/documents/${id}`, { method: 'DELETE' }),
    upload: async (file) => {
      const formData = new FormData()
      formData.append('file', file)

      const authToken = getAuthToken()
      const headers = {}
      if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`
      }

      const response = await fetch(`${BASE_URL}/documents/upload`, {
        method: 'POST',
        headers,
        body: formData,
      })
      const data = await response.json().catch(() => ({}))
      return { ok: response.ok, status: response.status, data }
    },
  },

  chat: {
    createSession: (title) => request('/chat/sessions', {
      method: 'POST',
      body: JSON.stringify({ title }),
    }),
    listSessions: () => request('/chat/sessions'),
    getSession: (id) => request(`/chat/sessions/${id}`),
    deleteSession: (id) => request(`/chat/sessions/${id}`, { method: 'DELETE' }),
    getMessages: (sessionId) => request(`/chat/sessions/${sessionId}/messages`),
    ask: (sessionId, message) => request('/chat/ask', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, message }),
    }),
    askStream: async function* (sessionId, message, ttsOptions = {}) {
      const headers = { 'Content-Type': 'application/json' }
      const authToken = getAuthToken()
      if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`
      }

      const body = { session_id: sessionId, message }
      if (ttsOptions.tts) body.tts = true
      if (ttsOptions.tts_voice) body.tts_voice = ttsOptions.tts_voice

      const response = await fetch(`${BASE_URL}/chat/ask/stream`, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
      })
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') return
            try {
              yield JSON.parse(data)
            } catch {
              warn('Parse error:', data)
            }
          }
        }
      }
    },
    // Guest chat - no authentication required
    guestMessage: async function* (sessionId, message, ttsOptions = {}) {
      const headers = { 'Content-Type': 'application/json' }
      const body = { message }
      if (sessionId) {
        body.session_id = sessionId
      }
      if (ttsOptions.tts) body.tts = true
      if (ttsOptions.tts_voice) body.tts_voice = ttsOptions.tts_voice

      const response = await fetch(`${BASE_URL}/chat/guest/message`, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
      })
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      // Get session ID from response header for subsequent requests
      const newSessionId = response.headers.get('X-Session-Id')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') return
            try {
              const parsed = JSON.parse(data)
              parsed.session_id = newSessionId
              yield parsed
            } catch {
              warn('Parse error:', data)
            }
          }
        }
      }
    },
  },

  // Exhibits (public API)
  exhibits: {
    list: (params = {}) => {
      // Filter out null/undefined values to avoid malformed queries
      const filteredParams = Object.fromEntries(
        Object.entries(params).filter(([, v]) => v != null)
      )
      return request(`/exhibits?${new URLSearchParams(filteredParams)}`)
    },
    get: (id) => request(`/exhibits/${id}`),
  },

  // Admin
  admin: {
    packages: {
      preview: async (file) => {
        const body = new FormData()
        body.append('file', file)
        try {
          const response = await fetch(BASE_URL + '/admin/museum/packages/preview', {
            method: 'POST', headers: { Authorization: 'Bearer ' + getAuthToken() }, body,
          })
          return { ok: response.ok, status: response.status, data: await response.json() }
        } catch (e) { return normalizeNetworkError(e) }
      },
      confirm: (id) => request('/admin/museum/packages/' + id + '/confirm', { method: 'POST' }),
      progress: (id) => request('/admin/museum/packages/' + id),
    },
    museum: {
      get: () => request('/admin/museum', { cache: 'no-store' }),
      export: () => request('/admin/museum/export', { cache: 'no-store' }),
      update: (data) => request('/admin/museum', { method: 'PUT', body: JSON.stringify(data) }),
      import: (data) => request('/admin/museum/import', { method: 'POST', body: JSON.stringify(data) }),
    },
    // Exhibits
    listExhibits: (params = {}) => request(`/admin/exhibits?${new URLSearchParams(params)}`),
    createExhibit: (data) => request('/admin/exhibits', {
      method: 'POST',
      body: JSON.stringify(data)
    }),
    updateExhibit: (id, data) => request(`/admin/exhibits/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    }),
    deleteExhibit: (id) => request(`/admin/exhibits/${id}`, { method: 'DELETE' }),
    uploadExhibitImage: async (id, file) => {
      const formData = new FormData()
      formData.append('file', file)

      const authToken = getAuthToken()
      const headers = {}
      if (authToken) headers.Authorization = `Bearer ${authToken}`

      try {
        const response = await fetch(`${BASE_URL}/admin/exhibits/${id}/image`, {
          method: 'POST', headers, body: formData,
        })
        const data = await response.json().catch(() => ({}))
        if (response.status === 401) clearAuthState()
        return { ok: response.ok, status: response.status, data }
      } catch (error) {
        return normalizeNetworkError(error)
      }
    },
    deleteExhibitImage: (id) => request(`/admin/exhibits/${id}/image`, { method: 'DELETE' }),

    // Halls
    listHalls: (params = {}) => request(`/admin/halls?${new URLSearchParams(params)}`),
    createHall: (data) => request('/admin/halls', {
      method: 'POST',
      body: JSON.stringify(data)
    }),
    updateHall: (slug, data) => request(`/admin/halls/${slug}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    }),
    deleteHall: (slug) => request(`/admin/halls/${slug}`, { method: 'DELETE' }),

    // Documents (knowledge base management)
    documents: {
      list: (params = {}) => request(`/admin/documents?${new URLSearchParams(params)}`),
      get: (id) => request(`/admin/documents/${id}`),
      status: (id) => request(`/admin/documents/${id}/status`),
      delete: (id) => request(`/admin/documents/${id}`, { method: 'DELETE' }),
      update: (id, data) => request(`/admin/documents/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
      reindex: (id) => request(`/admin/documents/${id}/reindex`, { method: 'POST' }),
      searchPreview: (data) => request('/admin/knowledge/search-preview', { method: 'POST', body: JSON.stringify(data) }),
      upload: async (file, metadata = {}) => {
        const formData = new FormData()
        formData.append('file', file)
        for (const key of ['title', 'source_label', 'source_url', 'hall_slug']) {
          if (metadata[key] != null) formData.append(key, metadata[key])
        }

        const authToken = getAuthToken()
        const headers = {}
        if (authToken) {
          headers['Authorization'] = `Bearer ${authToken}`
        }

        try {
          const response = await fetch(`${BASE_URL}/admin/documents/upload`, {
            method: 'POST', headers, body: formData,
          })
          const data = await response.json().catch(() => ({}))
          if (response.status === 401) clearAuthState()
          return { ok: response.ok, status: response.status, data }
        } catch (error) {
          return normalizeNetworkError(error)
        }
      },
    },

    // Tour Paths
    listTourPaths: () => request('/admin/tour-paths'),
    createTourPath: (data) => request('/admin/tour-paths', {
      method: 'POST',
      body: JSON.stringify(data)
    }),
    updateTourPath: (id, data) => request(`/admin/tour-paths/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    }),
    deleteTourPath: (id) => request(`/admin/tour-paths/${id}`, { method: 'DELETE' }),

    // Prompts
    prompts: {
      list: (params = {}) => {
        const filteredParams = Object.fromEntries(
          Object.entries(params).filter(([, v]) => v != null)
        )
        return request(`/admin/prompts?${new URLSearchParams(filteredParams)}`)
      },
      get: (key) => request(`/admin/prompts/${key}`),
      update: (key, data) => request(`/admin/prompts/${key}`, {
        method: 'PUT',
        body: JSON.stringify(data)
      }),
      listVersions: (key, params = {}) => {
        const filteredParams = Object.fromEntries(
          Object.entries(params).filter(([, v]) => v != null)
        )
        return request(`/admin/prompts/${key}/versions?${new URLSearchParams(filteredParams)}`)
      },
      getVersion: (key, version) => request(`/admin/prompts/${key}/versions/${version}`),
      rollback: (key, version) => request(`/admin/prompts/${key}/versions/${version}/rollback`, {
        method: 'POST'
      }),
      reload: (key) => request(`/admin/prompts/${key}/reload`, { method: 'POST' }),
      reloadAll: () => request('/admin/prompts/reload-all', { method: 'POST' }),
    },

    // TTS Personas
    ttsPersonas: {
      list: () => request('/admin/tts/personas'),
      get: (persona) => request(`/admin/tts/personas/${persona}`),
      update: (persona, data) => request(`/admin/tts/personas/${persona}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
      voicePreview: (data) => request('/admin/tts/voice-preview', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    },

    // LLM Traces
    llmTraces: {
      list: (params = {}) => {
        const filteredParams = Object.fromEntries(
          Object.entries(params).filter(([, v]) => v != null)
        )
        return request(`/admin/llm-traces?${new URLSearchParams(filteredParams)}`)
      },
      get: (callId) => request(`/admin/llm-traces/${callId}`),
    },
  },

  // Curator (AI-powered tour planning)
  curator: {
    planTour: (availableTime, interests, sessionId = null, sessionToken = null) => request('/curator/plan-tour', {
      method: 'POST',
      body: JSON.stringify({ available_time: availableTime, interests, ...(sessionId ? { session_id: sessionId } : {}) }),
      ...(sessionToken ? { headers: { 'X-Session-Token': sessionToken } } : {}),
    }),
    generateNarrative: (exhibitId) => request('/curator/narrative', {
      method: 'POST',
      body: JSON.stringify({ exhibit_id: exhibitId })
    }),
    getReflectionPrompts: (exhibitId) => request('/curator/reflection', {
      method: 'POST',
      body: JSON.stringify({ exhibit_id: exhibitId })
    }),
  },

  // User profile preferences
  profile: {
    get: () => request('/profile'),
    update: (data) => request('/profile', {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  },

  // TTS
  tts: {
    synthesize: (text, voice = null, style = null, persona = null, sessionId = null, sessionToken = null) => request('/tts/synthesize', {
      method: 'POST',
      body: JSON.stringify({ text, voice, style, persona, ...(sessionId ? { session_id: sessionId } : {}) }),
      ...(sessionToken ? { headers: { 'X-Session-Token': sessionToken } } : {}),
    }),
  },

  tour: {
    getRoute: (id, token) => request('/tour/sessions/' + id + '/route', {
      headers: token ? { 'X-Session-Token': token } : {},
    }),
    getSuggestions: (id, token, params = {}) => request('/tour/sessions/' + id + '/suggestions?' + new URLSearchParams(params), {
      headers: token ? { 'X-Session-Token': token } : {},
    }),
    createSession: (data) => request('/tour/sessions', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
    getSession: (id, token) => request(`/tour/sessions/${id}`, {
      headers: token ? { 'X-Session-Token': token } : {},
    }),
    updateSession: (id, data, token) => request(`/tour/sessions/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
      headers: token ? { 'X-Session-Token': token } : {},
    }),
    recordEvents: (id, events, token) => request(`/tour/sessions/${id}/events`, {
      method: 'POST',
      body: JSON.stringify({ events }),
      headers: token ? { 'X-Session-Token': token } : {},
    }),
    getEvents: (id, token) => request(`/tour/sessions/${id}/events`, {
      headers: token ? { 'X-Session-Token': token } : {},
    }),
    completeHall: (id, token) => request(`/tour/sessions/${id}/complete-hall`, {
      method: 'POST',
      headers: token ? { 'X-Session-Token': token } : {},
    }),
    generateReport: (id, token) => request(`/tour/sessions/${id}/report`, {
      method: 'POST',
      headers: token ? { 'X-Session-Token': token } : {},
    }),
    getReport: (id, token) => request(`/tour/sessions/${id}/report`, {
      headers: token ? { 'X-Session-Token': token } : {},
    }),
    chatStream: async function* (id, message, token, exhibitId = null, style = null, ttsOptions = {}) {
      const headers = { 'Content-Type': 'application/json' }
      if (token) headers['X-Session-Token'] = token
      const body = { message }
      if (exhibitId) body.exhibit_id = exhibitId
      if (style) body.style = style
      if (ttsOptions.tts) body.tts = true
      if (ttsOptions.clientEventId) body.client_event_id = ttsOptions.clientEventId
      if (ttsOptions.action) body.action = ttsOptions.action
      if (ttsOptions.shortcutId) body.shortcut_id = ttsOptions.shortcutId

      const response = await fetch(`${BASE_URL}/tour/sessions/${id}/chat/stream`, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
        signal: ttsOptions.signal,
      })
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      try {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6)
              if (data === '[DONE]') return
              try {
                yield JSON.parse(data)
              } catch {
                // skip unparseable lines
              }
            }
          }
        }
      } finally {
        try { await reader.cancel() } catch { /* Aborted fetch has already closed the stream. */ }
        reader.releaseLock()
      }
    },
    getHalls: () => request('/tour/halls', { publicRequest: true, cache: 'no-store' }),
  },
}
