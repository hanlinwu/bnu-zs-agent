import request from '../request'

// --- Types ---

export interface WorkflowNode {
  id: string
  name: string
  type: 'start' | 'intermediate' | 'terminal'
  view_roles: string[]
  edit_roles: string[]
}

export interface WorkflowAction {
  id: string
  name: string
}

export interface WorkflowTransition {
  from_node: string
  action: string
  to_node: string
}

export interface WorkflowDefinition {
  nodes: WorkflowNode[]
  actions: WorkflowAction[]
  transitions: WorkflowTransition[]
}

export interface ReviewWorkflow {
  id: string
  name: string
  code: string
  definition: WorkflowDefinition
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
  workflow_definition: WorkflowDefinition
  enabled: boolean
  created_at: string
}

export interface ResourceWorkflowInfo {
  workflow_id: string | null
  workflow_name?: string
  workflow_code?: string
  nodes: WorkflowNode[]
  actions: WorkflowAction[]
  transitions: WorkflowTransition[]
}

export interface ReviewHistoryRecord {
  id: string
  from_node: string
  from_node_name: string
  action: string
  action_name: string
  to_node: string
  to_node_name: string
  reviewer_id: string
  reviewer_name: string
  note: string | null
  created_at: string
}

// Deprecated compat type
export interface WorkflowStep {
  step: number
  name: string
  role_code: string
}

// --- API functions ---

export const getWorkflows = () =>
  request.get<{ items: ReviewWorkflow[] }>('/admin/workflows')

export const createWorkflow = (data: { name: string; code: string; definition: WorkflowDefinition }) =>
  request.post<ReviewWorkflow>('/admin/workflows', data)

export const updateWorkflow = (id: string, data: { name?: string; definition?: WorkflowDefinition }) =>
  request.put<ReviewWorkflow>(`/admin/workflows/${id}`, data)

export const deleteWorkflow = (id: string) =>
  request.delete(`/admin/workflows/${id}`)

export const getBindings = () =>
  request.get<{ items: WorkflowBinding[] }>('/admin/workflows/bindings')

export const updateBinding = (resourceType: string, data: { workflow_id?: string; enabled?: boolean }) =>
  request.put<WorkflowBinding>(`/admin/workflows/bindings/${resourceType}`, data)

export const getWorkflowForResource = (resourceType: string) =>
  request.get<ResourceWorkflowInfo>(`/admin/workflows/for-resource/${resourceType}`)

export const getReviewHistory = (resourceType: string, resourceId: string) =>
  request.get<{ items: ReviewHistoryRecord[] }>(`/admin/workflows/history/${resourceType}/${resourceId}`)
