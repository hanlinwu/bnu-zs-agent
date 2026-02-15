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
}) => request.get<PaginatedResult<AuditLog>>('/admin/logs', { params })

export const getLog = (id: string) =>
  request.get<AuditLog>(`/admin/logs/${id}`)

export const exportLogs = (params: { startDate: string; endDate: string; module?: string }) =>
  request.get('/admin/logs/export', { params, responseType: 'blob' })
