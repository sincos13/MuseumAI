<script setup>
defineProps({ name: { type: String, default: 'compass' } })
</script>

<template>
  <svg class="tour-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <template v-if="name === 'museum'">
      <path d="M2 8 12 2l10 6H2Zm1 13h18M4 18h16M5 8v10m4-10v10m6-10v10m4-10v10M2 23h20" />
    </template>
    <template v-else-if="name === 'picture'">
      <rect x="3" y="3" width="18" height="18" rx="1" /><circle cx="8" cy="8" r="1.5" /><path d="m4 18 5-6 4 4 3-3 5 6m-4-11h1" />
    </template>
    <template v-else-if="name === 'chat'">
      <path d="M21 11a9 9 0 0 1-9 9H8l-5 2 1-6a9 9 0 1 1 17-5Z" /><circle cx="11.5" cy="10.5" r="2" />
    </template>
    <template v-else-if="name === 'pin'">
      <path d="M19 9c0 5-7 13-7 13S5 14 5 9a7 7 0 0 1 14 0Z" /><circle cx="12" cy="9" r="2.5" />
    </template>
    <template v-else-if="name === 'calendar'">
      <rect x="4" y="5" width="16" height="16" rx="1" /><path d="M8 2v6m8-6v6M4 10h16m-12 4h3m-3 3h5" />
    </template>
    <template v-else-if="name === 'settings'">
      <path d="m10 2-.7 3-2 .8-2.7-1.4-2 3.4L5 10v3l-2.4 2.2 2 3.4 2.7-1.4 2 .8.7 3h4l.7-3 2-.8 2.7 1.4 2-3.4L19 13v-3l2.4-2.2-2-3.4-2.7 1.4-2-.8L14 2Z" /><circle cx="12" cy="11.5" r="3.5" />
    </template>
    <template v-else-if="name === 'user'">
      <circle cx="12" cy="7" r="4" /><path d="M4 22v-3a8 8 0 0 1 16 0v3" />
    </template>
    <template v-else-if="name === 'send'">
      <path d="m3 10 19-8-7 20-4-8-8-4Zm8 4L22 2" />
    </template>
    <template v-else-if="name === 'exit'">
      <path d="M14 4H5v16h9m-4-8h12m-4-4 4 4-4 4M5 4l5-2v20l-5-2" />
    </template>
    <template v-else-if="name === 'seal'">
      <path d="m12 2 3 2 3 .5 1 3 2 3-1 3-1 4-4 1-3 2-3-2-4-1-1-4-1-3 2-3 1-3 3-.5Z" /><path d="m9 13 5-5-1 7m-5-4 8 1" />
    </template>
    <template v-else-if="name === 'progress'">
      <path d="M4 20V10m8 10V4m8 16v-7M2 22h20" />
    </template>
    <template v-else>
      <circle cx="12" cy="12" r="9" /><path d="m17 5-3 9-9 5 4-10 8-4Zm-8 4 5 5M3 22 21 2" />
    </template>
  </svg>
</template>

<style scoped>
.tour-icon { width: 1em; height: 1em; flex: 0 0 auto; vertical-align: -.125em; }
</style>
