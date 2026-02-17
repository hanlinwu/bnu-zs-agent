import request from '../request'
import type { KnowledgeBase } from '@/types/knowledge'

export const getKnowledgeBases = () =>
  request.get<{ items: KnowledgeBase[] }>('/admin/knowledge-bases')

export const createKnowledgeBase = (data: { name: string; description?: string; enabled?: boolean; sort_order?: number }) =>
  request.post<KnowledgeBase>('/admin/knowledge-bases', data)

export const updateKnowledgeBase = (id: string, data: { name?: string; description?: string; enabled?: boolean; sort_order?: number }) =>
  request.put(`/admin/knowledge-bases/${id}`, data)

export const deleteKnowledgeBase = (id: string) =>
  request.delete(`/admin/knowledge-bases/${id}`)
