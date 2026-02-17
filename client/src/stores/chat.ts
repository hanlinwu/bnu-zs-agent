import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { handleUnauthorized } from '@/api/request'
import * as chatApi from '@/api/chat'
import { useConversationStore } from '@/stores/conversation'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  sources?: string[]
  loading?: boolean
}

const rolePriority: Record<ChatMessage['role'], number> = {
  user: 0,
  assistant: 1,
  system: 2,
}

function compareMessages(a: ChatMessage, b: ChatMessage): number {
  if (a.timestamp !== b.timestamp) {
    return a.timestamp - b.timestamp
  }

  const priorityDiff = rolePriority[a.role] - rolePriority[b.role]
  if (priorityDiff !== 0) {
    return priorityDiff
  }

  return a.id.localeCompare(b.id)
}

export const useChatStore = defineStore('chat', () => {
  // 使用 Map 存储消息，支持 O(1) 查找和去重
  const messageMap = ref<Map<string, ChatMessage>>(new Map())
  const isStreaming = ref(false)
  const isLoadingMessages = ref(false)
  const isLoadingHistory = ref(false) // 加载历史消息中
  const currentConversationId = ref<string | null>(null)

  // 分页状态
  const hasMoreHistory = ref(true) // 是否还有更多历史消息
  const oldestMessageId = ref<string | null>(null) // 最旧的消息ID（用于游标）
  const newestMessageId = ref<string | null>(null) // 最新的消息ID
  const totalMessageCount = ref(0) // 消息总数

  let abortController: AbortController | null = null

  // 计算属性：按时间排序的消息列表
  const messages = computed(() => {
    return Array.from(messageMap.value.values())
      .sort(compareMessages)
  })

  // 获取最新消息（用于初始加载）
  async function loadMessages(conversationId: string, pageSize: number = 20) {
    isLoadingMessages.value = true
    messageMap.value.clear()
    hasMoreHistory.value = true
    oldestMessageId.value = null
    newestMessageId.value = null

    try {
      const res = await chatApi.getMessagesPaginated(conversationId, {
        pageSize,
      })

      let items = res.data.items || []
      totalMessageCount.value = res.data.total || 0

      // 稳定排序：时间 -> 角色 -> ID（避免问答同时间戳导致乱序）
      items = items.sort((a: any, b: any) => {
        const timeDiff = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        if (timeDiff !== 0) {
          return timeDiff
        }

        const roleDiff = (rolePriority[(a.role as ChatMessage['role']) || 'assistant'] ?? 99)
          - (rolePriority[(b.role as ChatMessage['role']) || 'assistant'] ?? 99)
        if (roleDiff !== 0) {
          return roleDiff
        }

        return String(a.id ?? '').localeCompare(String(b.id ?? ''))
      })

      // 添加到 Map
      items.forEach((m: any) => {
        messageMap.value.set(m.id, {
          id: m.id,
          role: m.role,
          content: m.content,
          timestamp: new Date(m.created_at).getTime(),
          sources: m.sources || undefined,
        })
      })

      // 更新游标
      if (items.length > 0) {
        oldestMessageId.value = items[0]?.id || null
        newestMessageId.value = items[items.length - 1]?.id || null
      }

      // 如果加载的数量少于请求的，说明没有更多历史了
      hasMoreHistory.value = items.length >= pageSize && items.length < totalMessageCount.value
    } catch {
      messageMap.value.clear()
      hasMoreHistory.value = false
    } finally {
      isLoadingMessages.value = false
    }
  }

  // 加载更多历史消息（向上滚动时调用）
  async function loadMoreHistory(pageSize: number = 20): Promise<boolean> {
    if (!currentConversationId.value || !oldestMessageId.value || isLoadingHistory.value) {
      return false
    }

    // 如果已经没有更多历史，直接返回
    if (!hasMoreHistory.value) {
      return false
    }

    isLoadingHistory.value = true

    try {
      const res = await chatApi.getMessagesPaginated(currentConversationId.value, {
        before: oldestMessageId.value,
        pageSize,
      })

      const items = res.data.items || []

      if (items.length === 0) {
        hasMoreHistory.value = false
        return false
      }

      // 稳定排序：时间 -> 角色 -> ID（避免问答同时间戳导致乱序）
      const sortedItems = items.sort((a: any, b: any) => {
        const timeDiff = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        if (timeDiff !== 0) {
          return timeDiff
        }

        const roleDiff = (rolePriority[(a.role as ChatMessage['role']) || 'assistant'] ?? 99)
          - (rolePriority[(b.role as ChatMessage['role']) || 'assistant'] ?? 99)
        if (roleDiff !== 0) {
          return roleDiff
        }

        return String(a.id ?? '').localeCompare(String(b.id ?? ''))
      })

      // 添加到 Map（自动去重）
      sortedItems.forEach((m: any) => {
        if (!messageMap.value.has(m.id)) {
          messageMap.value.set(m.id, {
            id: m.id,
            role: m.role,
            content: m.content,
            timestamp: new Date(m.created_at).getTime(),
            sources: m.sources || undefined,
          })
        }
      })

      // 更新最旧消息游标
      oldestMessageId.value = sortedItems[0]?.id || oldestMessageId.value

      // 检查是否还有更多
      hasMoreHistory.value = items.length >= pageSize

      return items.length > 0
    } catch (error) {
      console.error('Failed to load history:', error)
      return false
    } finally {
      isLoadingHistory.value = false
    }
  }

  async function sendMessage(content: string) {
    // Lazily create conversation on first message
    if (!currentConversationId.value) {
      const conversationStore = useConversationStore()
      const title = content.length > 30 ? content.slice(0, 30) + '...' : content
      const conv = await conversationStore.createConversation(title)
      setConversationId(conv.id)
    }

    const now = Date.now()
    const userMsg: ChatMessage = {
      id: `msg-${now}`,
      role: 'user',
      content,
      timestamp: now,
    }
    messageMap.value.set(userMsg.id, userMsg)
    newestMessageId.value = userMsg.id

    // AI消息时间戳+1，确保排序时用户消息在前
    const assistantMsg: ChatMessage = {
      id: `msg-${now + 1}-reply`,
      role: 'assistant',
      content: '',
      timestamp: now + 1,
      loading: true,
    }
    messageMap.value.set(assistantMsg.id, assistantMsg)

    isStreaming.value = true

    // Reference the reactive proxy in the Map
    const getAssistantMessage = () => {
      const msg = messageMap.value.get(assistantMsg.id)
      if (!msg) {
        throw new Error('assistant message missing')
      }
      return msg
    }

    try {
      const token = localStorage.getItem('token') || ''
      const url = currentConversationId.value
        ? `/api/v1/chat/send?conversation_id=${encodeURIComponent(currentConversationId.value)}`
        : '/api/v1/chat/send'
      abortController = new AbortController()
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          content,
        }),
        signal: abortController.signal,
      })

      if (!response.ok) {
        if (response.status === 401) {
          handleUnauthorized()
          return
        }
        throw new Error('请求失败')
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (reader) {
        getAssistantMessage().loading = false
        let buffer = ''
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })

          // Parse SSE lines from buffer
          const lines = buffer.split('\n')
          buffer = lines.pop() || '' // keep incomplete line in buffer
          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            const payload = line.slice(6)
            if (payload === '[DONE]') continue
            try {
              const event = JSON.parse(payload)
              if (event.type === 'token') {
                getAssistantMessage().content += event.content
              } else if (event.type === 'sensitive_block' || event.type === 'high_risk') {
                getAssistantMessage().content = event.content
              } else if (event.type === 'done' && event.sources?.length) {
                getAssistantMessage().sources = event.sources
              }
            } catch {
              // skip malformed JSON
            }
          }
        }
      } else {
        getAssistantMessage().loading = false
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        // User stopped generation - keep partial content
        getAssistantMessage().loading = false
      } else {
        getAssistantMessage().content = '抱歉，请求出现异常，请稍后重试。'
        getAssistantMessage().loading = false
      }
    } finally {
      abortController = null
      isStreaming.value = false
    }
  }

  function clearMessages() {
    messageMap.value.clear()
    oldestMessageId.value = null
    newestMessageId.value = null
    hasMoreHistory.value = true
    totalMessageCount.value = 0
  }

  async function stopGeneration() {
    if (abortController) {
      // Signal server to stop and save partial response
      if (currentConversationId.value) {
        const token = localStorage.getItem('token') || ''
        try {
          await fetch(`/api/v1/chat/stop?conversation_id=${encodeURIComponent(currentConversationId.value)}`, {
            method: 'POST',
            headers: { Authorization: `Bearer ${token}` },
          })
        } catch {
          // ignore network errors
        }
      }
      // Delay abort to give server time to save partial response
      const controller = abortController
      await new Promise(resolve => setTimeout(resolve, 500))
      controller.abort()
      abortController = null
      isStreaming.value = false
    }
  }

  function setConversationId(id: string | null) {
    currentConversationId.value = id
    if (id) {
      localStorage.setItem('currentConversationId', id)
    } else {
      localStorage.removeItem('currentConversationId')
    }
    // 重置分页状态，等待 loadMessages 设置正确值
    hasMoreHistory.value = false
  }

  return {
    // State
    messages,
    messageMap,
    isStreaming,
    isLoadingMessages,
    isLoadingHistory,
    currentConversationId,
    hasMoreHistory,
    oldestMessageId,
    newestMessageId,
    totalMessageCount,

    // Actions
    sendMessage,
    stopGeneration,
    clearMessages,
    setConversationId,
    loadMessages,
    loadMoreHistory,
  }
})
