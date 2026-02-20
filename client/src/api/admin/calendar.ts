import request from '../request'
import type { CalendarPeriod } from '@/types/admin'

export const getPeriods = (year?: number) =>
  request.get<{ items: CalendarPeriod[] }>('/admin/calendar', { params: year ? { year } : {} })

export const getYears = () =>
  request.get<{ years: number[] }>('/admin/calendar/years')

export const createPeriod = (data: {
  period_name: string
  year: number
  start_date: string
  end_date: string
  tone_config: Record<string, unknown>
  additional_prompt?: string | null
  is_active?: boolean
}) => request.post<CalendarPeriod>('/admin/calendar', data)

export const updatePeriod = (id: string, data: {
  period_name?: string
  year?: number
  start_date?: string
  end_date?: string
  tone_config?: Record<string, unknown>
  additional_prompt?: string | null
  is_active?: boolean
}) => request.put<CalendarPeriod>(`/admin/calendar/${id}`, data)

export const deletePeriod = (id: string) =>
  request.delete(`/admin/calendar/${id}`)
