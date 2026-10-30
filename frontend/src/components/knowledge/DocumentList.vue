<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { useDocuments, documentErrorMessage } from '../../composables/useDocuments.js'
import { useAuth } from '../../composables/useAuth.js'
import { useHallDirectory } from '../../composables/useHallDirectory.js'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, Delete } from '@element-plus/icons-vue'

const { documents, loading, error, total, page, pageSize, fetchDocuments, deleteDocument,
  getDocument, getDocumentStatus, updateDocument, reindexDocument } = useDocuments()
const { isAdmin } = useAuth()
const { halls, getHallDisplayName } = useHallDirectory()
const tableRef = ref(null)
const selectedRows = ref([])
const batchDeleting = ref(false)
const actionId = ref(null)
const dialogVisible = ref(false)
const saving = ref(false)
const editing = ref(null)
const editForm = ref({ title: '', source_label: '', source_url: '', hall_slug: '', content_text: '' })
let pollTimer
let active = true
const statusMap = {
  pending: { type: 'warning', text: '等待索引' },
  processing: { type: 'warning', text: '索引中' },
  completed: { type: 'success', text: '索引完成' },
  failed: { type: 'danger', text: '索引失败' },
}
function isProcessing(doc) { return ['pending', 'processing'].includes(doc.status) }
function handleSelectionChange(selection) { selectedRows.value = selection }
async function refresh() { await fetchDocuments() }
async function changePage(value) {
  selectedRows.value = []
  tableRef.value?.clearSelection()
  await fetchDocuments({ page: value })
}
async function handleDelete(doc) {
  try {
    await ElMessageBox.confirm('确定删除此文档？此操作无法恢复，请先保留原始文件。', '确认删除', { type: 'warning' })
  } catch { return }
  const result = await deleteDocument(doc.id)
  if (result.ok) {
    ElMessage.success('删除成功')
    selectedRows.value = selectedRows.value.filter(item => item.id !== doc.id)
    await refresh()
  } else ElMessage.error(documentErrorMessage(result, '删除失败'))
}
async function handleBatchDelete() {
  if (!selectedRows.value.length) return
  try {
    await ElMessageBox.confirm(`确定删除已选中的 ${selectedRows.value.length} 个文档吗？此操作无法恢复，请先保留原始文件。`, '批量删除确认', { type: 'warning' })
  } catch { return }
  batchDeleting.value = true
  try {
    let successCount = 0
    let failedCount = 0
    for (const doc of [...selectedRows.value]) {
      const result = await deleteDocument(doc.id)
      if (result.ok) successCount += 1
      else failedCount += 1
    }
    selectedRows.value = []
    tableRef.value?.clearSelection()
    if (!failedCount) ElMessage.success(`批量删除成功，共删除 ${successCount} 个文档`)
    else ElMessage.warning(`已删除 ${successCount} 个文档，${failedCount} 个删除失败`)
    await refresh()
  } finally { batchDeleting.value = false }
}
async function handleViewStatus(doc) {
  const result = await getDocumentStatus(doc.id)
  if (!result.ok) { ElMessage.error(documentErrorMessage(result, '获取状态失败')); return }
  const data = result.data
  ElMessageBox.alert(`索引状态：${statusMap[data.status]?.text || data.status}；分块数：${data.chunk_count ?? '待生成'}${data.error ? `；失败原因：${data.error}` : ''}`, '文档索引状态')
}
async function handleEdit(doc) {
  actionId.value = doc.id
  try {
    const result = await getDocument(doc.id)
    if (!result.ok) { ElMessage.error(documentErrorMessage(result, '读取文档失败')); return }
    editing.value = result.data
    editForm.value = {
      title: result.data.title || '', source_label: result.data.source_label || '',
      source_url: result.data.source_url || '', hall_slug: result.data.hall_slug || '',
      content_text: result.data.content_text ?? '',
    }
    dialogVisible.value = true
  } finally { actionId.value = null }
}
async function saveEdit() {
  saving.value = true
  try {
    const value = editForm.value
    const data = { title: value.title.trim(), source_label: value.source_label.trim(),
      source_url: value.source_url.trim(), hall_slug: value.hall_slug || null }
    if (editing.value.content_text != null && value.content_text !== editing.value.content_text) {
      if (!value.content_text.trim()) { ElMessage.warning('正文不能为空'); return }
      data.content_text = value.content_text
    }
    const result = await updateDocument(editing.value.id, data)
    if (!result.ok) { ElMessage.error(documentErrorMessage(result, '保存失败')); return }
    ElMessage.success('资料已保存；正文修改会自动重新索引，完成后用于问答')
    dialogVisible.value = false
  } finally { saving.value = false }
}
async function handleReindex(doc) {
  actionId.value = doc.id
  try {
    const result = await reindexDocument(doc.id)
    if (!result.ok) { ElMessage.error(documentErrorMessage(result, '操作失败')); return }
    ElMessage.success('已提交重新索引，完成后自动用于问答')
  } finally { actionId.value = null }
}
function schedulePoll() {
  if (!active) return
  pollTimer = setTimeout(async () => {
    if (!loading.value && documents.value.some(isProcessing)) await refresh()
    schedulePoll()
  }, 3000)
}
onMounted(() => { fetchDocuments(); schedulePoll() })
onUnmounted(() => { active = false; clearTimeout(pollTimer) })
</script>

<template>
  <div class="document-list">
    <el-alert v-if="error" :title="error" type="error" :closable="false" />
    <div class="toolbar">
      <span class="selection-meta">共 {{ total }} 份资料<span v-if="isAdmin"> · 已选 {{ selectedRows.length }} 项</span></span>
      <div class="toolbar-actions"><el-button :loading="loading" @click="refresh">刷新</el-button>
        <el-button v-if="isAdmin" type="danger" plain :loading="batchDeleting"
          :disabled="batchDeleting || loading || !selectedRows.length" @click="handleBatchDelete">批量删除</el-button></div>
    </div>
    <p class="help-text">资料索引完成后即可参与问答。修改正文会自动重新索引；标题、来源和关联展厅可直接维护。</p>
    <el-table v-if="documents.length" ref="tableRef" :data="documents" row-key="id" v-loading="loading" border @selection-change="handleSelectionChange">
      <el-table-column v-if="isAdmin" type="selection" width="50" reserve-selection />
      <el-table-column label="资料与来源" min-width="270"><template #default="{ row }">
        <div class="filename-cell"><el-icon><Document /></el-icon><strong>{{ row.title || row.filename }}</strong></div>
        <div class="secondary">{{ row.filename }}</div><div class="source-text">{{ row.source_label || '尚未填写馆方来源' }}</div>
        <div class="secondary">关联展厅：{{ row.hall_slug ? getHallDisplayName(row.hall_slug) : '全馆通用' }}</div>
      </template></el-table-column>
      <el-table-column label="索引状态" width="150"><template #default="{ row }">
        <div class="status-stack"><el-tag :type="statusMap[row.status]?.type || 'info'" size="small">{{ statusMap[row.status]?.text || row.status }}</el-tag>
          <span class="secondary">版本 {{ row.revision ?? '—' }} / 已索引 {{ row.indexed_revision ?? '—' }}</span></div>
        <div v-if="row.error" class="error-text">{{ row.error }}</div>
      </template></el-table-column>
      <el-table-column label="上传时间" min-width="165"><template #default="{ row }">{{ new Date(row.created_at).toLocaleString('zh-CN') }}</template></el-table-column>
      <el-table-column label="操作" width="270" fixed="right"><template #default="{ row }">
        <div class="row-actions">
          <el-button size="small" :disabled="actionId === row.id || isProcessing(row)" @click="handleEdit(row)">查看 / 编辑</el-button>
          <el-button size="small" @click="handleViewStatus(row)">状态</el-button>
          <template v-if="isAdmin">
            <el-button size="small" :disabled="isProcessing(row) || actionId === row.id" @click="handleReindex(row)">重建索引</el-button>
            <el-button type="danger" size="small" :icon="Delete" :disabled="batchDeleting" @click="handleDelete(row)">删除</el-button>
          </template>
        </div>
      </template></el-table-column>
    </el-table>
    <div v-else-if="loading" class="table-state">加载中…</div><div v-else class="table-state">暂无文档，请先上传本馆资料</div>
    <el-pagination v-if="total > pageSize" :current-page="page" :page-size="pageSize" :total="total"
      :disabled="loading" layout="prev, pager, next, total" @current-change="changePage" />
    <el-dialog v-model="dialogVisible" title="核对 / 编辑馆方资料" width="min(850px, 94vw)" :close-on-click-modal="false">
      <el-alert title="修改正文后会自动重新索引；完成后即可参与问答，无需额外发布。" type="warning" :closable="false" />
      <el-form :model="editForm" label-width="100px" :disabled="saving" class="edit-form">
        <el-form-item label="资料标题"><el-input v-model="editForm.title" maxlength="200" /></el-form-item>
        <el-form-item label="馆方来源"><el-input v-model="editForm.source_label" maxlength="500" /></el-form-item>
        <el-form-item label="来源链接"><el-input v-model="editForm.source_url" maxlength="2000" /></el-form-item>
        <el-form-item label="关联展厅"><el-select v-model="editForm.hall_slug" class="scope-select"><el-option label="全馆通用" value="" /><el-option v-for="hall in halls" :key="hall.slug" :label="hall.name" :value="hall.slug" /><el-option v-if="editForm.hall_slug && !halls.some(hall => hall.slug === editForm.hall_slug)" :label="`${editForm.hall_slug}（已关闭或不存在）`" :value="editForm.hall_slug" /></el-select></el-form-item>
        <el-form-item label="资料正文"><el-input v-model="editForm.content_text" type="textarea" :rows="14" :disabled="editing?.content_text == null" /></el-form-item>
      </el-form>
      <el-alert v-if="editing?.content_text == null" title="这份旧资料未保留可编辑正文。请重新上传原始文件，索引完成后再删除旧资料。" type="warning" :closable="false" />
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button v-if="isAdmin" type="primary" :loading="saving" @click="saveEdit">保存修改</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.document-list { display: flex; flex-direction: column; gap: 12px; }
.toolbar, .toolbar-actions { display: flex; align-items: center; gap: 12px; }
.toolbar { justify-content: space-between; flex-wrap: wrap; }
.selection-meta, .help-text, .source-text { color: var(--el-text-color-regular); font-size: 13px; }
.help-text { margin: 0; line-height: 1.7; }
.filename-cell { display: flex; align-items: center; gap: 6px; overflow-wrap: anywhere; }
.secondary { color: var(--el-text-color-secondary); font-size: 12px; line-height: 1.8; overflow-wrap: anywhere; }
.source-text { margin-top: 6px; overflow-wrap: anywhere; }
.status-stack { display: flex; flex-direction: column; align-items: flex-start; gap: 6px; }
.error-text { color: var(--el-color-danger); font-size: 12px; margin-top: 8px; overflow-wrap: anywhere; }
.row-actions { display: flex; gap: 6px; flex-wrap: wrap; }
.row-actions .el-button { margin-left: 0; }
.table-state { text-align: center; color: var(--el-text-color-secondary); padding: 20px 0; }
.edit-form { margin-top: 16px; }
.scope-select { width: 100%; }
</style>
