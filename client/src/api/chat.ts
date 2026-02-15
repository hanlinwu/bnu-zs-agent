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
