import request from './request'
import type { SystemBasicConfig } from '@/types/admin'

interface SystemBasicResponse {
  key: 'system_basic'
  value: SystemBasicConfig
}

export const getPublicSystemBasicConfig = () =>
  request.get<SystemBasicResponse>('/system/basic')
