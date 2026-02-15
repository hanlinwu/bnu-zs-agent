import request from '../request'
import type { ModelConfig } from '@/types/admin'

export const getModels = () =>
  request.get<ModelConfig[]>('/admin/models')

export const getModel = (id: string) =>
  request.get<ModelConfig>(`/admin/models/${id}`)

export const createModel = (data: Partial<ModelConfig>) =>
  request.post<ModelConfig>('/admin/models', data)

export const updateModel = (id: string, data: Partial<ModelConfig>) =>
  request.put<ModelConfig>(`/admin/models/${id}`, data)

export const deleteModel = (id: string) =>
  request.delete(`/admin/models/${id}`)

export const setPrimaryModel = (id: string) =>
  request.post(`/admin/models/${id}/set-primary`)

export const setReviewerModel = (id: string) =>
  request.post(`/admin/models/${id}/set-reviewer`)

export const testModel = (id: string) =>
  request.post(`/admin/models/${id}/test`)
