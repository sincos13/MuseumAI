import { readonly, ref } from 'vue'
import { api } from '../api/index.js'
import { hallDisplayName, normalizeHallRecords, resolveHall } from '../utils/halls.js'

const halls = ref([])
const loading = ref(false)
const error = ref(null)
const loaded = ref(false)
let pending = null

export function getHallDisplayName(value) {
  return hallDisplayName(value, halls.value)
}

export function useHallDirectory() {
  function fetchHalls() {
    if (pending) return pending
    loading.value = true
    error.value = null
    // Hide a stale catalog while availability is being refreshed.
    halls.value = []
    pending = (async () => {
      try {
        const result = await api.tour.getHalls()
        if (!result?.ok || !Array.isArray(result.data?.halls)) {
          throw new Error(typeof result?.data?.detail === 'string' ? result.data.detail : '展厅目录加载失败，请重试')
        }
        halls.value = normalizeHallRecords(result.data.halls)
        loaded.value = true
      } catch (err) {
        halls.value = []
        loaded.value = false
        error.value = err instanceof Error ? err.message : '展厅目录加载失败，请重试'
      } finally {
        loading.value = false
        pending = null
      }
      return halls.value
    })()
    return pending
  }

  return {
    halls: readonly(halls),
    hallsLoading: readonly(loading),
    hallsError: readonly(error),
    hallsLoaded: readonly(loaded),
    fetchHalls,
    findHall: (value) => resolveHall(value, halls.value),
    getHallDisplayName,
  }
}
