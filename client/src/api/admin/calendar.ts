import request from '../request'
import type { CalendarPeriod } from '@/types/admin'

export const getPeriods = () =>
  request.get<CalendarPeriod[]>('/admin/calendar/periods')

export const getPeriod = (id: string) =>
  request.get<CalendarPeriod>(`/admin/calendar/periods/${id}`)

export const createPeriod = (data: Partial<CalendarPeriod>) =>
  request.post<CalendarPeriod>('/admin/calendar/periods', data)

export const updatePeriod = (id: string, data: Partial<CalendarPeriod>) =>
  request.put<CalendarPeriod>(`/admin/calendar/periods/${id}`, data)

export const deletePeriod = (id: string) =>
  request.delete(`/admin/calendar/periods/${id}`)

export const getActivePeriod = () =>
  request.get<CalendarPeriod>('/admin/calendar/periods/active')
