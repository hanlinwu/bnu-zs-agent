import request from '../request'
import type { PaginatedResult } from '@/types/admin'

export interface AdminItem {
  id: string
  username: string
  real_name: string
  nickname: string
  phone: string
  status: string
  role_code: string | null
  role_name: string | null
  last_login_at: string | null
  created_at: string
}

export const getAdmins = (params: { page: number; pageSize: number; keyword?: string; status?: string }) =>
  request.get<PaginatedResult<AdminItem>>('/admin/admins', { params })

export const createAdmin = (data: {
  username: string
  password: string
  real_name: string
  phone?: string
  role_code?: string
}) => request.post<AdminItem>('/admin/admins', data)

export const updateAdmin = (id: string, data: {
  real_name?: string
  phone?: string
  role_code?: string
  status?: string
}) => request.put(`/admin/admins/${id}`, data)

export const deleteAdmin = (id: string) =>
  request.delete(`/admin/admins/${id}`)

export const batchUpdateAdminStatus = (data: { ids: string[]; status: 'active' | 'disabled' }) =>
  request.put('/admin/admins/batch-status', data)

export const batchDeleteAdmins = (data: { ids: string[] }) =>
  request.post('/admin/admins/batch-delete', data)
