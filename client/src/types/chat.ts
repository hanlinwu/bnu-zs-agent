/** 消息角色 */
export type MessageRole = 'user' | 'assistant' | 'system'

/** 消息来源标注 */
export interface SourceReference {
  documentId: string
  title: string
  snippet: string
}

export interface MediaItem {
  id: string
  media_type: 'image' | 'video'
  url: string
  title: string
  description?: string
  tags?: string[]
  slot_key?: string
  slot_tags?: string[]
}

/** 聊天消息 */
export interface Message {
  id: string
  conversationId: string
  role: MessageRole
  content: string
  sources?: SourceReference[]
  mediaItems?: MediaItem[]
  riskLevel?: 'low' | 'medium' | 'high'
  createdAt: string
}

/** 对话 */
export interface Conversation {
  id: string
  userId: string
  title: string
  lastMessageAt: string
  messageCount: number
  createdAt: string
  updatedAt: string
}

/** WebSocket 聊天事件 */
export interface ChatEvent {
  type: 'message' | 'typing' | 'done' | 'error'
  conversationId: string
  data?: Partial<Message>
  content?: string
  error?: string
}

/** 发送消息参数 */
export interface SendMessageParams {
  conversationId: string
  content: string
}

/** 对话更新参数 */
export interface UpdateConversationParams {
  title?: string
}
