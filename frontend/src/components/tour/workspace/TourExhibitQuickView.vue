<script setup>
import { computed, ref } from 'vue'
import { useTour } from '../../../composables/useTour.js'
const { hallExhibits, currentExhibit, enterExhibit, loading, error, tourBusiness } = useTour()
const emit = defineEmits(['switch-tab'])
const search = ref('')
const cards = computed(() => new Map((tourBusiness.value?.visitor_experience?.exhibits || []).map(e => [e.source_record_id, e])))
const filtered = computed(() => hallExhibits.value.filter(e => [e.name, e.source_record_id, ...(cards.value.get(e.source_record_id)?.aliases || [])]
  .join(' ').toLowerCase().includes(search.value.trim().toLowerCase())))
async function open(exhibit) { if (await enterExhibit(exhibit)) emit('switch-tab', 'session') }
</script>
<template>
  <section class="browser">
    <h2>选一件展品，开始细看</h2>
    <p>点“进入展品导览”后，后续问答会围绕这件展品展开。</p>
    <el-input v-model="search" placeholder="搜索名称、编号或别名" clearable />
    <el-alert v-if="error" :title="error" type="error" :closable="false" />
    <div class="grid">
      <article v-for="exhibit in filtered" :key="exhibit.id" :class="{ current: currentExhibit?.id === exhibit.id }">
        <img v-if="exhibit.image_url" :src="exhibit.image_url" :alt="exhibit.name" loading="lazy" />
        <div class="body"><small>{{ exhibit.source_record_id }} · {{ exhibit.era }}</small><h3>{{ exhibit.name }}</h3>
          <p>{{ cards.get(exhibit.source_record_id)?.introduction || exhibit.description }}</p>
          <small>{{ cards.get(exhibit.source_record_id)?.image_caption }}</small>
          <el-button type="primary" plain :disabled="loading.session || loading.chat" @click="open(exhibit)">进入展品导览</el-button>
        </div>
      </article>
    </div>
    <el-empty v-if="!filtered.length" :description="search ? '没有匹配的展品，请换个关键词' : '当前展厅暂无展品'" />
  </section>
</template>
<style scoped>
.browser{padding:24px;max-width:1200px;margin:auto}.browser>p{color:var(--color-text-muted);line-height:1.8}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:18px;margin-top:24px}article{border:1px solid var(--color-border);border-radius:16px;overflow:hidden;background:var(--color-bg-elevated)}article.current{border-color:var(--color-accent)}img{width:100%;height:210px;object-fit:contain;background:#f8f2e8}.body{padding:18px}h3{margin:10px 0}.body p{font-size:14px;line-height:1.8}.body small{display:block;font-size:11px;color:var(--color-text-muted);line-height:1.7}.body .el-button{margin-top:18px}
</style>
