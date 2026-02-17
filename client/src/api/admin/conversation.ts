import request from '../request'
import type { PaginatedResult, AdminConversation, ConversationDetail } from '@/types/admin'

export interface ConversationQuery {
  page: number
  page_size: number
  keyword?: string
  risk_level?: string
  sensitive_level?: string
  start_time?: string
  end_time?: string
}

export function getConversations(params: ConversationQuery) {
  return request.get<PaginatedResult<AdminConversation>>('/admin/conversations', {
    params: {
      include_deleted: true,
      ...params,
    },
  })
}

export function getConversationMessages(conversationId: string) {
  return request.get<ConversationDetail>(`/admin/conversations/${conversationId}/messages`)
}
