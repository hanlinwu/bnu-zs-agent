import request from './request'
import type { LoginParams, LoginResult, User, UpdateProfileParams } from '@/types/user'

/** 发送短信验证码 */
export const sendSmsCode = (phone: string) =>
  request.post('/auth/sms-code', { phone })

/** 登录 */
export const login = (params: LoginParams) =>
  request.post<LoginResult>('/auth/login', params)

/** 登出 */
export const logout = () =>
  request.post('/auth/logout')

/** 获取当前用户资料 */
export const getProfile = () =>
  request.get<User>('/auth/profile')

/** 更新用户资料 */
export const updateProfile = (data: UpdateProfileParams) =>
  request.put<User>('/auth/profile', data)
