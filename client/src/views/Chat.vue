<script setup lang="ts">
import { ref, onMounted, computed, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { useConversationStore } from '@/stores/conversation'
import { useChatStore } from '@/stores/chat'
import { useUserStore } from '@/stores/user'
import AppHeader from '@/components/common/AppHeader.vue'
import AppSidebar from '@/components/common/AppSidebar.vue'
import ChatContainer from '@/components/chat/ChatContainer.vue'
import LoginForm from '@/components/auth/LoginForm.vue'
import { consumePendingChatQuestion } from '@/utils/chatNavigation'

const route = useRoute()
const conversationStore = useConversationStore()
const chatStore = useChatStore()
const userStore = useUserStore()

const sidebarCollapsed = ref(false)
const isMobile = ref(false)
const mobileDrawerVisible = ref(false)
const loginDialogVisible = ref(false)

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
const isLoggedIn = computed(() => !!userStore.token)

async function initializeChatPage() {
  if (!isLoggedIn.value) {
    loginDialogVisible.value = true
    return
  }

  const initialQuery = consumePendingChatQuestion()

  if (initialQuery) {
    chatStore.setConversationId(null)
    chatStore.clearMessages()
    void conversationStore.fetchConversations()
    await chatStore.sendMessage(initialQuery)
    return
  }

  await conversationStore.fetchConversations()

  const routeConversationId = typeof route.params.id === 'string' ? route.params.id : ''
  if (routeConversationId) {
    const target = conversationStore.conversations.find((c) => c.id === routeConversationId)
    if (target) {
      chatStore.setConversationId(target.id)
      await chatStore.loadMessages(target.id)
      return
    }
  }

  // Default entry for /chat: always start a new conversation
  if (conversationStore.conversations.length === 0) {
    chatStore.setConversationId(null)
    chatStore.clearMessages()
    return
  }

  chatStore.setConversationId(null)
  chatStore.clearMessages()
}

function handleAuthRequired() {
  loginDialogVisible.value = true
}

async function handleLoginSuccess() {
  loginDialogVisible.value = false
  await initializeChatPage()
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
  window.addEventListener('user-auth-required', handleAuthRequired)
  void initializeChatPage()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', checkMobile)
  window.removeEventListener('user-auth-required', handleAuthRequired)
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
        <ChatContainer v-if="isLoggedIn" />
        <div v-else class="chat-auth-placeholder">
          <el-empty description="登录后即可开始对话">
            <el-button type="primary" @click="loginDialogVisible = true">立即登录</el-button>
          </el-empty>
        </div>
      </main>
    </div>

    <el-dialog
      v-model="loginDialogVisible"
      title="登录后继续对话"
      width="460px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <LoginForm :redirect-on-success="false" @success="handleLoginSuccess" />
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100%;
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

.chat-auth-placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
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
