<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import * as userApi from '@/api/admin/user'
import * as roleApi from '@/api/admin/role'
import type { AdminUser } from '@/types/user'
import type { Role } from '@/types/admin'
import type { FormInstance, FormRules } from 'element-plus'

const loading = ref(false)
const admins = ref<AdminUser[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const roles = ref<Role[]>([])

const createDialogVisible = ref(false)
const editDialogVisible = ref(false)
const createFormRef = ref<FormInstance>()
const editFormRef = ref<FormInstance>()
const submitting = ref(false)

const createForm = reactive({
  username: '',
  password: '',
  nickname: '',
  phone: '',
  adminRole: '' as string,
})

const editForm = reactive({
  id: '',
  username: '',
  nickname: '',
  phone: '',
  adminRole: '' as string,
  enabled: true,
})

const createRules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少8位', trigger: 'blur' },
  ],
  nickname: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  adminRole: [{ required: true, message: '请选择角色', trigger: 'change' }],
}

const editRules: FormRules = {
  nickname: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  adminRole: [{ required: true, message: '请选择角色', trigger: 'change' }],
}

function adminRoleLabel(role: string) {
  const map: Record<string, string> = {
    super_admin: '超级管理员',
    content_reviewer: '内容审核员',
    admin: '普通管理员',
    teacher: '招生老师',
  }
  return map[role] || role
}

function adminRoleType(role: string) {
  const map: Record<string, string> = {
    super_admin: 'danger',
    content_reviewer: 'warning',
    admin: '',
    teacher: 'success',
  }
  return map[role] || 'info'
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

async function fetchAdmins() {
  loading.value = true
  try {
    const res = await userApi.getUsers({
      page: currentPage.value,
      pageSize: pageSize.value,
      keyword: undefined,
    })
    admins.value = res.data.items
    total.value = res.data.total
  } catch {
    ElMessage.error('加载管理员列表失败')
  } finally {
    loading.value = false
  }
}

async function fetchRoles() {
  try {
    const res = await roleApi.getRoles()
    roles.value = res.data
  } catch {
    // silent
  }
}

function handlePageChange(page: number) {
  currentPage.value = page
  fetchAdmins()
}

function openCreate() {
  createForm.username = ''
  createForm.password = ''
  createForm.nickname = ''
  createForm.phone = ''
  createForm.adminRole = ''
  createDialogVisible.value = true
}

function openEdit(admin: AdminUser) {
  editForm.id = admin.id
  editForm.username = admin.username
  editForm.nickname = admin.nickname
  editForm.phone = admin.phone
  editForm.adminRole = admin.adminRole
  editForm.enabled = admin.enabled
  editDialogVisible.value = true
}

async function handleCreate() {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await userApi.createUser({
      username: createForm.username,
      phone: createForm.phone,
      nickname: createForm.nickname,
      adminRole: createForm.adminRole as any,
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
    await userApi.updateUser(editForm.id, {
      nickname: editForm.nickname,
      phone: editForm.phone,
      adminRole: editForm.adminRole as any,
      enabled: editForm.enabled,
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

async function handleDelete(admin: AdminUser) {
  try {
    await ElMessageBox.confirm(
      `确定要删除管理员「${admin.nickname || admin.username}」吗？此操作不可撤销。`,
      '删除确认',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'error',
      }
    )
    await userApi.deleteUser(admin.id)
    ElMessage.success('删除成功')
    fetchAdmins()
  } catch {
    // cancelled
  }
}

onMounted(() => {
  fetchAdmins()
  fetchRoles()
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
        <el-table-column prop="username" label="用户名" width="140" />
        <el-table-column prop="nickname" label="姓名" width="120" show-overflow-tooltip />
        <el-table-column prop="phone" label="手机号" width="140" />
        <el-table-column prop="adminRole" label="角色" width="120" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="(adminRoleType(row.adminRole) as any)">
              {{ adminRoleLabel(row.adminRole) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.enabled ? 'success' : 'danger'">
              {{ row.enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="lastLoginAt" label="最后登录" width="160">
          <template #default="{ row }">{{ formatDate(row.lastLoginAt) }}</template>
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
        <el-form-item label="姓名" prop="nickname">
          <el-input v-model="createForm.nickname" placeholder="请输入真实姓名" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="createForm.phone" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="角色" prop="adminRole">
          <el-select v-model="createForm.adminRole" placeholder="请选择角色" style="width: 100%">
            <el-option label="超级管理员" value="super_admin" />
            <el-option label="内容审核员" value="content_reviewer" />
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
        <el-form-item label="姓名" prop="nickname">
          <el-input v-model="editForm.nickname" placeholder="请输入真实姓名" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="editForm.phone" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="角色" prop="adminRole">
          <el-select v-model="editForm.adminRole" placeholder="请选择角色" style="width: 100%">
            <el-option label="超级管理员" value="super_admin" />
            <el-option label="内容审核员" value="content_reviewer" />
            <el-option label="普通管理员" value="admin" />
            <el-option label="招生老师" value="teacher" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="editForm.enabled" active-text="启用" inactive-text="禁用" />
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

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

:deep(.el-table__header th) {
  background: var(--bg-secondary, #F4F6FA);
  font-weight: 600;
}
</style>
