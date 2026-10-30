<script setup>
import { onMounted, ref } from 'vue'
import { useDocuments, documentErrorMessage } from '../../composables/useDocuments.js'
import { useAuth } from '../../composables/useAuth.js'
import { useHallDirectory } from '../../composables/useHallDirectory.js'
import { ElMessage } from 'element-plus'
import { UploadFilled, Lock } from '@element-plus/icons-vue'

const { uploadDocument } = useDocuments()
const { isAdmin, isAuthenticated } = useAuth()
const { halls, hallsError, fetchHalls } = useHallDirectory()
const uploadRef = ref(null)
const uploading = ref(false)
const metadata = ref({ title: '', source_label: '', source_url: '', hall_slug: '' })

async function handleUpload(options) {
  if (uploading.value) return
  if (options.file.size > 50 * 1024 * 1024) {
    ElMessage.warning('文件不能超过 50MB')
    uploadRef.value?.clearFiles()
    return
  }
  uploading.value = true
  try {
    const result = await uploadDocument(options.file, {
      title: metadata.value.title.trim(), source_label: metadata.value.source_label.trim(),
      source_url: metadata.value.source_url.trim(), hall_slug: metadata.value.hall_slug || null,
    })
    if (result.ok) {
      ElMessage.success('上传成功，索引完成后即可用于问答')
      metadata.value.title = ''
    } else {
      ElMessage.error(documentErrorMessage(result, '上传失败'))
    }
  } finally {
    uploading.value = false
    uploadRef.value?.clearFiles()
  }
}

onMounted(() => { if (isAdmin.value) fetchHalls() })
</script>

<template>
  <div class="upload-panel">
    <template v-if="isAdmin">
      <el-alert title="上传 UTF-8 TXT 或 Markdown 资料，索引完成后即可参与问答，无需手动发布。" type="info" :closable="false" />
      <el-form :model="metadata" label-width="100px" :disabled="uploading">
        <el-form-item label="资料标题"><el-input v-model="metadata.title" maxlength="200" placeholder="例如：古代陶器展厅官方讲解词" /></el-form-item>
        <el-form-item label="馆方来源"><el-input v-model="metadata.source_label" maxlength="500" placeholder="例如：本馆藏品部审核，2026 年展厅讲解手册第 3 页" /></el-form-item>
        <el-form-item label="来源链接"><el-input v-model="metadata.source_url" maxlength="2000" placeholder="可选，填写官方网页的 http:// 或 https:// 地址" /></el-form-item>
        <el-form-item label="关联展厅">
          <el-select v-model="metadata.hall_slug" placeholder="全馆通用" class="scope-select">
            <el-option label="全馆通用" value="" />
            <el-option v-for="hall in halls" :key="hall.slug" :label="hall.name" :value="hall.slug" />
          </el-select>
        </el-form-item>
      </el-form>
      <el-alert v-if="hallsError" :title="`${hallsError}；可上传全馆资料，或刷新页面后选择展厅`" type="warning" :closable="false" />
      <el-upload ref="uploadRef" :auto-upload="true" :show-file-list="false" :limit="1"
        :disabled="uploading" :http-request="handleUpload" accept=".txt,.md,.markdown" drag>
        <el-icon class="upload-icon"><UploadFilled /></el-icon>
        <div>{{ uploading ? '正在上传，请稍候…' : '拖入文件或点击选择文件，标题和来源可选填' }}</div>
        <template #tip><div class="upload-tip">支持 .txt、.md、.markdown，UTF-8 编码，最大 50MB。扫描图片或 PDF 请先转成可核对的文字。</div></template>
      </el-upload>
    </template>
    <div v-else class="access-hint"><el-icon><Lock /></el-icon><div>仅管理员可上传文档</div><small v-if="!isAuthenticated">请先登录</small></div>
  </div>
</template>

<style scoped>
.upload-panel { padding: 8px; display: flex; flex-direction: column; gap: 16px; }
.scope-select { width: 100%; }
.upload-icon { font-size: 48px; color: var(--el-text-color-secondary); margin-bottom: 12px; }
.upload-tip { color: var(--el-text-color-secondary); font-size: 12px; line-height: 1.7; }
.access-hint { text-align: center; padding: 32px; color: var(--el-text-color-secondary); }
</style>
