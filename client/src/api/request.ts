import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 15_000,
})

/** 请求拦截：注入 Bearer token */
request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

/** 响应拦截：统一错误处理 */
request.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const message: string = error.response?.data?.message || error.message || '请求失败'

    if (status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
      ElMessage.error('登录已过期，请重新登录')
    } else {
      ElMessage.error(message)
    }

    return Promise.reject(error)
  },
)

export default request
