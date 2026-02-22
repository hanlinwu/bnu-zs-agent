import request from '../request'

// ── Types ─────────────────────────────────────────────────

export interface TavilyConfig {
  enabled: boolean
  api_key: string
  search_depth: 'ultra-fast' | 'fast' | 'basic' | 'advanced'
  max_results: number
  include_domains: string[]
  exclude_domains: string[]
  include_answer: boolean | 'basic' | 'advanced'
  include_raw_content: boolean | 'markdown' | 'text'
  topic: 'general' | 'news' | 'finance'
  country: string
  time_range: '' | 'day' | 'week' | 'month' | 'year'
  chunks_per_source: number
  include_images: boolean
}

export interface TavilySearchResult {
  title: string
  url: string
  content: string
  score: number
  raw_content?: string
  published_date?: string
}

export interface TavilySearchResponse {
  query: string
  answer?: string
  results: TavilySearchResult[]
  response_time: number
  images?: { url: string; description?: string }[]
}

// ── Config ────────────────────────────────────────────────

export const getConfig = () =>
  request.get<{ key: string; value: TavilyConfig }>('/admin/web-search/config')

export const updateConfig = (value: Partial<TavilyConfig>) =>
  request.put<{ key: string; value: TavilyConfig }>('/admin/web-search/config', { value })

export const validateApiKey = (apiKey?: string) =>
  request.post<{ valid: boolean; message: string }>(
    '/admin/web-search/config/validate',
    apiKey ? { api_key: apiKey } : {},
  )

// ── Search ────────────────────────────────────────────────

export const searchQuery = (data: {
  query: string
  search_depth?: string
  max_results?: number
  include_domains?: string[]
  topic?: string
}) => request.post<TavilySearchResponse>('/admin/web-search/search', data)
