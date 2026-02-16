<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  ChatLineSquare, Fold, Expand, Setting,
  SwitchButton, User,
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { useConversationStore } from '@/stores/conversation'
import { useChatStore } from '@/stores/chat'
import { generateAvatar } from '@/utils/avatar'
import ConversationList from '@/components/conversation/ConversationList.vue'

const props = defineProps<{
  collapsed: boolean
}>()

const emit = defineEmits<{
  'update:collapsed': [value: boolean]
}>()

const userStore = useUserStore()
const conversationStore = useConversationStore()
const chatStore = useChatStore()
const router = useRouter()

const userNickname = computed(() => userStore.userInfo?.nickname || '用户')
const userAvatar = computed(() => userStore.userInfo?.avatar_url || generateAvatar(userNickname.value))

function handleNewConversation() {
  chatStore.setConversationId(null)
  chatStore.clearMessages()
}

function toggleCollapse() {
  emit('update:collapsed', !props.collapsed)
}

function handleLogout() {
  chatStore.clearMessages()
  chatStore.setConversationId(null)
  conversationStore.conversations = []
  userStore.logout()
  router.replace('/login')
}

function handleSettingsCommand(command: string) {
  if (command === 'logout') {
    handleLogout()
  } else if (command === 'settings') {
    router.push('/settings')
  }
}
</script>

<template>
  <aside class="app-sidebar" :class="{ 'is-collapsed': collapsed }">
    <div class="sidebar-inner">
      <div class="sidebar-top">
        <el-button
          type="primary"
          class="new-chat-btn"
          @click="handleNewConversation"
        >
          <el-icon><ChatLineSquare /></el-icon>
          <span v-show="!collapsed" class="btn-text">新对话</span>
        </el-button>
      </div>

      <div v-show="!collapsed" class="sidebar-middle">
        <ConversationList />
      </div>

      <div class="sidebar-bottom">
        <div v-show="!collapsed" class="user-card">
          <el-avatar :size="36" :src="userAvatar">
            <span class="avatar-fallback">{{ userNickname.charAt(0) }}</span>
          </el-avatar>
          <div class="user-info">
            <span class="user-name">{{ userNickname }}</span>
          </div>

          <el-dropdown trigger="click" @command="handleSettingsCommand" placement="top-end">
            <el-button class="settings-btn" text>
              <el-icon :size="16"><Setting /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="settings">
                  <el-icon><User /></el-icon>
                  <span>个人中心</span>
                </el-dropdown-item>
                <el-dropdown-item command="logout" divided>
                  <el-icon><SwitchButton /></el-icon>
                  <span>退出登录</span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <el-button
          class="collapse-btn"
          text
          @click="toggleCollapse"
        >
          <el-icon :size="18">
            <Fold v-if="!collapsed" />
            <Expand v-else />
          </el-icon>
        </el-button>
      </div>
    </div>
  </aside>
</template>

<style scoped lang="scss">
.app-sidebar {
  width: 280px;
  height: 100%;
  background: var(--bg-secondary, #f4f6fa);
  border-right: 1px solid var(--border-color, #e2e6ed);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  transition: width 0.3s ease;
  overflow: hidden;

  &.is-collapsed {
    width: 64px;

    .new-chat-btn {
      width: 40px;
      padding: 8px;
      justify-content: center;
    }
  }
}

.sidebar-inner {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 12px;
  gap: 8px;
}

.sidebar-top {
  flex-shrink: 0;
}

.new-chat-btn {
  width: 100%;
  height: 42px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background-color: var(--bnu-blue, #003DA5);
  border-color: var(--bnu-blue, #003DA5);

  &:hover {
    background-color: #1a5fbf;
    border-color: #1a5fbf;
  }

  .btn-text {
    white-space: nowrap;
  }
}

.sidebar-middle {
  flex: 1 1 auto;
  overflow-y: auto;
  overflow-x: hidden;
  margin: 4px -4px;
  padding: 0 4px;

  &::-webkit-scrollbar {
    width: 4px;
  }

  &::-webkit-scrollbar-thumb {
    background: var(--border-color, #e2e6ed);
    border-radius: 2px;
  }
}

.sidebar-bottom {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-top: 1px solid var(--border-color, #e2e6ed);
  padding-top: 12px;
}

.user-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  border-radius: 8px;
  background: var(--bg-primary, #fff);
  min-width: 0;
}

.avatar-fallback {
  font-size: 14px;
  font-weight: 600;
}

.user-info {
  flex: 1;
  min-width: 0;
}

.user-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #1a1a2e);
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.settings-btn {
  flex-shrink: 0;
  color: var(--text-secondary, #5a5a72);
  padding: 4px;

  &:hover {
    color: var(--bnu-blue, #003DA5);
  }
}

.collapse-btn {
  align-self: center;
  color: var(--text-secondary, #5a5a72);
  padding: 4px 8px;

  &:hover {
    color: var(--bnu-blue, #003DA5);
  }
}

:deep(.el-dropdown-menu__item) {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
