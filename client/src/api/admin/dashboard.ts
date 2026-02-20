import request from '../request'

export interface DashboardStats {
  user_count: number
  admin_count: number
  conversation_count: number
  active_today: number
  active_7d: number
  message_count: number
  message_today: number
  new_user_7d: number
  knowledge_count: number
  knowledge_approved_count: number
  pending_review_count: number
  media_count: number
  media_pending_review_count: number
}

export interface TrendItem {
  date: string
  count: number
}

export interface HotQuestion {
  question: string
  count: number
}

export const getDashboardStats = () =>
  request.get<DashboardStats>('/admin/dashboard/stats')

export const getDashboardTrends = (days: number = 7) => {
  // Get timezone offset in hours (positive for east, negative for west)
  const timezoneOffset = -new Date().getTimezoneOffset() / 60
  return request.get<{ items: TrendItem[] }>('/admin/dashboard/trends', {
    params: { days, timezone_offset: timezoneOffset }
  })
}

export const getDashboardHot = (limit: number = 8, days: number = 7) =>
  request.get<{ items: HotQuestion[] }>('/admin/dashboard/hot', { params: { limit, days } })
