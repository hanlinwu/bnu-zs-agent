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

function mapConversation(item: any): Conversation {
  return {
    id: String(item.id),
    title: item.title || '',
    pinned: item.is_pinned ?? item.pinned ?? false,
    message_count: item.message_count ?? 0,
    created_at: item.created_at,
    updated_at: item.updated_at,
  }
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
      conversations.value = (res.data.items || []).map(mapConversation)
      total.value = res.data.total
    } finally {
      loading.value = false
    }
  }

  async function createConversation(title?: string) {
    const res = await request.post('/conversations', { title: title || undefined })
    const conv = mapConversation(res.data)
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
    const conv = conversations.value.find((c) => c.id === id)
    if (!conv) return
    const oldTitle = conv.title
    conv.title = title
    try {
      await request.put(`/conversations/${id}`, { title })
    } catch {
      conv.title = oldTitle
    }
  }

  async function togglePin(id: string) {
    const conv = conversations.value.find((c) => c.id === id)
    if (!conv) return
    const newPinned = !conv.pinned
    conv.pinned = newPinned
    try {
      await request.put(`/conversations/${id}`, { is_pinned: newPinned })
    } catch {
      conv.pinned = !newPinned
    }
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
