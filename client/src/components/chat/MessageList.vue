<script setup lang="ts">
import { ref, watch, nextTick, computed, onUnmounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import MessageBubble from './MessageBubble.vue'
import StreamingText from './StreamingText.vue'
import SuggestQuestions from './SuggestQuestions.vue'
import type { Message } from '@/types/chat'

const emit = defineEmits<{
  selectQuestion: [question: string]
}>()

const chatStore = useChatStore()
const scrollContainerRef = ref<HTMLElement | null>(null)

const isEmpty = computed(() => chatStore.messages.length === 0 && !chatStore.isStreaming)

const THINKING_HINTS = [
  '我正在思考你的问题',
  '稍等，我正在查询相关信息',
  '正在整理回答内容',
  '请稍候，马上就好',
]
const thinkingIndex = ref(0)
let thinkingTimer: ReturnType<typeof setInterval> | null = null

const thinkingText = computed(() => THINKING_HINTS[thinkingIndex.value])

watch(() => chatStore.isStreaming, (streaming) => {
  if (streaming) {
    thinkingIndex.value = 0
    thinkingTimer = setInterval(() => {
      thinkingIndex.value = (thinkingIndex.value + 1) % THINKING_HINTS.length
    }, 3000)
  } else {
    if (thinkingTimer) {
      clearInterval(thinkingTimer)
      thinkingTimer = null
    }
  }
}, { immediate: true })

onUnmounted(() => {
  if (thinkingTimer) clearInterval(thinkingTimer)
})

const displayMessages = computed<Message[]>(() => {
  return chatStore.messages.map((msg) => ({
    id: msg.id,
    conversationId: chatStore.currentConversationId || '',
    role: msg.role as 'user' | 'assistant',
    content: msg.content,
    sources: msg.sources
      ? msg.sources.map((s) => ({ documentId: '', title: s, snippet: '' }))
      : undefined,
    createdAt: new Date(msg.timestamp).toISOString(),
  }))
})

const streamingMessage = computed(() => {
  if (!chatStore.isStreaming) return null
  const lastMsg = chatStore.messages[chatStore.messages.length - 1]
  if (lastMsg && lastMsg.role === 'assistant' && lastMsg.loading) {
    return lastMsg
  }
  return null
})

const nonStreamingMessages = computed<Message[]>(() => {
  if (streamingMessage.value) {
    return displayMessages.value.slice(0, -1)
  }
  return displayMessages.value
})

function scrollToBottom() {
  nextTick(() => {
    const el = scrollContainerRef.value
    if (el) {
      el.scrollTop = el.scrollHeight
    }
  })
}

watch(
  () => chatStore.messages.length,
  () => scrollToBottom()
)

watch(
  () => streamingMessage.value?.content,
  () => scrollToBottom()
)

function handleSelectQuestion(question: string) {
  emit('selectQuestion', question)
}
</script>

<template>
  <div ref="scrollContainerRef" class="message-list">
    <SuggestQuestions v-if="isEmpty" @select="handleSelectQuestion" />

    <template v-else>
      <div class="messages-wrapper">
        <MessageBubble
          v-for="msg in nonStreamingMessages"
          :key="msg.id"
          :message="msg"
        />

        <div v-if="streamingMessage" class="message-bubble is-assistant">
          <div class="avatar-wrapper">
            <div class="ai-avatar">
              <svg viewBox="0 0 32 32" width="32" height="32" fill="none">
                <circle cx="16" cy="16" r="15" fill="var(--bnu-blue, #003DA5)" />
                <text
                  x="16" y="22" text-anchor="middle"
                  fill="#fff" font-size="14" font-weight="bold"
                  font-family="serif"
                >智</text>
              </svg>
            </div>
          </div>
          <div class="bubble-body">
            <div class="bubble-content assistant-bubble">
              <div v-if="!streamingMessage.content" class="thinking-hint">
                <span class="thinking-dots">
                  <span class="dot"></span>
                  <span class="dot"></span>
                  <span class="dot"></span>
                </span>
                <span class="thinking-text">{{ thinkingText }}</span>
              </div>
              <StreamingText
                v-else
                :text="streamingMessage.content"
                :is-streaming="chatStore.isStreaming"
              />
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped lang="scss">
.message-list {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 16px;

  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-thumb {
    background: var(--border-color, #e2e6ed);
    border-radius: 3px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }
}

.messages-wrapper {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
}

.message-bubble {
  display: flex;
  gap: 10px;
  padding: 8px 0;
  max-width: 80%;

  &.is-assistant {
    margin-right: auto;
  }
}

.avatar-wrapper {
  flex-shrink: 0;
  padding-top: 2px;
}

.ai-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.bubble-body {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.bubble-content.assistant-bubble {
  padding: 12px 16px;
  border-radius: 18px;
  border-top-left-radius: 4px;
  background-color: var(--bg-secondary, #f4f6fa);
  color: var(--text-primary, #1a1a2e);
}

.thinking-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--text-secondary, #5a5a72);
}

.thinking-dots {
  display: flex;
  gap: 4px;

  .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--bnu-blue, #003DA5);
    animation: dotBounce 1.4s ease-in-out infinite;

    &:nth-child(2) {
      animation-delay: 0.2s;
    }

    &:nth-child(3) {
      animation-delay: 0.4s;
    }
  }
}

@keyframes dotBounce {
  0%, 80%, 100% {
    opacity: 0.3;
    transform: scale(0.8);
  }
  40% {
    opacity: 1;
    transform: scale(1);
  }
}

.thinking-text {
  transition: opacity 0.3s;
}
</style>
