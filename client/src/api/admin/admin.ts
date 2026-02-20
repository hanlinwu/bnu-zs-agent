import request from '../request'
import type { PaginatedResult } from '@/types/admin'

export interface AdminItem {
  id: string
  username: string
  real_name: string
  nickname: string
  employee_id: string | null
  department: string | null
  title: string | null
  phone: string
  email: string | null
  avatar_url: string
  status: string
  role_code: string | null
  role_name: string | null
  last_login_at: string | null
  last_login_ip: string | null
  token_expire_at: string | null
  created_by: string | null
  created_by_name: string | null
  created_at: string
  updated_at: string
}

export const getAdmins = (params: { page: number; page_size: number; keyword?: string; status?: string }) =>
  request.get<PaginatedResult<AdminItem>>('/admin/admins', { params })

export const createAdmin = (data: {
  username: string
  password: string
  real_name: string
  employee_id?: string
  department?: string
  title?: string
  phone: string
  email?: string
  avatar_url?: string
  role_code?: string
}) => request.post<AdminItem>('/admin/admins', data)

export const updateAdmin = (id: string, data: {
  real_name?: string
  employee_id?: string
  department?: string
  title?: string
  phone?: string
  email?: string
  avatar_url?: string
  role_code?: string
  status?: string
}) => request.put(`/admin/admins/${id}`, data)

export const deleteAdmin = (id: string) =>
  request.delete(`/admin/admins/${id}`)

export const batchUpdateAdminStatus = (data: { ids: string[]; status: 'active' | 'disabled' }) =>
  request.put('/admin/admins/batch-status', data)

export const batchDeleteAdmins = (data: { ids: string[] }) =>
  request.post('/admin/admins/batch-delete', data)

// 个人信息相关
export const updateProfile = (data: {
  real_name?: string
  employee_id?: string
  department?: string
  title?: string
  email?: string
}) => request.put('/admin/auth/profile', data)

export const sendPasswordChangeSms = () =>
  request.post('/admin/auth/password/sms/send')

export const changePassword = (data: {
  old_password: string
  new_password: string
  sms_code: string
}) => request.put('/admin/auth/password', data)

export const sendPhoneChangeSms = (new_phone: string) =>
  request.post('/admin/auth/phone/change/send', { new_phone })

export const changePhone = (data: {
  new_phone: string
  sms_code: string
}) => request.put('/admin/auth/phone', data)
