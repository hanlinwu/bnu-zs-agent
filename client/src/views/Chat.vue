<script setup lang="ts">
import { ref, onMounted, computed, onBeforeUnmount } from 'vue'
import { useConversationStore } from '@/stores/conversation'
import { useChatStore } from '@/stores/chat'
import AppHeader from '@/components/common/AppHeader.vue'
import AppSidebar from '@/components/common/AppSidebar.vue'
import ChatContainer from '@/components/chat/ChatContainer.vue'

const conversationStore = useConversationStore()
const chatStore = useChatStore()

const sidebarCollapsed = ref(false)
const isMobile = ref(false)
const mobileDrawerVisible = ref(false)

function checkMobile() {
  isMobile.value = window.innerWidth < 768
  if (isMobile.value) {
    sidebarCollapsed.value = true
  }
}

function handleSidebarToggle(collapsed: boolean) {
  if (isMobile.value) {
    mobileDrawerVisible.value = !collapsed
  } else {
    sidebarCollapsed.value = collapsed
  }
}

function handleDrawerClose() {
  mobileDrawerVisible.value = false
}

const showDesktopSidebar = computed(() => !isMobile.value)
const showMobileDrawer = computed(() => isMobile.value)

onMounted(async () => {
  checkMobile()
  window.addEventListener('resize', checkMobile)

  await conversationStore.fetchConversations()

  if (conversationStore.conversations.length === 0) {
    const conv = await conversationStore.createConversation()
    chatStore.setConversationId(conv.id)
  } else {
    chatStore.setConversationId(conversationStore.conversations[0]!.id)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', checkMobile)
})
</script>

<template>
  <div class="chat-page">
    <AppHeader />

    <div class="chat-body">
      <template v-if="showDesktopSidebar">
        <AppSidebar
          :collapsed="sidebarCollapsed"
          @update:collapsed="handleSidebarToggle"
        />
      </template>

      <template v-if="showMobileDrawer">
        <el-drawer
          v-model="mobileDrawerVisible"
          direction="ltr"
          :size="280"
          :show-close="false"
          :with-header="false"
          @close="handleDrawerClose"
        >
          <AppSidebar
            :collapsed="false"
            @update:collapsed="handleSidebarToggle"
          />
        </el-drawer>

        <el-button
          class="mobile-menu-btn"
          text
          @click="mobileDrawerVisible = true"
        >
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </el-button>
      </template>

      <main class="chat-main">
        <ChatContainer />
      </main>
    </div>
  </div>
</template>

<style scoped lang="scss">
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100%;
  overflow: hidden;
  background: var(--bg-primary, #fff);
}

.chat-body {
  display: flex;
  flex: 1;
  min-height: 0;
  position: relative;
}

.chat-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.mobile-menu-btn {
  position: fixed;
  top: 68px;
  left: 8px;
  z-index: 50;
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: var(--bg-primary, #fff);
  box-shadow: var(--shadow-sm, 0 1px 3px rgba(0, 0, 0, 0.1));
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-primary, #1a1a2e);

  &:hover {
    color: var(--bnu-blue, #003DA5);
  }
}

:deep(.el-drawer) {
  background: var(--bg-secondary, #f4f6fa);
}

:deep(.el-drawer__body) {
  padding: 0;
  height: 100%;
}
</style>
