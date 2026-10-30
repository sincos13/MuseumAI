<script setup>
import { computed, ref, watch, nextTick, onMounted } from 'vue'
import { useTour } from '../../../composables/useTour.js'
import { useTourWorkbench } from '../../../composables/useTourWorkbench.js'
import { getHallDisplayName } from '../../../composables/useHallDirectory.js'
import SourceReferences from '../SourceReferences.vue'
import AnswerText from '../AnswerText.vue'
import TourIcon from '../TourIcon.vue'
const { chatMessages, streamingContent, loading, error, sendTourMessage, currentHall, currentExhibit,
  questionSuggestions, enterExhibit, tourBusiness, guideChoices, openingPending,
  startExhibitOpening, stopTourResponse } = useTour()
const { chatDraft, getStylePayload, uiPreferences, activeTab } = useTourWorkbench()
const messagesArea = ref(null)
const currentHallName = computed(() => currentHall.value ? getHallDisplayName(currentHall.value) : '')
const card = computed(() => tourBusiness.value?.visitor_experience?.exhibits?.find(e => e.source_record_id === currentExhibit.value?.source_record_id))
const hallIntroduction = computed(() => currentExhibit.value ? '' :
  chatMessages.value.find(m => m.isWelcome)?.content
  || tourBusiness.value?.visitor_experience?.hall_openings?.[currentHall.value] || '')
// Keep every turn and source in order, with the question attached to its answer.
const exchanges = computed(() => {
  const result = []
  for (const msg of chatMessages.value.filter(m => !m.isWelcome)) {
    if (msg.role === 'user') result.push({ question: msg.content, answers: [] })
    else {
      if (!result.length) result.push({ question: '', answers: [] })
      result[result.length - 1].answers.push(msg)
    }
  }
  return result
})
const chips = computed(() => {
  const subject = currentExhibit.value?.name || currentHallName.value
  if (currentExhibit.value) return guideChoices.value || []
  const base = [
    { label: '文物种类', question: subject + '有哪些类别的展品？' },
    { label: '看关键细节', question: subject + '可以从哪件展品的什么细节开始看？' },
    { label: '了解展厅主题', question: subject + '的主题是什么？' },
  ]
  const asked = new Set(chatMessages.value.filter(m => m.role === 'user').map(m => m.content))
  return [...base, ...questionSuggestions.value.slice(0, 3).map(q => ({ label: q, question: q }))]
    .filter((x, i, all) => !asked.has(x.question) && all.findIndex(y => y.question === x.question) === i)
})
function scrollToBottom() {
  if (uiPreferences.value.autoScroll && messagesArea.value) messagesArea.value.scrollTop = messagesArea.value.scrollHeight
}
watch([chatMessages, streamingContent], () => nextTick(scrollToBottom), { deep: true })
watch(activeTab, (_, old) => { if (old === 'session' && !uiPreferences.value.rememberDraft) chatDraft.value = '' })
async function sendMessage(question, options = {}) {
  const raw = typeof question === 'string' ? question : chatDraft.value.trim()
  if (!raw || loading.value.chat || loading.value.session) return
  chatDraft.value = ''
  await sendTourMessage(raw, false, getStylePayload(), options)
}
function onInputEnter(event) {
  if (!event.isComposing && event.keyCode !== 229) sendMessage()
}
onMounted(scrollToBottom)
</script>
<template>
  <section class="tour-session-panel" :class="['font-' + uiPreferences.fontScale, { compact: uiPreferences.messageDensity === 'compact' }]" aria-label="导览会话">
    <div v-if="currentExhibit" class="exhibit-navigation">
      <button type="button" :disabled="loading.chat || loading.session" @click="enterExhibit(null)">‹ 回到展厅问答</button>
    </div>
    <div ref="messagesArea" class="messages-area">
      <article class="conversation-card">
        <header class="conversation-heading">
          <h2><TourIcon name="seal" />{{ currentExhibit?.name || currentHallName }}<span class="heading-flourish" aria-hidden="true" /></h2>
        </header>
        <div v-if="currentExhibit" class="object-summary">
          <img v-if="currentExhibit.image_url" :src="currentExhibit.image_url" :alt="currentExhibit.name" />
          <div><strong>{{ currentExhibit.source_record_id }} {{ currentExhibit.name }}</strong>
            <p>{{ card?.material }} {{ card?.size }}</p><small>{{ card?.image_caption }}</small></div>
        </div>
        <div v-if="hallIntroduction" class="hall-introduction"><AnswerText :text="hallIntroduction" /></div>
        <div class="conversation-answers" role="log" aria-live="polite" aria-relevant="additions text" :aria-busy="loading.chat">
          <section v-for="(exchange, i) in exchanges" :key="i" class="exchange" :class="{ 'has-introduction': hallIntroduction }">
            <div v-if="exchange.question" class="question-badge"><TourIcon name="chat" /><span>{{ exchange.question }}</span></div>
            <div v-for="(msg, j) in exchange.answers" :key="j" class="message assistant">
              <small v-if="msg.isOpening" class="opening-label">一起从这里看起</small>
              <small v-if="msg.interrupted" class="interrupted-label">讲解已停止 · 这一段尚未完成</small>
              <div class="msg-content"><p v-for="(paragraph, p) in msg.content.split(/\n{2,}/)" :key="p"><AnswerText :text="paragraph" /></p></div>
              <SourceReferences :sources="msg.sources" />
            </div>
          </section>
          <div v-if="loading.chat" class="message assistant streaming-content">
            <div class="msg-content"><AnswerText :text="streamingContent || (openingPending ? '正在为你寻找第一个看点…' : '正在结合资料接着讲…')" /><span class="cursor"> ▍</span></div>
          </div>
        </div>
        <el-alert v-if="error" :title="error" type="error" :closable="false" />
        <el-button v-if="currentExhibit && !loading.chat && !chatMessages.some(m => m.isOpening && m.saved !== false) && (error || chatMessages.some(m => m.interrupted))" :disabled="loading.session" @click="startExhibitOpening">重试展品开场</el-button>
      </article>
    </div>
    <div class="composer">
      <div class="quick-prompts">
        <el-button class="browse-exhibits" type="primary" :disabled="loading.chat || loading.session" @click="activeTab = 'exhibit'"><TourIcon name="museum" />看展品</el-button>
        <template v-if="uiPreferences.showQuickPrompts">
          <button v-for="chip in chips" :key="chip.question" type="button" class="chip" :disabled="loading.chat || loading.session" @click="sendMessage(chip.question, { shortcutId: chip.id })">{{ chip.label }}</button>
        </template>
        <template v-if="currentExhibit">
          <button type="button" class="chip" :disabled="loading.chat || loading.session" @click="sendMessage('给个提示', { action: 'hint' })">给个提示</button>
          <button type="button" class="chip" :disabled="loading.chat || loading.session" @click="sendMessage('直接讲解', { action: 'explain' })">直接讲解</button>
        </template>
      </div>
      <div class="input-row">
        <el-input v-model="chatDraft" maxlength="2000" aria-label="输入导览问题" placeholder="说说你的观察、猜想，或直接提问…" :disabled="loading.chat || loading.session" @keyup.enter="onInputEnter">
          <template #prefix><TourIcon name="compass" /></template>
        </el-input>
        <button v-if="loading.chat" type="button" class="send-button stop-button" aria-label="停止讲解" title="停止讲解" @click="stopTourResponse"><span /></button>
        <button v-else type="button" class="send-button" aria-label="发送" title="发送" :disabled="loading.session || !chatDraft.trim()" @click="sendMessage()"><TourIcon name="send" /></button>
      </div>
    </div>
  </section>
</template>
<style scoped>
.tour-session-panel { --message-scale: 1; display: flex; flex-direction: column; height: 100%; min-height: 0; }
.font-sm { --message-scale: .9; }.font-lg { --message-scale: 1.15; }
.messages-area { flex: 1; overflow-y: auto; min-height: 0; padding: calc(28 * var(--tour-u, 1px)) calc(28 * var(--tour-u, 1px)) calc(8 * var(--tour-u, 1px)) calc(32 * var(--tour-u, 1px)); scrollbar-width: thin; scrollbar-color: #cbb99f transparent; }
.conversation-card { min-height: 100%; box-sizing: border-box; padding: calc(29 * var(--tour-u, 1px)) calc(36 * var(--tour-u, 1px)) calc(32 * var(--tour-u, 1px)) calc(50 * var(--tour-u, 1px)); background: #f5f2eceb; border: 1px solid #eee7dd; border-radius: calc(20 * var(--tour-u, 1px)); box-shadow: 0 2px 10px #6e533416; }
.conversation-heading { position: relative; display: flex; align-items: flex-start; justify-content: space-between; gap: calc(20 * var(--tour-u, 1px)); margin: 0 0 calc(26 * var(--tour-u, 1px)); min-height: calc(38 * var(--tour-u, 1px)); }
.conversation-heading h2 { display: flex; align-items: center; flex-wrap: wrap; gap: calc(19 * var(--tour-u, 1px)); font-size: calc(30 * var(--tour-u, 1px)); font-weight: 600; color: #69472e; line-height: 1.4; margin: 0 0 0 calc(-13 * var(--tour-u, 1px)); }
h2 .tour-icon { color: #8e6e43; font-size: calc(36 * var(--tour-u, 1px)); }
.heading-flourish { width: calc(64 * var(--tour-u, 1px)); height: 1px; background: linear-gradient(90deg, #aa8760 55%, transparent 55% 63%, #cdb9a0 63% 78%, transparent 78% 85%, #e1d2c0 85%); align-self: flex-end; margin-bottom: calc(7 * var(--tour-u, 1px)); }
.question-badge { display: flex; align-items: center; gap: calc(12 * var(--tour-u, 1px)); width: fit-content; max-width: 65%; margin-left: auto; border-radius: calc(24 * var(--tour-u, 1px)); padding: calc(17 * var(--tour-u, 1px)) calc(23 * var(--tour-u, 1px)); background: #a17b44; color: #fff7e6; font-size: calc(20 * var(--tour-u, 1px)); line-height: 1.5; overflow-wrap: anywhere; }
.question-badge .tour-icon { font-size: calc(23 * var(--tour-u, 1px)); }
.hall-introduction, .msg-content { font-size: calc(23 * var(--tour-u, 1px) * var(--message-scale)); line-height: 1.68; font-weight: 500; letter-spacing: .015em; color: #37332b; overflow-wrap: anywhere; }
.msg-content p { margin: 0; }.msg-content p + p { margin-top: calc(8 * var(--tour-u, 1px)); }
.exchange { margin-top: calc(20 * var(--tour-u, 1px)); }
.exchange.has-introduction, .exchange + .exchange { border-top: 1px solid #e9e2d8; padding-top: calc(20 * var(--tour-u, 1px)); }
.exchange > .question-badge { margin-bottom: calc(18 * var(--tour-u, 1px)); }
.message + .message { margin-top: calc(18 * var(--tour-u, 1px)); }
.opening-label, .interrupted-label { display: block; color: #9b805f; margin-bottom: 10px; }
.streaming-content { margin-top: 18px; }
.cursor { color: #a17b44; }
.object-summary { display: flex; gap: 22px; margin-bottom: 24px; font-size: 16px; line-height: 1.8; }
.object-summary img { width: 170px; max-height: 190px; object-fit: contain; border-radius: 10px; }
.object-summary small { color: #9b846c; }
.exhibit-navigation { padding: 10px 32px 0; }
.exhibit-navigation button { border: 0; background: transparent; color: #80603e; font: inherit; cursor: pointer; }
.composer { flex: 0 0 auto; padding: calc(20 * var(--tour-u, 1px)) calc(52 * var(--tour-u, 1px)) calc(37 * var(--tour-u, 1px)) calc(60 * var(--tour-u, 1px)); }
.quick-prompts { display: flex; align-items: center; gap: calc(16 * var(--tour-u, 1px)); margin-bottom: calc(22 * var(--tour-u, 1px)); overflow-x: auto; scrollbar-width: thin; }
.chip, .browse-exhibits { flex: 0 0 auto; border: 1px solid #d6c7b5; border-radius: 999px; padding: 0 calc(28 * var(--tour-u, 1px)); height: calc(51 * var(--tour-u, 1px)); font: inherit; font-size: calc(20 * var(--tour-u, 1px)); color: #876d52; background: transparent; cursor: pointer; white-space: nowrap; }
.browse-exhibits { background: #704a35; color: #fffaef; border-color: #704a35; padding: 0 calc(27 * var(--tour-u, 1px)); }
.browse-exhibits :deep(span) { gap: calc(9 * var(--tour-u, 1px)); }
.chip:hover { background: #e9dfd0; border-color: #b49770; }
.chip:disabled { opacity: .5; cursor: wait; }
.input-row { display: flex; align-items: center; gap: calc(20 * var(--tour-u, 1px)); }
.input-row :deep(.el-input) { flex: 1; min-width: 0; height: calc(67 * var(--tour-u, 1px)); font-size: calc(22 * var(--tour-u, 1px)); --el-input-bg-color: #fff; --el-input-border-color: transparent; --el-input-hover-border-color: #d7c6b0; --el-input-focus-border-color: #aa8657; }
.input-row :deep(.el-input__wrapper) { border-radius: calc(28 * var(--tour-u, 1px)); padding: 0 calc(23 * var(--tour-u, 1px)); box-shadow: none; background: #fff; }
.input-row :deep(.el-input__wrapper.is-focus) { box-shadow: 0 0 0 1px #aa8657 inset; }
.input-row :deep(.el-input__inner) { height: 100%; color: #44382b; font-family: inherit; }
.input-row :deep(.el-input__inner::placeholder) { color: #96938c; }
.input-row :deep(.el-input__prefix) { color: #a08660; margin-right: calc(17 * var(--tour-u, 1px)); font-size: calc(25 * var(--tour-u, 1px)); }
.send-button { width: calc(66 * var(--tour-u, 1px)); height: calc(66 * var(--tour-u, 1px)); border-radius: 50%; border: 0; flex: 0 0 auto; background: #704a35; color: #fff7e9; font-size: calc(27 * var(--tour-u, 1px)); display: grid; place-items: center; cursor: pointer; box-shadow: 0 2px 5px #76543520; }
.send-button:hover { background: #5c3c2a; }.send-button:disabled { cursor: default; }
.stop-button span { width: 16px; height: 16px; border-radius: 3px; background: currentColor; }
.compact .msg-content { line-height: 1.45; }.compact .exchange { margin-top: 12px; padding-top: 12px; }
@media (max-width: 1100px) { .conversation-heading { flex-wrap: wrap; } }
@media (max-width: 767px) {
  .messages-area { padding: 12px; }
  .conversation-card { padding: 20px; border-radius: 16px; }
  .conversation-heading { margin-bottom: 18px; gap: 14px; }
  .conversation-heading h2 { font-size: 22px; margin: 0; gap: 10px; }
  h2 .tour-icon { font-size: 25px; }.heading-flourish { width: 32px; }
  .hall-introduction, .msg-content { font-size: calc(16px * var(--message-scale)); line-height: 1.85; }
  .question-badge { max-width: 95%; font-size: 14px; padding: 10px 15px; border-radius: 18px; }
  .composer { padding: 8px 12px max(14px, env(safe-area-inset-bottom)); }
  .quick-prompts { gap: 8px; margin-bottom: 12px; }
  .chip, .browse-exhibits { font-size: 14px; padding: 0 16px; height: 38px; }
  .input-row { gap: 10px; }.input-row :deep(.el-input) { height: 48px; font-size: 15px; }
  .input-row :deep(.el-input__wrapper) { padding: 0 14px; }.input-row :deep(.el-input__prefix) { margin-right: 5px; font-size: 18px; }
  .send-button { width: 48px; height: 48px; font-size: 22px; }
  .object-summary { flex-direction: column; }.object-summary img { width: 100%; max-height: 180px; }
}
</style>
