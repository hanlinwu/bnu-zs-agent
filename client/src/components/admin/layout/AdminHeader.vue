<script setup lang="ts">
import { useAdminStore } from '@/stores/admin'
import { useThemeStore } from '@/stores/theme'
import { useRoute, useRouter } from 'vue-router'
import { computed } from 'vue'
import {
  Fold,
  Expand,
  SwitchButton,
  User,
  ArrowDown,
  Sunny,
  Moon,
} from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'

defineProps<{
  collapsed: boolean
}>()

const emit = defineEmits<{
  (e: 'toggle-sidebar'): void
}>()

const adminStore = useAdminStore()
const themeStore = useThemeStore()
const route = useRoute()
const router = useRouter()

const breadcrumbs = computed(() => {
  const crumbs: { title: string; path?: string }[] = [{ title: '管理后台', path: '/admin/dashboard' }]
  if (route.meta?.title && route.name !== 'AdminDashboard') {
    crumbs.push({ title: route.meta.title as string })
  }
  return crumbs
})

const adminName = computed(() => adminStore.adminInfo?.display_name || adminStore.adminInfo?.username || '管理员')
const isDark = computed(() => themeStore.mode === 'dark')

async function handleLogout() {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '退出确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    adminStore.logout()
    router.push('/admin/login')
  } catch {
    // cancelled
  }
}

function handleCommand(command: string) {
  if (command === 'logout') {
    handleLogout()
  } else if (command === 'profile') {
    router.push('/admin/profile')
  }
}

function handleThemeToggle(e: MouseEvent) {
  themeStore.toggleTheme(e)
}
</script>

<template>
  <header class="admin-header">
    <div class="header-left">
      <el-button
        text
        class="toggle-btn"
        @click="emit('toggle-sidebar')"
      >
        <el-icon :size="18">
          <Fold v-if="!collapsed" />
          <Expand v-else />
        </el-icon>
      </el-button>

      <el-breadcrumb separator="/">
        <el-breadcrumb-item
          v-for="(crumb, index) in breadcrumbs"
          :key="index"
          :to="crumb.path ? { path: crumb.path } : undefined"
        >
          {{ crumb.title }}
        </el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <div class="header-right">
      <el-button
        text
        class="theme-toggle-btn"
        @click="handleThemeToggle"
        :title="isDark ? '切换浅色主题' : '切换深色主题'"
      >
        <el-icon :size="18">
          <Moon v-if="!isDark" />
          <Sunny v-else />
        </el-icon>
      </el-button>

      <el-dropdown trigger="click" @command="handleCommand">
        <div class="admin-profile">
          <el-avatar :size="32" class="admin-avatar">
            <el-icon><User /></el-icon>
          </el-avatar>
          <span class="admin-name">{{ adminName }}</span>
          <el-icon class="dropdown-arrow"><ArrowDown /></el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile">
              <el-icon><User /></el-icon>
              个人信息
            </el-dropdown-item>
            <el-dropdown-item divided command="logout">
              <el-icon><SwitchButton /></el-icon>
              退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<style lang="scss" scoped>
.admin-header {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background: var(--bg-primary, #ffffff);
  border-bottom: 1px solid var(--border-color, #E2E6ED);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toggle-btn {
  padding: 6px;
  color: var(--text-secondary, #5A5A72);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.theme-toggle-btn {
  color: var(--text-secondary, #5A5A72);
  border-radius: 8px;
  padding: 6px;

  &:hover {
    background: var(--bg-secondary, #F4F6FA);
    color: var(--text-primary, #1A1A2E);
  }
}

.admin-profile {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 8px;
  transition: background 0.2s;

  &:hover {
    background: var(--bg-secondary, #F4F6FA);
  }
}

.admin-avatar {
  background: var(--bnu-blue, #003DA5);
  color: #ffffff;
}

.admin-name {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary, #1A1A2E);
}

.dropdown-arrow {
  font-size: 0.75rem;
  color: var(--text-secondary, #5A5A72);
}

:deep(.el-breadcrumb) {
  font-size: 0.875rem;

  .el-breadcrumb__inner {
    color: var(--text-secondary, #5A5A72);
  }

  .el-breadcrumb__item:last-child .el-breadcrumb__inner {
    color: var(--text-primary, #1A1A2E);
    font-weight: 500;
  }
}
</style>
