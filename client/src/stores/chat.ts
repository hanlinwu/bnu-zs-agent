import { defineStore } from 'pinia'
import { ref } from 'vue'
import { handleUnauthorized } from '@/api/request'
import request from '@/api/request'
import { useConversationStore } from '@/stores/conversation'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  sources?: string[]
  loading?: boolean
}

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const isStreaming = ref(false)
  const isLoadingMessages = ref(false)
  const currentConversationId = ref<string | null>(null)
  let abortController: AbortController | null = null

  async function loadMessages(conversationId: string) {
    isLoadingMessages.value = true
    try {
      const res = await request.get(`/conversations/${conversationId}/messages`, {
        params: { page: 1, page_size: 200 },
      })
      const items = res.data.items || []
      messages.value = items.map((m: any) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        timestamp: new Date(m.created_at).getTime(),
        sources: m.sources || undefined,
      }))
    } catch {
      messages.value = []
    } finally {
      isLoadingMessages.value = false
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

    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content,
      timestamp: Date.now(),
    }
    messages.value.push(userMsg)

    messages.value.push({
      id: `msg-${Date.now()}-reply`,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      loading: true,
    })
    isStreaming.value = true

    // Reference the reactive proxy in the array (not a plain local object)
    const assistantIdx = messages.value.length - 1
    const getAssistantMessage = () => {
      const msg = messages.value[assistantIdx]
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
    messages.value = []
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
  }

  return {
    messages,
    isStreaming,
    isLoadingMessages,
    currentConversationId,
    sendMessage,
    stopGeneration,
    clearMessages,
    setConversationId,
    loadMessages,
  }
})
