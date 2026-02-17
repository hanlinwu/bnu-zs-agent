/** 权限 */
export interface Permission {
  id: string
  code: string
  name: string
  description: string
  group: string
}

/** 角色 */
export interface Role {
  id: string
  name: string
  code: string
  description: string
  permissions: string[]
  builtIn: boolean
  createdAt: string
  updatedAt: string
}

/** 敏感词组 */
export interface SensitiveWordGroup {
  id: string
  name: string
  description: string | null
  level: 'block' | 'warn' | 'review'
  word_list: string
  word_count: number
  is_active: boolean
  created_at: string
}

/** 媒体资源 */
export interface MediaResource {
  id: string
  title: string
  media_type: 'image' | 'video'
  file_url: string
  file_size: number | null
  thumbnail_url: string | null
  tags: string[]
  description: string | null
  status: string
  current_node: string
  current_step: number
  is_approved: boolean
  uploaded_by: string | null
  uploader_name: string | null
  reviewed_by: string | null
  review_note: string | null
  created_at: string
}

/** 审计日志 */
export interface AuditLog {
  id: string
  userId: string
  userName: string
  ip: string
  action: string
  module: string
  detail: string
  modelVersion?: string
  knowledgeHits?: string[]
  createdAt: string
}

/** 招生日历阶段 */
export interface CalendarPeriod {
  id: string
  name: string
  startDate: string
  endDate: string
  style: 'motivational' | 'guidance' | 'enrollment' | 'general'
  description: string
  keywords: string[]
  enabled: boolean
  createdAt: string
  updatedAt: string
}

/** 模型接入点 */
export interface ModelEndpoint {
  id: string
  name: string
  provider: string
  baseUrl: string
  apiKey: string  // masked
  createdAt: string
}

/** 模型实例 */
export interface ModelInstance {
  id: string
  groupId: string
  endpointId: string
  modelName: string
  enabled: boolean
  weight: number
  maxTokens: number
  temperature: number
  priority: number
  createdAt: string
  endpoint?: ModelEndpoint
}

/** 模型组 */
export interface ModelGroup {
  id: string
  name: string
  type: 'llm' | 'embedding' | 'review'
  strategy: 'failover' | 'round_robin' | 'weighted'
  enabled: boolean
  priority: number
  createdAt: string
  instances: ModelInstance[]
}

/** 模型配置总览 */
export interface ModelConfigOverview {
  endpoints: ModelEndpoint[]
  groups: ModelGroup[]
}

export interface ChatGuardrailRiskConfig {
  high_keywords: string[]
  medium_keywords: string[]
  medium_topics: string[]
  medium_specific_hints: string[]
}

export interface ChatGuardrailPromptConfig {
  medium_system_prompt: string
  low_system_prompt: string
  medium_citation_hint: string
  medium_knowledge_instructions: string
  high_risk_response: string
  no_knowledge_response: string
}

export interface ChatGuardrailConfig {
  risk: ChatGuardrailRiskConfig
  prompts: ChatGuardrailPromptConfig
}

/** 分页参数 */
export interface PaginationParams {
  page: number
  pageSize: number
}

/** 分页响应 */
export interface PaginatedResult<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
}

/** 对话列表项 (admin) */
export interface AdminConversation {
  id: string
  user_id: string
  user_phone: string
  user_nickname: string
  title: string | null
  is_deleted: boolean
  deleted_at: string | null
  message_count: number
  user_char_count: number
  assistant_char_count: number
  max_risk_level: string | null
  max_sensitive_level: string | null
  created_at: string
  updated_at: string
}

/** 对话消息详情 (admin) */
export interface AdminMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  char_count: number
  risk_level: string | null
  review_passed: boolean | null
  sources: Record<string, unknown> | null
  sensitive_words: string[] | null
  sensitive_level: string | null
  created_at: string
}

/** 对话消息列表响应 */
export interface ConversationDetail {
  conversation_id: string
  title: string | null
  messages: AdminMessage[]
}
