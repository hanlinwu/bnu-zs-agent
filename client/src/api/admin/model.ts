import request from '../request'
import type { ModelConfigOverview } from '@/types/admin'

// ── Overview ──
export const getModelConfig = () =>
  request.get<ModelConfigOverview>('/admin/models')

// ── Endpoints ──
export const createEndpoint = (data: { name: string; provider: string; baseUrl: string; apiKey: string }) =>
  request.post('/admin/models/endpoints', data)

export const updateEndpoint = (id: string, data: { name?: string; provider?: string; baseUrl?: string; apiKey?: string }) =>
  request.put(`/admin/models/endpoints/${id}`, data)

export const deleteEndpoint = (id: string) =>
  request.delete(`/admin/models/endpoints/${id}`)

// ── Groups ──
export const createGroup = (data: { name: string; type: string; strategy?: string; enabled?: boolean; priority?: number }) =>
  request.post('/admin/models/groups', data)

export const updateGroup = (id: string, data: { name?: string; strategy?: string; enabled?: boolean; priority?: number }) =>
  request.put(`/admin/models/groups/${id}`, data)

export const deleteGroup = (id: string) =>
  request.delete(`/admin/models/groups/${id}`)

// ── Instances ──
export const createInstance = (groupId: string, data: {
  endpointId: string; modelName: string; enabled?: boolean;
  weight?: number; maxTokens?: number; temperature?: number; priority?: number
}) =>
  request.post(`/admin/models/groups/${groupId}/instances`, data)

export const updateInstance = (id: string, data: {
  endpointId?: string; modelName?: string; enabled?: boolean;
  weight?: number; maxTokens?: number; temperature?: number; priority?: number
}) =>
  request.put(`/admin/models/instances/${id}`, data)

export const deleteInstance = (id: string) =>
  request.delete(`/admin/models/instances/${id}`)

// ── Test ──
export const testModel = (data: { provider: string; api_key: string; base_url: string; model: string }) =>
  request.post('/admin/models/test', data)

export const testEmbedding = (data: { model: string; base_url: string; api_key: string }) =>
  request.post('/admin/models/test-embedding', data)
