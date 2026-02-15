<script setup lang="ts">
import { useAdminStore } from '@/stores/admin'
import { computed } from 'vue'
import { useRoute } from 'vue-router'
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
} from '@element-plus/icons-vue'
import { markRaw, type Component } from 'vue'

const props = defineProps<{
  collapsed: boolean
}>()

const adminStore = useAdminStore()
const route = useRoute()

interface MenuItem {
  index: string
  title: string
  icon: Component
  permission?: string
}

const menuItems: MenuItem[] = [
  { index: '/admin/dashboard', title: '仪表盘', icon: markRaw(Odometer) },
  { index: '/admin/knowledge', title: '知识库管理', icon: markRaw(Collection), permission: 'knowledge:read' },
  { index: '/admin/users', title: '用户管理', icon: markRaw(User), permission: 'user:read' },
  { index: '/admin/admins', title: '管理员管理', icon: markRaw(UserFilled), permission: 'admin:read' },
  { index: '/admin/roles', title: '角色权限', icon: markRaw(Key), permission: 'role:read' },
  { index: '/admin/sensitive', title: '敏感词库', icon: markRaw(Warning), permission: 'sensitive:read' },
  { index: '/admin/model', title: '模型配置', icon: markRaw(Cpu), permission: 'model:read' },
  { index: '/admin/calendar', title: '招生日历', icon: markRaw(CalendarIcon), permission: 'calendar:read' },
  { index: '/admin/media', title: '多媒体资源', icon: markRaw(Picture), permission: 'media:read' },
  { index: '/admin/logs', title: '审计日志', icon: markRaw(Document), permission: 'log:read' },
]

const visibleItems = computed(() =>
  menuItems.filter(item => !item.permission || adminStore.hasPermission(item.permission))
)

const activeIndex = computed(() => {
  const path = route.path
  const match = visibleItems.value.find(item => path.startsWith(item.index))
  return match?.index || '/admin/dashboard'
})
</script>

<template>
  <div class="admin-sidebar" :class="{ 'admin-sidebar--collapsed': props.collapsed }">
    <div class="sidebar-logo">
      <div class="logo-icon">
        <span class="logo-text-icon">京</span>
      </div>
      <transition name="fade">
        <span v-if="!props.collapsed" class="logo-title">京师小智管理</span>
      </transition>
    </div>

    <el-menu
      :default-active="activeIndex"
      :collapse="props.collapsed"
      :collapse-transition="false"
      router
      class="sidebar-menu"
      background-color="transparent"
      text-color="rgba(255, 255, 255, 0.7)"
      active-text-color="#ffffff"
    >
      <el-menu-item
        v-for="item in visibleItems"
        :key="item.index"
        :index="item.index"
      >
        <el-icon><component :is="item.icon" /></el-icon>
        <template #title>{{ item.title }}</template>
      </el-menu-item>
    </el-menu>
  </div>
</template>

<style lang="scss" scoped>
.admin-sidebar {
  width: 240px;
  height: 100vh;
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

.logo-text-icon {
  color: #ffffff;
  font-size: 16px;
  font-weight: 700;
}

.logo-title {
  color: #ffffff;
  font-size: 15px;
  font-weight: 600;
  white-space: nowrap;
}

.sidebar-menu {
  flex: 1;
  overflow-y: auto;
  border-right: none;
  padding: 8px 0;

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
      font-size: 18px;
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
