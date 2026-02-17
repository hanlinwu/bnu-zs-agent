import request from './request'
import type { Conversation, Message, UpdateConversationParams } from '@/types/chat'
import type { PaginatedResult } from '@/types/admin'

/** 发送消息（HTTP 通道，非流式） */
export const sendMessage = (conversationId: string, content: string) =>
  request.post<Message>('/chat/send', { conversation_id: conversationId, content })

/** 获取对话列表 */
export const getConversations = (page: number, pageSize: number) =>
  request.get<PaginatedResult<Conversation>>('/conversations', { params: { page, pageSize } })

/** 创建对话 */
export const createConversation = (title?: string) =>
  request.post<Conversation>('/conversations', { title })

/** 获取单个对话 */
export const getConversation = (id: string) =>
  request.get<Conversation>(`/conversations/${id}`)

/** 更新对话 */
export const updateConversation = (id: string, data: UpdateConversationParams) =>
  request.put<Conversation>(`/conversations/${id}`, data)

/** 删除对话 */
export const deleteConversation = (id: string) =>
  request.delete(`/conversations/${id}`)

/** 获取对话消息列表 */
export const getMessages = (conversationId: string, page: number, pageSize: number) =>
  request.get<PaginatedResult<Message>>(`/conversations/${conversationId}/messages`, { params: { page, pageSize } })

/** 获取对话消息列表（游标分页，用于无限滚动）
 * @param conversationId 对话ID
 * @param params 分页参数
 *   - before: 加载此ID之前的消息（更早的消息，向上滚动）
 *   - after: 加载此ID之后的消息（更新的消息，向下滚动）
 *   - pageSize: 每页数量，默认20
 */
export const getMessagesPaginated = (
  conversationId: string,
  params: { before?: string; after?: string; pageSize?: number }
) =>
  request.get<PaginatedResult<Message>>(`/conversations/${conversationId}/messages`, {
    params: {
      before: params.before,
      after: params.after,
      page_size: params.pageSize || 20,
    },
  })
