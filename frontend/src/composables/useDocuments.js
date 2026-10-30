import { ref } from 'vue'
import { api } from '../api/index.js'
import { useAuth } from './useAuth.js'

const documents = ref([])
const loading = ref(false)
const error = ref(null)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

export function documentErrorMessage(result, fallback = '请求失败，请检查网络后重试') {
  const detail = result?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map(item => item.msg || '资料格式不正确').join('；')
  return fallback
}

export function useDocuments() {
  const { isAdmin, isAuthenticated } = useAuth()

  function handleError(result) {
    error.value = result.status === 401 ? '请先登录'
      : result.status === 403 ? '需要管理员权限' : documentErrorMessage(result)
    return result
  }

  function checkAccess() {
    if (!isAuthenticated.value) return handleError({ ok: false, status: 401, data: { detail: '请先登录' } })
    if (!isAdmin.value) return handleError({ ok: false, status: 403, data: { detail: '需要管理员权限' } })
    return null
  }

  async function perform(action) {
    const denied = checkAccess()
    if (denied) return denied
    try {
      const result = await action()
      return result.ok ? result : handleError(result)
    } catch {
      return handleError({ ok: false, status: 0, data: { detail: '请求失败，请检查网络后重试' } })
    }
  }

  async function fetchDocuments(options = {}) {
    const denied = checkAccess()
    if (denied) return denied
    loading.value = true
    error.value = null
    try {
      const nextPage = options.page ?? page.value
      const limit = options.limit ?? pageSize.value
      const result = await perform(() => api.admin.documents.list({ limit, offset: (nextPage - 1) * limit }))
      if (result.ok) {
        documents.value = result.data.documents || []
        total.value = result.data.total ?? documents.value.length
        page.value = nextPage
        pageSize.value = limit
        // A deletion can empty the last page. Return to an existing page.
        const lastPage = Math.max(1, Math.ceil(total.value / limit))
        if (nextPage > lastPage) return await fetchDocuments({ page: lastPage, limit })
      }
      return result
    } finally {
      loading.value = false
    }
  }

  async function uploadDocument(file, metadata = {}) {
    const result = await perform(() => api.admin.documents.upload(file, metadata))
    if (result.ok) await fetchDocuments({ page: 1 })
    return result
  }

  async function deleteDocument(docId) {
    const result = await perform(() => api.admin.documents.delete(docId))
    if (result.ok) {
      documents.value = documents.value.filter(d => d.id !== docId)
      total.value = Math.max(0, total.value - 1)
    }
    return result
  }

  function getDocument(docId) { return perform(() => api.admin.documents.get(docId)) }
  function getDocumentStatus(docId) { return perform(() => api.admin.documents.status(docId)) }
  async function changeDocument(action, docId, data) {
    const result = await perform(() => api.admin.documents[action](docId, data))
    if (result.ok) await fetchDocuments()
    return result
  }

  return {
    documents, loading, error, total, page, pageSize,
    fetchDocuments, uploadDocument, deleteDocument, getDocument, getDocumentStatus,
    updateDocument: (id, data) => changeDocument('update', id, data),
    reindexDocument: id => changeDocument('reindex', id),
    searchPreview: data => perform(() => api.admin.documents.searchPreview(data)),
  }
}
