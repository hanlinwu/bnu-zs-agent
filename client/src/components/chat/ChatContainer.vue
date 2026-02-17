<script setup lang="ts">
import { computed } from 'vue'
import { useChatStore } from '@/stores/chat'
import MessageList from './MessageList.vue'
import MessageInput from './MessageInput.vue'
import MessageSkeleton from './MessageSkeleton.vue'

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
    <!-- 骨架屏：切换会话时显示 -->
    <div v-if="isLoadingMessages" class="skeleton-wrapper">
      <div class="skeleton-content">
        <MessageSkeleton v-for="i in 4" :key="i" :index="i" />
      </div>
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

.skeleton-wrapper {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 16px;
}

.skeleton-content {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
</style>
