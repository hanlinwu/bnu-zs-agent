<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, Refresh } from '@element-plus/icons-vue'
import * as logApi from '@/api/admin/log'
import type { AuditLog } from '@/types/admin'

const loading = ref(false)
const logs = ref<LogRow[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

const dateRange = ref<[string, string] | null>(null)
const actionFilter = ref<string>('')
const moduleFilter = ref<string>('')
const exporting = ref(false)
const detailDrawerVisible = ref(false)
const currentDetailTitle = ref('')
const currentDetailEntries = ref<Array<{ label: string; value: string }>>([])

type LogRow = AuditLog & {
  detailObj: Record<string, unknown> | null
  url: string
  code: string
  duration: string
}

const actionOptions = [
  { label: '全部操作', value: '' },
  { label: '登录', value: 'login' },
  { label: '登出', value: 'logout' },
  { label: '查询', value: 'query' },
  { label: '创建', value: 'create' },
  { label: '更新', value: 'update' },
  { label: '删除', value: 'delete' },
  { label: '审核', value: 'review' },
  { label: '上传', value: 'upload' },
  { label: '导出', value: 'export' },
]

const moduleOptions = [
  { label: '全部模块', value: '' },
  { label: '用户', value: 'user' },
  { label: '管理员', value: 'admin' },
  { label: '知识库', value: 'knowledge' },
  { label: '模型', value: 'model' },
  { label: '敏感词', value: 'sensitive' },
  { label: '日历', value: 'calendar' },
  { label: '媒体', value: 'media' },
  { label: '对话', value: 'chat' },
]

function actionLabel(action: string) {
  const opt = actionOptions.find(o => o.value === action)
  return opt?.label || action
}

function actionTagType(action: string) {
  const map: Record<string, string> = {
    login: 'success',
    logout: 'info',
    query: '',
    create: 'success',
    update: 'warning',
    delete: 'danger',
    review: '',
    upload: 'success',
    export: 'info',
  }
  return map[action] || 'info'
}

function formatDateTime(date: string) {
  return new Date(date).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function parseDetail(detail: unknown): Record<string, unknown> | null {
  if (!detail) return null
  if (typeof detail === 'object') {
    return detail as Record<string, unknown>
  }
  if (typeof detail === 'string') {
    try {
      const parsed = JSON.parse(detail)
      if (parsed && typeof parsed === 'object') return parsed as Record<string, unknown>
    } catch {
      return { raw: detail }
    }
    return { raw: detail }
  }
  return { raw: String(detail) }
}

function stringifyValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '-'
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  if (Array.isArray(value)) return value.map(v => stringifyValue(v)).join(', ')
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}

function pickFirst(detail: Record<string, unknown> | null, keys: string[]): unknown {
  if (!detail) return undefined
  for (const key of keys) {
    if (detail[key] !== undefined && detail[key] !== null && detail[key] !== '') {
      return detail[key]
    }
  }
  return undefined
}

function normalizeDuration(raw: unknown): string {
  if (raw === undefined || raw === null || raw === '') return '-'
  if (typeof raw === 'number') return `${raw} ms`
  const text = String(raw).trim()
  if (!text) return '-'
  if (/ms$/i.test(text)) return text
  if (/^\d+(\.\d+)?$/.test(text)) return `${text} ms`
  return text
}

function moduleLabel(moduleValue: string): string {
  const opt = moduleOptions.find(o => o.value === moduleValue)
  return opt?.label || moduleValue || '-'
}

function buildDetailEntries(row: LogRow): Array<{ label: string; value: string }> {
  const detail = row.detailObj || {}
  const hiddenKeys = new Set(['path', 'url', 'request_url', 'status_code', 'code', 'duration_ms', 'duration', 'elapsed_ms'])
  const entries: Array<{ label: string; value: string }> = [
    { label: '时间', value: formatDateTime(row.createdAt) },
    { label: '操作人', value: row.userName || '-' },
    { label: '模块', value: moduleLabel(row.module) },
    { label: '操作', value: actionLabel(row.action) },
    { label: 'IP 地址', value: row.ip || '-' },
    { label: 'URL', value: row.url || '-' },
    { label: '状态码', value: row.code || '-' },
    { label: '耗时', value: row.duration || '-' },
  ]

  Object.entries(detail).forEach(([key, value]) => {
    if (hiddenKeys.has(key)) return
    if (key === 'query' && value && typeof value === 'object' && !Array.isArray(value)) {
      const queryText = Object.entries(value as Record<string, unknown>)
        .map(([k, v]) => `${k}=${stringifyValue(v)}`)
        .join(' , ')
      entries.push({ label: '查询参数', value: queryText || '-' })
      return
    }
    entries.push({ label: key, value: stringifyValue(value) })
  })

  return entries
}

function openDetail(log: LogRow) {
  currentDetailTitle.value = `${actionLabel(log.action)} · ${moduleLabel(log.module)}`
  currentDetailEntries.value = buildDetailEntries(log)
  detailDrawerVisible.value = true
}

async function fetchLogs() {
  loading.value = true
  try {
    const params: {
      page: number
      pageSize: number
      action?: string
      module?: string
      startDate?: string
      endDate?: string
    } = {
      page: currentPage.value,
      pageSize: pageSize.value,
    }
    if (actionFilter.value) params.action = actionFilter.value
    if (moduleFilter.value) params.module = moduleFilter.value
    if (dateRange.value) {
      params.startDate = dateRange.value[0]
      params.endDate = dateRange.value[1]
    }
    const res = await logApi.getLogs(params)
    const rawItems = (res.data.items || []) as any[]
    logs.value = rawItems.map((item) => {
      const detailObj = parseDetail(item.detail)
      const url = stringifyValue(pickFirst(detailObj, ['path', 'url', 'request_url']))
      const code = stringifyValue(pickFirst(detailObj, ['status_code', 'code']))
      const duration = normalizeDuration(pickFirst(detailObj, ['duration_ms', 'duration', 'elapsed_ms']))

      return {
      id: String(item.id),
      userId: item.user_id || item.admin_id || '',
      userName: item.admin_id ? `管理员:${String(item.admin_id).slice(0, 8)}` : (item.user_id ? `用户:${String(item.user_id).slice(0, 8)}` : '-'),
      ip: item.ip_address || '-',
      action: item.action || 'query',
      module: item.resource || '-',
      detail: stringifyValue(item.detail),
      detailObj,
      url,
      code,
      duration,
      createdAt: item.created_at,
    } as LogRow
    })
    total.value = res.data.total
  } catch {
    ElMessage.error('加载审计日志失败')
  } finally {
    loading.value = false
  }
}

function handleFilterChange() {
  currentPage.value = 1
  fetchLogs()
}

function handlePageChange(page: number) {
  currentPage.value = page
  fetchLogs()
}

async function handleExport() {
  if (!dateRange.value) {
    ElMessage.warning('请先选择日期范围')
    return
  }
  exporting.value = true
  try {
    const res = await logApi.exportLogs({
      startDate: dateRange.value[0],
      endDate: dateRange.value[1],
      module: moduleFilter.value || undefined,
    })
    const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `audit-logs-${dateRange.value[0]}-${dateRange.value[1]}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch {
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}

onMounted(() => {
  fetchLogs()
})
</script>

<template>
  <div class="logs-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">审计日志</h2>
        <p class="page-desc">系统操作审计记录</p>
      </div>
      <el-button
        :icon="Download"
        :loading="exporting"
        @click="handleExport"
      >
        导出
      </el-button>
    </div>

    <div class="content-card">
      <div class="toolbar">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          @change="handleFilterChange"
          style="width: 280px"
        />
        <el-select
          v-model="actionFilter"
          placeholder="操作类型"
          clearable
          @change="handleFilterChange"
          style="width: 140px"
        >
          <el-option
            v-for="opt in actionOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
        <el-select
          v-model="moduleFilter"
          placeholder="模块"
          clearable
          @change="handleFilterChange"
          style="width: 140px"
        >
          <el-option
            v-for="opt in moduleOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
      </div>

      <el-table
        v-loading="loading"
        :data="logs"
        stripe
        class="log-table"
        height="100%"
      >
        <el-table-column prop="createdAt" label="时间" width="170" class-name="time-column">
          <template #default="{ row }">
            <span class="log-time">{{ formatDateTime(row.createdAt) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="userName" label="操作人" width="120" show-overflow-tooltip />
        <el-table-column prop="action" label="操作" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="(actionTagType(row.action) as any)">
              {{ actionLabel(row.action) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="module" label="模块" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.module }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="ip" label="IP 地址" width="140" />
        <el-table-column prop="url" label="URL" min-width="260" show-overflow-tooltip />
        <el-table-column prop="code" label="状态码" width="90" align="center" />
        <el-table-column prop="duration" label="耗时" width="110" align="right" />
        <el-table-column label="操作" width="100" align="center" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" text size="small" @click="openDetail(row)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-button
          :icon="Refresh"
          circle
          size="small"
          @click="fetchLogs"
          title="刷新数据"
        />
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next, jumper"
          @current-change="handlePageChange"
        />
      </div>

      <el-drawer
        v-model="detailDrawerVisible"
        :title="`审计详情 · ${currentDetailTitle}`"
        size="560px"
        destroy-on-close
      >
        <el-descriptions
          v-if="currentDetailEntries.length"
          :column="1"
          border
        >
          <el-descriptions-item
            v-for="(item, index) in currentDetailEntries"
            :key="`${item.label}-${index}`"
            :label="item.label"
          >
            <span
              class="detail-value"
              :class="{ 'detail-value--nowrap': item.label === '时间' }"
            >{{ item.value }}</span>
          </el-descriptions-item>
        </el-descriptions>
        <div v-else class="detail-empty">无详情</div>
      </el-drawer>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.logs-page {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
}

.page-title {
  font-size: 1.375rem;
  font-weight: 700;
  color: var(--text-primary, #1A1A2E);
  margin: 0 0 4px;
}

.page-desc {
  font-size: 0.875rem;
  color: var(--text-secondary, #5A5A72);
  margin: 0;
}

.content-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary, #ffffff);
  border-radius: 12px;
  border: 1px solid var(--border-color, #E2E6ED);
  padding: 20px;
  overflow: hidden;
  min-height: 0;
}

.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.log-table {
  flex: 1;
  overflow: hidden;

  :deep(.el-table) {
    height: 100%;
  }

  :deep(.el-table__header th) {
    background: var(--bg-secondary, #F4F6FA);
    font-weight: 600;
  }
}

.log-time {
  font-size: 0.8125rem;
  font-family: monospace;
  color: var(--text-secondary, #5A5A72);
  white-space: nowrap;
  display: inline-block;
}

:deep(.time-column .cell) {
  white-space: nowrap;
}

.pagination-wrapper {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  margin-top: 16px;
  gap: 12px;
}

.detail-value {
  color: var(--text-primary, #1A1A2E);
  font-size: 0.8125rem;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.detail-value--nowrap {
  white-space: nowrap;
  word-break: normal;
}

.detail-empty {
  text-align: center;
  color: var(--text-secondary, #5A5A72);
  padding: 24px 0;
}

@media (max-width: 768px) {
  .toolbar {
    flex-direction: column;
  }
}
</style>
