<script setup lang="ts">
import { ref, watch, nextTick, computed, onUnmounted, onMounted } from 'vue'
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
const lastUserMessageRef = ref<HTMLElement | null>(null)
const isEmpty = computed(() => chatStore.messages.length === 0 && !chatStore.isStreaming)

// Track if user has manually scrolled up (to disable auto-scroll)
const isUserScrolledUp = ref(false)
const lastScrollTop = ref(0)

// 无限滚动状态
const isLoadingHistory = computed(() => chatStore.isLoadingHistory)
const hasMoreHistory = computed(() => chatStore.hasMoreHistory)
const LOAD_THRESHOLD = 100 // 距离顶部多少像素时触发加载

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
  // chatStore.messages 已经是按时间排序的
  return chatStore.messages.map((msg) => ({
    id: msg.id,
    conversationId: chatStore.currentConversationId || '',
    role: msg.role as 'user' | 'assistant',
    content: msg.content,
    sources: msg.sources
      ? msg.sources.map((s: any) => {
        if (typeof s === 'string') {
          return { documentId: '', title: s, snippet: '' }
        }
        return {
          documentId: s.document_id || s.documentId || '',
          title: s.title || '',
          snippet: s.snippet || '',
        }
      })
      : undefined,
    mediaItems: msg.mediaItems,
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

// Check if scroll is near bottom (within 100px)
function isNearBottom(): boolean {
  const el = scrollContainerRef.value
  if (!el) return true
  const threshold = 100
  return el.scrollHeight - el.scrollTop - el.clientHeight < threshold
}

// 保存当前滚动位置（用于加载历史后恢复）
function saveScrollPosition(): number {
  const el = scrollContainerRef.value
  if (!el) return 0
  return el.scrollHeight - el.scrollTop
}

// 恢复滚动位置（加载历史后）
function restoreScrollPosition() {
  const el = scrollContainerRef.value
  if (!el) return
  const newScrollHeight = el.scrollHeight
  el.scrollTop = newScrollHeight - oldScrollPosition.value
}

const oldScrollPosition = ref(0)

// Handle scroll events to detect user manual scrolling and trigger history loading
async function handleScroll() {
  const el = scrollContainerRef.value
  if (!el) return

  const scrollTop = el.scrollTop

  // 检测是否滚动到顶部附近，触发加载历史
  if (scrollTop < LOAD_THRESHOLD && !isLoadingHistory.value && hasMoreHistory.value) {
    oldScrollPosition.value = saveScrollPosition()
    const loaded = await chatStore.loadMoreHistory(20)
    if (loaded) {
      nextTick(() => restoreScrollPosition())
    }
  }

  // User scrolled up if scrollTop decreased or if not near bottom
  if (scrollTop < lastScrollTop.value || !isNearBottom()) {
    isUserScrolledUp.value = true
  } else if (isNearBottom()) {
    isUserScrolledUp.value = false
  }
  lastScrollTop.value = scrollTop
}

// Scroll element to top of visible area
function scrollElementToTop(element: HTMLElement) {
  const container = scrollContainerRef.value
  if (!container || !element) return

  // Use scrollIntoView with block: 'start' to scroll element to top
  element.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

// Auto-scroll to bottom during streaming
function autoScrollToBottom() {
  // Only auto-scroll if user hasn't manually scrolled up
  if (isUserScrolledUp.value) return

  nextTick(() => {
    const el = scrollContainerRef.value
    if (el) {
      el.scrollTo({
        top: el.scrollHeight,
        behavior: 'smooth'
      })
    }
  })
}

// Watch for new messages - scroll user message to top when ref is set
watch(lastUserMessageRef, (el) => {
  if (el) {
    // Reset user scroll flag for new user message
    isUserScrolledUp.value = false
    // Small delay to ensure DOM is ready
    setTimeout(() => scrollElementToTop(el), 50)
  }
})

// Watch streaming content - auto-scroll if near bottom
watch(
  () => streamingMessage.value?.content,
  () => {
    autoScrollToBottom()
  }
)

// Reset scroll state when conversation changes
watch(
  () => chatStore.currentConversationId,
  () => {
    isUserScrolledUp.value = false
    lastScrollTop.value = 0
    lastUserMessageRef.value = null
    oldScrollPosition.value = 0
  }
)

onMounted(() => {
  const container = scrollContainerRef.value
  if (container) {
    container.addEventListener('scroll', handleScroll, { passive: true })
  }
})

onUnmounted(() => {
  const container = scrollContainerRef.value
  if (container) {
    container.removeEventListener('scroll', handleScroll)
  }
})

function handleSelectQuestion(question: string) {
  emit('selectQuestion', question)
}

// Set ref for the last user message
function setMessageRef(el: HTMLElement | null, msg: Message) {
  if (el && msg.role === 'user') {
    // 找最后一个用户消息
    const lastUserMsg = [...chatStore.messages].reverse().find(m => m.role === 'user')
    if (lastUserMsg && lastUserMsg.id === msg.id) {
      lastUserMessageRef.value = el
    }
  }
}
</script>

<template>
  <div ref="scrollContainerRef" class="message-list">
    <SuggestQuestions v-if="isEmpty" @select="handleSelectQuestion" />

    <template v-else>
      <div class="messages-wrapper">
        <!-- 加载历史指示器 -->
        <div v-if="isLoadingHistory || (hasMoreHistory && displayMessages.length > 0)" class="history-loader">
          <div v-if="isLoadingHistory" class="loading-indicator">
            <el-icon class="loading-icon" :size="16"><Loading /></el-icon>
            <span>加载历史消息...</span>
          </div>
          <div v-else-if="hasMoreHistory && displayMessages.length > 0" class="load-more-hint">
            <span>向上滚动加载更多</span>
          </div>
        </div>

        <div
          v-for="msg in nonStreamingMessages"
          :key="msg.id"
          :ref="(el) => setMessageRef(el as HTMLElement, msg)"
          class="message-item"
        >
          <MessageBubble :message="msg" />
        </div>

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

        <!-- Bottom anchor for scrolling -->
        <div ref="bottomAnchor" class="bottom-anchor"></div>
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
  -webkit-overflow-scrolling: touch;

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

// 历史消息加载器
.history-loader {
  display: flex;
  justify-content: center;
  padding: 16px 0;
  min-height: 48px;
}

.loading-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8125rem;
  color: var(--text-secondary, #5a5a72);

  .loading-icon {
    animation: spin 1s linear infinite;
    color: var(--bnu-blue, #003DA5);
  }
}

.load-more-hint {
  font-size: 0.75rem;
  color: var(--text-secondary, #9e9eb3);
  padding: 4px 12px;
  background: var(--bg-secondary, #f4f6fa);
  border-radius: 12px;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.message-item {
  display: flex;
  flex-direction: column;
  scroll-margin-top: 20px;
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
  font-size: 0.875rem;
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

.bottom-anchor {
  height: 1px;
  flex-shrink: 0;
}
</style>
