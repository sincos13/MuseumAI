<script setup>
import TourIcon from './TourIcon.vue'
defineProps({ sources: { type: Array, default: () => [] } })
</script>
<template>
  <details v-if="sources.length" class="references">
    <summary><TourIcon name="seal" />检索依据 · {{ sources.length }} 个片段</summary>
    <p class="note">以下是本次回答使用的检索上下文，展开核对原文；不表示每一句回答均已得到独立验证。</p>
    <article v-for="(source, i) in sources" :key="i">
      <strong>{{ source.title }}</strong><small>{{ source.source_label }}</small>
      <p>{{ source.snippet }}</p>
    </article>
  </details>
</template>
<style scoped>
.references{margin-top:12px;font-size:12px;white-space:normal}.references summary{cursor:pointer;color:var(--color-accent);font-weight:600}.note{color:var(--color-text-muted);line-height:1.6}article{margin-top:12px;padding:12px;border:1px solid var(--color-border);border-radius:8px}small{display:block;margin:4px 0;color:var(--color-text-muted)}article p{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.7;max-height:320px;overflow:auto}
.references summary { display: flex; align-items: center; gap: .5em; list-style: none; }
.references summary::-webkit-details-marker { display: none; }
</style>
