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
  words: string[]
  enabled: boolean
  createdAt: string
  updatedAt: string
}

/** 媒体资源 */
export interface MediaResource {
  id: string
  name: string
  type: 'image' | 'video' | 'document'
  url: string
  fileSize: number
  mimeType: string
  uploaderId: string
  uploaderName: string
  tags: string[]
  createdAt: string
  updatedAt: string
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

/** 模型配置 */
export interface ModelConfig {
  id: string
  name: string
  provider: 'qwen' | 'glm' | 'local' | string
  endpoint: string
  apiKey?: string
  isPrimary: boolean
  isReviewer: boolean
  enabled: boolean
  weight: number
  maxTokens: number
  temperature: number
  createdAt: string
  updatedAt: string
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
