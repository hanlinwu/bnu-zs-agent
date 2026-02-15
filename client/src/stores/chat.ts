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

    const assistantMsg: ChatMessage = {
      id: `msg-${Date.now()}-reply`,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      loading: true,
    }
    messages.value.push(assistantMsg)
    isStreaming.value = true

    try {
      const token = localStorage.getItem('token') || ''
      const response = await fetch('/api/chat/send', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          conversation_id: currentConversationId.value,
          message: content,
        }),
      })

      if (!response.ok) throw new Error('请求失败')

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (reader) {
        assistantMsg.loading = false
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          const chunk = decoder.decode(value, { stream: true })
          assistantMsg.content += chunk
        }
      }
    } catch (error) {
      assistantMsg.content = '抱歉，请求出现异常，请稍后重试。'
      assistantMsg.loading = false
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
