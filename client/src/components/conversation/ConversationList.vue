<script setup lang="ts">
import { computed } from 'vue'
import { useConversationStore } from '@/stores/conversation'
import { useChatStore } from '@/stores/chat'
import ConversationItem from './ConversationItem.vue'
import type { Conversation } from '@/stores/conversation'

const conversationStore = useConversationStore()
const chatStore = useChatStore()

interface GroupedConversations {
  label: string
  items: Conversation[]
}

const grouped = computed<GroupedConversations[]>(() => {
  const now = new Date()
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  const yesterdayStart = todayStart - 86400000

  const today: Conversation[] = []
  const yesterday: Conversation[] = []
  const earlier: Conversation[] = []

  for (const conv of conversationStore.conversations) {
    const t = new Date(conv.updated_at).getTime()
    if (t >= todayStart) {
      today.push(conv)
    } else if (t >= yesterdayStart) {
      yesterday.push(conv)
    } else {
      earlier.push(conv)
    }
  }

  const groups: GroupedConversations[] = []
  if (today.length) groups.push({ label: '今天', items: today })
  if (yesterday.length) groups.push({ label: '昨天', items: yesterday })
  if (earlier.length) groups.push({ label: '更早', items: earlier })
  return groups
})

const isEmpty = computed(() => conversationStore.conversations.length === 0)

function handleSelect(conv: Conversation) {
  chatStore.setConversationId(conv.id)
  chatStore.clearMessages()
  chatStore.loadMessages(conv.id)
}

function handleDelete(conv: Conversation) {
  conversationStore.deleteConversation(conv.id)
}

function handleUpdateTitle(conv: Conversation, title: string) {
  conversationStore.updateTitle(conv.id, title)
}
</script>

<template>
  <div class="conversation-list">
    <div v-if="isEmpty" class="empty-state">
      <div class="empty-icon">
        <svg viewBox="0 0 48 48" width="48" height="48" fill="none">
          <rect x="6" y="10" width="36" height="28" rx="4" stroke="var(--text-secondary, #5a5a72)" stroke-width="2" fill="none" />
          <line x1="14" y1="20" x2="34" y2="20" stroke="var(--text-secondary, #5a5a72)" stroke-width="2" stroke-linecap="round" />
          <line x1="14" y1="26" x2="28" y2="26" stroke="var(--text-secondary, #5a5a72)" stroke-width="2" stroke-linecap="round" />
          <line x1="14" y1="32" x2="22" y2="32" stroke="var(--text-secondary, #5a5a72)" stroke-width="2" stroke-linecap="round" />
        </svg>
      </div>
      <span class="empty-text">暂无对话记录</span>
    </div>

    <template v-else>
      <div v-for="group in grouped" :key="group.label" class="conversation-group">
        <div class="group-label">{{ group.label }}</div>
        <ConversationItem
          v-for="conv in group.items"
          :key="conv.id"
          :conversation="conv"
          :active="chatStore.currentConversationId === conv.id"
          @select="handleSelect(conv)"
          @delete="handleDelete(conv)"
          @update-title="(title: string) => handleUpdateTitle(conv, title)"
        />
      </div>
    </template>
  </div>
</template>

<style scoped lang="scss">
.conversation-list {
  display: flex;
  flex-direction: column;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 16px;
  gap: 12px;
}

.empty-icon {
  opacity: 0.5;
}

.empty-text {
  font-size: 14px;
  color: var(--text-secondary, #5a5a72);
}

.conversation-group {
  margin-bottom: 8px;
}

.group-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary, #5a5a72);
  padding: 8px 12px 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
</style>
