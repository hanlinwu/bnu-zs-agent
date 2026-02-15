import request from '../request'
import type { KnowledgeDocument, KnowledgeChunk } from '@/types/knowledge'
import type { PaginatedResult } from '@/types/admin'

export const getDocuments = (params: { page: number; pageSize: number; status?: string }) =>
  request.get<PaginatedResult<KnowledgeDocument>>('/admin/knowledge/documents', { params })

export const getDocument = (id: string) =>
  request.get<KnowledgeDocument>(`/admin/knowledge/documents/${id}`)

export const uploadDocument = (formData: FormData) =>
  request.post<KnowledgeDocument>('/admin/knowledge/documents', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })

export const reviewDocument = (id: string, data: { approved: boolean; note?: string }) =>
  request.post(`/admin/knowledge/documents/${id}/review`, data)

export const deleteDocument = (id: string) =>
  request.delete(`/admin/knowledge/documents/${id}`)

export const getChunks = (documentId: string, params: { page: number; pageSize: number }) =>
  request.get<PaginatedResult<KnowledgeChunk>>(`/admin/knowledge/documents/${documentId}/chunks`, { params })

export const reprocessDocument = (id: string) =>
  request.post(`/admin/knowledge/documents/${id}/reprocess`)
