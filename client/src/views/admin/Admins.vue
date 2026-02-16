<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import * as adminApi from '@/api/admin/admin'
import type { AdminItem } from '@/api/admin/admin'
import type { FormInstance, FormRules } from 'element-plus'

const loading = ref(false)
const admins = ref<AdminItem[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

const createDialogVisible = ref(false)
const editDialogVisible = ref(false)
const createFormRef = ref<FormInstance>()
const editFormRef = ref<FormInstance>()
const submitting = ref(false)

const createForm = reactive({
  username: '',
  password: '',
  real_name: '',
  phone: '',
  role_code: '' as string,
})

const editForm = reactive({
  id: '',
  username: '',
  real_name: '',
  phone: '',
  role_code: '' as string,
  status: 'active' as string,
})

const createRules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少8位', trigger: 'blur' },
  ],
  real_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  role_code: [{ required: true, message: '请选择角色', trigger: 'change' }],
}

const editRules: FormRules = {
  real_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  role_code: [{ required: true, message: '请选择角色', trigger: 'change' }],
}

function adminRoleLabel(roleCode: string | null) {
  if (!roleCode) return '-'
  const map: Record<string, string> = {
    super_admin: '超级管理员',
    reviewer: '内容审核员',
    admin: '普通管理员',
    teacher: '招生老师',
  }
  return map[roleCode] || roleCode
}

function adminRoleType(roleCode: string | null) {
  if (!roleCode) return 'info'
  const map: Record<string, string> = {
    super_admin: 'danger',
    reviewer: 'warning',
    admin: '',
    teacher: 'success',
  }
  return map[roleCode] || 'info'
}

function formatDate(date?: string | null) {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

async function fetchAdmins() {
  loading.value = true
  try {
    const res = await adminApi.getAdmins({
      page: currentPage.value,
      pageSize: pageSize.value,
    })
    admins.value = res.data.items
    total.value = res.data.total
  } catch {
    ElMessage.error('加载管理员列表失败')
  } finally {
    loading.value = false
  }
}

function handlePageChange(page: number) {
  currentPage.value = page
  fetchAdmins()
}

function openCreate() {
  createForm.username = ''
  createForm.password = ''
  createForm.real_name = ''
  createForm.phone = ''
  createForm.role_code = ''
  createDialogVisible.value = true
}

function openEdit(admin: AdminItem) {
  editForm.id = admin.id
  editForm.username = admin.username
  editForm.real_name = admin.real_name || admin.nickname
  editForm.phone = admin.phone
  editForm.role_code = admin.role_code || ''
  editForm.status = admin.status
  editDialogVisible.value = true
}

async function handleCreate() {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await adminApi.createAdmin({
      username: createForm.username,
      password: createForm.password,
      real_name: createForm.real_name,
      phone: createForm.phone || undefined,
      role_code: createForm.role_code || undefined,
    })
    ElMessage.success('管理员创建成功')
    createDialogVisible.value = false
    fetchAdmins()
  } catch {
    ElMessage.error('创建失败')
  } finally {
    submitting.value = false
  }
}

async function handleEdit() {
  const valid = await editFormRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await adminApi.updateAdmin(editForm.id, {
      real_name: editForm.real_name,
      phone: editForm.phone || undefined,
      role_code: editForm.role_code || undefined,
      status: editForm.status,
    })
    ElMessage.success('修改成功')
    editDialogVisible.value = false
    fetchAdmins()
  } catch {
    ElMessage.error('修改失败')
  } finally {
    submitting.value = false
  }
}

async function handleDelete(admin: AdminItem) {
  try {
    await ElMessageBox.confirm(
      `确定要删除管理员「${admin.real_name || admin.username}」吗？此操作不可撤销。`,
      '删除确认',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'error',
      }
    )
    await adminApi.deleteAdmin(admin.id)
    ElMessage.success('删除成功')
    fetchAdmins()
  } catch {
    // cancelled
  }
}

onMounted(() => {
  fetchAdmins()
})
</script>

<template>
  <div class="admins-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">管理员管理</h2>
        <p class="page-desc">管理系统管理员账号与权限分配</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openCreate">
        添加管理员
      </el-button>
    </div>

    <div class="content-card">
      <el-table
        v-loading="loading"
        :data="admins"
        stripe
      >
        <el-table-column prop="username" label="用户名" min-width="140" />
        <el-table-column prop="real_name" label="姓名" min-width="120" show-overflow-tooltip />
        <el-table-column prop="phone" label="手机号" min-width="140" />
        <el-table-column label="角色" width="120" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="(adminRoleType(row.role_code) as any)">
              {{ adminRoleLabel(row.role_code) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'active' ? 'success' : 'danger'">
              {{ row.status === 'active' ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_login_at" label="最后登录" width="160">
          <template #default="{ row }">{{ formatDate(row.last_login_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="openEdit(row)">编辑</el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
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
      v-model="createDialogVisible"
      title="添加管理员"
      width="480px"
      destroy-on-close
    >
      <el-form
        ref="createFormRef"
        :model="createForm"
        :rules="createRules"
        label-width="80px"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="createForm.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="createForm.password"
            type="password"
            placeholder="请输入密码（至少8位）"
            show-password
          />
        </el-form-item>
        <el-form-item label="姓名" prop="real_name">
          <el-input v-model="createForm.real_name" placeholder="请输入真实姓名" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="createForm.phone" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="角色" prop="role_code">
          <el-select v-model="createForm.role_code" placeholder="请选择角色" style="width: 100%">
            <el-option label="超级管理员" value="super_admin" />
            <el-option label="内容审核员" value="reviewer" />
            <el-option label="普通管理员" value="admin" />
            <el-option label="招生老师" value="teacher" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleCreate">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="editDialogVisible"
      title="编辑管理员"
      width="480px"
      destroy-on-close
    >
      <el-form
        ref="editFormRef"
        :model="editForm"
        :rules="editRules"
        label-width="80px"
      >
        <el-form-item label="用户名">
          <el-input :model-value="editForm.username" disabled />
        </el-form-item>
        <el-form-item label="姓名" prop="real_name">
          <el-input v-model="editForm.real_name" placeholder="请输入真实姓名" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="editForm.phone" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="角色" prop="role_code">
          <el-select v-model="editForm.role_code" placeholder="请选择角色" style="width: 100%">
            <el-option label="超级管理员" value="super_admin" />
            <el-option label="内容审核员" value="reviewer" />
            <el-option label="普通管理员" value="admin" />
            <el-option label="招生老师" value="teacher" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch
            v-model="editForm.status"
            active-value="active"
            inactive-value="disabled"
            active-text="启用"
            inactive-text="禁用"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.admins-page {
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
  overflow: hidden;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

:deep(.el-table__header th) {
  background: var(--bg-secondary, #F4F6FA) !important;
  font-weight: 600;
}
</style>
