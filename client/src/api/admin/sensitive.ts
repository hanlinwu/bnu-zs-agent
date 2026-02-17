import request from '../request'
import type { SensitiveWordGroup } from '@/types/admin'

export interface GroupListItem {
  id: string
  name: string
  description: string | null
  level: 'block' | 'warn' | 'review'
  is_active: boolean
  word_count: number
  created_at: string
}

export interface GroupDetail extends SensitiveWordGroup {
  word_count: number
}

export const getGroups = () =>
  request.get<{ items: GroupListItem[] }>('/admin/sensitive/groups')

export const getGroup = (id: string) =>
  request.get<GroupDetail>(`/admin/sensitive/groups/${id}`)

export const createGroup = (data: Partial<SensitiveWordGroup>) =>
  request.post<SensitiveWordGroup>('/admin/sensitive/groups', data)

export const updateGroup = (id: string, data: Partial<SensitiveWordGroup>) =>
  request.put<SensitiveWordGroup>(`/admin/sensitive/groups/${id}`, data)

export const deleteGroup = (id: string) =>
  request.delete(`/admin/sensitive/groups/${id}`)

export const toggleGroup = (id: string, is_active: boolean) =>
  request.put(`/admin/sensitive/groups/${id}`, { is_active })

/** 上传txt文件创建敏感词组 */
export const uploadWordFile = (data: {
  name: string
  level: string
  description?: string
  file: File
}) => {
  const formData = new FormData()
  formData.append('name', data.name)
  formData.append('level', data.level)
  if (data.description) {
    formData.append('description', data.description)
  }
  formData.append('file', data.file)

  // 不要手动设置 Content-Type，让 axios 自动设置（包含 boundary）
  return request.post<GroupListItem>('/admin/sensitive/groups/upload', formData)
}
