<script setup lang="ts">
import { computed } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { useChatStore } from '@/stores/chat'
import MessageList from './MessageList.vue'
import MessageInput from './MessageInput.vue'

const chatStore = useChatStore()

const isStreaming = computed(() => chatStore.isStreaming)

async function handleSend(content: string) {
  await chatStore.sendMessage(content)
}

function handleSelectQuestion(question: string) {
  handleSend(question)
}
</script>

<template>
  <div class="chat-container">
    <MessageList @select-question="handleSelectQuestion" />

    <div v-if="isStreaming" class="thinking-indicator">
      <el-icon class="thinking-icon" :size="14"><Loading /></el-icon>
      <span>AI正在思考...</span>
    </div>

    <MessageInput :disabled="isStreaming" @send="handleSend" />
  </div>
</template>

<style scoped lang="scss">
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-primary, #fff);
  overflow: hidden;
}

.thinking-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 6px 0;
  font-size: 13px;
  color: var(--text-secondary, #5a5a72);
  background: var(--bg-primary, #fff);

  .thinking-icon {
    animation: spin 1.2s linear infinite;
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
