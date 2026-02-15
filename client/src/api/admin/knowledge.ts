import request from '../request'
import type { KnowledgeDocument, KnowledgeChunk } from '@/types/knowledge'
import type { PaginatedResult } from '@/types/admin'

export const getDocuments = (params: { page: number; pageSize: number; status?: string }) =>
  request.get<PaginatedResult<KnowledgeDocument>>('/admin/knowledge', { params })

export const getDocument = (id: string) =>
  request.get<KnowledgeDocument>(`/admin/knowledge/${id}`)

export const uploadDocument = (formData: FormData) =>
  request.post<KnowledgeDocument>('/admin/knowledge/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })

export const reviewDocument = (id: string, data: { approved: boolean; note?: string }) =>
  request.post(`/admin/knowledge/${id}/review`, data)

export const deleteDocument = (id: string) =>
  request.delete(`/admin/knowledge/${id}`)

export const getChunks = (documentId: string, params: { page: number; pageSize: number }) =>
  request.get<PaginatedResult<KnowledgeChunk>>(`/admin/knowledge/${documentId}/chunks`, { params })
