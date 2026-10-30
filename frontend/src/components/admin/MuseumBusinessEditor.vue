<script setup>
import { computed, reactive, ref } from 'vue'
import BusinessJsonField from './BusinessJsonField.vue'
const props = defineProps({ modelValue: { type: Object, required: true } })
const emit = defineEmits(['update:modelValue', 'validity'])
const business = computed(() => props.modelValue)
const activeRoute = ref('A')
const newTopic = ref('')
const topicError = ref('')
const jsonValid = reactive({})
const codes = ['A', 'B', 'C', 'D', 'default']
const lines = (value) => (value || []).join('\n')
const split = (value) => String(value).split(/\r?\n/).map((item) => item.trim()).filter(Boolean)
const vocabularyLabels = {
  subject_noise_prefixes: '名称前缀（如馆名、时代名）', subject_noise_suffixes: '名称后缀（如复制品、标本）',
  subject_object_endings: '展品名称词尾', subject_modifier_terms: '名称修饰词', site_subject_markers: '遗址类识别词',
  display_subject_markers: '展示模型类识别词', fragment_subject_markers: '残片类识别词',
  tool_or_artifact_markers: '器物类识别词', strong_detail_anchors: '重点细节词',
}
const templateLabels = {
  fragment: '残片', display: '展示模型', site: '遗址', kiln: '窑址', artifact: '器物', inventory: '目录',
  default: '通用', anchor_mark: '刻痕细节', anchor_pattern: '纹样细节', anchor_trace: '痕迹细节', anchor_default: '通用细节',
}
const advancedReflection = computed({
  get: () => Object.fromEntries(Object.entries(business.value.reflection || {}).filter(([key]) => !['topics', 'personas', 'radar_dimensions', 'focused_halls', 'focus_keywords'].includes(key))),
  set: (value) => { business.value.reflection = { ...value, ...Object.fromEntries(['topics', 'personas', 'radar_dimensions', 'focused_halls', 'focus_keywords'].map((key) => [key, business.value.reflection[key]])) } },
})
function validateJson(key, valid) { jsonValid[key] = valid; emit('validity', Object.values(jsonValid).every(Boolean)) }
function addCategory() { business.value.categories.push({ value: '', label: '', reflection_prompts: [] }) }
function addTopic() {
  const key = newTopic.value.trim()
  if (!/^[a-z][a-z0-9_-]{0,63}$/.test(key) || business.value.reflection.topics[key]) {
    topicError.value = '主题编号需为不重复的小写英文编号，可含数字、连字符或下划线。'; return
  }
  business.value.reflection.topics[key] = { label: '', keywords: [], focus: '', evidence: '', next: '' }
  newTopic.value = ''; topicError.value = ''
}
function topicUsed(key) {
  return business.value.questionnaire.assumption_options.some((item) => item.topic === key)
    || Object.values(business.value.reflection.personas).some((item) => item.topic === key)
}
</script>

<template>
  <div class="business-editor" data-testid="business-editor">
    <section class="form-card">
      <h2>三步问卷与初始判断</h2>
      <p class="help-text">保留三道题和 A—D 稳定选项编号。题目支持 {museum_name}；初始判断的主题同时用于回答与报告，避免各处含义不一致。</p>
      <el-form-item label="第一题：参观关注方向"><el-input v-model="business.questionnaire.focus_title" data-testid="focus-title" /></el-form-item>
      <div v-for="option in business.questionnaire.focus_options" :key="option.code" class="option-box">
        <h3>选项 {{ option.code }}</h3>
        <div class="field-grid">
          <el-form-item label="选项名称"><el-input v-model="option.label" /></el-form-item>
          <el-form-item label="游客看到的说明"><el-input v-model="option.description" /></el-form-item>
        </div>
        <el-form-item label="此选项给 AI 的关注方向（仅管理员可见）"><el-input v-model="option.context" type="textarea" :rows="2" /></el-form-item>
      </div>
      <el-form-item label="第二题：导览身份"><el-input v-model="business.questionnaire.persona_title" /></el-form-item>
      <p class="help-text">第二题的四个选项使用上方“四种导览身份”的名称与简介。</p>
      <el-form-item label="第三题：初始判断或兴趣线索"><el-input v-model="business.questionnaire.assumption_title" data-testid="assumption-title" /></el-form-item>
      <div v-for="option in business.questionnaire.assumption_options" :key="option.code" class="option-box">
        <h3>选项 {{ option.code }}</h3>
        <div class="field-grid">
          <el-form-item label="选项名称"><el-input v-model="option.label" :data-testid="`assumption-label-${option.code}`" /></el-form-item>
          <el-form-item label="游客看到的说明"><el-input v-model="option.description" /></el-form-item>
        </div>
        <el-form-item label="对应报告主题"><el-select v-model="option.topic"><el-option v-for="(topic, key) in business.reflection.topics" :key="key" :value="key" :label="`${topic.label || key} (${key})`" /></el-select></el-form-item>
        <el-form-item label="回答中如何理解这个选择"><el-input v-model="option.chat_context" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="可进一步验证的问题"><el-input v-model="option.challenge" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="报告中如何回顾这个选择"><el-input v-model="option.review_hint" type="textarea" :rows="2" /></el-form-item>
      </div>
    </section>

    <section class="form-card">
      <h2>身份路线与观察问题</h2>
      <p class="help-text">优先展厅按每行一个展厅标识填写；关闭展厅自动跳过，其余开放展厅按目录补充。路线不是对馆藏事实的替代。</p>
      <el-tabs v-model="activeRoute">
        <el-tab-pane v-for="code in codes" :key="code" :name="code" :label="code === 'default' ? '默认路线' : `身份 ${code}`">
          <el-form-item label="路线主题"><el-input v-model="business.routes[code].theme" /></el-form-item>
          <el-form-item label="路线介绍"><el-input v-model="business.routes[code].summary" type="textarea" :rows="2" /></el-form-item>
          <el-form-item label="观察重点"><el-input v-model="business.routes[code].focus" type="textarea" :rows="2" /></el-form-item>
          <el-form-item label="建议问题（每行一个）"><el-input :model-value="lines(business.routes[code].questions)" type="textarea" :rows="3" @update:model-value="business.routes[code].questions = split($event)" /></el-form-item>
          <el-form-item label="优先展厅标识（每行一个，可留空）"><el-input :model-value="lines(business.routes[code].preferred_halls)" type="textarea" :rows="3" @update:model-value="business.routes[code].preferred_halls = split($event)" /></el-form-item>
        </el-tab-pane>
      </el-tabs>
      <h3>参观时长与推荐站数</h3>
      <div v-for="(duration, index) in business.route_durations" :key="index" class="duration-row">
        <el-form-item label="不超过（分钟）"><el-input-number v-model="duration.max_minutes" :min="1" :max="1440" /></el-form-item>
        <el-form-item label="推荐站数"><el-input-number v-model="duration.stops" :min="1" :max="100" /></el-form-item>
        <el-button :disabled="business.route_durations.length <= 1" @click="business.route_durations.splice(index, 1)">移除</el-button>
      </div>
      <el-button @click="business.route_durations.push({ max_minutes: 1440, stops: 5 })">增加时长档位</el-button>
    </section>

    <section class="form-card">
      <h2>本馆展品分类</h2>
      <p class="help-text">分类编号用于展品数据，修改前请核对已导入展品；分类名称用于游客展示。反思问题可留空，每行一个。</p>
      <div v-for="(category, index) in business.categories" :key="index" class="option-box">
        <div class="field-grid">
          <el-form-item label="分类编号"><el-input v-model="category.value" :data-testid="`category-value-${index}`" /></el-form-item>
          <el-form-item label="分类名称"><el-input v-model="category.label" :data-testid="`category-label-${index}`" /></el-form-item>
        </div>
        <el-form-item label="该分类的反思问题"><el-input :model-value="lines(category.reflection_prompts)" type="textarea" :rows="2" @update:model-value="category.reflection_prompts = split($event)" /></el-form-item>
        <el-button :disabled="business.categories.length <= 1" @click="business.categories.splice(index, 1)">移除此分类</el-button>
      </div>
      <el-button @click="addCategory">增加分类</el-button>
    </section>

    <section class="form-card">
      <h2>报告主题与 Reflection 规则</h2>
      <p class="help-text">关键词用于识别游客实际关注的主题；报告仍根据真实参观记录生成。证据文案可使用 {halls} 代入参观展厅。</p>
      <details v-for="(topic, key) in business.reflection.topics" :key="key" class="option-box">
        <summary>{{ topic.label || '未命名主题' }} · {{ key }}</summary>
        <el-form-item label="主题名称"><el-input v-model="topic.label" /></el-form-item>
        <el-form-item label="识别关键词（每行一个）"><el-input :model-value="lines(topic.keywords)" type="textarea" :rows="3" @update:model-value="topic.keywords = split($event)" /></el-form-item>
        <el-form-item label="关注点说明"><el-input v-model="topic.focus" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="证据回顾"><el-input v-model="topic.evidence" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="下一步问题"><el-input v-model="topic.next" type="textarea" :rows="2" /></el-form-item>
        <el-button :disabled="topicUsed(key) || Object.keys(business.reflection.topics).length <= 1" @click="delete business.reflection.topics[key]">删除未被引用的主题</el-button>
      </details>
      <div class="duration-row"><el-input v-model="newTopic" placeholder="新主题编号，如 city_life" /><el-button @click="addTopic">增加主题</el-button></div>
      <p v-if="topicError" role="alert">{{ topicError }}</p>
      <h3>各身份的报告视角</h3>
      <details v-for="code in codes" :key="code" class="option-box">
        <summary>{{ code === 'default' ? '默认' : `身份 ${code}` }}</summary>
        <el-form-item label="首选主题"><el-select v-model="business.reflection.personas[code].topic"><el-option v-for="(topic, key) in business.reflection.topics" :key="key" :label="topic.label || key" :value="key" /></el-select></el-form-item>
        <el-form-item label="报告主题编号"><el-input v-model="business.reflection.personas[code].theme" /></el-form-item>
        <el-form-item label="回顾引言"><el-input v-model="business.reflection.personas[code].entry" type="textarea" :rows="2" /></el-form-item>
      </details>
      <h3>五项参观指标</h3>
      <details v-for="(dimension, key) in business.reflection.radar_dimensions" :key="key" class="option-box">
        <summary>{{ dimension.label }} · {{ key }}</summary>
        <el-form-item label="展示名称"><el-input v-model="dimension.label" /></el-form-item>
        <el-form-item label="统计依据"><el-select v-model="dimension.metric"><el-option v-for="item in [{ value: 'total_duration_minutes', label: '总参观分钟' }, { value: 'total_questions', label: '提问次数' }, { value: 'total_exhibits_viewed', label: '参观展品数' }, { value: 'site_hall_duration_minutes', label: '重点展厅分钟' }, { value: 'ceramic_questions', label: '重点词提问次数' }]" :key="item.value" :value="item.value" :label="item.label" /></el-select></el-form-item>
        <div class="field-grid"><el-form-item label="中档阈值"><el-input-number v-model="dimension.medium" :min="0" /></el-form-item><el-form-item label="高档阈值"><el-input-number v-model="dimension.high" :min="0" /></el-form-item></div>
        <el-form-item label="高档要求严格大于阈值"><el-switch v-model="dimension.high_exclusive" /></el-form-item>
      </details>
      <el-form-item label="重点展厅标识（每行一个）"><el-input :model-value="lines(business.reflection.focused_halls)" type="textarea" :rows="2" @update:model-value="business.reflection.focused_halls = split($event)" /></el-form-item>
      <el-form-item label="重点提问识别词（每行一个）"><el-input :model-value="lines(business.reflection.focus_keywords)" type="textarea" :rows="3" @update:model-value="business.reflection.focus_keywords = split($event)" /></el-form-item>
      <details class="option-box"><summary>高级：事件权重、置信阈值与报告模板</summary>
        <p class="help-text">保留字段名和模板占位符，仅调整本馆需要的数值与文案；服务器会在发布时检查范围和引用。</p>
        <BusinessJsonField v-model="advancedReflection" label="报告规则 JSON" @validity="validateJson('reflection', $event)" />
      </details>
    </section>

    <section class="form-card">
      <h2>展品建议问题</h2>
      <p class="help-text">问题基于实际展品生成。模板中的 {subject} 表示展品，{anchor} 表示资料里真实出现的细节；每行一条模板。</p>
      <details v-for="(templates, key) in business.suggestions.question_templates" :key="key" class="option-box">
        <summary>{{ templateLabels[key] || key }}模板</summary>
        <el-form-item label="问题模板"><el-input :model-value="lines(templates)" type="textarea" :rows="3" @update:model-value="business.suggestions.question_templates[key] = split($event)" /></el-form-item>
      </details>
      <details class="option-box"><summary>本馆名称与细节词表</summary>
        <el-form-item v-for="(label, key) in vocabularyLabels" :key="key" :label="`${label}（每行一个）`"><el-input :model-value="lines(business.suggestions[key])" type="textarea" :rows="3" @update:model-value="business.suggestions[key] = split($event)" /></el-form-item>
        <BusinessJsonField v-model="business.suggestions.description_anchors" label="细节词与通俗称呼对照（每项是两个字符串的数组）" @validity="validateJson('anchors', $event)" />
      </details>
    </section>

    <section class="form-card">
      <h2>导览引导与参观节奏</h2>
      <el-form-item label="快速开始的讲解方式（仅管理员可见）"><el-input v-model="business.dialogue.default_persona_prompt" type="textarea" :rows="3" /></el-form-item>
      <el-form-item v-for="code in codes" :key="code" :label="`${code === 'default' ? '默认' : code} 身份的引导原则`"><el-input v-model="business.dialogue.persona_challenges[code]" type="textarea" :rows="2" /></el-form-item>
      <p class="help-text">参观节奏供接入本系统的导览客户端使用；不会改变三步问卷结构。</p>
      <div v-for="(rhythm, index) in business.rhythms" :key="index" class="field-grid">
        <el-form-item label="节奏编号"><el-input v-model="rhythm.value" /></el-form-item><el-form-item label="节奏名称"><el-input v-model="rhythm.label" /></el-form-item>
      </div>
    </section>

    <section class="form-card">
      <h2>语音配置</h2>
      <p class="help-text">填写当前语音供应商支持的声线名或标识。声线和播报风格随新导览配置一起保存，已有会话保留创建时配置。</p>
      <el-form-item label="默认声线"><el-input v-model="business.tts.default_voice" data-testid="default-voice" /></el-form-item>
      <el-form-item label="默认播报风格（仅管理员可见）"><el-input v-model="business.tts.default_style" type="textarea" :rows="2" /></el-form-item>
      <details v-for="code in codes" :key="code" class="option-box"><summary>{{ code === 'default' ? '默认身份' : `身份 ${code}` }}</summary>
        <el-form-item label="声线"><el-input v-model="business.tts.personas[code].voice" /></el-form-item>
        <el-form-item label="播报风格"><el-input v-model="business.tts.personas[code].style" type="textarea" :rows="2" /></el-form-item>
      </details>
    </section>
  </div>
</template>

<style scoped>
.form-card { padding: 24px; margin-bottom: 20px; border: 1px solid var(--color-border); border-radius: 12px; background: var(--color-bg-elevated); }
.form-card h2 { margin: 0 0 18px; font-size: 20px; }
.help-text { line-height: 1.7; color: var(--color-text-secondary); }
.field-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 20px; }
.option-box { border: 1px solid var(--color-border); padding: 16px; border-radius: 8px; margin-bottom: 14px; }
.option-box h3 { margin: 0 0 12px; }
summary { cursor: pointer; font-weight: 600; margin-bottom: 12px; }
.duration-row { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin: 12px 0; }
.duration-row > .el-input { max-width: 320px; }
.el-select { width: 100%; }
@media (max-width: 767px) { .field-grid { grid-template-columns: 1fr; } .form-card { padding: 16px; } }
</style>
