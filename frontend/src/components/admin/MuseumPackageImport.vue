<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { api } from '../../api/index.js'
const job = ref(null), error = ref(''), busy = ref(false), status = ref(null)
let timer = null
const progress = computed(() => job.value?.total ? Math.floor(100 * job.value.completed / job.value.total) : 0)
function message(result) {
  error.value = typeof result?.data?.detail === 'string' ? result.data.detail : '操作失败，请检查网络后重试。'
}
async function upload(event) {
  const file = event.target.files?.[0]
  if (!file) return
  busy.value = true
  error.value = ''
  clearTimeout(timer)
  try {
    const result = await api.admin.packages.preview(file)
    if (!result.ok) { message(result); return }
    job.value = result.data
    localStorage.setItem('museum_import_job', job.value.id)
  } finally { busy.value = false; event.target.value = '' }
}
async function refresh() {
  if (!job.value?.id) return
  const result = await api.admin.packages.progress(job.value.id)
  if (!result.ok) { message(result); return }
  job.value = result.data
  if (job.value.status === 'running' || job.value.status === 'queued') timer = setTimeout(refresh, 2000)
}
async function confirm() {
  busy.value = true
  error.value = ''
  const result = await api.admin.packages.confirm(job.value.id)
  busy.value = false
  if (!result.ok) { message(result); return }
  if (result.data.status === 'completed') job.value = result.data
  else { job.value.status = 'queued'; job.value.message = '导入请求已提交…'; timer = setTimeout(refresh, 1000) }
}
onMounted(async () => {
  const result = await api.museum.importStatus()
  if (result.ok) status.value = result.data
  const id = localStorage.getItem('museum_import_job')
  if (id) { job.value = { id }; await refresh() }
})
onUnmounted(() => clearTimeout(timer))
</script>
<template>
  <main class="import-page">
    <header><p>馆方资料接入</p><h1>从资料包开始，建立你的博物馆导览</h1>
      <div>上传 → 校验预览 → 确认导入 → 建立索引 → 游客体验</div>
    </header>
    <el-alert v-if="status?.self_service === false" title="当前实例使用已有馆藏。请在空白馆实例中首次导入，日常更新使用知识库、展厅与展品管理。" type="info" :closable="false" />
    <section class="card">
      <h2>1. 上传标准资料包</h2>
      <p>ZIP 包括馆方基本信息、展厅与展品目录、讲解文档、图片对应关系，以及整理好的问卷、导览身份、路线和引导话题。无需修改代码或重启服务。</p>
      <p class="muted">原始 Word、PDF 和图片先整理成标准包。已有馆藏的日常补充，可在“知识库管理”和“展品管理”中单独维护。</p>
      <label class="upload-button" :class="{ disabled: busy || job?.status === 'running' || job?.status === 'queued' }">
        {{ busy ? '正在读取和校验…' : '选择资料包 ZIP（最大 100 MB）' }}
        <input type="file" accept=".zip" :disabled="busy || job?.status === 'running' || job?.status === 'queued'" @change="upload" />
      </label>
    </section>
    <el-alert v-if="error" :title="error" type="error" :closable="false" />
    <section v-if="job?.museum_name" class="card">
      <h2>2. 核对导入内容</h2><h3>{{ job.museum_name }}</h3>
      <div class="counts">
        <span>{{ job.halls.length }} 个展厅</span><span>{{ job.exhibits.length }} 件展品</span>
        <span>{{ job.documents.length }} 份知识文档</span><span>{{ job.image_count }} 张图片</span><span>{{ job.route_count }} 条路线模板</span>
      </div>
      <details><summary>查看展厅和展品目录</summary><div v-for="hall in job.halls" :key="hall.slug">
        <h4>{{ hall.name }}</h4><p>{{ job.exhibits.filter(e => e.hall === hall.slug).map(e => e.id + ' ' + e.name).join('；') }}</p>
      </div></details>
      <details><summary>查看知识文档与来源</summary><ul><li v-for="(doc, i) in job.documents" :key="i">{{ doc.title }} · {{ doc.source_label }}</li></ul></details>
      <p class="muted">预览通过后才写入本馆。首次导入绑定当前资料包；重复操作可继续未完成的索引，不会重复创建展品。导入后的内容可在后台逐项维护。</p>
      <el-button v-if="job.status === 'preview' || job.status === 'failed'" type="primary" :loading="busy" @click="confirm">{{ job.status === 'failed' ? '重试未完成的导入' : '确认导入本馆' }}</el-button>
    </section>
    <section v-if="job && job.status !== 'preview' && job.museum_name" class="card">
      <h2>3. 导入与索引进度</h2><p role="status">{{ job.message }}</p>
      <el-progress :percentage="progress" :status="job.status === 'failed' ? 'exception' : job.status === 'completed' ? 'success' : undefined" />
      <p>{{ job.completed }} / {{ job.total }} 份知识文档完成</p>
      <el-button v-if="job.status === 'running' || job.status === 'queued'" @click="refresh">刷新进度</el-button>
      <el-button v-if="job.status === 'running' || job.status === 'queued'" text @click="confirm">服务重启后继续导入</el-button>
      <div v-if="job.status === 'completed'" class="actions">
        <a class="link" href="/tour" target="_blank" rel="noopener">进入游客导览 →</a>
        <a class="link" href="/admin/documents">查看和维护知识库</a>
        <a class="link" href="/admin/museum">查看导入后的馆方配置</a>
      </div>
    </section>
  </main>
</template>
<style scoped>
.import-page{padding:32px;max-width:1100px;margin:auto;color:#25362e}header{margin-bottom:24px}header>p{color:#97613d;font-weight:700}h1{font-size:28px;line-height:1.6}header div{color:#62786b}.card{padding:28px;background:white;border:1px solid #dce5df;border-radius:16px;margin:20px 0}.card h2{font-size:20px;margin:0 0 16px}.card p{line-height:1.8}.muted{color:#64766b;font-size:13px}.counts{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0}.counts span{padding:10px 14px;background:#eef5f0;border-radius:8px}.upload-button{display:inline-block;background:#456d59;color:white;border-radius:8px;padding:14px 20px;cursor:pointer}.upload-button input{display:block;margin-top:10px;max-width:100%}.disabled{opacity:.5}details{padding:16px 0;border-top:1px solid #e5ebe6}summary{cursor:pointer;font-weight:600}li{line-height:1.9;font-size:13px}.actions{display:flex;gap:24px;flex-wrap:wrap;margin-top:24px}.link{color:#456d59;font-weight:600}@media(max-width:600px){.import-page{padding:16px}.card{padding:18px}h1{font-size:23px}}
</style>
