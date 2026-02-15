import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

export interface AdminInfo {
  id: string
  username: string
  display_name: string
  role: string
  status: string
}

export const useAdminStore = defineStore('admin', () => {
  const adminToken = ref<string>(localStorage.getItem('admin_token') || '')
  const adminInfo = ref<AdminInfo | null>(null)
  const permissions = ref<string[]>([])

  const isLoggedIn = computed(() => !!adminToken.value)

  async function login(username: string, password: string, mfaCode: string) {
    const res = await axios.post('/api/v1/admin/auth/login', {
      username,
      password,
      mfa_code: mfaCode,
    })
    const data = res.data
    adminToken.value = data.token
    adminInfo.value = data.admin
    permissions.value = data.permissions || []
    localStorage.setItem('admin_token', data.token)
    return data
  }

  function logout() {
    adminToken.value = ''
    adminInfo.value = null
    permissions.value = []
    localStorage.removeItem('admin_token')
  }

  async function fetchProfile() {
    const res = await axios.get('/api/v1/admin/auth/me', {
      headers: { Authorization: `Bearer ${adminToken.value}` },
    })
    adminInfo.value = res.data.admin
    permissions.value = res.data.permissions || []
    return res.data
  }

  function hasPermission(perm: string): boolean {
    return permissions.value.includes(perm)
  }

  return {
    adminToken,
    adminInfo,
    permissions,
    isLoggedIn,
    login,
    logout,
    fetchProfile,
    hasPermission,
  }
})
