import request from '../request'

// ── Types ─────────────────────────────────────────────────

export interface WebSearchSite {
  id: string
  domain: string
  name: string
  start_url: string
  max_depth: number
  max_pages: number
  same_domain_only: boolean
  crawl_frequency_minutes: number
  enabled: boolean
  remote_site_id?: string
  last_crawl_at?: string
  last_crawl_status?: string
  created_at: string
  updated_at: string
}

export interface CrawlTask {
  id: string
  site_id?: string
  start_url: string
  status: 'pending' | 'running' | 'success' | 'failed'
  progress: number
  total_pages: number
  success_pages: number
  failed_pages: number
  error_message?: string
  started_at?: string
  finished_at?: string
  created_at: string
}

export interface SearchHit {
  id: string
  url: string
  title: string
  content_snippet: string
  domain: string
  crawled_at: string
  score?: number
}

export interface SearchResponse {
  hits: SearchHit[]
  total: number
  query: string
  page: number
  page_size: number
}

// ── Site CRUD ─────────────────────────────────────────────

export const getSites = () =>
  request.get<{ items: WebSearchSite[] }>('/admin/web-search/sites')

export const createSite = (data: {
  domain: string
  name: string
  start_url: string
  max_depth?: number
  max_pages?: number
  same_domain_only?: boolean
  crawl_frequency_minutes?: number
  enabled?: boolean
}) => request.post<WebSearchSite>('/admin/web-search/sites', data)

export const updateSite = (id: string, data: Partial<WebSearchSite>) =>
  request.put<WebSearchSite>(`/admin/web-search/sites/${id}`, data)

export const deleteSite = (id: string) =>
  request.delete(`/admin/web-search/sites/${id}`)

// ── Crawl operations ──────────────────────────────────────

export const triggerCrawl = (siteId: string) =>
  request.post<{ task_id: string; status: string }>(`/admin/web-search/sites/${siteId}/crawl`)

export const getCrawlTasks = (params: { page?: number; page_size?: number }) =>
  request.get<{ items: CrawlTask[]; total: number; page: number; page_size: number }>(
    '/admin/web-search/crawl-tasks',
    { params },
  )

export const getCrawlTask = (taskId: string) =>
  request.get<CrawlTask>(`/admin/web-search/crawl-tasks/${taskId}`)

// ── Search ────────────────────────────────────────────────

export const searchQuery = (data: {
  query: string
  domain?: string
  page?: number
  page_size?: number
}) => request.post<SearchResponse>('/admin/web-search/search', data)

// ── Health ────────────────────────────────────────────────

export const getHealth = () => request.get<{ status: string }>('/admin/web-search/health')
