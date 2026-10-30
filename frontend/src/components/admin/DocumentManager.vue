<script setup>
import { ref } from 'vue'
import DocumentUpload from '../knowledge/DocumentUpload.vue'
import DocumentList from '../knowledge/DocumentList.vue'
import { useDocuments, documentErrorMessage } from '../../composables/useDocuments.js'
import { useHallDirectory } from '../../composables/useHallDirectory.js'

const { searchPreview } = useDocuments()
const { halls, getHallDisplayName } = useHallDirectory()
const query = ref('')
const hallSlug = ref('')
const previewLoading = ref(false)
const previewError = ref('')
const previewSources = ref([])
const searched = ref(false)
async function runPreview() {
  if (!query.value.trim()) { previewError.value = '请先输入游客可能会问的问题'; return }
  previewLoading.value = true
  previewError.value = ''
  previewSources.value = []
  searched.value = false
  try {
    const result = await searchPreview({ query: query.value.trim(), hall_slug: hallSlug.value || null })
    if (!result.ok) { previewError.value = documentErrorMessage(result, '检索失败，请检查索引和模型服务后重试'); return }
    previewSources.value = result.data.sources || []
    searched.value = true
  } finally { previewLoading.value = false }
}
function safeSourceUrl(value) {
  try { const url = new URL(value); return ['http:', 'https:'].includes(url.protocol) ? url.href : null } catch { return null }
}
</script>

<template>
  <div class="document-manager">
    <div class="header">
      <h2>馆方知识库管理</h2>
      <p>上传本馆资料，索引完成后即可参与问答。馆藏信息仍在“展品管理”中维护。</p>
    </div>
    <el-alert title="请核对上传资料的准确性，并在游客导览中检查实际回答效果。" type="warning" :closable="false" />
    <el-card shadow="never" class="upload-card"><template #header><span>1. 上传馆方资料</span></template><DocumentUpload /></el-card>
    <el-card shadow="never" class="list-card"><template #header><span>2. 查看、编辑与维护</span></template><DocumentList /></el-card>
    <el-card shadow="never" class="preview-card">
      <template #header><span>3. 检索预览</span></template>
      <p class="preview-help">输入游客可能会问的问题，检查系统能找到哪些已索引资料和馆藏信息。这里展示检索依据，不生成 AI 回答；实际讲解还需到游客导览中验收。选择展厅时沿用导览的展品关联校验；修改资料后请重新预览。</p>
      <el-form @submit.prevent="runPreview" label-width="90px">
        <el-form-item label="游客问题"><el-input v-model="query" maxlength="1000" placeholder="例如：这件陶器有什么用途？" @keyup.enter="runPreview" /></el-form-item>
        <el-form-item label="导览展厅"><el-select v-model="hallSlug" class="scope-select"><el-option label="全馆检索" value="" /><el-option v-for="hall in halls" :key="hall.slug" :label="hall.name" :value="hall.slug" /></el-select></el-form-item>
        <el-form-item><el-button type="primary" :loading="previewLoading" @click="runPreview">检索知识库</el-button></el-form-item>
      </el-form>
      <el-alert v-if="previewError" :title="previewError" type="error" :closable="false" />
      <el-empty v-else-if="searched && !previewSources.length" description="没有找到相关资料。请检查索引状态、尝试其他问法或补充资料。" />
      <div v-for="(source, index) in previewSources" :key="`${source.source_id}-${index}`" class="preview-source">
        <strong>{{ source.title || '未命名资料' }}</strong>
        <span class="source-scope">{{ source.hall_slug ? getHallDisplayName(source.hall_slug) : '全馆通用' }}</span>
        <p class="source-label">来源：{{ source.source_label || '馆藏记录' }}</p>
        <a v-if="safeSourceUrl(source.source_url)" :href="safeSourceUrl(source.source_url)" target="_blank" rel="noopener noreferrer">查看官方来源</a>
        <p class="source-content">{{ source.content }}</p>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.document-manager { padding: 20px; display: flex; flex-direction: column; gap: 16px; }
.header h2 { margin: 0; font-size: 20px; color: var(--el-text-color-primary); }
.header p, .preview-help { margin: 8px 0 16px; color: var(--el-text-color-regular); font-size: 14px; line-height: 1.8; }
.upload-card, .list-card, .preview-card { border: 1px solid var(--el-border-color-lighter); }
.scope-select { width: 100%; }
.preview-source { border: 1px solid var(--el-border-color-lighter); border-radius: 6px; padding: 16px; margin-top: 12px; overflow-wrap: anywhere; }
.source-scope { color: var(--el-text-color-secondary); font-size: 12px; margin-left: 12px; }
.source-label { margin: 8px 0; color: var(--el-text-color-regular); font-size: 13px; }
.source-content { margin-bottom: 0; white-space: pre-wrap; font-size: 14px; line-height: 1.8; }
</style>
