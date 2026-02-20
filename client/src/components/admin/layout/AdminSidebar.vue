<script setup lang="ts">
import { useAdminStore } from '@/stores/admin'
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Odometer,
  Collection,
  User,
  UserFilled,
  Key,
  Warning,
  Cpu,
  Calendar as CalendarIcon,
  Picture,
  Document,
  ChatLineRound,
  SetUp,
  Setting,
} from '@element-plus/icons-vue'
import { markRaw, type Component } from 'vue'
import { useSystemStore } from '@/stores/system'

const props = defineProps<{
  collapsed: boolean
}>()

const adminStore = useAdminStore()
const systemStore = useSystemStore()
const route = useRoute()
const router = useRouter()
const systemName = computed(() => systemStore.basic.system_name || '京师小智')
const systemLogo = computed(() => systemStore.basic.system_logo || '')
const defaultLogo = '/images/default-logo-shi.svg'
const displayLogo = computed(() => systemLogo.value || defaultLogo)

interface MenuItem {
  index: string
  title: string
  icon: Component
  permission?: string
}

interface MenuGroup {
  label: string
  items: MenuItem[]
}

const menuGroups: MenuGroup[] = [
  {
    label: '概览',
    items: [
      { index: '/admin/dashboard', title: '仪表盘', icon: markRaw(Odometer) },
    ],
  },
  {
    label: '业务管理',
    items: [
      { index: '/admin/knowledge', title: '知识库管理', icon: markRaw(Collection), permission: 'knowledge:read' },
      { index: '/admin/media', title: '多媒体资源', icon: markRaw(Picture), permission: 'media:read' },
      { index: '/admin/calendar', title: '招生日历', icon: markRaw(CalendarIcon), permission: 'calendar:read' },
    ],
  },
  {
    label: '用户与权限',
    items: [
      { index: '/admin/users', title: '用户管理', icon: markRaw(User), permission: 'user:read' },
      { index: '/admin/admins', title: '管理员管理', icon: markRaw(UserFilled), permission: 'admin:read' },
      { index: '/admin/roles', title: '角色权限', icon: markRaw(Key), permission: 'role:read' },
      { index: '/admin/workflows', title: '工作流管理', icon: markRaw(SetUp), permission: 'role:read' },
    ],
  },
  {
    label: '系统配置',
    items: [
      { index: '/admin/model', title: '模型配置', icon: markRaw(Cpu), permission: 'model:read' },
      { index: '/admin/system-config', title: '智能体配置', icon: markRaw(SetUp), permission: 'system_config:read' },
      { index: '/admin/sensitive', title: '敏感词库', icon: markRaw(Warning), permission: 'sensitive:read' },
      { index: '/admin/system-settings', title: '系统设置', icon: markRaw(Setting), permission: 'system_config:read' },
    ],
  },
  {
    label: '系统监控',
    items: [
      { index: '/admin/conversations', title: '对话日志', icon: markRaw(ChatLineRound), permission: 'conversation:read' },
      { index: '/admin/logs', title: '审计日志', icon: markRaw(Document), permission: 'log:read' },
    ],
  },
]

const visibleGroups = computed(() =>
  menuGroups
    .map(group => ({
      ...group,
      items: group.items.filter(item => !item.permission || adminStore.hasPermission(item.permission)),
    }))
    .filter(group => group.items.length > 0)
)

const allVisibleItems = computed(() => visibleGroups.value.flatMap(g => g.items))

const activeIndex = computed(() => {
  const path = route.path
  const match = allVisibleItems.value.find(item => path.startsWith(item.index))
  return match?.index || '/admin/dashboard'
})

function handleMenuSelect(index: string) {
  if (!index || route.path === index) return
  router.push(index)
}

onMounted(() => {
  systemStore.fetchBasic()
})
</script>

<template>
  <div class="admin-sidebar" :class="{ 'admin-sidebar--collapsed': props.collapsed }">
    <div class="sidebar-logo">
      <div class="logo-icon logo-icon--image">
        <img :src="displayLogo" :alt="`${systemName} Logo`" class="logo-image">
      </div>
      <transition name="fade">
        <span v-if="!props.collapsed" class="logo-title">{{ systemName }}管理</span>
      </transition>
    </div>

    <el-menu
      :default-active="activeIndex"
      :collapse="props.collapsed"
      :collapse-transition="false"
      @select="handleMenuSelect"
      class="sidebar-menu"
      background-color="transparent"
      text-color="rgba(255, 255, 255, 0.7)"
      active-text-color="#ffffff"
    >
      <template v-for="group in visibleGroups" :key="group.label">
        <div v-if="!props.collapsed" class="menu-group-label">{{ group.label }}</div>
        <div v-else class="menu-group-divider" />
        <el-menu-item
          v-for="item in group.items"
          :key="item.index"
          :index="item.index"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <template #title>{{ item.title }}</template>
        </el-menu-item>
      </template>
    </el-menu>
  </div>
</template>

<style lang="scss" scoped>
.admin-sidebar {
  width: 240px;
  height: 100%;
  background: linear-gradient(180deg, #0A1628 0%, #0F1D36 100%);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: width 0.3s ease;

  &--collapsed {
    width: 64px;
  }
}

.sidebar-logo {
  height: 56px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  flex-shrink: 0;
}

.logo-icon {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: linear-gradient(135deg, #003DA5, #1A5FBF);
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-icon--image {
  background: #ffffff;
}

.logo-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: 8px;
}

.logo-title {
  color: #ffffff;
  font-size: 0.9375rem;
  font-weight: 600;
  white-space: nowrap;
}

.menu-group-label {
  padding: 16px 20px 4px;
  font-size: 0.6875rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.35);
  text-transform: uppercase;
  letter-spacing: 1px;
  white-space: nowrap;
  overflow: hidden;

  &:first-child {
    padding-top: 8px;
  }
}

.menu-group-divider {
  height: 1px;
  margin: 8px 12px;
  background: rgba(255, 255, 255, 0.06);

  &:first-child {
    display: none;
  }
}

.sidebar-menu {
  flex: 1;
  overflow-y: auto;
  border-right: none;
  padding: 0 0 8px;

  &::-webkit-scrollbar {
    width: 0;
  }

  :deep(.el-menu-item) {
    height: 44px;
    line-height: 44px;
    margin: 2px 8px;
    border-radius: 8px;
    padding-left: 16px !important;

    &.is-active {
      background: rgba(0, 61, 165, 0.5) !important;
      color: #ffffff !important;
    }

    &:hover:not(.is-active) {
      background: rgba(255, 255, 255, 0.06) !important;
    }

    .el-icon {
      font-size: 1.125rem;
    }
  }

  :deep(.el-menu--collapse) {
    .el-menu-item {
      padding-left: 0 !important;
      justify-content: center;
      margin: 2px 4px;
    }
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
