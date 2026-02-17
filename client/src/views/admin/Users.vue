<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import * as userApi from '@/api/admin/user'
import type { AdminUser } from '@/types/user'

const loading = ref(false)
const users = ref<AdminUser[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const searchKeyword = ref('')
const detailDialogVisible = ref(false)
const selectedUser = ref<AdminUser | null>(null)

const activeStatus = ref<string>('all')
const selectedUsers = ref<any[]>([])
const batchLoading = ref(false)
const tableRef = ref()

const batchEnabled = computed(() => activeStatus.value !== 'all')

function roleLabel(role: string) {
  const map: Record<string, string> = {
    gaokao: '高考生',
    kaoyan: '考研生',
    international: '国际学生',
    parent: '家长',
  }
  return map[role] || role
}

function formatDate(date?: string) {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

async function fetchUsers() {
  loading.value = true
  try {
    const res = await userApi.getUsers({
      page: currentPage.value,
      pageSize: pageSize.value,
      keyword: searchKeyword.value || undefined,
      status: activeStatus.value === 'all' ? undefined : activeStatus.value,
    })
    users.value = res.data.items
    total.value = res.data.total
  } catch {
    ElMessage.error('加载用户列表失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  currentPage.value = 1
  tableRef.value?.clearSelection()
  fetchUsers()
}

function handlePageChange(page: number) {
  currentPage.value = page
  tableRef.value?.clearSelection()
  fetchUsers()
}

function handleStatusTabChange(status: string) {
  activeStatus.value = status
  currentPage.value = 1
  selectedUsers.value = []
  tableRef.value?.clearSelection()
  fetchUsers()
}

function handleSelectionChange(selection: any[]) {
  selectedUsers.value = selection
}

async function handleBatchAction(action: 'ban' | 'unban') {
  if (selectedUsers.value.length === 0) return
  const label = action === 'ban' ? '封禁' : '解封'
  try {
    await ElMessageBox.confirm(
      `确定要批量${label}选中的 ${selectedUsers.value.length} 个用户吗？`,
      '批量操作确认',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    batchLoading.value = true
    const res = await userApi.batchBanUsers({
      ids: selectedUsers.value.map((u: any) => u.id),
      action,
    })
    const data = res.data as any
    ElMessage.success(`批量${label}完成，成功 ${data.success_count} 项`)
    selectedUsers.value = []
    fetchUsers()
  } catch {
    // cancelled
  } finally {
    batchLoading.value = false
  }
}

function viewDetail(user: AdminUser) {
  selectedUser.value = user
  detailDialogVisible.value = true
}

async function toggleStatus(user: AdminUser) {
  const action = user.status === 'active' ? '封禁' : '解封'
  try {
    await ElMessageBox.confirm(
      `确定要${action}用户「${user.nickname || user.phone}」吗？`,
      `${action}确认`,
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    await userApi.toggleUserBan(user.id)
    ElMessage.success(`${action}成功`)
    fetchUsers()
  } catch {
    // cancelled
  }
}

onMounted(() => {
  fetchUsers()
})
</script>

<template>
  <div class="users-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">用户管理</h2>
        <p class="page-desc">管理系统注册用户</p>
      </div>
    </div>

    <div class="content-card">
      <div class="toolbar">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索手机号 / 昵称"
          :prefix-icon="Search"
          clearable
          style="width: 280px"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        />
        <el-button type="primary" @click="handleSearch">搜索</el-button>
      </div>

      <el-tabs :model-value="activeStatus" @update:model-value="handleStatusTabChange">
        <el-tab-pane label="全部" name="all" />
        <el-tab-pane label="正常" name="active" />
        <el-tab-pane label="封禁" name="banned" />
      </el-tabs>

      <div v-if="batchEnabled && selectedUsers.length > 0" class="batch-bar">
        <span class="batch-count">已选 {{ selectedUsers.length }} 项</span>
        <el-button
          v-if="activeStatus === 'active'"
          type="danger"
          size="small"
          :loading="batchLoading"
          @click="handleBatchAction('ban')"
        >
          批量封禁
        </el-button>
        <el-button
          v-if="activeStatus === 'banned'"
          type="success"
          size="small"
          :loading="batchLoading"
          @click="handleBatchAction('unban')"
        >
          批量解封
        </el-button>
      </div>

      <el-table
        ref="tableRef"
        v-loading="loading"
        :data="users"
        stripe
        height="100%"
        class="user-table"
        @selection-change="handleSelectionChange"
      >
        <el-table-column v-if="batchEnabled" type="selection" width="50" />
        <el-table-column prop="phone" label="手机号" min-width="140" />
        <el-table-column prop="nickname" label="昵称" min-width="140" show-overflow-tooltip />
        <el-table-column prop="province" label="省份" min-width="100" show-overflow-tooltip />
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag
              size="small"
              :type="row.status === 'active' ? 'success' : 'danger'"
            >
              {{ row.status === 'active' ? '正常' : '封禁' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="lastLoginAt" label="最后登录" width="160">
          <template #default="{ row }">{{ formatDate(row.lastLoginAt) }}</template>
        </el-table-column>
        <el-table-column prop="createdAt" label="注册时间" width="160">
          <template #default="{ row }">{{ formatDate(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="viewDetail(row)">
              查看详情
            </el-button>
            <el-button
              :type="row.status === 'active' ? 'danger' : 'success'"
              link
              size="small"
              @click="toggleStatus(row)"
            >
              {{ row.status === 'active' ? '封禁' : '解封' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="handlePageChange"
        />
      </div>
    </div>

    <el-dialog
      v-model="detailDialogVisible"
      title="用户详情"
      width="480px"
      destroy-on-close
    >
      <div v-if="selectedUser" class="user-detail">
        <div class="detail-row">
          <span class="detail-label">手机号</span>
          <span class="detail-value">{{ selectedUser.phone }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">昵称</span>
          <span class="detail-value">{{ selectedUser.nickname || '-' }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">省份</span>
          <span class="detail-value">{{ selectedUser.province || '-' }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">账号状态</span>
          <el-tag size="small" :type="selectedUser.status === 'active' ? 'success' : 'danger'">
            {{ selectedUser.status === 'active' ? '正常' : '封禁' }}
          </el-tag>
        </div>
        <div class="detail-row">
          <span class="detail-label">注册时间</span>
          <span class="detail-value">{{ formatDate(selectedUser.createdAt) }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">最后登录</span>
          <span class="detail-value">{{ formatDate(selectedUser.lastLoginAt) }}</span>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.users-page {
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
}

.batch-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--el-color-primary-light-9, #ECF5FF);
  border-radius: 8px;
  margin-bottom: 12px;
}

.batch-count {
  font-size: 13px;
  color: var(--text-primary, #1A1A2E);
  font-weight: 500;
}

.user-table {
  flex: 1;
  overflow: hidden;

  :deep(.el-table) {
    height: 100%;
  }

  :deep(.el-table__header th) {
    background: var(--bg-secondary, #F4F6FA) !important;
    font-weight: 600;
  }
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.user-detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.detail-label {
  width: 80px;
  flex-shrink: 0;
  font-size: 13px;
  color: var(--text-secondary, #5A5A72);
}

.detail-value {
  font-size: 14px;
  color: var(--text-primary, #1A1A2E);
  font-weight: 500;
}
</style>
