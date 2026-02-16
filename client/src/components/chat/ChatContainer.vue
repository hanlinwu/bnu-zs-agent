<script setup lang="ts">
import { computed } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { useChatStore } from '@/stores/chat'
import MessageList from './MessageList.vue'
import MessageInput from './MessageInput.vue'

const chatStore = useChatStore()

const isStreaming = computed(() => chatStore.isStreaming)
const isLoadingMessages = computed(() => chatStore.isLoadingMessages)

async function handleSend(content: string) {
  await chatStore.sendMessage(content)
}

function handleSelectQuestion(question: string) {
  handleSend(question)
}

function handleStop() {
  chatStore.stopGeneration()
}
</script>

<template>
  <div class="chat-container">
    <div v-if="isLoadingMessages" class="loading-overlay">
      <el-icon class="loading-icon" :size="24"><Loading /></el-icon>
      <span>加载消息中...</span>
    </div>
    <template v-else>
      <MessageList @select-question="handleSelectQuestion" />
      <MessageInput :disabled="isStreaming" @send="handleSend" @stop="handleStop" />
    </template>
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

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.loading-overlay {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  gap: 12px;
  font-size: 14px;
  color: var(--text-secondary, #5a5a72);

  .loading-icon {
    animation: spin 1.2s linear infinite;
    color: var(--bnu-blue, #003DA5);
  }
}
</style>
