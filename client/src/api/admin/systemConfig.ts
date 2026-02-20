import request from '../request'
import type { ChatGuardrailConfig, SystemBasicConfig, BackendVersionInfo } from '@/types/admin'

interface ChatGuardrailConfigResponse {
  key: 'chat_guardrail'
  value: ChatGuardrailConfig
}

interface SystemBasicConfigResponse {
  key: 'system_basic'
  value: SystemBasicConfig
  version: BackendVersionInfo
}

export const getChatGuardrailConfig = () =>
  request.get<ChatGuardrailConfigResponse>('/admin/system-configs/chat-guardrail')

export const updateChatGuardrailConfig = (value: ChatGuardrailConfig) =>
  request.put<ChatGuardrailConfigResponse>('/admin/system-configs/chat-guardrail', { value })

export const getSystemBasicConfig = () =>
  request.get<SystemBasicConfigResponse>('/admin/system-configs/basic')

export const updateSystemBasicConfig = (value: SystemBasicConfig) =>
  request.put<SystemBasicConfigResponse>('/admin/system-configs/basic', { value })

export const uploadSystemLogo = (formData: FormData) =>
  request.post<{ url: string }>('/admin/system-configs/logo/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
