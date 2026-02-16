import { defineStore } from 'pinia'
import { ref } from 'vue'
import request from '@/api/request'

export interface Conversation {
  id: string
  title: string
  pinned: boolean
  message_count: number
  created_at: string
  updated_at: string
}

export const useConversationStore = defineStore('conversation', () => {
  const conversations = ref<Conversation[]>([])
  const total = ref(0)
  const loading = ref(false)

  async function fetchConversations(page = 1, pageSize = 20) {
    loading.value = true
    try {
      const res = await request.get('/conversations', {
        params: { page, page_size: pageSize },
      })
      conversations.value = res.data.items
      total.value = res.data.total
    } finally {
      loading.value = false
    }
  }

  async function createConversation() {
    const res = await request.post('/conversations', {})
    const conv: Conversation = res.data
    conversations.value.unshift(conv)
    total.value++
    return conv
  }

  async function deleteConversation(id: string) {
    await request.delete(`/conversations/${id}`)
    conversations.value = conversations.value.filter((c) => c.id !== id)
    total.value--
  }

  async function updateTitle(id: string, title: string) {
    await request.put(`/conversations/${id}`, { title })
    const conv = conversations.value.find((c) => c.id === id)
    if (conv) conv.title = title
  }

  async function togglePin(id: string) {
    const conv = conversations.value.find((c) => c.id === id)
    if (!conv) return
    const pinned = !conv.pinned
    await request.put(`/conversations/${id}`, { pinned })
    conv.pinned = pinned
  }

  return {
    conversations,
    total,
    loading,
    fetchConversations,
    createConversation,
    deleteConversation,
    updateTitle,
    togglePin,
  }
})
