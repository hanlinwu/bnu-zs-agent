<script setup lang="ts">
import { ref, computed } from 'vue'
import { Sunny, Moon, ArrowDown, User, Setting, SwitchButton } from '@element-plus/icons-vue'
import { useThemeStore } from '@/stores/theme'
import { useUserStore } from '@/stores/user'
import { useConversationStore } from '@/stores/conversation'

const themeStore = useThemeStore()
const userStore = useUserStore()
const conversationStore = useConversationStore()

const isEditingTitle = ref(false)
const editTitleValue = ref('')

const currentTitle = computed(() => {
  const conv = conversationStore.conversations.find(
    (c) => c.id === (conversationStore as any).currentId
  )
  return conv?.title || '新对话'
})

const fontSizeOptions = [
  { label: '小 (14px)', value: 14 },
  { label: '标准 (16px)', value: 16 },
  { label: '大 (18px)', value: 18 },
  { label: '特大 (20px)', value: 20 },
]

function startEditTitle() {
  editTitleValue.value = currentTitle.value
  isEditingTitle.value = true
}

function saveTitle() {
  const currentId = (conversationStore as any).currentId
  if (currentId && editTitleValue.value.trim()) {
    conversationStore.updateTitle(currentId, editTitleValue.value.trim())
  }
  isEditingTitle.value = false
}

function cancelEditTitle() {
  isEditingTitle.value = false
}

function handleFontSize(size: number) {
  themeStore.setFontSize(size as 14 | 16 | 18 | 20)
}

function handleLogout() {
  userStore.logout()
}

const isDark = computed(() => themeStore.mode === 'dark')
const userNickname = computed(() => userStore.userInfo?.nickname || '用户')
const userAvatar = computed(() => userStore.userInfo?.avatar_url || '')
</script>

<template>
  <header class="app-header">
    <div class="header-left">
      <div class="logo-area">
        <div class="logo-icon">
          <svg viewBox="0 0 32 32" width="28" height="28" fill="none">
            <circle cx="16" cy="16" r="15" fill="var(--bnu-blue, #003DA5)" />
            <text
              x="16" y="22" text-anchor="middle"
              fill="#fff" font-size="16" font-weight="bold"
              font-family="serif"
            >智</text>
          </svg>
        </div>
        <span class="logo-text">京师小智</span>
      </div>
    </div>

    <div class="header-center">
      <div
        v-if="!isEditingTitle"
        class="conversation-title"
        @dblclick="startEditTitle"
        :title="'双击编辑标题'"
      >
        {{ currentTitle }}
      </div>
      <input
        v-else
        ref="titleInput"
        v-model="editTitleValue"
        class="title-edit-input"
        maxlength="50"
        @keydown.enter="saveTitle"
        @keydown.esc="cancelEditTitle"
        @blur="saveTitle"
        autofocus
      />
    </div>

    <div class="header-right">
      <el-tooltip :content="isDark ? '切换到亮色模式' : '切换到暗色模式'" placement="bottom">
        <el-button class="icon-btn" text @click="themeStore.toggleTheme">
          <el-icon :size="18">
            <Moon v-if="!isDark" />
            <Sunny v-else />
          </el-icon>
        </el-button>
      </el-tooltip>

      <el-dropdown trigger="click" @command="handleFontSize">
        <el-button class="icon-btn" text>
          <span class="font-size-label">A</span>
          <el-icon :size="12"><ArrowDown /></el-icon>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item
              v-for="opt in fontSizeOptions"
              :key="opt.value"
              :command="opt.value"
              :class="{ 'is-active': themeStore.fontSize === opt.value }"
            >
              {{ opt.label }}
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>

      <el-dropdown trigger="click">
        <div class="user-trigger">
          <el-avatar :size="32" :src="userAvatar">
            <el-icon :size="18"><User /></el-icon>
          </el-avatar>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item disabled>
              <span class="dropdown-nickname">{{ userNickname }}</span>
            </el-dropdown-item>
            <el-dropdown-item divided>
              <el-icon><User /></el-icon>
              <span>个人资料</span>
            </el-dropdown-item>
            <el-dropdown-item>
              <el-icon><Setting /></el-icon>
              <span>设置</span>
            </el-dropdown-item>
            <el-dropdown-item divided @click="handleLogout">
              <el-icon><SwitchButton /></el-icon>
              <span>退出登录</span>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<style scoped lang="scss">
.app-header {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  border-bottom: 1px solid var(--border-color, #e2e6ed);
  background: var(--bg-primary, #fff);
  flex-shrink: 0;
  z-index: 100;
}

.header-left {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
}

.logo-area {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: default;
}

.logo-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: var(--bnu-blue, #003DA5);
  letter-spacing: 1px;
  white-space: nowrap;
}

.header-center {
  flex: 1 1 auto;
  display: flex;
  justify-content: center;
  align-items: center;
  min-width: 0;
  padding: 0 24px;
}

.conversation-title {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary, #1a1a2e);
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: default;
  padding: 4px 12px;
  border-radius: 6px;
  transition: background-color 0.2s;

  &:hover {
    background-color: var(--bg-secondary, #f4f6fa);
  }
}

.title-edit-input {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary, #1a1a2e);
  background: var(--bg-secondary, #f4f6fa);
  border: 1px solid var(--bnu-blue, #003DA5);
  border-radius: 6px;
  padding: 4px 12px;
  outline: none;
  max-width: 300px;
  width: 240px;
  text-align: center;
}

.header-right {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 4px;
}

.icon-btn {
  padding: 6px 8px;
  color: var(--text-secondary, #5a5a72);

  &:hover {
    color: var(--bnu-blue, #003DA5);
  }
}

.font-size-label {
  font-size: 16px;
  font-weight: 600;
  margin-right: 2px;
}

.user-trigger {
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: 2px;
  border-radius: 50%;
  transition: box-shadow 0.2s;

  &:hover {
    box-shadow: 0 0 0 2px var(--bnu-blue, #003DA5);
  }
}

.dropdown-nickname {
  font-weight: 600;
  color: var(--text-primary, #1a1a2e);
}

:deep(.el-dropdown-menu__item) {
  display: flex;
  align-items: center;
  gap: 8px;

  &.is-active {
    color: var(--bnu-blue, #003DA5);
    font-weight: 600;
  }
}
</style>
