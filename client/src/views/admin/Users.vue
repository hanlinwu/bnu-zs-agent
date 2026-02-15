<script setup lang="ts">
import { ref, onMounted } from 'vue'
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
  fetchUsers()
}

function handlePageChange(page: number) {
  currentPage.value = page
  fetchUsers()
}

function viewDetail(user: AdminUser) {
  selectedUser.value = user
  detailDialogVisible.value = true
}

async function toggleStatus(user: AdminUser) {
  const action = user.enabled ? '封禁' : '解封'
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
    await userApi.toggleUserStatus(user.id, !user.enabled)
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

      <el-table
        v-loading="loading"
        :data="users"
        stripe
        class="user-table"
      >
        <el-table-column prop="phone" label="手机号" width="140" />
        <el-table-column prop="nickname" label="昵称" width="140" show-overflow-tooltip />
        <el-table-column prop="adminRole" label="角色" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ roleLabel(row.adminRole) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag
              size="small"
              :type="row.enabled ? 'success' : 'danger'"
            >
              {{ row.enabled ? '正常' : '封禁' }}
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
              :type="row.enabled ? 'danger' : 'success'"
              link
              size="small"
              @click="toggleStatus(row)"
            >
              {{ row.enabled ? '封禁' : '解封' }}
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
          <span class="detail-label">用户角色</span>
          <span class="detail-value">{{ roleLabel(selectedUser.adminRole) }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">账号状态</span>
          <el-tag size="small" :type="selectedUser.enabled ? 'success' : 'danger'">
            {{ selectedUser.enabled ? '正常' : '封禁' }}
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
  max-width: 1200px;
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
}

.user-table {
  :deep(.el-table__header th) {
    background: var(--bg-secondary, #F4F6FA);
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
