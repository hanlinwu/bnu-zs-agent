import request from '../request'
import type { MediaResource, PaginatedResult } from '@/types/admin'

export const getMediaList = (params: { page: number; page_size: number; media_type?: string; status?: string }) =>
  request.get<PaginatedResult<MediaResource>>('/admin/media', { params })

export const uploadMedia = (formData: FormData) =>
  request.post<MediaResource>('/admin/media/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })

export const reviewMedia = (id: string, data: { action: string; note?: string }) =>
  request.post<MediaResource>(`/admin/media/${id}/review`, data)

export const batchReviewMedia = (data: { ids: string[]; action: string; note?: string }) =>
  request.post('/admin/media/batch-review', data)

export const updateMedia = (id: string, data: { title?: string; description?: string; tags?: string[] }) =>
  request.put<MediaResource>(`/admin/media/${id}`, data)

export const deleteMedia = (id: string) =>
  request.delete(`/admin/media/${id}`)
