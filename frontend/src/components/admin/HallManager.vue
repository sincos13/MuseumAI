<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../../api/index.js'
import { useMuseumProfile } from '../../composables/useMuseumProfile.js'
import { useHallDirectory } from '../../composables/useHallDirectory.js'
import { normalizeHallRecords, normalizeHallSlug } from '../../utils/halls.js'

const { museum } = useMuseumProfile()
const { fetchHalls: refreshPublicHalls } = useHallDirectory()
const halls = ref([])
const fetchLoading = ref(false)
const loading = ref(false)
const fetchError = ref('')
const dialogVisible = ref(false)
const editingSlug = ref(null)
const formRef = ref(null)
const emptyForm = () => ({ slug: '', name: '', description: '', short_description: '', floor: 1,
  estimated_duration_minutes: 20, display_order: 10, is_active: true,
  is_temporary: false, aliasesText: '' })
const form = ref(emptyForm())
const rules = {
  slug: [{ required: true, message: '请输入展厅标识', trigger: 'blur' },
    { validator: (_, value, callback) => normalizeHallSlug(value) === value
      ? callback() : callback(new Error('使用小写英文字母、数字和单个连字符，最长 100 字符')), trigger: 'blur' }],
  name: [{ required: true, whitespace: true, message: '请输入展厅名称', trigger: 'blur' }],
}
const activeCount = computed(() => halls.value.filter((hall) => hall.is_active).length)
const temporaryCount = computed(() => halls.value.filter((hall) => hall.is_temporary).length)

async function fetchHalls() {
  fetchLoading.value = true
  fetchError.value = ''
  try {
    const result = await api.admin.listHalls({ include_inactive: 'true' })
    if (!result?.ok) throw new Error(typeof result?.data?.detail === 'string' ? result.data.detail : '获取展厅失败')
    halls.value = normalizeHallRecords(result.data.halls || [], { includeInactive: true })
  } catch (err) {
    halls.value = []
    fetchError.value = err.message || '获取展厅失败'
  } finally {
    fetchLoading.value = false
  }
}
function handleAdd() {
  editingSlug.value = null
  form.value = emptyForm()
  dialogVisible.value = true
}
function handleEdit(row) {
  editingSlug.value = row.slug
  form.value = { ...emptyForm(), ...row, aliasesText: (row.aliases || []).join('\n') }
  dialogVisible.value = true
}
function errorMessage(result) {
  const detail = result?.data?.detail
  return typeof detail === 'string' ? detail : '保存失败，请检查展厅标识、名称和别名是否重复，或字段是否超出范围'
}
async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    const data = form.value
    const payload = {
      name: data.name.trim(), description: data.description.trim(),
      short_description: (data.short_description || '').trim(), floor: data.floor,
      estimated_duration_minutes: data.estimated_duration_minutes, display_order: data.display_order,
      is_active: data.is_active, is_temporary: data.is_temporary,
      aliases: [...new Set(data.aliasesText.split(/\r?\n/).map((value) => value.trim()).filter(Boolean))],
    }
    const result = editingSlug.value
      ? await api.admin.updateHall(editingSlug.value, payload)
      : await api.admin.createHall({ slug: data.slug, ...payload })
    if (!result?.ok) { ElMessage.error(errorMessage(result)); return }
    ElMessage.success('展厅已保存')
    dialogVisible.value = false
    await Promise.all([fetchHalls(), refreshPublicHalls()])
  } catch {
    ElMessage.error('保存失败，请检查网络后重试')
  } finally {
    loading.value = false
  }
}
onMounted(fetchHalls)
</script>

<template>
  <div class="hall-manager">
    <header class="admin-hero">
      <div>
        <span class="kicker">展厅目录</span>
        <h2>{{ museum.short_name || museum.name }}展厅设置</h2>
        <p>维护本馆展厅名称、顺序和开放状态。保存后游客刷新页面即可看到最新目录。关闭展厅会停止新的导览访问，历史参观记录保留。</p>
      </div>
      <div class="hero-actions">
        <el-button :loading="fetchLoading" @click="fetchHalls">刷新</el-button>
        <el-button type="primary" data-testid="add-hall" @click="handleAdd">新增展厅</el-button>
      </div>
    </header>
    <section class="stat-grid">
      <div class="stat-card"><span>展厅总数</span><strong>{{ halls.length }}</strong></div>
      <div class="stat-card"><span>当前开放</span><strong>{{ activeCount }}</strong></div>
      <div class="stat-card"><span>临时展厅</span><strong>{{ temporaryCount }}</strong></div>
      <div class="stat-card"><span>已关闭</span><strong>{{ halls.length - activeCount }}</strong></div>
    </section>
    <el-alert v-if="fetchError" :title="fetchError" type="error" :closable="false" />
    <el-table :data="halls" row-key="slug" v-loading="fetchLoading" class="contract-table" empty-text="暂无展厅，请新增展厅或导入馆藏资料">
      <el-table-column label="展厅" min-width="280">
        <template #default="{ row }">
          <div class="hall-cell"><span class="hall-icon">{{ row.icon }}</span><div>
            <div class="hall-name">{{ row.name }}</div><div class="hall-desc">{{ row.description }}</div>
            <div class="hall-tags"><el-tag size="small" effect="plain">{{ row.type }}</el-tag>
              <span v-if="row.aliases.length">别名：{{ row.aliases.join('、') }}</span></div>
          </div></div>
        </template>
      </el-table-column>
      <el-table-column prop="slug" label="展厅标识" min-width="180" />
      <el-table-column prop="floor" label="楼层" width="80" />
      <el-table-column prop="estimated_duration_minutes" label="建议时长" width="110"><template #default="{ row }">{{ row.estimated_duration_minutes }} 分钟</template></el-table-column>
      <el-table-column prop="display_order" label="排序" width="80" />
      <el-table-column label="状态" width="100"><template #default="{ row }"><el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '开放' : '已关闭' }}</el-tag></template></el-table-column>
      <el-table-column label="操作" width="100"><template #default="{ row }"><el-button size="small" @click="handleEdit(row)">编辑</el-button></template></el-table-column>
    </el-table>
    <el-dialog v-model="dialogVisible" :title="editingSlug ? '编辑展厅' : '新增展厅'" width="640px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
        <el-form-item label="展厅标识" prop="slug"><el-input v-model="form.slug" :disabled="Boolean(editingSlug)" maxlength="100" placeholder="例如 history-hall-10" /></el-form-item>
        <el-form-item label="展厅名称" prop="name"><el-input v-model="form.name" maxlength="200" /></el-form-item>
        <el-form-item label="卡片简介"><el-input v-model="form.short_description" maxlength="48" show-word-limit placeholder="最多 48 字，用于展厅卡片概览" /></el-form-item>
        <el-form-item label="别名"><el-input v-model="form.aliasesText" type="textarea" :rows="2" placeholder="每行一个，用于匹配资料中的旧名或简称" /></el-form-item>
        <el-form-item label="简介"><el-input v-model="form.description" type="textarea" :rows="3" /></el-form-item>
        <el-row :gutter="16"><el-col :span="12"><el-form-item label="楼层"><el-input-number v-model="form.floor" :min="1" :max="10" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="建议时长"><el-input-number v-model="form.estimated_duration_minutes" :min="0" :max="480" /></el-form-item></el-col></el-row>
        <el-form-item label="排序"><el-input-number v-model="form.display_order" :min="0" :max="100000" /></el-form-item>
        <el-form-item label="临时展厅"><el-switch v-model="form.is_temporary" /></el-form-item>
        <el-form-item label="开放"><el-switch v-model="form.is_active" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" :loading="loading" @click="handleSubmit">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.hall-manager {
  min-height: 100%;
  padding: 28px 34px 52px;
  background: linear-gradient(180deg, #fffdf9 0%, #f8f2ea 100%);
}

.admin-hero {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 20px;
  padding: 24px;
  border: 1px solid rgba(126, 91, 65, 0.16);
  border-radius: 16px;
  background: #fffaf3;
  box-shadow: 0 14px 36px rgba(77, 49, 31, 0.07);
}

.kicker {
  color: #c57548;
  font-size: 13px;
  font-weight: 700;
}

.admin-hero h2 {
  margin: 8px 0;
  color: #2f2118;
  font-size: 28px;
}

.admin-hero p {
  max-width: 720px;
  margin: 0;
  color: #7e6a59;
  line-height: 1.7;
}

.hero-actions {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  white-space: nowrap;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.stat-card {
  padding: 18px;
  border: 1px solid rgba(126, 91, 65, 0.14);
  border-radius: 14px;
  background: rgba(255, 252, 247, 0.9);
}

.stat-card span {
  color: #957c67;
  font-size: 13px;
}

.stat-card strong {
  display: block;
  margin-top: 8px;
  color: #35261c;
  font-size: 28px;
}

.stat-card.warn strong {
  color: #b66c45;
}

.legacy-alert {
  margin-bottom: 18px;
}

.legacy-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
}

.contract-table {
  border-radius: 12px;
  overflow: hidden;
}

.hall-cell {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}

.hall-icon {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 10px;
  background: #f1e4d4;
  font-size: 22px;
  flex: 0 0 auto;
}

.hall-name {
  color: #2f2118;
  font-weight: 700;
}

.hall-desc {
  margin-top: 4px;
  color: #7b6758;
  line-height: 1.5;
}

.hall-tags {
  display: flex;
  gap: 6px;
  margin-top: 8px;
}

@media (max-width: 960px) {
  .admin-hero {
    flex-direction: column;
  }

  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
