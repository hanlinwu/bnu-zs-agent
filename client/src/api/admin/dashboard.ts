import request from '../request'

export interface DashboardStats {
  user_count: number
  conversation_count: number
  active_today: number
  message_count: number
  knowledge_count: number
  pending_review_count: number
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

export const getDashboardTrends = (days: number = 7) =>
  request.get<{ items: TrendItem[] }>('/admin/dashboard/trends', { params: { days } })

export const getDashboardHot = (limit: number = 8, days: number = 7) =>
  request.get<{ items: HotQuestion[] }>('/admin/dashboard/hot', { params: { limit, days } })
