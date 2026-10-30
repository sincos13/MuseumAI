<script setup>
import { computed, provide, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from './components/layout/AppHeader.vue'
import AppSidebar from './components/layout/AppSidebar.vue'
import AuthModal from './components/auth/AuthModal.vue'
import { AppDrawer } from './design-system/components/index.js'
import { useMuseumProfile } from './composables/useMuseumProfile.js'
import { useMediaQuery } from './composables/useMediaQuery.js'

const showAuthModal = ref(false)
provide('showAuthModal', (show = true) => {
  showAuthModal.value = show
})

const route = useRoute()
const { museum } = useMuseumProfile()
watch(() => [route.meta?.title, museum.value.name, museum.value.description, museum.value.language], ([page, name, description, language]) => {
  document.title = [page, name || 'MuseAI'].filter(Boolean).join(' · ')
  document.documentElement.lang = language || 'zh-CN'
  document.querySelector('meta[name="description"]')?.setAttribute('content', description || 'MuseAI 博物馆智能导览')
}, { immediate: true })
const isTourRoute = computed(() => route.path.startsWith('/tour'))
const isAdminRoute = computed(() => route.path.startsWith('/admin'))
const sidebarType = computed(() => route.meta?.sidebar ?? null)
const hasSidebar = computed(() => !!sidebarType.value)

const isMobile = useMediaQuery('(max-width: 767px)')
const isSidebarDrawerOpen = ref(false)

watch(
  () => route.fullPath,
  () => {
    isSidebarDrawerOpen.value = false
  },
)

function toggleSidebarDrawer() {
  if (!hasSidebar.value) return
  isSidebarDrawerOpen.value = !isSidebarDrawerOpen.value
}

function reloadPage() {
  window.location.reload()
}
</script>

<template>
  <div class="app-container" :class="{ 'visitor-theme': isTourRoute }">
    <template v-if="isAdminRoute">
      <router-view />
    </template>

    <template v-else>
      <AppHeader
        :show-sidebar-toggle="isMobile && hasSidebar"
        @toggle-sidebar="toggleSidebarDrawer"
      />

      <div class="app-body">
        <AppSidebar v-if="hasSidebar && !isMobile" :type="sidebarType" />

        <AppDrawer
          v-if="hasSidebar && isMobile"
          :open="isSidebarDrawerOpen"
          title="侧边栏"
          @update:open="isSidebarDrawerOpen = $event"
        >
          <AppSidebar :type="sidebarType" />
        </AppDrawer>

        <main
          class="app-main"
          :class="{ 'app-main--no-padding': isTourRoute }"
        >
          <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </main>
      </div>
    </template>

    <AuthModal v-model:visible="showAuthModal" @success="reloadPage" />
  </div>
</template>

<style>
@import './styles/custom.css';
@import './styles/visitor-theme.css';

.app-main {
  overflow: auto;
  padding: var(--space-fluid-md);
  background: var(--color-bg-base);
}

.app-main--no-padding {
  padding: 0;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--duration-slow) var(--ease-default);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 767px) {
  .app-main {
    padding: var(--space-3);
  }
}
</style>
