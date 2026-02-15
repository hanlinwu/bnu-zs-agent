<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import * as logApi from '@/api/admin/log'
import type { AuditLog } from '@/types/admin'

const loading = ref(false)
const logs = ref<AuditLog[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

const dateRange = ref<[string, string] | null>(null)
const actionFilter = ref<string>('')
const moduleFilter = ref<string>('')
const exporting = ref(false)

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
    logs.value = res.data.items
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
      >
        <el-table-column prop="createdAt" label="时间" width="170">
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
        <el-table-column prop="detail" label="详情" min-width="240" show-overflow-tooltip />
        <el-table-column prop="modelVersion" label="模型版本" width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.modelVersion || '-' }}</template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next, jumper"
          @current-change="handlePageChange"
        />
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.logs-page {
  max-width: 1400px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary, #1A1A2E);
  margin: 0 0 4px;
}

.page-desc {
  font-size: 14px;
  color: var(--text-secondary, #5A5A72);
  margin: 0;
}

.content-card {
  background: var(--bg-primary, #ffffff);
  border-radius: 12px;
  border: 1px solid var(--border-color, #E2E6ED);
  padding: 20px;
}

.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.log-table {
  :deep(.el-table__header th) {
    background: var(--bg-secondary, #F4F6FA);
    font-weight: 600;
  }
}

.log-time {
  font-size: 13px;
  font-family: monospace;
  color: var(--text-secondary, #5A5A72);
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

@media (max-width: 768px) {
  .toolbar {
    flex-direction: column;
  }
}
</style>
