<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import AdminSidebar from '@/components/admin/layout/AdminSidebar.vue'
import AdminHeader from '@/components/admin/layout/AdminHeader.vue'
import { useAdminStore } from '@/stores/admin'

const adminStore = useAdminStore()

const sidebarCollapsed = ref(false)
const isMobile = ref(false)
const drawerVisible = ref(false)

function toggleSidebar() {
  if (isMobile.value) {
    drawerVisible.value = !drawerVisible.value
  } else {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }
}

function checkScreenSize() {
  const width = window.innerWidth
  isMobile.value = width < 768
  if (width < 1024 && width >= 768) {
    sidebarCollapsed.value = true
  }
  if (width >= 1024) {
    sidebarCollapsed.value = false
  }
}

onMounted(() => {
  checkScreenSize()
  window.addEventListener('resize', checkScreenSize)
  if (!adminStore.adminInfo) {
    adminStore.fetchProfile().catch(() => {})
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', checkScreenSize)
})
</script>

<template>
  <div class="admin-layout">
    <template v-if="!isMobile">
      <AdminSidebar :collapsed="sidebarCollapsed" />
    </template>

    <el-drawer
      v-if="isMobile"
      v-model="drawerVisible"
      direction="ltr"
      :size="240"
      :show-close="false"
      :with-header="false"
      class="mobile-sidebar-drawer"
    >
      <AdminSidebar :collapsed="false" />
    </el-drawer>

    <div class="admin-main">
      <AdminHeader
        :collapsed="sidebarCollapsed"
        @toggle-sidebar="toggleSidebar"
      />
      <div class="admin-content">
        <router-view />
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.admin-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--bg-secondary, #F4F6FA);
}

.admin-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.admin-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

:deep(.mobile-sidebar-drawer) {
  .el-drawer__body {
    padding: 0;
  }
}

@media (max-width: 768px) {
  .admin-content {
    padding: 16px;
  }
}
</style>
