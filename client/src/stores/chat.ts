import { defineStore } from 'pinia'
import { ref } from 'vue'

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
  const currentConversationId = ref<string | null>(null)

  async function sendMessage(content: string) {
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
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          content,
        }),
      })

      if (!response.ok) throw new Error('请求失败')

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
      getAssistantMessage().content = '抱歉，请求出现异常，请稍后重试。'
      getAssistantMessage().loading = false
    } finally {
      isStreaming.value = false
    }
  }

  function clearMessages() {
    messages.value = []
  }

  function setConversationId(id: string | null) {
    currentConversationId.value = id
  }

  return {
    messages,
    isStreaming,
    currentConversationId,
    sendMessage,
    clearMessages,
    setConversationId,
  }
})
