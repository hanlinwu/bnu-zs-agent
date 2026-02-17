import request from '../request'
import type { AdminUser } from '@/types/user'
import type { PaginatedResult } from '@/types/admin'

export const getUsers = (params: { page: number; pageSize: number; keyword?: string; status?: string }) =>
  request.get<PaginatedResult<AdminUser>>('/admin/users', { params })

export const getUser = (id: string) =>
  request.get<AdminUser>(`/admin/users/${id}`)

export const createUser = (data: Partial<AdminUser>) =>
  request.post<AdminUser>('/admin/users', data)

export const updateUser = (id: string, data: Partial<AdminUser>) =>
  request.put<AdminUser>(`/admin/users/${id}`, data)

export const deleteUser = (id: string) =>
  request.delete(`/admin/users/${id}`)

export const toggleUserBan = (id: string) =>
  request.put(`/admin/users/${id}/ban`)

export const batchBanUsers = (data: { ids: string[]; action: 'ban' | 'unban' }) =>
  request.put('/admin/users/batch-ban', data)

/** @deprecated Use toggleUserBan instead */
export const toggleUserStatus = (_id: string, _enabled: boolean) =>
  request.put(`/admin/users/${_id}/ban`)
