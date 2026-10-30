<script setup>
import { computed, inject, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  ChatDotRound,
  Collection,
  Compass,
  MapLocation,
  Menu,
  Setting,
  SwitchButton,
  User,
} from '@element-plus/icons-vue'
import { api } from '../../api/index.js'
import { useAuth } from '../../composables/useAuth.js'
import { useMuseumProfile } from '../../composables/useMuseumProfile.js'
import TourIcon from '../tour/TourIcon.vue'
import { useTourWorkbench } from '../../composables/useTourWorkbench.js'

defineProps({
  showSidebarToggle: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['toggle-sidebar'])

const showAuthModal = inject('showAuthModal', () => {})
const route = useRoute()
const { museum } = useMuseumProfile()
const { user, isAuthenticated, isAdmin, logout } = useAuth()
const isVisitor = computed(() => route.path.startsWith('/tour'))
const { activeTab } = useTourWorkbench()

const navItems = [
  { path: '/', title: '工作台', icon: ChatDotRound, requiresAuth: false },
  { path: '/tour', title: 'AI 导览', icon: Compass, requiresAuth: false },
  { path: '/curator', title: '导览助手', icon: MapLocation, requiresAuth: true },
  { path: '/exhibits', title: '展品浏览', icon: Collection, requiresAuth: true },
  { path: '/admin', title: '管理后台', icon: Setting, requiresAuth: true, requiresAdmin: true },
]

const displayedNavItems = computed(() => isVisitor.value ? [
  { path: '/', title: '工作台', tourIcon: 'chat' },
  { path: '/tour', title: '导览助手', tourIcon: 'pin' },
  { path: '/tour#exhibits', title: '展品浏览', tourIcon: 'picture' },
  { path: '/tour#progress', title: '展览信息', tourIcon: 'calendar' },
  { path: '/admin', title: '管理后台', tourIcon: 'settings', requiresAuth: true, requiresAdmin: true },
] : navItems)

function onNavSelect(path) {
  if (path === '/tour#exhibits') activeTab.value = 'exhibit'
  else if (path === '/tour#progress') activeTab.value = 'progress'
  else if (path === '/tour') activeTab.value = 'session'
}

const activeMenu = computed(() => {
  if (route.path.startsWith('/admin')) return '/admin'
  return route.path
})
const healthStatus = ref('checking')

async function checkHealth() {
  healthStatus.value = 'checking'
  try {
    const result = await api.health()
    healthStatus.value = result.ok ? 'healthy' : 'unhealthy'
  } catch {
    healthStatus.value = 'error'
  }
}

async function handleLogout() {
  await logout()
  window.location.reload()
}

function handleLoginClick() {
  showAuthModal(true)
}

onMounted(checkHealth)
</script>

<template>
  <header class="app-header">
    <div class="header-left">
      <el-button
        v-if="showSidebarToggle"
        text
        class="sidebar-toggle"
        data-testid="sidebar-toggle"
        @click="emit('toggle-sidebar')"
      >
        <el-icon><Menu /></el-icon>
      </el-button>

      <div class="logo">
        <img v-if="museum.logo_url" :src="museum.logo_url" :alt="`${museum.name} Logo`" class="logo-image" />
        <span v-else class="logo-mark" aria-hidden="true"><TourIcon v-if="isVisitor" name="museum" /><template v-else>🏛️</template></span>
        <span class="logo-title">MuseAI · {{ museum.short_name || museum.name }}</span>
      </div>
    </div>

    <el-menu
      :default-active="activeMenu"
      mode="horizontal"
      :ellipsis="false"
      router
      class="nav-menu"
      @select="onNavSelect"
    >
      <el-menu-item
        v-for="item in displayedNavItems"
        :key="item.path"
        :index="item.path"
        v-show="!item.requiresAdmin || isAdmin"
        :disabled="item.requiresAuth && !isAuthenticated"
      >
        <el-icon><TourIcon v-if="item.tourIcon" :name="item.tourIcon" /><component v-else :is="item.icon" /></el-icon>
        <span>{{ item.title }}</span>
      </el-menu-item>
    </el-menu>

    <div class="header-actions">
      <el-tag
        :type="healthStatus === 'healthy' ? 'success' : healthStatus === 'checking' ? 'info' : 'danger'"
        size="small"
      >
        {{ healthStatus === 'healthy' ? '服务正常' : healthStatus === 'checking' ? '检测中...' : '服务异常' }}
      </el-tag>

      <template v-if="isAuthenticated">
        <el-dropdown>
          <div class="user-trigger">
            <el-icon><User /></el-icon>
            <span class="user-text">{{ user?.email || '用户' }}</span>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="handleLogout">
                <el-icon><SwitchButton /></el-icon>
                退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </template>

      <template v-else>
        <el-button type="primary" size="small" @click="handleLoginClick">
          登录 / 注册
        </el-button>
      </template>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-3);
  min-height: 64px;
  padding: 0 var(--space-5);
  border-bottom: 1px solid rgba(77, 51, 31, 0.08);
  background: rgba(255, 252, 247, 0.96);
  backdrop-filter: blur(12px);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}

.nav-menu {
  min-width: 0;
  border-bottom: none;
  background: transparent;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  white-space: nowrap;
}

.logo-image { width: 32px; height: 32px; object-fit: contain; flex: 0 0 auto; }

.logo-mark {
  flex: 0 0 auto;
  color: var(--color-accent);
}

.logo-title {
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: var(--font-family-base);
  font-weight: var(--font-weight-semibold);
  letter-spacing: 0;
}

.nav-menu .el-menu-item {
  font-size: var(--font-size-body);
}

.nav-menu .el-menu-item.is-disabled {
  opacity: 0.5;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
}

.user-text {
  font-size: var(--font-size-body);
}

.sidebar-toggle {
  color: var(--color-text-primary);
}

@media (max-width: 900px) {
  .app-header {
    grid-template-columns: auto 1fr;
    gap: var(--space-2);
    padding: 0 var(--space-3);
  }

  .nav-menu {
    display: none;
  }

  .header-actions {
    justify-content: flex-end;
  }
}

@media (max-width: 767px) {
  .logo-title {
    max-width: 160px;
    font-size: var(--font-size-body);
  }

  .header-actions .el-tag {
    display: none;
  }

  .user-text {
    display: none;
  }
}
</style>
