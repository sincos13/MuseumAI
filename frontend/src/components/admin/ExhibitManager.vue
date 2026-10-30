<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../../api/index.js'
import { useMuseumProfile } from '../../composables/useMuseumProfile.js'
import { useAdmin } from '../../composables/useAdmin.js'
import { hallDisplayName, normalizeHallRecords, normalizeHallSlug } from '../../utils/halls.js'
import AdminIcon from './AdminIcon.vue'

const { museum, categories, getCategoryLabel } = useMuseumProfile()
const { loading, createExhibit, updateExhibit, deleteExhibit } = useAdmin()

const formRef = ref(null)
const exhibits = ref([])
const halls = ref([])
const selectedIds = ref([])
const batchHall = ref('')
const batchDeleting = ref(false)
const batchBinding = ref(false)
const problemResolving = ref(false)
const fetching = ref(false)
const dialogVisible = ref(false)
const isEditing = ref(false)
const imageDialogVisible = ref(false)
const imageInputRef = ref(null)
const imageTarget = ref(null)
const imagePreviewUrl = ref('')
const imageUploading = ref(false)
const imageDeleting = ref(false)

const filters = reactive({
  keyword: '',
  hall: '',
  category: '',
  status: 'active',
})

const form = reactive({
  id: null,
  name: '',
  description: '',
  location_x: 0,
  location_y: 0,
  floor: 1,
  hall: '',
  category: '',
  era: '',
  importance: 3,
  estimated_visit_time: 8,
  document_id: null,
  is_active: true,
})

const rules = {
  name: [{ required: true, message: '请输入展品名称', trigger: 'blur' }],
  hall: [{ required: true, message: '请选择所属展厅', trigger: 'change' }],
  category: [{ required: true, message: '请选择展品分类', trigger: 'change' }],
  description: [{ required: true, message: '请输入展品简介', trigger: 'blur' }],
}

const museumName = computed(() => museum.value.short_name || museum.value.name || '本馆')
const categoryOptions = computed(() => categories.value)
const canonicalHalls = computed(() => halls.value.filter((hall) => hall.is_active !== false))
const activeHallSlugs = computed(() => new Set(canonicalHalls.value.map((hall) => hall.slug)))

const normalizedExhibits = computed(() => exhibits.value.map(normalizeExhibit))
const activeNormalizedExhibits = computed(() => normalizedExhibits.value.filter((item) => item.is_active !== false))

const filteredExhibits = computed(() => {
  const q = filters.keyword.trim().toLowerCase()
  return normalizedExhibits.value.filter((item) => {
    const matchesKeyword = !q
      || String(item.name || '').toLowerCase().includes(q)
      || String(item.description || '').toLowerCase().includes(q)
      || String(item.era || '').toLowerCase().includes(q)
    const matchesHall = !filters.hall || item.hall === filters.hall
    const matchesCategory = !filters.category || item.category === filters.category
    const matchesStatus = filters.status === 'all'
      || (filters.status === 'active' && item.is_active !== false)
      || (filters.status === 'inactive' && item.is_active === false)
    return matchesKeyword && matchesHall && matchesCategory && matchesStatus
  })
})

const selectedRows = computed(() => normalizedExhibits.value.filter((item) => selectedIds.value.includes(item.id)))
const allSelected = computed(() => filteredExhibits.value.length > 0
  && filteredExhibits.value.every((item) => selectedIds.value.includes(item.id)))

const nonExhibitRows = computed(() => activeNormalizedExhibits.value.filter((item) => isNonExhibitName(item.name)))
const unmappedRows = computed(() => activeNormalizedExhibits.value.filter((item) => !activeHallSlugs.value.has(item.hall)))
const problemRows = computed(() => [...nonExhibitRows.value, ...unmappedRows.value])

const coveredHallCount = computed(() => {
  const used = new Set(normalizedExhibits.value.map((item) => item.hall).filter(Boolean))
  return canonicalHalls.value.filter((hall) => used.has(hall.slug)).length
})

const stats = computed(() => [
  { key: 'total', label: '展品总数', value: normalizedExhibits.value.length, unit: '件', icon: 'vase' },
  { key: 'active', label: '可展示', value: activeNormalizedExhibits.value.length, unit: '件', icon: 'frame' },
  {
    key: 'halls',
    label: '展厅覆盖',
    value: `${coveredHallCount.value}/${canonicalHalls.value.length}`,
    hint: '当前开放展厅',
    icon: 'seal',
  },
  {
    key: 'issues',
    label: '需处理',
    value: problemRows.value.length,
    unit: '件',
    icon: 'warning',
    tone: 'is-warn',
    action: problemRows.value.length ? '处理' : '',
  },
])

watch(
  () => [filters.keyword, filters.hall, filters.category, filters.status],
  () => { selectedIds.value = [] },
)

onMounted(async () => {
  await Promise.all([fetchHalls(), fetchExhibits()])
})

function normalizeExhibit(item) {
  const rawHall = item.hall || item.hall_slug || item.hallSlug
  const hall = normalizeHallSlug(rawHall)
  return {
    ...item,
    rawHall,
    hall,
    hallName: hallDisplayName(rawHall, halls.value),
    categoryLabel: getCategoryLabel(item.category),
    activeText: item.is_active === false ? '停用' : '启用',
    nonExhibit: isNonExhibitName(item.name),
  }
}

async function fetchHalls() {
  const result = await api.admin.listHalls({ include_inactive: 'true' })
  halls.value = result.ok ? normalizeHallRecords(result.data.halls || [], { includeInactive: true }) : []
  if (!result.ok) ElMessage.error('展厅目录加载失败，请刷新后再维护展品')
  if (!canonicalHalls.value.some((hall) => hall.slug === batchHall.value)) {
    batchHall.value = canonicalHalls.value[0]?.slug || ''
  }
}

async function fetchExhibits() {
  fetching.value = true
  try {
    const result = await api.admin.listExhibits({ limit: 1000 })
    if (result.ok) {
      exhibits.value = result.data.exhibits || []
      selectedIds.value = []
    } else {
      ElMessage.error(result.data?.detail || '获取展品失败')
    }
  } finally {
    fetching.value = false
  }
}

function isNonExhibitName(name = '') {
  const exactNames = new Set(halls.value.map((hall) => hall.name))
  return exactNames.has(String(name).trim())
}

function categoryIcon(value) {
  const icons = {
    woodwork: 'box',
    pottery: 'vase',
    stonework: 'seal',
    model: 'hall',
    inscription: 'image',
    production: 'frame',
    textile: 'chat',
    metal: 'vase',
    document: 'frame',
    bamboo: 'vase',
  }
  return icons[value] || 'vase'
}

function prettyHall(value) {
  const text = String(value || '')
  if (!text) return '未绑定展厅'
  return text.charAt(0).toUpperCase() + text.slice(1)
}

function isSelected(row) {
  return selectedIds.value.includes(row.id)
}

function toggleRow(row) {
  const index = selectedIds.value.indexOf(row.id)
  if (index >= 0) selectedIds.value.splice(index, 1)
  else selectedIds.value.push(row.id)
}

function toggleAll() {
  const visibleIds = filteredExhibits.value.map((row) => row.id)
  if (allSelected.value) {
    const visible = new Set(visibleIds)
    selectedIds.value = selectedIds.value.filter((id) => !visible.has(id))
    return
  }
  selectedIds.value = Array.from(new Set([...selectedIds.value, ...visibleIds]))
}

function clearSelection() {
  selectedIds.value = []
}

function resetFilters() {
  filters.keyword = ''
  filters.hall = ''
  filters.category = ''
  filters.status = 'active'
  batchHall.value = canonicalHalls.value[0]?.slug || ''
  clearSelection()
}

function resetForm() {
  Object.assign(form, {
    id: null,
    name: '',
    description: '',
    location_x: 0,
    location_y: 0,
    floor: 1,
    hall: canonicalHalls.value[0]?.slug || '',
    category: '',
    era: '',
    importance: 3,
    estimated_visit_time: 8,
    document_id: null,
    is_active: true,
  })
}

function handleAdd() {
  isEditing.value = false
  resetForm()
  dialogVisible.value = true
}

function handleEdit(row) {
  isEditing.value = true
  Object.assign(form, {
    id: row.id,
    name: row.name || '',
    description: row.description || '',
    location_x: row.location_x ?? 0,
    location_y: row.location_y ?? 0,
    floor: row.floor || 1,
    hall: normalizeHallSlug(row.hall || row.hall_slug || row.hallSlug) || '',
    category: row.category || '',
    era: row.era || '',
    importance: row.importance || 3,
    estimated_visit_time: row.estimated_visit_time || 8,
    document_id: row.document_id || null,
    is_active: row.is_active !== false,
  })
  dialogVisible.value = true
}

function openImageDialog(row) {
  imageTarget.value = {
    id: row.id,
    name: row.name,
    hallName: row.hallName || row.hall || '',
    image_url: row.image_url || '',
  }
  imagePreviewUrl.value = row.image_url || ''
  imageDialogVisible.value = true
}

function resetImageDialog() {
  imageTarget.value = null
  imagePreviewUrl.value = ''
  if (imageInputRef.value) imageInputRef.value.value = ''
}

function chooseImage() {
  imageInputRef.value?.click()
}

function withCacheBuster(url) {
  if (!url) return ''
  return `${url}${url.includes('?') ? '&' : '?'}v=${Date.now()}`
}

async function handleImageSelected(event) {
  const file = event.target?.files?.[0]
  if (event.target) event.target.value = ''
  const target = imageTarget.value
  if (!file || !target) return

  if (file.type && !['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
    ElMessage.error('请选择 JPEG、PNG 或 WebP 图片')
    return
  }
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.error('图片不能超过 5 MiB')
    return
  }

  imageUploading.value = true
  try {
    const result = await api.admin.uploadExhibitImage(target.id, file)
    if (!result.ok) {
      ElMessage.error(result.data?.detail || '图片上传失败')
      return
    }
    const imageUrl = result.data?.image_url
    if (!imageUrl) {
      ElMessage.error('图片上传成功，但没有返回图片地址')
      return
    }
    const displayUrl = withCacheBuster(imageUrl)
    const row = exhibits.value.find((item) => item.id === target.id)
    if (row) row.image_url = displayUrl
    if (imageTarget.value?.id === target.id) {
      imageTarget.value.image_url = imageUrl
      imagePreviewUrl.value = displayUrl
    }
    ElMessage.success('展品图片已更新')
  } finally {
    imageUploading.value = false
  }
}

async function handleDeleteImage() {
  const target = imageTarget.value
  if (!target) return
  try {
    await ElMessageBox.confirm(
      `确定删除「${target.name}」的图片吗？`,
      '删除图片',
      { type: 'warning' },
    )
  } catch {
    return
  }

  imageDeleting.value = true
  try {
    const result = await api.admin.deleteExhibitImage(target.id)
    if (!result.ok) {
      ElMessage.error(result.data?.detail || '图片删除失败')
      return
    }
    const row = exhibits.value.find((item) => item.id === target.id)
    if (row) row.image_url = null
    if (imageTarget.value?.id === target.id) {
      imagePreviewUrl.value = ''
      imageTarget.value.image_url = ''
    }
    ElMessage.success('展品图片已删除')
  } finally {
    imageDeleting.value = false
  }
}

function buildPayload() {
  return {
    name: form.name.trim(),
    description: form.description.trim(),
    location_x: Number(form.location_x) || 0,
    location_y: Number(form.location_y) || 0,
    floor: Number(form.floor) || 1,
    hall: normalizeHallSlug(form.hall),
    category: form.category,
    era: form.era.trim(),
    importance: Number(form.importance) || 3,
    estimated_visit_time: Number(form.estimated_visit_time) || 8,
    document_id: form.document_id || null,
    is_active: Boolean(form.is_active),
  }
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  if (!activeHallSlugs.value.has(form.hall) && (!isEditing.value || form.is_active)) {
    ElMessage.error('请选择当前开放的展厅')
    return
  }
  const payload = buildPayload()
  const result = isEditing.value
    ? await updateExhibit(form.id, payload)
    : await createExhibit(payload)

  if (result.ok) {
    ElMessage.success(isEditing.value ? '展品已更新' : '展品已创建')
    dialogVisible.value = false
    await fetchExhibits()
  } else {
    ElMessage.error(result.data?.detail || '保存失败')
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.name}」吗？`, '删除确认', { type: 'warning' })
    const result = await deleteExhibit(row.id)
    if (result.ok) {
      ElMessage.success('展品已删除')
      await fetchExhibits()
    } else {
      ElMessage.error(result.data?.detail || '删除失败')
    }
  } catch {
    // user cancelled
  }
}

async function handleResolveProblemRows() {
  const rowsToDisable = nonExhibitRows.value
  if (rowsToDisable.length) {
    try {
      await ElMessageBox.confirm(
        `将停用 ${rowsToDisable.length} 条可能不是展品的条目。未绑定展厅的展品不会自动停用，请选择行后批量绑定展厅。是否继续？`,
        '处理需处理项',
        { type: 'warning' },
      )
      problemResolving.value = true
      let successCount = 0
      let failedCount = 0

      for (const row of rowsToDisable) {
        const result = await updateExhibit(row.id, { is_active: false })
        if (result.ok) successCount += 1
        else failedCount += 1
      }
      await fetchExhibits()
      if (failedCount) {
        ElMessage.warning(`已处理 ${successCount} 条，${failedCount} 条失败`)
      } else {
        ElMessage.success(`已处理 ${successCount} 条异常项`)
      }
    } catch {
      // user cancelled
    } finally {
      problemResolving.value = false
    }
    return
  }

  if (unmappedRows.value.length) {
    if (!batchHall.value) {
      ElMessage.warning('请先在工具栏选择目标展厅，再处理未绑定展厅的异常项')
      return
    }
    selectedIds.value = unmappedRows.value.map((row) => row.id)
    ElMessage.info(`已选中 ${unmappedRows.value.length} 件未绑定展厅的展品，请确认目标展厅后点击“绑定展厅”`)
    return
  }

  ElMessage.warning('当前没有可自动处理的异常项')
}

async function handleBatchBindHall() {
  const targetRows = selectedRows.value
  if (!targetRows.length) {
    ElMessage.warning('请先选择要绑定展厅的展品')
    return
  }
  if (!batchHall.value) {
    ElMessage.warning('请先选择目标展厅')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定将 ${targetRows.length} 件展品绑定到「${hallDisplayName(batchHall.value, halls.value)}」吗？`,
      '批量绑定展厅',
      { type: 'warning' },
    )
    batchBinding.value = true
    let successCount = 0
    let failedCount = 0
    for (const row of targetRows) {
      const result = await updateExhibit(row.id, { hall: batchHall.value })
      if (result.ok) successCount += 1
      else failedCount += 1
    }
    await fetchExhibits()
    if (failedCount) {
      ElMessage.warning(`已绑定 ${successCount} 件，${failedCount} 件失败`)
    } else {
      ElMessage.success(`已绑定 ${successCount} 件展品`)
    }
  } catch {
    // user cancelled
  } finally {
    batchBinding.value = false
  }
}

async function handleBatchDelete() {
  if (!selectedRows.value.length) return
  try {
    await ElMessageBox.confirm(`确定删除已选中的 ${selectedRows.value.length} 件展品吗？`, '批量删除确认', {
      type: 'warning',
    })
    batchDeleting.value = true
    let successCount = 0
    let failedCount = 0
    for (const row of selectedRows.value) {
      const result = await deleteExhibit(row.id)
      if (result.ok) successCount += 1
      else failedCount += 1
    }
    await fetchExhibits()
    if (failedCount) {
      ElMessage.warning(`已删除 ${successCount} 件，${failedCount} 件失败`)
    } else {
      ElMessage.success(`已删除 ${successCount} 件展品`)
    }
  } catch {
    // user cancelled
  } finally {
    batchDeleting.value = false
  }
}
</script>

<template>
  <div class="exhibit-manager">
    <section class="exhibit-hero">
      <span class="hero-seal" aria-hidden="true">藏</span>
      <div class="hero-copy">
        <p class="hero-kicker">MUSEUM GUIDE SYSTEM</p>
        <h1 class="hero-title">{{ museumName }}展品管理</h1>
        <p class="hero-desc">
          本馆展览以“古城文明·历史传承”为主线，汇聚青铜器、陶瓷、书画等珍贵文物。<br />
          在这里，每一件展品都是一段历史的回响。
        </p>
        <span class="hero-rule" aria-hidden="true" />
      </div>
      <button type="button" class="hero-add" @click="handleAdd">
        <AdminIcon name="plus" />
        <span>添加展品</span>
      </button>
    </section>

    <section class="exhibit-stats">
      <article
        v-for="item in stats"
        :key="item.key"
        class="stat-card"
        :class="item.tone"
      >
        <div class="stat-head">
          <span class="stat-icon"><AdminIcon :name="item.icon" /></span>
          <span class="stat-label">{{ item.label }}</span>
          <button
            v-if="item.action"
            type="button"
            class="stat-action"
            :disabled="problemResolving"
            @click="handleResolveProblemRows"
          >
            {{ item.action }}
          </button>
        </div>
        <div class="stat-value">
          <strong>{{ item.value }}</strong>
          <em v-if="item.unit">{{ item.unit }}</em>
        </div>
        <p v-if="item.hint" class="stat-hint">{{ item.hint }}</p>
      </article>
    </section>

    <el-alert
      v-if="nonExhibitRows.length"
      type="warning"
      :closable="false"
      show-icon
      class="data-alert"
      title="检测到可能不是展品的条目"
    >
      <template #default>
        {{ nonExhibitRows.map((item) => item.name).join('、') }}
        不应出现在小程序“搜展品”结果中，建议改为资料条目或从展品库删除。
      </template>
    </el-alert>

    <el-alert
      v-if="unmappedRows.length"
      type="error"
      :closable="false"
      show-icon
      class="data-alert"
      title="检测到展厅映射异常"
    >
      <template #default>
        有 {{ unmappedRows.length }} 条展品未绑定到当前开放展厅，会影响展厅筛选、报告统计和 OCR 匹配。
        请先在工具栏确认目标展厅，再执行批量绑定。
      </template>
    </el-alert>

    <section class="exhibit-toolbar">
      <label class="search-field">
        <AdminIcon name="search" />
        <input
          v-model="filters.keyword"
          type="search"
          placeholder="搜索展品名称、简介或年代"
          aria-label="搜索展品名称、简介或年代"
        />
      </label>
      <el-select v-model="filters.hall" placeholder="全部展厅" clearable filterable>
        <el-option v-for="hall in canonicalHalls" :key="hall.slug" :label="hall.name" :value="hall.slug" />
      </el-select>
      <el-select v-model="filters.category" placeholder="全部分类" clearable>
        <el-option v-for="category in categoryOptions" :key="category.value" :label="category.label" :value="category.value" />
      </el-select>
      <el-select v-model="filters.status" placeholder="状态">
        <el-option label="启用展品" value="active" />
        <el-option label="停用展品" value="inactive" />
        <el-option label="全部状态" value="all" />
      </el-select>
      <el-select v-model="batchHall" placeholder="目标展厅" filterable title="批量绑定展厅的目标">
        <el-option v-for="hall in canonicalHalls" :key="hall.slug" :label="hall.name" :value="hall.slug" />
      </el-select>
      <button type="button" class="reset-button" @click="resetFilters">
        <AdminIcon name="reset" />
        <span>重置</span>
      </button>
    </section>

    <section v-if="selectedRows.length" class="selection-bar">
      <span class="selection-count">已选择 {{ selectedRows.length }} 件展品</span>
      <span class="selection-target">目标展厅：{{ hallDisplayName(batchHall, halls) || '未选择' }}</span>
      <el-button
        type="primary"
        plain
        size="small"
        :loading="batchBinding"
        :disabled="batchBinding || !batchHall"
        @click="handleBatchBindHall"
      >
        绑定展厅
      </el-button>
      <el-button
        type="danger"
        plain
        size="small"
        :loading="batchDeleting"
        :disabled="batchDeleting"
        @click="handleBatchDelete"
      >
        批量删除
      </el-button>
      <button type="button" class="selection-clear" @click="clearSelection">取消选择</button>
    </section>

    <section class="exhibit-table-panel">
      <div class="table-scroll">
        <table class="exhibit-table">
          <colgroup>
            <col class="col-check" />
            <col class="col-name" />
            <col class="col-image" />
            <col class="col-hall" />
            <col class="col-category" />
            <col class="col-era" />
            <col class="col-rating" />
            <col class="col-visit" />
            <col class="col-actions" />
          </colgroup>
          <thead>
            <tr>
              <th class="cell-check">
                <label class="check">
                  <input
                    type="checkbox"
                    :checked="allSelected"
                    aria-label="选择全部展品"
                    @change="toggleAll"
                  />
                  <span class="check-box"><AdminIcon name="check" /></span>
                </label>
              </th>
              <th>展品名称</th>
              <th>展品图</th>
              <th>所属展厅</th>
              <th>分类</th>
              <th>年代</th>
              <th>重要度</th>
              <th>参观</th>
              <th class="cell-actions">操作</th>
            </tr>
          </thead>
          <tbody v-if="filteredExhibits.length">
            <tr
              v-for="row in filteredExhibits"
              :key="row.id"
              :class="{ 'is-selected': isSelected(row) }"
            >
              <td class="cell-check">
                <label class="check">
                  <input
                    type="checkbox"
                    :checked="isSelected(row)"
                    :aria-label="`选择${row.name}`"
                    @change="toggleRow(row)"
                  />
                  <span class="check-box"><AdminIcon name="check" /></span>
                </label>
              </td>
              <td class="col-name">
                <div class="name-cell">
                  <span class="artifact-tile"><AdminIcon :name="categoryIcon(row.category)" /></span>
                  <div class="name-copy">
                    <div class="exhibit-name">
                      <span>{{ row.name }}</span>
                      <em v-if="row.nonExhibit" class="badge">非展品</em>
                      <em v-if="!activeHallSlugs.has(row.hall)" class="badge badge-warn">未绑定</em>
                      <em v-if="row.is_active === false" class="badge">停用</em>
                    </div>
                    <p class="exhibit-desc">{{ row.description || '暂无简介' }}</p>
                  </div>
                </div>
              </td>
              <td class="col-image">
                <button
                  type="button"
                  class="image-thumb"
                  :class="{ 'is-empty': !row.image_url }"
                  :title="row.image_url ? '预览并管理展品图片' : '为展品上传图片'"
                  :aria-label="row.image_url ? `预览并管理${row.name}的图片` : `为${row.name}上传图片`"
                  @click="openImageDialog(row)"
                >
                  <img v-if="row.image_url" :src="row.image_url" :alt="`${row.name}图片`" loading="lazy" />
                  <span v-else class="image-placeholder">
                    <AdminIcon name="image" />
                    <small>上传</small>
                  </span>
                </button>
              </td>
              <td class="col-hall">
                <div class="hall-cell">
                  <strong>{{ row.hallName }}</strong>
                  <span>{{ prettyHall(row.hall || row.rawHall) }}</span>
                </div>
              </td>
              <td class="col-category">
                <span class="category-tag">{{ row.categoryLabel }}</span>
              </td>
              <td class="col-era">{{ row.era || '未标注' }}</td>
              <td class="col-rating">
                <span class="stars" role="img" :aria-label="`重要度 ${row.importance || 3} 分，共 5 分`">
                  <AdminIcon
                    v-for="n in 5"
                    :key="n"
                    name="star"
                    :class="{ 'is-on': n <= (row.importance || 3) }"
                  />
                </span>
              </td>
              <td class="col-visit">{{ row.estimated_visit_time || 0 }} 分</td>
              <td class="col-actions">
                <div class="row-actions">
                  <button type="button" class="row-btn" @click="handleEdit(row)">编辑</button>
                  <button type="button" class="row-btn row-btn--danger" @click="handleDelete(row)">删除</button>
                </div>
              </td>
            </tr>
          </tbody>
          <tbody v-else-if="!fetching">
            <tr>
              <td colspan="9">
                <div class="table-empty">
                  <AdminIcon name="vase" />
                  <p>暂无符合条件的展品</p>
                  <button type="button" @click="handleAdd">添加第一件展品</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="fetching" class="table-loading">
        <span class="spinner" aria-hidden="true" />
        <span>正在加载展品…</span>
      </div>

      <div class="table-footer">
        <span>共 {{ filteredExhibits.length }} 件展品</span>
        <button type="button" class="refresh-link" :disabled="fetching" @click="fetchExhibits">
          <AdminIcon name="reset" />
          <span>刷新列表</span>
        </button>
      </div>
    </section>

    <el-dialog v-model="dialogVisible" :title="isEditing ? '编辑展品' : '添加展品'" width="720px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-form-item label="展品名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="简介" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="4" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="所属展厅" prop="hall">
              <el-select v-model="form.hall" filterable style="width: 100%;">
                <el-option v-for="hall in canonicalHalls" :key="hall.slug" :label="hall.name" :value="hall.slug" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="分类" prop="category">
              <el-select v-model="form.category" style="width: 100%;">
                <el-option v-for="category in categoryOptions" :key="category.value" :label="category.label" :value="category.value" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="年代">
              <el-input v-model="form.era" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="参观时长">
              <el-input-number v-model="form.estimated_visit_time" :min="1" :max="60" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="楼层">
              <el-input-number v-model="form.floor" :min="1" :max="5" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="重要度">
              <el-input-number v-model="form.importance" :min="1" :max="5" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="启用">
              <el-switch v-model="form.is_active" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="坐标 X">
              <el-input-number v-model="form.location_x" :step="0.1" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="坐标 Y">
              <el-input-number v-model="form.location_y" :step="0.1" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="loading" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="imageDialogVisible"
      title="展品图片"
      width="620px"
      @closed="resetImageDialog"
    >
      <div v-if="imageTarget" class="image-manager">
        <div class="image-preview">
          <img v-if="imagePreviewUrl" :src="imagePreviewUrl" :alt="`${imageTarget.name}图片预览`" />
          <div v-else class="image-empty">暂无图片</div>
        </div>

        <div class="image-info">
          <strong>{{ imageTarget.name }}</strong>
          <span>{{ imageTarget.hallName || '未绑定展厅' }}</span>
        </div>

        <p class="image-hint">
          支持 JPEG、PNG、WebP，最大 5 MiB、4000 万像素。上传成功后立即替换当前图片，旧图会被删除。
        </p>

        <input
          ref="imageInputRef"
          class="image-file-input"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          @change="handleImageSelected"
        />

        <div class="image-actions">
          <el-button
            type="primary"
            :loading="imageUploading"
            :disabled="imageDeleting"
            @click="chooseImage"
          >
            {{ imagePreviewUrl ? '上传并替换' : '上传图片' }}
          </el-button>
          <el-button
            v-if="imagePreviewUrl"
            type="danger"
            plain
            :loading="imageDeleting"
            :disabled="imageUploading"
            @click="handleDeleteImage"
          >
            删除图片
          </el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.exhibit-manager {
  display: flex;
  min-height: 100%;
  flex-direction: column;
  color: #2f261d;
  font-family: 'Noto Sans SC', 'Microsoft YaHei', 'PingFang SC', sans-serif;
}

/* ---------- Hero ---------- */
.exhibit-hero {
  position: relative;
  aspect-ratio: 6.05 / 1;
  min-height: 184px;
  max-height: 246px;
  overflow: hidden;
  border: 1px solid #ece2d3;
  border-radius: 12px;
  background: #efe6d8 url('/admin/hero-hall.webp') 0% 47% / 136% auto no-repeat;
  box-shadow: 0 8px 24px rgba(88, 61, 36, 0.08);
}

.exhibit-hero::before {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, rgba(250, 247, 240, 0.94) 0%, rgba(250, 247, 240, 0.8) 28%, rgba(250, 247, 240, 0.3) 54%, rgba(250, 247, 240, 0) 78%),
    linear-gradient(180deg, rgba(255, 252, 246, 0.2), rgba(72, 52, 31, 0.05));
  content: '';
}

.hero-copy {
  position: absolute;
  top: clamp(20px, 2.6vw, 34px);
  left: clamp(22px, 3.1vw, 42px);
  z-index: 2;
  max-width: 66%;
}

.hero-kicker {
  margin: 0;
  color: #9a846b;
  font-size: 9.5px;
  font-weight: 500;
  letter-spacing: 0.34em;
  line-height: 1.4;
}

.hero-title {
  margin: 9px 0 0;
  color: #33291f;
  font-family: 'MuseAI Song', 'Noto Serif SC', 'Songti SC', SimSun, serif;
  font-size: clamp(27px, 2.6vw, 39px);
  font-weight: 600;
  letter-spacing: 0.025em;
  line-height: 1.24;
  text-shadow: 0 1px 0 rgba(255, 255, 255, 0.35);
}

.hero-desc {
  max-width: 660px;
  margin: 11px 0 0;
  color: #5d4f40;
  font-size: clamp(12.5px, 1.02vw, 14.5px);
  font-weight: 400;
  line-height: 1.9;
}

.hero-rule {
  display: block;
  width: 42px;
  height: 2px;
  margin-top: 13px;
  background: linear-gradient(90deg, #a97c46, #d2b183);
  opacity: 0.85;
}

.hero-add {
  position: absolute;
  right: 25px;
  bottom: 23px;
  z-index: 3;
  display: flex;
  align-items: center;
  gap: 8px;
  height: 44px;
  padding: 0 20px 0 16px;
  border: 1px solid rgba(202, 166, 116, 0.55);
  border-radius: 8px;
  background: linear-gradient(135deg, rgba(62, 45, 28, 0.95), rgba(45, 32, 20, 0.95));
  box-shadow: 0 8px 20px rgba(45, 32, 20, 0.22);
  color: #f2e2c8;
  font-family: inherit;
  font-size: 14px;
  letter-spacing: 0.03em;
  cursor: pointer;
  transition: background 0.18s ease, transform 0.18s ease;
}

.hero-add .admin-icon {
  color: #dcc096;
  font-size: 19px;
}

.hero-add:hover {
  background: linear-gradient(135deg, #4b3520, #382615);
  transform: translateY(-1px);
}

.hero-seal {
  position: absolute;
  top: 33px;
  right: 37px;
  z-index: 2;
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  transform: rotate(-3deg);
  border: 1.5px solid #a9513e;
  border-radius: 3px;
  background: rgba(169, 81, 62, 0.04);
  color: #a9513e;
  font-family: 'MuseAI Song', 'Noto Serif SC', serif;
  font-size: 17px;
  line-height: 1;
  opacity: 0.6;
}

/* ---------- Stat cards ---------- */
.exhibit-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-top: 16px;
}

.stat-card {
  position: relative;
  min-height: 112px;
  overflow: hidden;
  padding: 16px 19px 14px;
  border: 1px solid #ece2d3;
  border-radius: 10px;
  background: linear-gradient(135deg, #fefcf8 0%, #f9f4eb 100%);
  box-shadow: 0 4px 14px rgba(93, 67, 42, 0.04);
}

.stat-card::after {
  position: absolute;
  right: -24px;
  bottom: -38px;
  width: 190px;
  height: 168px;
  background: url('/admin/sidebar-art.webp') center / contain no-repeat;
  content: '';
  opacity: 0.9;
  pointer-events: none;
}

.stat-card > * {
  position: relative;
  z-index: 1;
}

.stat-head {
  display: flex;
  align-items: center;
  gap: 11px;
}

.stat-icon {
  display: grid;
  flex: 0 0 auto;
  width: 40px;
  height: 40px;
  place-items: center;
  border: 1px solid #e8d8c1;
  border-radius: 50%;
  background: #f3e8d7;
  color: #8a6136;
  font-size: 21px;
}

.stat-card.is-warn .stat-icon {
  border-color: #edd7ca;
  background: #f8e9e2;
  color: #a9573f;
}

.stat-label {
  color: #5f5142;
  font-size: 13px;
  letter-spacing: 0.03em;
}

.stat-action {
  margin-left: auto;
  padding: 2px 8px;
  border: 1px solid #dcc0a0;
  border-radius: 4px;
  background: transparent;
  color: #8a5a2f;
  font-family: inherit;
  font-size: 11px;
  cursor: pointer;
}

.stat-action:hover {
  background: #f3e7d6;
}

.stat-value {
  display: flex;
  align-items: baseline;
  gap: 5px;
  margin-top: 7px;
}

.stat-value strong {
  color: #2f261c;
  font-family: 'MuseAI Song', 'Noto Serif SC', 'Songti SC', SimSun, serif;
  font-size: clamp(32px, 2.6vw, 38px);
  font-weight: 500;
  letter-spacing: 0.01em;
  line-height: 1;
}

.stat-value em {
  color: #8d7c68;
  font-size: 11.5px;
  font-style: normal;
}

.stat-hint {
  margin: 6px 0 0;
  color: #a08c74;
  font-size: 11px;
  letter-spacing: 0.02em;
}

/* ---------- Alerts ---------- */
.data-alert {
  margin: 14px 0 0;
}

/* ---------- Toolbar ---------- */
.exhibit-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-top: 16px;
  padding: 12px 14px;
  border: 1px solid #ece4d7;
  border-radius: 10px;
  background: #fdfdfb;
  box-shadow: 0 2px 8px rgba(93, 67, 42, 0.03);
}

.search-field {
  display: flex;
  flex: 1 1 280px;
  align-items: center;
  gap: 9px;
  max-width: 430px;
  height: 38px;
  padding: 0 12px;
  border: 1px solid #eae2d6;
  border-radius: 6px;
  background: #ffffff;
  color: #b3a28e;
  font-size: 16px;
  cursor: text;
}

.search-field input {
  width: 100%;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: #3b3228;
  font-family: inherit;
  font-size: 13px;
}

.search-field input::placeholder {
  color: #a79684;
}

.search-field input::-webkit-search-cancel-button {
  display: none;
}

.exhibit-toolbar :deep(.el-select) {
  flex: 0 0 auto;
  width: 132px;
}

.exhibit-toolbar :deep(.el-select__wrapper) {
  background: #ffffff;
}

.reset-button {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 7px;
  height: 38px;
  margin-left: auto;
  padding: 0 16px;
  border: 1px solid #d9bd94;
  border-radius: 6px;
  background: #fffdf8;
  color: #8a5a2f;
  font-family: inherit;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.16s ease, border-color 0.16s ease;
}

.reset-button .admin-icon {
  font-size: 15px;
}

.reset-button:hover {
  border-color: #c3a071;
  background: #f8efe2;
}

/* ---------- Selection bar ---------- */
.selection-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
  padding: 9px 14px;
  border: 1px solid #e7d3b5;
  border-radius: 8px;
  background: #fbf3e6;
  color: #6f5537;
  font-size: 12.5px;
}

.selection-count {
  color: #7c4f2b;
  font-weight: 600;
}

.selection-target {
  color: #8b7358;
}

.selection-bar :deep(.el-button) {
  min-height: 28px;
  padding: 0 12px;
  font-size: 12px;
}

.selection-clear {
  margin-left: auto;
  padding: 0;
  border: 0;
  background: transparent;
  color: #9a7a52;
  font-family: inherit;
  font-size: 12px;
  cursor: pointer;
}

.selection-clear:hover {
  color: #7c4f2b;
  text-decoration: underline;
}

/* ---------- Table ---------- */
.exhibit-table-panel {
  position: relative;
  margin-top: 14px;
}

.table-scroll {
  overflow-x: auto;
  border-radius: 10px;
  scrollbar-width: thin;
}

.exhibit-table {
  width: 100%;
  min-width: 1010px;
  border-collapse: separate;
  border-spacing: 0;
  table-layout: fixed;
}

.exhibit-table col.col-check {
  width: 48px;
}

.exhibit-table col.col-name {
  width: auto;
}

.exhibit-table col.col-image {
  width: 118px;
}

.exhibit-table col.col-hall {
  width: 128px;
}

.exhibit-table col.col-category {
  width: 112px;
}

.exhibit-table col.col-era {
  width: 146px;
}

.exhibit-table col.col-rating {
  width: 138px;
}

.exhibit-table col.col-visit {
  width: 78px;
}

.exhibit-table col.col-actions {
  width: 92px;
}

.exhibit-table thead th {
  height: 48px;
  padding: 0 12px;
  border-top: 1px solid #ece3d6;
  border-bottom: 1px solid #ece3d6;
  background: #f3efe7;
  color: #6b5a47;
  font-size: 12.5px;
  font-weight: 500;
  letter-spacing: 0.04em;
  text-align: left;
  white-space: nowrap;
}

.exhibit-table thead th:first-child {
  border-left: 1px solid #ece3d6;
  border-top-left-radius: 10px;
}

.exhibit-table thead th:last-child {
  border-right: 1px solid #ece3d6;
  border-top-right-radius: 10px;
  text-align: right;
}

.exhibit-table tbody tr {
  background: #fbf9f5;
  transition: background 0.15s ease;
}

.exhibit-table tbody tr.is-selected {
  background: #fbf4e8;
}

.exhibit-table tbody tr:hover {
  background: #f9f4eb;
}

.exhibit-table tbody td {
  padding: 15px 12px;
  border-bottom: 1px solid #f1e9dd;
  color: #4a3d30;
  font-size: 13px;
  vertical-align: middle;
}

.exhibit-table tbody tr:last-child td {
  border-bottom: 0;
}

.exhibit-table tbody tr:last-child td:first-child {
  border-bottom-left-radius: 10px;
}

.exhibit-table tbody tr:last-child td:last-child {
  border-bottom-right-radius: 10px;
}

.cell-check {
  text-align: center;
}

.check {
  position: relative;
  display: inline-flex;
  width: 16px;
  height: 16px;
  cursor: pointer;
  vertical-align: middle;
}

.check input {
  position: absolute;
  width: 100%;
  height: 100%;
  margin: 0;
  opacity: 0;
  cursor: pointer;
}

.check-box {
  display: grid;
  width: 16px;
  height: 16px;
  place-items: center;
  border: 1px solid #d8cbb8;
  border-radius: 4px;
  background: #fffdfa;
  color: #ffffff;
  transition: background 0.15s ease, border-color 0.15s ease;
}

.check-box .admin-icon {
  font-size: 11px;
  opacity: 0;
  stroke-width: 2.3;
}

.check input:checked + .check-box {
  border-color: #8a5a2f;
  background: #8a5a2f;
}

.check input:checked + .check-box .admin-icon {
  opacity: 1;
}

.check input:focus-visible + .check-box {
  box-shadow: 0 0 0 3px rgba(185, 138, 87, 0.22);
}

.name-cell {
  display: flex;
  min-width: 0;
  align-items: flex-start;
  gap: 12px;
}

.artifact-tile {
  display: grid;
  flex: 0 0 auto;
  width: 46px;
  height: 46px;
  place-items: center;
  border: 1px solid #e5ddd0;
  border-radius: 9px;
  background: linear-gradient(145deg, #efede6, #e4e1d8);
  color: #786550;
  font-size: 27px;
}

.name-copy {
  min-width: 0;
  padding-top: 1px;
}

.exhibit-name {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  color: #332a20;
  font-size: 15.5px;
  font-weight: 600;
  letter-spacing: 0.01em;
  line-height: 1.45;
}

.badge {
  padding: 1px 5px;
  border: 1px solid #ead7bd;
  border-radius: 3px;
  background: #fbf1e2;
  color: #a47945;
  font-size: 10px;
  font-style: normal;
  font-weight: 400;
  letter-spacing: 0;
  line-height: 1.5;
}

.badge-warn {
  border-color: #ecc9c0;
  background: #fdf1ee;
  color: #b05f4f;
}

.exhibit-desc {
  display: -webkit-box;
  margin: 5px 0 0;
  overflow: hidden;
  color: #8b7a68;
  font-size: 12.5px;
  font-weight: 400;
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.image-thumb {
  display: grid;
  width: 96px;
  height: 62px;
  place-items: center;
  padding: 0;
  overflow: hidden;
  border: 1px solid #e9dfd1;
  border-radius: 7px;
  background: #f3ece1;
  color: #a58f76;
  cursor: pointer;
  transition: border-color 0.16s ease;
}

.image-thumb img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-thumb.is-empty {
  border-style: dashed;
  background: #fbf7ef;
}

.image-thumb:hover {
  border-color: #c8a97d;
}

.image-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  font-size: 16px;
}

.image-placeholder small {
  font-size: 10px;
  letter-spacing: 0.08em;
}

.hall-cell {
  display: grid;
  gap: 3px;
}

.hall-cell strong {
  overflow: hidden;
  color: #3b3025;
  font-size: 13px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hall-cell span {
  overflow: hidden;
  color: #a28d77;
  font-size: 11px;
  letter-spacing: 0.02em;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.category-tag {
  display: inline-block;
  padding: 3px 9px;
  border: 1px solid #efdfc9;
  border-radius: 4px;
  background: #fbf1e3;
  color: #9a6a3c;
  font-size: 11.5px;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.col-era {
  color: #5e5042;
  font-size: 12.5px;
  line-height: 1.7;
}

.stars {
  display: inline-flex;
  gap: 1px;
  color: #e3d8c6;
  font-size: 17px;
  line-height: 1;
}

.stars .admin-icon {
  fill: transparent;
  stroke-width: 1.2;
}

.stars .admin-icon.is-on {
  color: #c99a52;
  fill: currentColor;
}

.col-visit {
  color: #5f5142;
  font-size: 13px;
  white-space: nowrap;
}

.cell-actions {
  padding-right: 16px !important;
}

.row-actions {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: stretch;
}

.row-btn {
  height: 29px;
  padding: 0 9px;
  border: 1px solid #e6dbcb;
  border-radius: 5px;
  background: #fffdfa;
  color: #6d5a45;
  font-family: inherit;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}

.row-btn:hover {
  border-color: #c9ae88;
  background: #faf3e8;
  color: #5b3b22;
}

.row-btn--danger {
  border-color: #eccac2;
  color: #b35f4e;
}

.row-btn--danger:hover {
  border-color: #d99e92;
  background: #fdf1ee;
  color: #a04c3b;
}

.table-loading {
  position: absolute;
  inset: 0 0 34px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  border-radius: 10px;
  background: rgba(250, 246, 238, 0.76);
  color: #8b7a66;
  font-size: 12.5px;
  backdrop-filter: blur(1px);
}

.spinner {
  width: 26px;
  height: 26px;
  border: 2px solid #e6d8c4;
  border-top-color: #a97a45;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.table-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 9px;
  padding: 46px 20px;
  color: #a08c74;
}

.table-empty .admin-icon {
  color: #c7b396;
  font-size: 36px;
}

.table-empty p {
  margin: 0;
  font-size: 13px;
}

.table-empty button {
  padding: 0;
  border: 0;
  background: transparent;
  color: #8a5a2f;
  font-family: inherit;
  font-size: 12.5px;
  cursor: pointer;
}

.table-empty button:hover {
  text-decoration: underline;
}

.table-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 11px 4px 0;
  color: #a08c74;
  font-size: 11.5px;
  letter-spacing: 0.02em;
}

.refresh-link {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 0;
  border: 0;
  background: transparent;
  color: #a08c74;
  font-family: inherit;
  font-size: 11.5px;
  cursor: pointer;
}

.refresh-link .admin-icon {
  font-size: 13px;
}

.refresh-link:hover {
  color: #7c4f2b;
}

/* ---------- Image dialog ---------- */
.image-manager {
  display: grid;
  gap: 14px;
}

.image-preview {
  display: grid;
  min-height: 280px;
  place-items: center;
  padding: 16px;
  border: 1px solid #ece2d3;
  border-radius: 10px;
  background: #f8f3ea;
}

.image-preview img {
  display: block;
  max-width: 100%;
  max-height: 360px;
  border-radius: 8px;
  object-fit: contain;
}

.image-empty {
  color: #9a8575;
}

.image-info {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px;
  color: #2f261d;
}

.image-info span {
  color: #8a7565;
  font-size: 13px;
}

.image-hint {
  margin: 0;
  color: #7e6a59;
  font-size: 13px;
  line-height: 1.65;
}

.image-file-input {
  display: none;
}

.image-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

/* ---------- Responsive ---------- */
@media (max-width: 1180px) {
  .exhibit-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .exhibit-toolbar :deep(.el-select) {
    flex: 1 1 128px;
  }
}

@media (max-width: 1000px) {
  .search-field {
    flex-basis: 100%;
    max-width: none;
  }

  .reset-button {
    margin-left: 0;
  }
}

@media (max-width: 820px) {
  .exhibit-hero {
    aspect-ratio: auto;
    height: 196px;
    background-position: 22% 47%;
  }

  .hero-copy {
    max-width: 76%;
  }

  .hero-title {
    font-size: 25px;
  }

  .hero-desc {
    font-size: 12px;
  }

  .hero-add {
    right: 16px;
    bottom: 16px;
    height: 40px;
    padding: 0 16px 0 13px;
    font-size: 13px;
  }

  .hero-seal {
    display: none;
  }

  .exhibit-toolbar {
    padding: 11px;
  }
}

@media (max-width: 620px) {
  .exhibit-stats {
    grid-template-columns: 1fr;
  }

  .exhibit-hero {
    height: 178px;
  }

  .hero-desc {
    display: none;
  }

  .hero-rule {
    margin-top: 9px;
  }

  .stat-card {
    min-height: 102px;
  }

  .stat-value strong {
    font-size: 30px;
  }

  .exhibit-toolbar :deep(.el-select) {
    flex-basis: calc(50% - 5px);
  }

  .selection-clear {
    margin-left: 0;
  }
}
</style>
