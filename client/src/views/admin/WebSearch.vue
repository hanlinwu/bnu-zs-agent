<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh, Delete, Edit, ChromeFilled } from '@element-plus/icons-vue'
import * as webSearchApi from '@/api/admin/webSearch'
import type { WebSearchSite, CrawlTask, SearchHit } from '@/api/admin/webSearch'

// ── Site management ─────────────────────────────────────────

const sites = ref<WebSearchSite[]>([])
const siteLoading = ref(false)
const siteDialogVisible = ref(false)
const siteEditing = ref<WebSearchSite | null>(null)
const siteSaving = ref(false)
const siteForm = ref({
  domain: '',
  name: '',
  start_url: '',
  max_depth: 3,
  max_pages: 100,
  same_domain_only: true,
  crawl_frequency_minutes: 1440,
  enabled: true,
})

async function fetchSites() {
  siteLoading.value = true
  try {
    const res = await webSearchApi.getSites()
    sites.value = res.data.items
  } catch {
    ElMessage.error('获取站点列表失败')
  } finally {
    siteLoading.value = false
  }
}

function openSiteDialog(site?: WebSearchSite) {
  if (site) {
    siteEditing.value = site
    siteForm.value = {
      domain: site.domain,
      name: site.name,
      start_url: site.start_url,
      max_depth: site.max_depth,
      max_pages: site.max_pages,
      same_domain_only: site.same_domain_only,
      crawl_frequency_minutes: site.crawl_frequency_minutes,
      enabled: site.enabled,
    }
  } else {
    siteEditing.value = null
    siteForm.value = {
      domain: '',
      name: '',
      start_url: '',
      max_depth: 3,
      max_pages: 100,
      same_domain_only: true,
      crawl_frequency_minutes: 1440,
      enabled: true,
    }
  }
  siteDialogVisible.value = true
}

async function handleSiteSubmit() {
  if (!siteForm.value.domain || !siteForm.value.name || !siteForm.value.start_url) {
    ElMessage.warning('请填写必要字段')
    return
  }
  siteSaving.value = true
  try {
    if (siteEditing.value) {
      await webSearchApi.updateSite(siteEditing.value.id, siteForm.value)
      ElMessage.success('站点已更新')
    } else {
      await webSearchApi.createSite(siteForm.value)
      ElMessage.success('站点已创建')
    }
    siteDialogVisible.value = false
    await fetchSites()
  } catch {
    ElMessage.error('操作失败')
  } finally {
    siteSaving.value = false
  }
}

async function handleDeleteSite(site: WebSearchSite) {
  try {
    await ElMessageBox.confirm(`确定删除站点 "${site.name}" 吗？删除后该域名的索引数据也将被清除。`, '确认删除', {
      type: 'warning',
    })
    await webSearchApi.deleteSite(site.id)
    ElMessage.success('站点已删除')
    await fetchSites()
  } catch {
    // cancelled or error
  }
}

async function handleToggleEnabled(site: WebSearchSite) {
  try {
    await webSearchApi.updateSite(site.id, { enabled: site.enabled })
  } catch {
    site.enabled = !site.enabled
    ElMessage.error('更新失败')
  }
}

async function handleTriggerCrawl(site: WebSearchSite) {
  try {
    await webSearchApi.triggerCrawl(site.id)
    ElMessage.success('爬取任务已触发')
    await fetchCrawlTasks()
  } catch {
    ElMessage.error('触发爬取失败，请检查搜索微服务是否正常运行')
  }
}

function formatFrequency(minutes: number): string {
  if (minutes < 60) return `${minutes} 分钟`
  if (minutes < 1440) return `${Math.round(minutes / 60)} 小时`
  return `${Math.round(minutes / 1440)} 天`
}

// ── Search test ─────────────────────────────────────────────

const searchKeyword = ref('')
const searchDomain = ref('')
const searchResults = ref<SearchHit[]>([])
const searchTotal = ref(0)
const searchLoading = ref(false)
const searchPage = ref(1)

async function handleSearch() {
  if (!searchKeyword.value.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }
  searchLoading.value = true
  searchPage.value = 1
  try {
    const res = await webSearchApi.searchQuery({
      query: searchKeyword.value,
      domain: searchDomain.value || undefined,
      page: searchPage.value,
      page_size: 10,
    })
    searchResults.value = res.data.hits
    searchTotal.value = res.data.total
  } catch {
    ElMessage.error('搜索失败，请检查搜索微服务是否正常运行')
  } finally {
    searchLoading.value = false
  }
}

// ── Crawl tasks ─────────────────────────────────────────────

const crawlTasks = ref<CrawlTask[]>([])
const crawlTasksLoading = ref(false)
const crawlTasksTotal = ref(0)
const crawlTasksPage = ref(1)
const crawlTimer = ref<ReturnType<typeof setInterval> | null>(null)

async function fetchCrawlTasks() {
  crawlTasksLoading.value = true
  try {
    const res = await webSearchApi.getCrawlTasks({
      page: crawlTasksPage.value,
      page_size: 10,
    })
    crawlTasks.value = res.data.items
    crawlTasksTotal.value = res.data.total

    // Auto-poll if tasks are running
    const hasRunning = crawlTasks.value.some(t => t.status === 'pending' || t.status === 'running')
    if (hasRunning && !crawlTimer.value) {
      crawlTimer.value = setInterval(fetchCrawlTasks, 5000)
    } else if (!hasRunning && crawlTimer.value) {
      clearInterval(crawlTimer.value)
      crawlTimer.value = null
    }
  } catch {
    // microservice may be down
  } finally {
    crawlTasksLoading.value = false
  }
}

function statusType(status: string) {
  switch (status) {
    case 'success': return 'success'
    case 'running': return 'primary'
    case 'pending': return 'info'
    case 'failed': return 'danger'
    default: return 'info'
  }
}

function statusLabel(status: string) {
  switch (status) {
    case 'success': return '完成'
    case 'running': return '进行中'
    case 'pending': return '等待中'
    case 'failed': return '失败'
    default: return status
  }
}

function formatTime(iso: string | null | undefined) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN')
}

// ── Lifecycle ───────────────────────────────────────────────

onMounted(() => {
  fetchSites()
  fetchCrawlTasks()
})

onBeforeUnmount(() => {
  if (crawlTimer.value) {
    clearInterval(crawlTimer.value)
    crawlTimer.value = null
  }
})
</script>

<template>
  <div class="web-search-page">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h2 class="page-title">网页搜索管理</h2>
        <p class="page-desc">配置网页爬取站点、测试搜索功能、监控爬取任务</p>
      </div>
    </div>

    <!-- Section 1: Site Management -->
    <div class="section-card">
      <div class="section-header">
        <h3 class="section-title">站点管理</h3>
        <el-button type="primary" :icon="Plus" @click="openSiteDialog()">添加站点</el-button>
      </div>
      <el-table :data="sites" v-loading="siteLoading" stripe style="width: 100%">
        <el-table-column prop="name" label="名称" min-width="120" />
        <el-table-column prop="domain" label="域名" min-width="180" />
        <el-table-column prop="start_url" label="起始URL" min-width="200" show-overflow-tooltip />
        <el-table-column label="深度" width="70" align="center">
          <template #default="{ row }">{{ row.max_depth }}</template>
        </el-table-column>
        <el-table-column label="最大页数" width="90" align="center">
          <template #default="{ row }">{{ row.max_pages }}</template>
        </el-table-column>
        <el-table-column label="爬取频率" width="100" align="center">
          <template #default="{ row }">{{ formatFrequency(row.crawl_frequency_minutes) }}</template>
        </el-table-column>
        <el-table-column label="启用" width="80" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.enabled" @change="handleToggleEnabled(row)" />
          </template>
        </el-table-column>
        <el-table-column label="上次爬取" width="160" align="center">
          <template #default="{ row }">
            <span>{{ formatTime(row.last_crawl_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" :icon="ChromeFilled" @click="handleTriggerCrawl(row)">
              爬取
            </el-button>
            <el-button type="primary" link size="small" :icon="Edit" @click="openSiteDialog(row)">
              编辑
            </el-button>
            <el-button type="danger" link size="small" :icon="Delete" @click="handleDeleteSite(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Section 2: Search Test -->
    <div class="section-card">
      <div class="section-header">
        <h3 class="section-title">搜索测试</h3>
      </div>
      <div class="search-bar">
        <el-input
          v-model="searchKeyword"
          placeholder="输入搜索关键词"
          clearable
          style="flex: 1"
          @keyup.enter="handleSearch"
        />
        <el-select v-model="searchDomain" clearable placeholder="所有域名" style="width: 220px">
          <el-option v-for="s in sites" :key="s.id" :label="s.domain" :value="s.domain" />
        </el-select>
        <el-button type="primary" :icon="Search" :loading="searchLoading" @click="handleSearch">
          搜索
        </el-button>
      </div>

      <div v-if="searchResults.length > 0" class="search-results">
        <p class="search-summary">共找到约 {{ searchTotal }} 条结果</p>
        <div v-for="hit in searchResults" :key="hit.id" class="search-hit">
          <div class="search-hit-title">
            <a :href="hit.url" target="_blank" rel="noopener">{{ hit.title || hit.url }}</a>
          </div>
          <div class="search-hit-url">{{ hit.url }}</div>
          <div class="search-hit-snippet">{{ hit.content_snippet }}</div>
          <div class="search-hit-meta">
            <el-tag size="small" type="info">{{ hit.domain }}</el-tag>
            <span class="search-hit-time">{{ formatTime(hit.crawled_at) }}</span>
          </div>
        </div>
      </div>
      <div v-else-if="searchKeyword && !searchLoading" class="search-empty">
        暂无搜索结果
      </div>
    </div>

    <!-- Section 3: Crawl Tasks -->
    <div class="section-card">
      <div class="section-header">
        <h3 class="section-title">爬取任务</h3>
        <el-button :icon="Refresh" @click="fetchCrawlTasks">刷新</el-button>
      </div>
      <el-table :data="crawlTasks" v-loading="crawlTasksLoading" stripe style="width: 100%">
        <el-table-column prop="start_url" label="起始URL" min-width="200" show-overflow-tooltip />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="150">
          <template #default="{ row }">
            <el-progress
              :percentage="row.progress"
              :status="row.status === 'failed' ? 'exception' : row.status === 'success' ? 'success' : undefined"
              :stroke-width="10"
            />
          </template>
        </el-table-column>
        <el-table-column label="成功/总数" width="110" align="center">
          <template #default="{ row }">
            <span>{{ row.success_pages }} / {{ row.total_pages }}</span>
          </template>
        </el-table-column>
        <el-table-column label="失败" width="70" align="center">
          <template #default="{ row }">
            <span :class="{ 'text-danger': row.failed_pages > 0 }">{{ row.failed_pages }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="error_message" label="错误信息" min-width="150" show-overflow-tooltip />
        <el-table-column label="开始时间" width="160" align="center">
          <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
        </el-table-column>
        <el-table-column label="完成时间" width="160" align="center">
          <template #default="{ row }">{{ formatTime(row.finished_at) }}</template>
        </el-table-column>
      </el-table>

      <div v-if="crawlTasksTotal > 10" class="pagination-wrapper">
        <el-pagination
          v-model:current-page="crawlTasksPage"
          :page-size="10"
          :total="crawlTasksTotal"
          layout="total, prev, pager, next"
          @current-change="fetchCrawlTasks"
        />
      </div>
    </div>

    <!-- Site Create/Edit Dialog -->
    <el-dialog
      v-model="siteDialogVisible"
      :title="siteEditing ? '编辑站点' : '添加站点'"
      width="560px"
      destroy-on-close
    >
      <el-form :model="siteForm" label-width="100px">
        <el-form-item label="站点名称" required>
          <el-input v-model="siteForm.name" placeholder="例如：北师大招生网" maxlength="100" />
        </el-form-item>
        <el-form-item label="域名" required>
          <el-input
            v-model="siteForm.domain"
            placeholder="例如：admission.bnu.edu.cn"
            :disabled="!!siteEditing"
            maxlength="200"
          />
        </el-form-item>
        <el-form-item label="起始URL" required>
          <el-input v-model="siteForm.start_url" placeholder="https://admission.bnu.edu.cn" maxlength="500" />
        </el-form-item>
        <el-form-item label="最大深度">
          <el-input-number v-model="siteForm.max_depth" :min="1" :max="10" />
        </el-form-item>
        <el-form-item label="最大页数">
          <el-input-number v-model="siteForm.max_pages" :min="1" :max="10000" :step="10" />
        </el-form-item>
        <el-form-item label="仅同域名">
          <el-switch v-model="siteForm.same_domain_only" />
        </el-form-item>
        <el-form-item label="爬取频率">
          <el-select v-model="siteForm.crawl_frequency_minutes" style="width: 200px">
            <el-option :value="60" label="每小时" />
            <el-option :value="360" label="每 6 小时" />
            <el-option :value="720" label="每 12 小时" />
            <el-option :value="1440" label="每天" />
            <el-option :value="10080" label="每周" />
            <el-option :value="43200" label="每月" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="siteForm.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="siteDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="siteSaving" @click="handleSiteSubmit">
          {{ siteEditing ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.web-search-page {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.page-title {
  font-size: 1.375rem;
  font-weight: 700;
  color: var(--text-primary, #1a1a2e);
  margin: 0 0 4px;
}

.page-desc {
  font-size: 0.875rem;
  color: var(--text-secondary, #6B7280);
  margin: 0;
}

.section-card {
  background: var(--bg-primary, #ffffff);
  border-radius: 12px;
  border: 1px solid var(--border-color, #e2e6ed);
  padding: 20px;
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary, #1a1a2e);
  margin: 0;
}

// ── Search ──────────────────────────────────

.search-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.search-results {
  margin-top: 8px;
}

.search-summary {
  font-size: 0.875rem;
  color: var(--text-secondary, #6B7280);
  margin-bottom: 12px;
}

.search-hit {
  padding: 12px 0;
  border-bottom: 1px solid var(--border-color, #e2e6ed);

  &:last-child {
    border-bottom: none;
  }
}

.search-hit-title a {
  font-size: 1rem;
  font-weight: 500;
  color: var(--bnu-blue, #1a4b8c);
  text-decoration: none;

  &:hover {
    text-decoration: underline;
  }
}

.search-hit-url {
  font-size: 0.75rem;
  color: var(--text-tertiary, #9CA3AF);
  margin: 2px 0;
  word-break: break-all;
}

.search-hit-snippet {
  font-size: 0.875rem;
  color: var(--text-secondary, #6B7280);
  line-height: 1.5;
  margin: 4px 0;
}

.search-hit-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.search-hit-time {
  font-size: 0.75rem;
  color: var(--text-tertiary, #9CA3AF);
}

.search-empty {
  text-align: center;
  padding: 32px 0;
  color: var(--text-secondary, #6B7280);
}

// ── Misc ────────────────────────────────────

.text-danger {
  color: var(--el-color-danger);
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
