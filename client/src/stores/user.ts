import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import request from '@/api/request'

export interface UserInfo {
  id: string
  phone: string
  nickname: string
  avatar_url: string
  province?: string | null
  admission_stages?: string[]
  identity_type?: 'student' | 'parent' | null
  source_group?: 'mainland_general' | 'hkmo_tw' | 'international' | null
  status: string
}

export interface UserLoginResponse {
  success: boolean
  token: string
  user: UserInfo
  message?: string
  is_first_login?: boolean
}

export const useUserStore = defineStore('user', () => {
  const token = ref<string>(localStorage.getItem('token') || '')
  const userInfo = ref<UserInfo | null>(null)
  let profilePromise: Promise<UserInfo> | null = null

  const isLoggedIn = computed(() => !!token.value)

  async function login(phone: string, code: string, nickname?: string, role?: string) {
    const res = await axios.post<UserLoginResponse>('/api/v1/auth/login', { phone, code, nickname, user_role: role })
    const data = res.data
    if (!data?.success || !data?.token) {
      const error = new Error(data?.message || '登录失败，请检查验证码') as Error & {
        response?: { data?: { message?: string } }
      }
      error.response = { data: { message: data?.message || '登录失败，请检查验证码' } }
      throw error
    }
    token.value = data.token
    userInfo.value = data.user
    localStorage.setItem('token', data.token)
    return data as UserLoginResponse
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

  async function updateProfile(
    updates: Partial<Pick<UserInfo, 'nickname' | 'avatar_url' | 'province' | 'admission_stages' | 'identity_type' | 'source_group'>>
  ) {
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
