import request from '../request'
import type { ChatGuardrailConfig } from '@/types/admin'

interface ChatGuardrailConfigResponse {
  key: 'chat_guardrail'
  value: ChatGuardrailConfig
}

export const getChatGuardrailConfig = () =>
  request.get<ChatGuardrailConfigResponse>('/admin/system-configs/chat-guardrail')

export const updateChatGuardrailConfig = (value: ChatGuardrailConfig) =>
  request.put<ChatGuardrailConfigResponse>('/admin/system-configs/chat-guardrail', { value })
