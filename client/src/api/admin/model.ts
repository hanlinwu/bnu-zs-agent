import request from '../request'
import type { ModelConfig } from '@/types/admin'

export const getModels = () =>
  request.get<ModelConfig[]>('/admin/models')

export const updateModels = (data: Partial<ModelConfig>) =>
  request.put('/admin/models', data)

export const testModel = (_id?: string) =>
  request.post('/admin/models/test')

export const setPrimaryModel = (id: string) =>
  request.put('/admin/models', { primary_model_id: id })

export const setReviewerModel = (id: string) =>
  request.put('/admin/models', { review_model_id: id })
