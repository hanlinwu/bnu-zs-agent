import request from '../request'
import type { CalendarPeriod } from '@/types/admin'

export const getPeriods = () =>
  request.get<CalendarPeriod[]>('/admin/calendar')

export const updatePeriod = (id: string, data: Partial<CalendarPeriod>) =>
  request.put<CalendarPeriod>(`/admin/calendar/${id}`, data)
