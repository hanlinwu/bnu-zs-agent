import request from '../request'
import type { MediaResource, PaginatedResult } from '@/types/admin'

export const getMediaList = (params: { page: number; pageSize: number; type?: string }) =>
  request.get<PaginatedResult<MediaResource>>('/admin/media', { params })

export const getMedia = (id: string) =>
  request.get<MediaResource>(`/admin/media/${id}`)

export const uploadMedia = (formData: FormData) =>
  request.post<MediaResource>('/admin/media', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })

export const updateMedia = (id: string, data: { name?: string; tags?: string[] }) =>
  request.put<MediaResource>(`/admin/media/${id}`, data)

export const deleteMedia = (id: string) =>
  request.delete(`/admin/media/${id}`)
