import request from './request'
import type { Conversation, Message, SendMessageParams, UpdateConversationParams } from '@/types/chat'
import type { PaginatedResult } from '@/types/admin'

/** 发送消息（HTTP 通道，非流式） */
export const sendMessage = (conversationId: string, content: string) =>
  request.post<Message>(`/chat/conversations/${conversationId}/messages`, { content } as SendMessageParams)

/** 获取对话列表 */
export const getConversations = (page: number, pageSize: number) =>
  request.get<PaginatedResult<Conversation>>('/chat/conversations', { params: { page, pageSize } })

/** 创建对话 */
export const createConversation = (title?: string) =>
  request.post<Conversation>('/chat/conversations', { title })

/** 获取单个对话 */
export const getConversation = (id: string) =>
  request.get<Conversation>(`/chat/conversations/${id}`)

/** 更新对话 */
export const updateConversation = (id: string, data: UpdateConversationParams) =>
  request.put<Conversation>(`/chat/conversations/${id}`, data)

/** 删除对话 */
export const deleteConversation = (id: string) =>
  request.delete(`/chat/conversations/${id}`)

/** 获取对话消息列表 */
export const getMessages = (conversationId: string, page: number, pageSize: number) =>
  request.get<PaginatedResult<Message>>(`/chat/conversations/${conversationId}/messages`, { params: { page, pageSize } })
