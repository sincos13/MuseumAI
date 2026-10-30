<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AdminIcon from '../../components/admin/AdminIcon.vue'
import { useAuth } from '../../composables/useAuth.js'
import { useMuseumProfile } from '../../composables/useMuseumProfile.js'

const route = useRoute()
const { museum } = useMuseumProfile()
const { user, userRole, logout } = useAuth()

const museumName = computed(() => museum.value.short_name || museum.value.name || '本馆')
const brandEnglish = computed(() => {
  if (museum.value.museum_id === 'jingheng-city') return 'JINGHENG ANCIENT CITY MUSEUM'
  return 'MUSEUM GUIDE SYSTEM'
})
const displayName = computed(() => {
  if (userRole.value === 'admin') return '管理员'
  return user.value?.name || user.value?.email || '访问者'
})

const topTabs = [
  { key: 'guide', label: '导览管理', icon: 'hall', to: '/admin/overview' },
  { key: 'exhibit', label: '展品管理', icon: 'vase', to: '/admin/exhibits' },
  { key: 'stats', label: '数据统计', icon: 'chart', to: '/admin/llm-traces' },
  { key: 'settings', label: '系统设置', icon: 'settings', to: '/admin/museum' },
]

const navGroups = computed(() => [
  {
    label: '导览台',
    items: [
      { label: `${museumName.value}导览配置`, path: '/admin/overview', icon: 'guide' },
      { label: '路线管理', path: '/admin/tour-paths', icon: 'route' },
      { label: '语音讲解管理', path: '/admin/tts-personas', icon: 'audio' },
      { label: '知识库管理', path: '/admin/documents', icon: 'image' },
      { label: '展厅设置', path: '/admin/halls', icon: 'hall' },
    ],
  },
  {
    label: '展品管理',
    icon: 'vase',
    items: [
      { label: '展品管理', path: '/admin/exhibits', icon: 'vase' },
      { label: '馆方配置', path: '/admin/museum', icon: 'museum' },
      { label: '资料包导入', path: '/admin/import', icon: 'box' },
      { label: '提示词管理', path: '/admin/prompts', icon: 'chat' },
      { label: 'LLM 调用追踪', path: '/admin/llm-traces', icon: 'chip' },
    ],
  },
])

const tabForPath = computed(() => {
  const path = route.path
  if (path.startsWith('/admin/exhibits')) return 'exhibit'
  if (path.startsWith('/admin/llm-traces')) return 'stats'
  if (path.startsWith('/admin/museum') || path.startsWith('/admin/prompts') || path.startsWith('/admin/import')) return 'settings'
  return 'guide'
})

function isNavActive(path) {
  return route.path === path || route.path.startsWith(`${path}/`)
}

const mobileNavOpen = ref(false)
watch(() => route.fullPath, () => { mobileNavOpen.value = false })

function closeMobileNav() {
  mobileNavOpen.value = false
}

async function handleLogout() {
  await logout()
  window.location.reload()
}

onMounted(() => {
  document.body.classList.add('admin-mode')
})

onBeforeUnmount(() => {
  document.body.classList.remove('admin-mode')
})
</script>

<template>
  <div class="admin-shell">
    <div
      v-if="mobileNavOpen"
      class="admin-nav-scrim"
      aria-hidden="true"
      @click="closeMobileNav"
    />

    <aside class="admin-sidebar" :class="{ 'is-open': mobileNavOpen }">
      <router-link class="admin-brand" to="/admin/overview" @click="closeMobileNav">
        <span class="admin-brand-mark"><AdminIcon name="museum" /></span>
        <span class="admin-brand-copy">
          <span class="admin-brand-name">{{ museumName }}</span>
          <span class="admin-brand-en">{{ brandEnglish }}</span>
        </span>
      </router-link>

      <nav class="admin-nav" aria-label="后台导航">
        <section
          v-for="(group, groupIndex) in navGroups"
          :key="group.label"
          class="admin-nav-group"
          :class="{ 'has-divider': groupIndex > 0 }"
        >
          <p class="admin-nav-label">
            <AdminIcon v-if="group.icon" :name="group.icon" class="admin-nav-label-icon" />
            <span>{{ group.label }}</span>
          </p>
          <router-link
            v-for="item in group.items"
            :key="`${group.label}-${item.path}`"
            :to="item.path"
            class="admin-nav-item"
            :class="{ 'is-active': isNavActive(item.path) }"
            @click="closeMobileNav"
          >
            <AdminIcon :name="item.icon" class="admin-nav-icon" />
            <span class="admin-nav-text">{{ item.label }}</span>
          </router-link>
        </section>
      </nav>

      <div class="admin-sidebar-art" aria-hidden="true" />
    </aside>

    <div class="admin-body">
      <header class="admin-topbar">
        <button type="button" class="admin-nav-toggle" aria-label="打开后台导航" @click="mobileNavOpen = true">
          <AdminIcon name="menu" />
        </button>

        <nav class="admin-tabs" aria-label="后台栏目">
          <router-link
            v-for="tab in topTabs"
            :key="tab.key"
            :to="tab.to"
            class="admin-tab"
            :class="{ 'is-active': tabForPath === tab.key }"
          >
            <AdminIcon :name="tab.icon" class="admin-tab-icon" />
            <span>{{ tab.label }}</span>
          </router-link>
        </nav>

        <div class="admin-topbar-actions">
          <el-dropdown trigger="click" popper-class="admin-user-popper">
            <button type="button" class="admin-user">
              <span class="admin-avatar"><AdminIcon name="user" /></span>
              <span class="admin-user-name">{{ displayName }}</span>
              <AdminIcon name="chevron-down" class="admin-user-chevron" />
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="handleLogout">
                  <AdminIcon name="logout" class="admin-dropdown-icon" />
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <main class="admin-content">
        <slot />
      </main>
    </div>
  </div>
</template>

<style scoped>
.admin-shell {
  --admin-ink: #2f261d;
  --admin-muted: #8b7a66;
  --admin-faint: #a99783;
  --admin-page: #f6f3ec;
  --admin-panel: #fdfbf7;
  --admin-line: #e9dfd0;
  --admin-brown: #7c4f2b;
  --admin-brown-deep: #5b3b22;
  --admin-gold: #b08a57;
  --admin-serif: 'MuseAI Song', 'Noto Serif SC', 'Source Han Serif SC', 'Songti SC', SimSun, serif;
  --admin-sans: 'Noto Sans SC', 'Microsoft YaHei', 'PingFang SC', 'Hiragino Sans GB', sans-serif;
  display: flex;
  width: 100%;
  height: 100vh;
  height: 100svh;
  overflow: hidden;
  background: var(--admin-page);
  color: var(--admin-ink);
  font-family: var(--admin-sans);
  --el-font-family: var(--admin-sans);
  --el-color-primary: #8a5a2f;
  --el-color-primary-light-3: #a9805a;
  --el-color-primary-light-5: #c0a184;
  --el-color-primary-light-7: #ddcbb8;
  --el-color-primary-light-8: #eadbc9;
  --el-color-primary-light-9: #f4ebe0;
  --el-color-primary-dark-2: #6f4525;
  --el-text-color-primary: #2f261d;
  --el-text-color-regular: #5f5142;
  --el-border-color: #e6dccd;
  --el-border-color-light: #ece4d8;
  --el-border-color-lighter: #f1eadf;
  --el-fill-color-blank: #fffdfa;
  --el-bg-color: #fffdfa;
  --el-bg-color-page: var(--admin-page);
  --el-border-radius-base: 6px;
}

.admin-sidebar {
  position: relative;
  z-index: 30;
  display: flex;
  flex: 0 0 266px;
  flex-direction: column;
  width: 266px;
  height: 100%;
  overflow: hidden;
  background: #29251f;
  color: #d8cbb8;
}

.admin-sidebar::before {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(120% 38% at 0% 0%, rgba(158, 120, 78, 0.12), transparent 60%),
    linear-gradient(180deg, #2c2822 0%, #27231d 58%, #221e19 100%);
  content: '';
  pointer-events: none;
}

.admin-brand {
  position: relative;
  z-index: 2;
  display: flex;
  flex: 0 0 100px;
  align-items: center;
  gap: 13px;
  height: 100px;
  padding: 0 22px;
  border-bottom: 1px solid rgba(216, 192, 160, 0.14);
  color: inherit;
  text-decoration: none;
}

.admin-brand-mark {
  display: grid;
  flex: 0 0 auto;
  width: 44px;
  height: 44px;
  place-items: center;
  color: #b79765;
  font-size: 42px;
}

.admin-brand-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 5px;
}

.admin-brand-name {
  overflow: hidden;
  color: #f0e6d6;
  font-family: var(--admin-serif);
  font-size: 23px;
  font-weight: 600;
  letter-spacing: 0.05em;
  line-height: 1.15;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.admin-brand-en {
  overflow: hidden;
  color: #9c8b74;
  font-size: 7.5px;
  letter-spacing: 0.17em;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.admin-nav {
  position: relative;
  z-index: 2;
  flex: 1;
  padding: 0 17px 24px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(190, 160, 120, 0.25) transparent;
}

.admin-nav-group {
  margin-top: 24px;
}

.admin-nav-group.has-divider {
  padding-top: 21px;
  border-top: 1px solid rgba(216, 192, 160, 0.14);
  margin-top: 22px;
}

.admin-nav-label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 8px;
  padding: 0 10px;
  color: #a99881;
  font-size: 12.5px;
  font-weight: 400;
  letter-spacing: 0.16em;
}

.admin-nav-label-icon {
  color: #b08f62;
  font-size: 15px;
}

.admin-nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 41px;
  margin-top: 3px;
  padding: 0 11px;
  border: 1px solid transparent;
  border-radius: 7px;
  color: #d3c6b3;
  font-size: 13.5px;
  letter-spacing: 0.02em;
  text-decoration: none;
  transition: background 0.18s ease, color 0.18s ease, border-color 0.18s ease;
}

.admin-nav-icon {
  color: #a99881;
  font-size: 18px;
  transition: color 0.18s ease;
}

.admin-nav-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.admin-nav-item:hover {
  background: rgba(255, 240, 214, 0.06);
  color: #f1e5d2;
}

.admin-nav-item:hover .admin-nav-icon {
  color: #cbb392;
}

.admin-nav-item.is-active {
  border-color: rgba(226, 195, 151, 0.16);
  background: linear-gradient(112deg, #7c5536 0%, #64452b 52%, #5b3d26 100%);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2), inset 0 1px 0 rgba(255, 226, 185, 0.1);
  color: #f8eedd;
}

.admin-nav-item.is-active .admin-nav-icon {
  color: #e4c697;
}

.admin-sidebar-art {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 1;
  height: 232px;
  background: url('/admin/sidebar-art.webp') center bottom / 100% auto no-repeat;
  opacity: 0.72;
  pointer-events: none;
  -webkit-mask-image: linear-gradient(180deg, transparent 0%, #000 24%);
  mask-image: linear-gradient(180deg, transparent 0%, #000 24%);
}

.admin-body {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  height: 100%;
}

.admin-topbar {
  position: relative;
  z-index: 10;
  display: flex;
  flex: 0 0 68px;
  align-items: center;
  height: 68px;
  padding: 0 34px;
  background: var(--admin-page);
}

.admin-topbar::after {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  height: 1px;
  background: linear-gradient(90deg, rgba(120, 94, 64, 0.1), rgba(120, 94, 64, 0.04) 72%, transparent);
  content: '';
}

.admin-tabs {
  display: flex;
  height: 100%;
  gap: 38px;
}

.admin-tab {
  position: relative;
  display: flex;
  align-items: center;
  gap: 9px;
  height: 100%;
  color: #726352;
  font-size: 14.5px;
  letter-spacing: 0.03em;
  text-decoration: none;
  transition: color 0.18s ease;
}

.admin-tab-icon {
  font-size: 18px;
  color: #98846c;
  transition: color 0.18s ease;
}

.admin-tab:hover {
  color: #4f3e2c;
}

.admin-tab.is-active {
  color: #8a5627;
  font-weight: 500;
}

.admin-tab.is-active .admin-tab-icon {
  color: #a3713d;
}

.admin-tab.is-active::after {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  height: 2px;
  background: linear-gradient(90deg, #a06a35, #c09057 50%, #a06a35);
  content: '';
}

.admin-topbar-actions {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-left: auto;
}

.admin-user {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 4px 6px;
  border: 0;
  background: transparent;
  color: #574837;
  font-family: inherit;
  font-size: 13.5px;
  cursor: pointer;
}

.admin-avatar {
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  border: 1px solid #e1d2bd;
  border-radius: 50%;
  background: #f0e6d7;
  color: #8e6a41;
  font-size: 17px;
}

.admin-user-chevron {
  color: #9d8a72;
  font-size: 14px;
}

.admin-user:hover .admin-user-name {
  color: #8a5627;
}

.admin-nav-toggle {
  display: none;
  padding: 0;
  border: 0;
  background: transparent;
  color: #6b5740;
  font-size: 22px;
  cursor: pointer;
}

.admin-content {
  flex: 1;
  min-height: 0;
  padding: 6px 16px 30px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(150, 122, 86, 0.28) transparent;
}

.admin-content::-webkit-scrollbar,
.admin-nav::-webkit-scrollbar {
  width: 6px;
}

.admin-content::-webkit-scrollbar-thumb,
.admin-nav::-webkit-scrollbar-thumb {
  border-radius: 3px;
  background: rgba(150, 122, 86, 0.25);
}

.admin-content::-webkit-scrollbar-track,
.admin-nav::-webkit-scrollbar-track {
  background: transparent;
}

.admin-nav-scrim {
  display: none;
}

@media (max-width: 1180px) {
  .admin-sidebar {
    flex-basis: 240px;
    width: 240px;
  }

  .admin-brand-name {
    font-size: 21px;
  }

  .admin-tabs {
    gap: 26px;
  }

  .admin-content {
    padding: 4px 14px 24px;
  }
}

@media (max-width: 900px) {
  .admin-sidebar {
    position: fixed;
    top: 0;
    bottom: 0;
    left: 0;
    z-index: 60;
    width: 258px;
    transform: translateX(-102%);
    transition: transform 0.24s ease;
  }

  .admin-sidebar.is-open {
    transform: translateX(0);
  }

  .admin-nav-scrim {
    position: fixed;
    inset: 0;
    z-index: 55;
    display: block;
    background: rgba(35, 28, 21, 0.42);
    backdrop-filter: blur(2px);
  }

  .admin-nav-toggle {
    display: grid;
    place-items: center;
    margin-right: 14px;
  }

  .admin-topbar {
    padding: 0 16px;
  }

  .admin-tabs {
    flex: 1;
    gap: 20px;
    overflow-x: auto;
    scrollbar-width: none;
  }

  .admin-tabs::-webkit-scrollbar {
    display: none;
  }

  .admin-tab {
    flex: 0 0 auto;
    gap: 6px;
    font-size: 13.5px;
  }

  .admin-user-name {
    display: none;
  }

  .admin-content {
    padding: 2px 12px 22px;
  }
}
</style>
