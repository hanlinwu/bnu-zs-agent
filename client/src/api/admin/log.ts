import request from '../request'
import type { AuditLog, PaginatedResult } from '@/types/admin'

export const getLogs = (params: {
  page: number
  pageSize: number
  userId?: string
  action?: string
  module?: string
  startDate?: string
  endDate?: string
}) => request.get<PaginatedResult<AuditLog>>('/admin/logs', {
  params: {
    page: params.page,
    page_size: params.pageSize,
    user_id: params.userId,
    action: params.action,
    resource: params.module,
    start_time: params.startDate,
    end_time: params.endDate,
  },
})

export const getLog = (id: string) =>
  request.get<AuditLog>(`/admin/logs/${id}`)

export const exportLogs = (params: { startDate: string; endDate: string; module?: string }) =>
  request.get('/admin/logs/export', {
    params: {
      start_time: params.startDate,
      end_time: params.endDate,
      resource: params.module,
    },
    responseType: 'blob',
  })
