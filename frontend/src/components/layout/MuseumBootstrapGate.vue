<script setup>
import { onMounted } from 'vue'
import { useMuseumProfile } from '../../composables/useMuseumProfile.js'

const { ready, loading, error, loadProfile } = useMuseumProfile()
onMounted(loadProfile)
</script>

<template>
  <slot v-if="ready" />
  <main v-else class="bootstrap-state" aria-live="polite" :aria-busy="loading">
    <h1>MuseAI</h1>
    <p v-if="loading">正在加载博物馆导览配置…</p>
    <template v-else-if="error">
      <p role="alert">{{ error }}</p>
      <button type="button" @click="loadProfile">重新加载</button>
    </template>
  </main>
</template>

<style scoped>
.bootstrap-state { min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 16px; padding: 24px; text-align: center; background: var(--color-bg-base); color: var(--color-text-primary); }
.bootstrap-state h1 { color: var(--color-accent); }
.bootstrap-state button { padding: 10px 24px; border: 1px solid var(--color-accent); border-radius: 8px; background: var(--color-bg-elevated); color: var(--color-accent); cursor: pointer; }
</style>
