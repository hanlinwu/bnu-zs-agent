import request from '../request'
import type { AdminUser } from '@/types/user'
import type { PaginatedResult } from '@/types/admin'

export const getUsers = (params: { page: number; pageSize: number; keyword?: string }) =>
  request.get<PaginatedResult<AdminUser>>('/admin/users', { params })

export const getUser = (id: string) =>
  request.get<AdminUser>(`/admin/users/${id}`)

export const createUser = (data: Partial<AdminUser>) =>
  request.post<AdminUser>('/admin/users', data)

export const updateUser = (id: string, data: Partial<AdminUser>) =>
  request.put<AdminUser>(`/admin/users/${id}`, data)

export const deleteUser = (id: string) =>
  request.delete(`/admin/users/${id}`)

export const toggleUserStatus = (id: string, enabled: boolean) =>
  request.patch(`/admin/users/${id}/status`, { enabled })
