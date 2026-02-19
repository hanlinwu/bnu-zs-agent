import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

let isRedirecting = false
let last429NoticeAt = 0

function parseRetryAfterSeconds(value?: string): number {
  const parsed = Number(value)
  if (Number.isFinite(parsed) && parsed > 0) {
    return Math.max(1, Math.floor(parsed))
  }
  return 2
}

/**
 * Handle 401 unauthorized — clear token and redirect to login.
 * Exported so non-axios code (e.g. fetch) can reuse the same logic.
 */
export function handleUnauthorized() {
  if (isRedirecting) return
  isRedirecting = true

  const isAdmin = router.currentRoute.value.path.startsWith('/admin')
  if (isAdmin) {
    localStorage.removeItem('admin_token')
  } else {
    localStorage.removeItem('token')
  }

  ElMessage.error('登录已过期，请重新登录')
  router.replace(isAdmin ? '/admin/login' : '/login').finally(() => {
    isRedirecting = false
  })
}

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 15_000,
})

/** 请求拦截：注入 Bearer token */
request.interceptors.request.use((config) => {
  // Admin endpoints use admin_token, user endpoints use token
  // 检查完整 URL 路径，确保匹配 /admin/* 路由
  const fullPath = (config.baseURL || '') + (config.url || '')
  const isAdmin = fullPath.includes('/admin')
  const token = localStorage.getItem(isAdmin ? 'admin_token' : 'token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

/** 响应拦截：统一错误处理 */
request.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config || {}
    const status = error.response?.status
    const method = String(config.method || '').toLowerCase()
    const message: string = error.response?.data?.detail?.message
      || error.response?.data?.message
      || error.message
      || '请求失败'

    if (status === 401) {
      handleUnauthorized()
    } else if (status === 429) {
      const retryAfterRaw = error.response?.headers?.['retry-after'] as string | undefined
      const retryAfterSeconds = parseRetryAfterSeconds(retryAfterRaw)
      const now = Date.now()

      if (now - last429NoticeAt > 1200) {
        ElMessage.warning(`请求较频繁，${retryAfterSeconds} 秒后自动重试`)
        last429NoticeAt = now
      }

      if (method === 'get' && !config.__retried429) {
        config.__retried429 = true
        await new Promise((resolve) => {
          setTimeout(resolve, retryAfterSeconds * 1000)
        })
        return request(config)
      }
    } else {
      ElMessage.error(message)
    }

    return Promise.reject(error)
  },
)

export default request
