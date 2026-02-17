import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import request from '@/api/request'

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
  let profilePromise: Promise<UserInfo> | null = null

  const isLoggedIn = computed(() => !!token.value)

  async function login(phone: string, code: string, nickname?: string, role?: string) {
    const res = await axios.post('/api/v1/auth/login', { phone, code, nickname, user_role: role })
    const data = res.data
    token.value = data.token
    userInfo.value = data.user
    localStorage.setItem('token', data.token)
    return data
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    profilePromise = null
    localStorage.removeItem('token')
  }

  async function fetchProfile() {
    if (userInfo.value) {
      return userInfo.value
    }

    if (profilePromise) {
      return profilePromise
    }

    profilePromise = request
      .get('/auth/me')
      .then((res) => {
        userInfo.value = res.data
        return res.data as UserInfo
      })
      .finally(() => {
        profilePromise = null
      })

    return profilePromise
  }

  async function updateProfile(updates: Partial<Pick<UserInfo, 'nickname' | 'avatar_url' | 'role'>>) {
    const res = await request.put('/auth/me', updates)
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
