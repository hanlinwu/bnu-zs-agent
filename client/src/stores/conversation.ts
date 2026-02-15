import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'

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

  function getAuthHeaders() {
    return { Authorization: `Bearer ${localStorage.getItem('token') || ''}` }
  }

  async function fetchConversations(page = 1, pageSize = 20) {
    loading.value = true
    try {
      const res = await axios.get('/api/v1/conversations', {
        params: { page, page_size: pageSize },
        headers: getAuthHeaders(),
      })
      conversations.value = res.data.items
      total.value = res.data.total
    } finally {
      loading.value = false
    }
  }

  async function createConversation() {
    const res = await axios.post('/api/v1/conversations', {}, {
      headers: getAuthHeaders(),
    })
    const conv: Conversation = res.data
    conversations.value.unshift(conv)
    total.value++
    return conv
  }

  async function deleteConversation(id: string) {
    await axios.delete(`/api/conversations/${id}`, {
      headers: getAuthHeaders(),
    })
    conversations.value = conversations.value.filter((c) => c.id !== id)
    total.value--
  }

  async function updateTitle(id: string, title: string) {
    await axios.put(`/api/conversations/${id}`, { title }, {
      headers: getAuthHeaders(),
    })
    const conv = conversations.value.find((c) => c.id === id)
    if (conv) conv.title = title
  }

  async function togglePin(id: string) {
    const conv = conversations.value.find((c) => c.id === id)
    if (!conv) return
    const pinned = !conv.pinned
    await axios.put(`/api/conversations/${id}`, { pinned }, {
      headers: getAuthHeaders(),
    })
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
