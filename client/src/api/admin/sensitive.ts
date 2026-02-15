import request from '../request'
import type { SensitiveWordGroup } from '@/types/admin'

export const getGroups = () =>
  request.get<SensitiveWordGroup[]>('/admin/sensitive/groups')

export const getGroup = (id: string) =>
  request.get<SensitiveWordGroup>(`/admin/sensitive/groups/${id}`)

export const createGroup = (data: Partial<SensitiveWordGroup>) =>
  request.post<SensitiveWordGroup>('/admin/sensitive/groups', data)

export const updateGroup = (id: string, data: Partial<SensitiveWordGroup>) =>
  request.put<SensitiveWordGroup>(`/admin/sensitive/groups/${id}`, data)

export const deleteGroup = (id: string) =>
  request.delete(`/admin/sensitive/groups/${id}`)

export const toggleGroup = (id: string, enabled: boolean) =>
  request.patch(`/admin/sensitive/groups/${id}`, { is_active: enabled })

export const addWord = (data: { group_id: string; word: string; level: string }) =>
  request.post('/admin/sensitive/words', data)

export const deleteWord = (wordId: string) =>
  request.delete(`/admin/sensitive/words/${wordId}`)
