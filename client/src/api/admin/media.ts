import request from '../request'
import type { MediaResource, PaginatedResult } from '@/types/admin'

export const getMediaList = (params: { page: number; page_size: number; media_type?: string; status?: string }) =>
  request.get<PaginatedResult<MediaResource>>('/admin/media', { params })

export const uploadMedia = (formData: FormData) =>
  request.post<MediaResource>('/admin/media/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })

export const reviewMedia = (id: string, data: { action: 'approve' | 'reject'; note?: string }) =>
  request.post<MediaResource>(`/admin/media/${id}/review`, data)

export const deleteMedia = (id: string) =>
  request.delete(`/admin/media/${id}`)
