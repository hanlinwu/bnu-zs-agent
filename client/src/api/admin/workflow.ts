import request from '../request'

export interface WorkflowStep {
  step: number
  name: string
  role_code: string
}

export interface ReviewWorkflow {
  id: string
  name: string
  code: string
  steps: WorkflowStep[]
  is_system: boolean
  created_at: string
  updated_at: string
}

export interface WorkflowBinding {
  id: string
  resource_type: string
  workflow_id: string
  workflow_name: string
  workflow_code: string
  workflow_steps: WorkflowStep[]
  enabled: boolean
  created_at: string
}

export const getWorkflows = () =>
  request.get<{ items: ReviewWorkflow[] }>('/admin/workflows')

export const createWorkflow = (data: { name: string; code: string; steps: WorkflowStep[] }) =>
  request.post<ReviewWorkflow>('/admin/workflows', data)

export const updateWorkflow = (id: string, data: { name?: string; steps?: WorkflowStep[] }) =>
  request.put<ReviewWorkflow>(`/admin/workflows/${id}`, data)

export const deleteWorkflow = (id: string) =>
  request.delete(`/admin/workflows/${id}`)

export const getBindings = () =>
  request.get<{ items: WorkflowBinding[] }>('/admin/workflows/bindings')

export const updateBinding = (resourceType: string, data: { workflow_id?: string; enabled?: boolean }) =>
  request.put<WorkflowBinding>(`/admin/workflows/bindings/${resourceType}`, data)

export const getReviewHistory = (resourceType: string, resourceId: string) =>
  request.get<{ items: any[] }>(`/admin/workflows/history/${resourceType}/${resourceId}`)
