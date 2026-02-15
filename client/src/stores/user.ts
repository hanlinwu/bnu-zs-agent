import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

export interface UserInfo {
  id: string
  phone: string
  nickname: string
  avatar_url: string
  role: string
  status: string
}

export const useUserStore = defineStore('user', () => {
  const token = ref<string>(localStorage.getItem('token') || '')
  const userInfo = ref<UserInfo | null>(null)

  const isLoggedIn = computed(() => !!token.value)

  async function login(phone: string, code: string, nickname?: string, role?: string) {
    const res = await axios.post('/api/auth/login', { phone, code, nickname, role })
    const data = res.data
    token.value = data.token
    userInfo.value = data.user
    localStorage.setItem('token', data.token)
    return data
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('token')
  }

  async function fetchProfile() {
    const res = await axios.get('/api/user/profile', {
      headers: { Authorization: `Bearer ${token.value}` },
    })
    userInfo.value = res.data
    return res.data
  }

  async function updateProfile(updates: Partial<Pick<UserInfo, 'nickname' | 'avatar_url'>>) {
    const res = await axios.put('/api/user/profile', updates, {
      headers: { Authorization: `Bearer ${token.value}` },
    })
    userInfo.value = { ...userInfo.value!, ...res.data }
    return res.data
  }

  return {
    token,
    userInfo,
    isLoggedIn,
    login,
    logout,
    fetchProfile,
    updateProfile,
  }
})
