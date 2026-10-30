<script setup>
defineProps({
  name: { type: String, default: 'vase' },
})
</script>

<template>
  <svg
    class="admin-icon"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.45"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <template v-if="name === 'museum'">
      <path d="M2.5 8.6 12 3l9.5 5.6" />
      <path d="M5.2 8.6h13.6M3.6 11h16.8" />
      <path d="M6 11v9.4M10 11v9.4M14 11v9.4M18 11v9.4" />
      <path d="M3.4 20.4h17.2M5 22h14" />
    </template>
    <template v-else-if="name === 'monitor'">
      <rect x="3" y="4.2" width="18" height="12.6" rx="1.5" />
      <path d="M8.4 21h7.2M12 16.8V21M7 8.2h6M7 11.4h10" />
    </template>
    <template v-else-if="name === 'guide'">
      <circle cx="9.6" cy="7.2" r="3.1" />
      <path d="M3.8 20.4v-1.2c0-2.8 2.5-4.7 5.8-4.7 1 0 1.9.2 2.7.5" />
      <path d="M17.6 13.4c1.9 2.1 2.9 3.5 2.9 4.7a2.9 2.9 0 0 1-5.8 0c0-1.2 1-2.6 2.9-4.7Z" />
      <circle cx="17.6" cy="18.2" r="0.9" />
    </template>
    <template v-else-if="name === 'route'">
      <path d="m3.2 6.2 6-2 5.6 2 6-2v13.6l-6 2-5.6-2-6 2V6.2Z" />
      <path d="M9.2 4.2v13.6M14.8 6.2v13.6" />
    </template>
    <template v-else-if="name === 'audio'">
      <path d="M4 9.6v4.8h3.2L11.6 18V6L7.2 9.6H4Z" />
      <path d="M15.2 9.2a4.4 4.4 0 0 1 0 5.6M17.8 6.6a8 8 0 0 1 0 10.8" />
    </template>
    <template v-else-if="name === 'points'">
      <path d="M9.2 6h10.4M9.2 12h10.4M9.2 18h10.4" />
      <circle cx="4.8" cy="6" r="0.9" />
      <circle cx="4.8" cy="12" r="0.9" />
      <circle cx="4.8" cy="18" r="0.9" />
    </template>
    <template v-else-if="name === 'image'">
      <rect x="3.2" y="4.2" width="17.6" height="15.6" rx="1.5" />
      <circle cx="8.2" cy="9.2" r="1.5" />
      <path d="m4 17.6 5.2-5.2 3.8 3.8 3.1-3.1 4.2 4.2" />
    </template>
    <template v-else-if="name === 'hall'">
      <path d="M3 9.4 12 3l9 6.4" />
      <path d="M4.6 9.4h14.8M5.4 21V9.4M9.8 21V9.4M14.2 21V9.4M18.6 21V9.4" />
      <path d="M3.6 21h16.8" />
    </template>
    <template v-else-if="name === 'vase'">
      <path d="M9.4 3.2h5.2M10.6 3.2v2.1c-2 1.4-3.1 3.3-3.1 5.5V15c0 3 2 5.1 4.5 5.1s4.5-2.1 4.5-5.1v-4.2c0-2.2-1.1-4.1-3.1-5.5V3.2" />
      <path d="M7.4 8.8c-2 0-3.1 1.3-3.1 3.1s1.1 3.1 3.1 3.1M16.6 8.8c2 0 3.1 1.3 3.1 3.1s-1.1 3.1-3.1 3.1" />
      <path d="M9.8 20.4h4.4" />
    </template>
    <template v-else-if="name === 'box'">
      <path d="M21 8 12 3 3 8l9 5 9-5Z" />
      <path d="M3 8v8l9 5 9-5V8M12 13v8" />
    </template>
    <template v-else-if="name === 'chat'">
      <path d="M21 11.5a8.5 8.5 0 0 1-12.6 7.6L3 21l1.9-5.4A8.5 8.5 0 1 1 21 11.5Z" />
      <path d="M8 10h8M8 14h5" />
    </template>
    <template v-else-if="name === 'user'">
      <circle cx="12" cy="7.4" r="3.5" />
      <path d="M4.6 21v-1.1c0-3.4 3.3-5.5 7.4-5.5s7.4 2.1 7.4 5.5V21" />
    </template>
    <template v-else-if="name === 'chip'">
      <rect x="6.2" y="6.2" width="11.6" height="11.6" rx="1.4" />
      <rect x="9.6" y="9.6" width="4.8" height="4.8" rx="0.7" />
      <path d="M9.2 1.6v3M14.8 1.6v3M9.2 19.4v3M14.8 19.4v3M1.6 9.2h3M1.6 14.8h3M19.4 9.2h3M19.4 14.8h3" />
    </template>
    <template v-else-if="name === 'search'">
      <circle cx="10.6" cy="10.6" r="6.4" />
      <path d="m15.4 15.4 5 5" />
    </template>
    <template v-else-if="name === 'reset'">
      <path d="M20 11.4a8 8 0 1 1-2.3-5.9" />
      <path d="M20 4.4v7h-7" />
    </template>
    <template v-else-if="name === 'plus'">
      <circle cx="12" cy="12" r="8.6" />
      <path d="M12 8v8M8 12h8" />
    </template>
    <template v-else-if="name === 'edit'">
      <path d="m4 20 4.6-1.1 10-10a2.15 2.15 0 0 0-3-3l-10 10L4 20Z" />
      <path d="m13.5 6.8 3.8 3.8" />
    </template>
    <template v-else-if="name === 'trash'">
      <path d="M4 7h16M9.2 7V4.2h5.6V7M6.6 7l.9 12.8h9l.9-12.8" />
      <path d="M10.2 10.8v5.6M13.8 10.8v5.6" />
    </template>
    <template v-else-if="name === 'chevron-down'">
      <path d="m6 9 6 6 6-6" />
    </template>
    <template v-else-if="name === 'logout'">
      <path d="M14 4H5v16h9M10.4 12h10.4M16.8 8l4 4-4 4" />
    </template>
    <template v-else-if="name === 'menu'">
      <path d="M3.6 6h16.8M3.6 12h16.8M3.6 18h16.8" />
    </template>
    <template v-else-if="name === 'frame'">
      <rect x="3.4" y="4.2" width="17.2" height="15.6" rx="1.4" />
      <path d="M8 4.2v15.6M8 8.6h8.4M8 12h8.4M8 15.4h5.4" />
    </template>
    <template v-else-if="name === 'seal'">
      <rect x="4.6" y="3.6" width="14.8" height="16.8" rx="1.2" />
      <path d="M8.2 8h7.6M8.2 11.6h7.6M10.2 15.2h3.6" />
    </template>
    <template v-else-if="name === 'warning'">
      <path d="M12 3.4 21.6 20.4H2.4L12 3.4Z" />
      <path d="M12 9.2v4.6" />
      <circle cx="12" cy="17.2" r="0.9" fill="currentColor" stroke="none" />
    </template>
    <template v-else-if="name === 'star'">
      <path d="m12 3.4 2.7 5.5 6.1.9-4.4 4.3 1 6.1L12 17.3l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9L12 3.4Z" />
    </template>
    <template v-else-if="name === 'chart'">
      <circle cx="12" cy="12" r="8.6" />
      <path d="M8.4 15.6V11M12 15.6V7.8M15.6 15.6v-6" />
    </template>
    <template v-else-if="name === 'settings'">
      <circle cx="12" cy="12" r="3.1" />
      <path d="M19.4 13.4a7.6 7.6 0 0 0 0-2.8l2-1.5-2-3.4-2.3.9a7.6 7.6 0 0 0-2.4-1.4L14.4 2h-4l-.3 2.4a7.6 7.6 0 0 0-2.4 1.4l-2.3-.9-2 3.4 2 1.5a7.6 7.6 0 0 0 0 2.8l-2 1.5 2 3.4 2.3-.9a7.6 7.6 0 0 0 2.4 1.4l.3 2.4h4l.3-2.4a7.6 7.6 0 0 0 2.4-1.4l2.3.9 2-3.4-2-1.5Z" />
    </template>
    <template v-else-if="name === 'close'">
      <path d="m6 6 12 12M18 6 6 18" />
    </template>
    <template v-else-if="name === 'check'">
      <path d="m4.4 12.2 4.8 4.8L19.6 6.6" />
    </template>
    <template v-else-if="name === 'arrow-right'">
      <path d="M4 12h15M13.5 6.5 20 12l-6.5 5.5" />
    </template>
    <template v-else>
      <circle cx="12" cy="12" r="8.6" />
    </template>
  </svg>
</template>

<style scoped>
.admin-icon {
  display: block;
  flex: 0 0 auto;
  width: 1em;
  height: 1em;
}
</style>
