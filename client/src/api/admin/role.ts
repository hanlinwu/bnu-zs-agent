import request from '../request'
import type { Role, Permission } from '@/types/admin'

export const getRoles = () =>
  request.get<Role[]>('/admin/roles')

export const getRole = (id: string) =>
  request.get<Role>(`/admin/roles/${id}`)

export const createRole = (data: Partial<Role>) =>
  request.post<Role>('/admin/roles', data)

export const updateRole = (id: string, data: Partial<Role>) =>
  request.put<Role>(`/admin/roles/${id}`, data)

export const deleteRole = (id: string) =>
  request.delete(`/admin/roles/${id}`)

export const getPermissions = () =>
  request.get<Permission[]>('/admin/permissions')

export const updatePermissions = (roleId: string, permissionIds: string[]) =>
  request.put(`/admin/roles/${roleId}/permissions`, { permission_ids: permissionIds })
