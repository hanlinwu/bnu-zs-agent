import request from '../request'
import type { KnowledgeDocument, KnowledgeChunk, KnowledgeChunkDetail, KnowledgeCrawlTask } from '@/types/knowledge'
import type { PaginatedResult } from '@/types/admin'

export const getDocuments = (params: { page: number; pageSize: number; status?: string; kb_id?: string }) =>
  request.get<PaginatedResult<KnowledgeDocument>>('/admin/knowledge', { params })

export const getDocument = (id: string) =>
  request.get<KnowledgeDocument>(`/admin/knowledge/${id}`)

export const uploadDocument = (formData: FormData) =>
  request.post<KnowledgeDocument>('/admin/knowledge/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })

export const reviewDocument = (id: string, data: { action: string; note?: string }) =>
  request.post(`/admin/knowledge/${id}/review`, data)

export const batchReviewDocuments = (data: { ids: string[]; action: string; note?: string }) =>
  request.post('/admin/knowledge/batch-review', data)

export const batchDeleteDocuments = (data: { ids: string[] }) =>
  request.post('/admin/knowledge/batch-delete', data)

export const deleteDocument = (id: string) =>
  request.delete(`/admin/knowledge/${id}`)

export const getChunks = (documentId: string, params: { page: number; pageSize: number }) =>
  request.get<PaginatedResult<KnowledgeChunk>>(`/admin/knowledge/${documentId}/chunks`, { params })

export const getChunkDetail = (chunkId: string) =>
  request.get<KnowledgeChunkDetail>(`/admin/knowledge/chunks/${chunkId}/detail`)

export const reembedMissingChunks = (data: { documentId?: string; limit?: number }) =>
  request.post('/admin/knowledge/re-embed-missing', data)

export const createCrawlTask = (data: {
  kbId: string
  startUrl: string
  maxDepth: number
  sameDomainOnly: boolean
}) => request.post<KnowledgeCrawlTask>('/admin/knowledge/crawl/tasks', data)

export const getCrawlTasks = (params: { page: number; pageSize: number; kb_id?: string; status?: string }) =>
  request.get<PaginatedResult<KnowledgeCrawlTask>>('/admin/knowledge/crawl/tasks', { params })

export const getCrawlTask = (id: string) =>
  request.get<KnowledgeCrawlTask>(`/admin/knowledge/crawl/tasks/${id}`)

export function downloadDocument(id: string) {
  const token = localStorage.getItem('admin_token')
  const url = `/api/v1/admin/knowledge/${id}/download`
  // Use fetch with auth header then trigger download via blob URL
  fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
    .then((res) => {
      if (!res.ok) throw new Error('下载失败')
      const disposition = res.headers.get('Content-Disposition') || ''
      const match = disposition.match(/filename\*?=(?:UTF-8'')?(.+)/i)
      const filename = match?.[1] ? decodeURIComponent(match[1]) : 'document'
      return res.blob().then((blob) => ({ blob, filename }))
    })
    .then(({ blob, filename }) => {
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = filename
      a.click()
      URL.revokeObjectURL(a.href)
    })
    .catch(() => {
      import('element-plus').then(({ ElMessage }) => {
        ElMessage.error('文件下载失败')
      })
    })
}
