<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Sunny, Moon } from '@element-plus/icons-vue'
import { useConversationStore } from '@/stores/conversation'
import { useChatStore } from '@/stores/chat'
import { useThemeStore } from '@/stores/theme'
import { useSystemStore } from '@/stores/system'

const conversationStore = useConversationStore()
const chatStore = useChatStore()
const themeStore = useThemeStore()
const systemStore = useSystemStore()

const isEditingTitle = ref(false)
const editTitleValue = ref('')

const currentTitle = computed(() => {
  const conv = conversationStore.conversations.find(
    (c) => c.id === chatStore.currentConversationId
  )
  return conv?.title || '新对话'
})

const isDark = computed(() => themeStore.mode === 'dark')
const systemName = computed(() => systemStore.basic.system_name || '京师小智')
const systemLogo = computed(() => systemStore.basic.system_logo || '')
const defaultLogo = '/images/default-logo-shi.svg'
const displayLogo = computed(() => systemLogo.value || defaultLogo)

const fontSizeOptions = [
  { label: '小', value: 14 },
  { label: '标准', value: 16 },
  { label: '大', value: 18 },
  { label: '特大', value: 20 },
]

function startEditTitle() {
  editTitleValue.value = currentTitle.value
  isEditingTitle.value = true
}

function saveTitle() {
  const currentId = chatStore.currentConversationId
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

function handleThemeToggle(e: MouseEvent) {
  themeStore.toggleTheme(e)
}

onMounted(() => {
  systemStore.fetchBasic()
})
</script>

<template>
  <header class="app-header">
    <div class="header-left">
      <div class="logo-area">
        <div class="logo-icon logo-icon--image">
          <img :src="displayLogo" :alt="`${systemName} Logo`" class="logo-img">
        </div>
        <span class="logo-text">{{ systemName }}</span>
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
      <!-- Font size selector -->
      <el-dropdown trigger="click" placement="bottom-end">
        <el-button class="header-action-btn" text>
          <span class="font-size-icon">A</span>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <li class="font-size-dropdown">
              <div class="font-size-label">字体大小</div>
              <div class="font-size-options">
                <button
                  v-for="opt in fontSizeOptions"
                  :key="opt.value"
                  class="font-size-opt"
                  :class="{ 'is-active': themeStore.fontSize === opt.value }"
                  @click="handleFontSize(opt.value)"
                >
                  {{ opt.label }}
                </button>
              </div>
            </li>
          </el-dropdown-menu>
        </template>
      </el-dropdown>

      <!-- Theme toggle -->
      <el-button class="header-action-btn" text @click="handleThemeToggle">
        <el-icon :size="18">
          <Moon v-if="!isDark" />
          <Sunny v-else />
        </el-icon>
      </el-button>
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

.logo-icon--image {
  width: 28px;
  height: 28px;
}

.logo-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.logo-text {
  font-size: 1.125rem;
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
  font-size: 0.9375rem;
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
  font-size: 0.9375rem;
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

.header-action-btn {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  color: var(--text-secondary, #5a5a72);
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;

  &:hover {
    color: var(--bnu-blue, #003DA5);
    background-color: var(--bg-secondary, #f4f6fa);
  }
}

.font-size-icon {
  font-size: 1rem;
  font-weight: 700;
  line-height: 1;
}

.font-size-dropdown {
  padding: 8px 12px;
  list-style: none;
}

.font-size-label {
  font-size: 0.75rem;
  color: var(--text-secondary, #5a5a72);
  margin-bottom: 8px;
  font-weight: 500;
}

.font-size-options {
  display: flex;
  gap: 4px;
}

.font-size-opt {
  padding: 6px 12px;
  font-size: 0.8125rem;
  border-radius: 6px;
  color: var(--text-primary, #1a1a2e);
  background: var(--bg-secondary, #f4f6fa);
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s;
  white-space: nowrap;

  &:hover {
    border-color: var(--border-color, #e2e6ed);
  }

  &.is-active {
    color: #fff;
    background-color: var(--bnu-blue, #003DA5);
    border-color: var(--bnu-blue, #003DA5);
    font-weight: 600;
  }
}
</style>
