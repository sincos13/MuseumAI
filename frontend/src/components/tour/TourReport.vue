<script setup>
import { computed, onMounted, ref } from 'vue'
import { useTour } from '../../composables/useTour.js'
import TourStats from './TourStats.vue'
import SourceReferences from './SourceReferences.vue'
import AnswerText from './AnswerText.vue'
const { tourBusiness, tourReport, generateReport, tourSession, reportThemeTitle, loading, error, resetTour } = useTour()
const final = computed(() => tourReport.value?.final_report)
const personal = computed(() => tourReport.value?.personal)
const visitDate = computed(() => personal.value?.started_at ? new Date(personal.value.started_at).toLocaleDateString('zh-CN', { timeZone: personal.value.timezone || 'Asia/Shanghai' }) : '')
const failedImage = ref('')
const coverImage = computed(() => personal.value?.cover_image)
const originLabels = { visitor: '你当时的表达', guide: '导览解释节选', source: '资料线索节选' }
const displayReport = computed(() => {
  const report = tourReport.value
  return report && { ...report, most_viewed_exhibit_name: report.viewed_exhibits?.find(e => e.id === report.most_viewed_exhibit_id)?.name }
})
function save() {
  const blob = new Blob([JSON.stringify({ ...tourReport.value, disclosure: tourBusiness.value?.visitor_experience?.disclosure }, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = '导览报告-' + (tourSession.value?.id || '').slice(0, 8) + '.json'
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
function print() { window.print() }
onMounted(() => { if (!tourReport.value) generateReport() })
</script>
<template>
  <section class="tour-report">
    <div v-if="loading.report" class="report-loading" role="status">正在把这次交流整理成你的导览手记…</div>
    <el-alert v-if="error" :title="error" type="error" :closable="false"><el-button :disabled="loading.report" @click="generateReport">重新生成</el-button></el-alert>

    <!-- 新版最终报告（封面 / 兴趣 / 卡片 / 画像） -->
    <template v-if="final">
      <header class="report-cover">
        <p class="kicker">{{ final.cover.date }} · {{ final.cover.museum_name }}</p>
        <p class="cover-role">{{ final.cover.persona.icon }} {{ final.cover.persona.name }}</p>
        <div class="route-strip">
          <template v-for="(seg, i) in final.cover.route" :key="seg.hall">
            <span v-if="i" class="route-arrow">→</span>
            <span class="route-seg">
              <strong>{{ seg.name }}</strong>
              <small v-if="seg.exhibits">{{ seg.exhibits }} 件展品</small>
            </span>
          </template>
        </div>
        <p class="cover-meta">
          {{ final.cover.duration_minutes }} 分钟 · {{ final.cover.questions }} 次提问 ·
          {{ final.cover.exhibits }} 件展品 · {{ final.cover.halls }} 个展厅
        </p>
      </header>

      <section v-if="final.interests?.length" class="report-section" data-testid="report-interests">
        <p class="section-number">01 / 你关心的</p>
        <h2>这次你在意什么</h2>
        <article v-for="interest in final.interests" :key="interest.dimension" class="report-card interest">
          <h3>{{ interest.dimension }}</h3>
          <p v-if="interest.story" class="interest-story">{{ interest.story }}</p>
          <p v-if="interest.background" class="muted">{{ interest.background }}</p>
          <div v-if="interest.reading?.length" class="reading">
            <strong>延伸阅读</strong>
            <a v-for="link in interest.reading" :key="link.url" :href="link.url" target="_blank" rel="noopener noreferrer">
              {{ link.title }}<small v-if="link.source_label"> · {{ link.source_label }}</small>
            </a>
          </div>
          <details v-if="interest.evidence_questions?.length" class="interest-evidence">
            <summary>你当时问过</summary>
            <ul><li v-for="q in interest.evidence_questions" :key="q">{{ q }}</li></ul>
          </details>
        </article>
      </section>

      <section v-if="final.cards?.length" class="report-section" data-testid="report-cards">
        <p class="section-number">02 / 带走这些</p>
        <h2>这次你学到了什么</h2>
        <div class="cards-grid">
          <article v-for="card in final.cards" :key="card.id" class="report-card knowledge-card">
            <h3>{{ card.title }}</h3>
            <ul class="card-points"><li v-for="point in card.points" :key="point">{{ point }}</li></ul>
            <p v-if="card.caveat" class="card-caveat">资料没说明：{{ card.caveat }}</p>
            <p v-if="card.self_check" class="self-check">{{ card.self_check }}</p>
            <details v-if="card.sources?.length" class="card-sources">
              <summary>依据</summary>
              <div v-for="src in card.sources" :key="src.id" class="source-mini">
                <small>{{ src.title }}</small><AnswerText :text="src.snippet" />
              </div>
            </details>
          </article>
        </div>
      </section>

      <section v-if="final.profile" class="report-section profile" data-testid="report-profile">
        <p class="section-number">03 / 关于你</p>
        <h2>{{ final.profile.label }}</h2>
        <p class="profile-summary">{{ final.profile.summary }}</p>
        <blockquote v-for="quote in final.profile.evidence || []" :key="quote">{{ quote }}</blockquote>
        <p v-if="final.profile.next_suggestion" class="next-suggestion">下次可以：{{ final.profile.next_suggestion }}</p>
      </section>

      <div class="actions">
        <el-button type="primary" @click="print">打印 / 保存 PDF</el-button>
        <el-button @click="save">保存报告 JSON</el-button>
        <el-button @click="resetTour">开启新的参观</el-button>
      </div>
    </template>

    <!-- 旧版个人手记（兼容尚未生成新版报告的会话） -->
    <template v-else-if="tourReport">
      <header class="report-cover">
        <p class="kicker">{{ visitDate }} · 一次参观留下的东西</p>
        <p class="cover-role">{{ personal?.persona_icon }} {{ personal?.persona_name || reportThemeTitle }}</p>
        <h1>{{ personal?.title || reportThemeTitle || '我的导览手记' }}</h1>
        <figure v-if="coverImage?.url && failedImage !== coverImage.url" class="cover-image">
          <img :src="coverImage.url" :alt="coverImage.subject" @error="failedImage = coverImage.url" />
          <figcaption>{{ coverImage.subject }} · 本次导览中的展品</figcaption>
        </figure>
        <p class="cover-meta">{{ tourReport.total_duration_minutes }} 分钟 · {{ tourReport.halls_visited?.length || 0 }} 个展厅 · {{ tourReport.total_exhibits_viewed }} 件展品</p>
        <p class="muted">{{ tourBusiness?.visitor_experience?.disclosure }}</p>
      </header>
      <section class="report-section" data-testid="report-moments">
        <p class="section-number">01 / 留在现场</p><h2>值得回看的瞬间</h2>
        <p v-if="!personal?.moments?.length" class="empty-note">这次尚未留下你的回应。我们保留了导览介绍，等下次再接着聊。</p>
        <article v-for="(moment, i) in personal?.moments || []" :key="moment.event_id" class="report-card moment">
          <span class="moment-index">{{ String(i + 1).padStart(2, '0') }}</span>
          <p class="muted">{{ moment.hall_name }}</p><h3>{{ moment.subject }}</h3>
          <p class="quote-label">你当时说</p><blockquote>{{ moment.question }}</blockquote>
          <p class="quote-label">我们讨论到了 · 回答节选</p><AnswerText :text="moment.discussion" />
          <div v-if="moment.clue" class="clue"><strong>留下的一条线索</strong><small>{{ originLabels[moment.clue.origin] }}</small><AnswerText :text="moment.clue.text" /></div>
          <SourceReferences :sources="moment.sources" />
        </article>
      </section>
      <section class="report-section journey" data-testid="report-journey">
        <p class="section-number">02 / 顺着问题走</p><h2>你的问题走到了哪里</h2>
        <p>{{ personal?.journey || '本次交流记录保留在下方，可以从这里回看。' }}</p>
        <details v-if="personal?.journey_records?.length > 2"><summary>展开完整的交流线索</summary>
          <ol><li v-for="item in personal.journey_records" :key="item.event_id"><strong>{{ item.subject }}</strong> · {{ item.quote }}</li></ol>
        </details>
      </section>
      <section class="report-section" data-testid="report-takeaway">
        <p class="section-number">03 / 带走这一页</p><h2>{{ personal?.takeaway_title || '我的参观小结' }}</h2>
        <p v-if="!personal?.takeaway?.length" class="empty-note">还没有足够的交流来整理身份小结。这一页先留白，不替你补写发现。</p>
        <article v-for="note in personal?.takeaway || []" :key="note.event_id" class="report-card takeaway">
          <h3>{{ note.subject }}</h3>
          <div v-for="(part, i) in note.sections" :key="i" class="note-part">
            <h4>{{ part.label }}</h4>
            <template v-if="part.evidence"><small class="muted">{{ originLabels[part.evidence.origin] }}</small><AnswerText :text="part.evidence.text" /></template>
            <p v-else class="muted">本次交流没有留下这一项，留待下次补充。</p>
          </div>
          <SourceReferences :sources="note.sources" />
        </article>
      </section>
      <details v-if="personal?.introduced?.length" class="report-card supporting">
        <summary>这次导览介绍过什么</summary>
        <article v-for="item in personal.introduced" :key="item.event_id"><h3>{{ item.subject }}</h3><AnswerText :text="item.answer" /><SourceReferences :sources="item.sources" /></article>
      </details>
      <details class="report-card supporting"><summary>参观记录与完整问答</summary>
        <p class="muted">{{ tourReport.total_questions }} 次提问或回应。统计描述应用内参观记录，不代表实际到馆或学习能力评分。</p>
        <TourStats :report="displayReport" :persona="tourSession?.persona" />
        <div class="tags"><span v-for="e in tourReport.viewed_exhibits || []" :key="e.id">{{ e.name || '展品记录' }}</span></div>
        <details v-for="(record, i) in tourReport.evidence_records || []" :key="i" class="record"><summary>{{ i + 1 }}. {{ record.question }}</summary><AnswerText :text="record.answer" /><SourceReferences :sources="record.sources" /></details>
      </details>
      <div class="actions"><el-button type="primary" @click="print">打印 / 保存 PDF</el-button><el-button @click="save">保存报告 JSON</el-button><el-button @click="resetTour">开启新的参观</el-button></div>
    </template>
  </section>
</template>
<style scoped>
.cover-image{margin:24px 0}.cover-image img{display:block;width:100%;max-height:280px;object-fit:contain;border-radius:12px;background:var(--color-bg-base)}.cover-image figcaption{font-size:12px;color:var(--color-text-muted);margin-top:8px}
.tour-report{max-width:860px;margin:auto;padding:40px 24px 64px;color:var(--color-text-primary);line-height:1.9}
.report-loading{padding:40px;text-align:center;color:var(--color-text-muted)}
.report-cover{padding:36px;border:1px solid var(--color-border);border-top:5px solid var(--color-accent);border-radius:4px 4px 24px 24px;background:var(--color-bg-elevated);margin-bottom:44px}
.kicker,.section-number{font-size:12px;letter-spacing:.12em;color:var(--color-accent)}
.cover-role{color:var(--color-accent);font-weight:600;font-size:18px;margin-top:20px}
h1{font-size:32px;line-height:1.55;max-width:620px;margin:16px 0 24px}h2{font-size:24px;margin:0 0 20px}h3{font-size:18px;margin:4px 0 12px}h4{font-size:14px;margin:0 0 5px}
.route-strip{display:flex;align-items:flex-start;flex-wrap:wrap;gap:10px;margin:22px 0}
.route-arrow{color:var(--color-text-muted);align-self:center}
.route-seg{display:flex;flex-direction:column;padding:10px 14px;border:1px solid var(--color-border);border-radius:10px;background:var(--color-bg-base)}
.route-seg strong{font-size:15px}.route-seg small{font-size:11px;color:var(--color-text-muted)}
.cover-meta{font-size:13px;color:var(--color-text-muted)}.muted{font-size:12px;color:var(--color-text-muted);line-height:1.8}
.report-section{margin-bottom:44px}.report-card{position:relative;padding:24px;border:1px solid var(--color-border);border-radius:16px;background:var(--color-bg-elevated);margin-bottom:18px}
.moment-index{position:absolute;right:24px;top:18px;font-size:32px;color:var(--color-accent);opacity:.4}
.quote-label{font-size:12px;color:var(--color-text-muted);margin:22px 0 8px}
blockquote{margin:0;padding:12px 18px;border-left:3px solid var(--color-accent);background:var(--color-accent-muted);font-size:17px;white-space:pre-wrap}
.clue{margin-top:22px;padding-top:16px;border-top:1px dashed var(--color-border)}.clue strong,.clue small{display:block}.clue small{font-size:11px;color:var(--color-text-muted);margin-bottom:8px}
.journey{padding:24px 28px;background:var(--color-accent-muted);border-radius:16px}.journey p{white-space:pre-wrap}
.note-part{padding:16px 0;border-top:1px solid var(--color-border)}
.empty-note{padding:20px;border:1px dashed var(--color-border);border-radius:12px;color:var(--color-text-muted)}
.interest-story{white-space:pre-wrap}
.reading{margin-top:16px;padding-top:14px;border-top:1px dashed var(--color-border)}.reading strong{display:block;margin-bottom:8px}
.reading a{display:block;color:var(--color-accent);text-decoration:none;margin:4px 0}.reading a small{color:var(--color-text-muted)}
.interest-evidence{margin-top:12px}.interest-evidence summary{font-size:12px;color:var(--color-text-muted);cursor:pointer}.interest-evidence li{font-size:13px;color:var(--color-text-muted)}
.cards-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px}
.knowledge-card h3{color:var(--color-accent)}.card-points{margin:0 0 12px;padding-left:18px}.card-points li{margin:6px 0}
.card-caveat{font-size:12px;color:var(--color-text-muted);border-left:2px solid var(--color-border);padding-left:10px}
.self-check{font-size:12px;color:var(--color-text-muted);font-style:italic}
.card-sources{margin-top:12px;font-size:12px}.card-sources summary{cursor:pointer;color:var(--color-text-muted)}
.source-mini{margin:8px 0;padding:8px;background:var(--color-bg-base);border-radius:8px}.source-mini small{color:var(--color-text-muted)}
.profile{padding:26px;background:var(--color-accent-muted);border-radius:16px}.profile-summary{white-space:pre-wrap}
.profile blockquote{margin:14px 0;padding:10px 16px;border-left:3px solid var(--color-accent);background:var(--color-bg-elevated);font-size:15px}
.next-suggestion{font-size:14px;color:var(--color-accent)}
.tags,.actions{display:flex;gap:10px;flex-wrap:wrap}.actions{margin-top:20px}
.tags span{border-radius:20px;background:var(--color-accent-muted);padding:6px 12px;font-size:13px}
.record{border-top:1px solid var(--color-border);padding:16px 0}summary{cursor:pointer}
.supporting>summary{font-size:14px;color:var(--color-text-muted);padding:6px 0}
@media(max-width:600px){.tour-report{padding:20px 14px}.report-cover{padding:24px 20px}.cards-grid{grid-template-columns:1fr}h1{font-size:26px}}
@media print{.actions,.supporting,.report-loading{display:none}.tour-report{max-width:none;padding:0}.report-cover,.report-card,.journey,.profile{break-inside:avoid}.report-cover{margin-bottom:28px}blockquote{font-size:14px}h1{font-size:28px}}
</style>
<style>
@media print {
  @page { size: A4; margin: 16mm; }
  body:has(.tour-report), body:has(.tour-report) #app,
  body:has(.tour-report) .app-container, body:has(.tour-report) .app-body,
  body:has(.tour-report) .app-main, body:has(.tour-report) .tour-container,
  body:has(.tour-report) .tour-content {
    height: auto !important; min-height: 0 !important; max-height: none !important;
    overflow: visible !important; display: block !important; padding: 0 !important;
    background: white !important; color: #222 !important;
  }
  body:has(.tour-report) .app-header { display: none !important; }
}
</style>
