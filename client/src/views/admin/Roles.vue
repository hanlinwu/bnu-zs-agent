<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import * as roleApi from '@/api/admin/role'
import type { Role, Permission } from '@/types/admin'
import type { FormInstance, FormRules } from 'element-plus'

const loading = ref(false)
const roles = ref<Role[]>([])
const allPermissions = ref<Permission[]>([])
const selectedRole = ref<Role | null>(null)
const permDialogVisible = ref(false)
const formDialogVisible = ref(false)
const formRef = ref<FormInstance>()
const submitting = ref(false)
const isEdit = ref(false)

const form = reactive({
  id: '',
  name: '',
  code: '',
  description: '',
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入角色名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入角色编码', trigger: 'blur' }],
}

const selectedPermissions = ref<string[]>([])

interface PermissionGroup {
  group: string
  items: Permission[]
}

function groupedPermissions(): PermissionGroup[] {
  const groups: Record<string, Permission[]> = {}
  allPermissions.value.forEach(p => {
    if (!groups[p.group]) groups[p.group] = []
    groups[p.group].push(p)
  })
  return Object.entries(groups).map(([group, items]) => ({ group, items }))
}

function groupLabel(group: string) {
  const map: Record<string, string> = {
    knowledge: '知识库',
    user: '用户',
    admin: '管理员',
    role: '角色',
    sensitive: '敏感词',
    model: '模型',
    calendar: '日历',
    media: '媒体',
    log: '日志',
  }
  return map[group] || group
}

async function fetchRoles() {
  loading.value = true
  try {
    const res = await roleApi.getRoles()
    roles.value = res.data
  } catch {
    ElMessage.error('加载角色列表失败')
  } finally {
    loading.value = false
  }
}

async function fetchPermissions() {
  try {
    const res = await roleApi.getPermissions()
    allPermissions.value = res.data
  } catch {
    // silent
  }
}

function openPermissions(role: Role) {
  selectedRole.value = role
  selectedPermissions.value = [...role.permissions]
  permDialogVisible.value = true
}

async function savePermissions() {
  if (!selectedRole.value) return
  submitting.value = true
  try {
    await roleApi.updateRole(selectedRole.value.id, {
      permissions: selectedPermissions.value,
    })
    ElMessage.success('权限保存成功')
    permDialogVisible.value = false
    fetchRoles()
  } catch {
    ElMessage.error('保存失败')
  } finally {
    submitting.value = false
  }
}

function openCreate() {
  isEdit.value = false
  form.id = ''
  form.name = ''
  form.code = ''
  form.description = ''
  formDialogVisible.value = true
}

function openEdit(role: Role) {
  isEdit.value = true
  form.id = role.id
  form.name = role.name
  form.code = role.code
  form.description = role.description
  formDialogVisible.value = true
}

async function handleSaveRole() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    if (isEdit.value) {
      await roleApi.updateRole(form.id, {
        name: form.name,
        description: form.description,
      })
      ElMessage.success('修改成功')
    } else {
      await roleApi.createRole({
        name: form.name,
        code: form.code,
        description: form.description,
      })
      ElMessage.success('创建成功')
    }
    formDialogVisible.value = false
    fetchRoles()
  } catch {
    ElMessage.error('操作失败')
  } finally {
    submitting.value = false
  }
}

async function handleDelete(role: Role) {
  if (role.builtIn) {
    ElMessage.warning('内置角色不可删除')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定要删除角色「${role.name}」吗？`,
      '删除确认',
      { type: 'error', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await roleApi.deleteRole(role.id)
    ElMessage.success('删除成功')
    fetchRoles()
  } catch {
    // cancelled
  }
}

function isGroupAllChecked(group: PermissionGroup) {
  return group.items.every(p => selectedPermissions.value.includes(p.code))
}

function isGroupIndeterminate(group: PermissionGroup) {
  const checked = group.items.filter(p => selectedPermissions.value.includes(p.code)).length
  return checked > 0 && checked < group.items.length
}

function toggleGroup(group: PermissionGroup, checked: boolean) {
  const codes = group.items.map(p => p.code)
  if (checked) {
    const set = new Set([...selectedPermissions.value, ...codes])
    selectedPermissions.value = Array.from(set)
  } else {
    selectedPermissions.value = selectedPermissions.value.filter(c => !codes.includes(c))
  }
}

onMounted(() => {
  fetchRoles()
  fetchPermissions()
})
</script>

<template>
  <div class="roles-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">角色权限</h2>
        <p class="page-desc">管理系统角色与权限分配</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openCreate">
        新建角色
      </el-button>
    </div>

    <div class="content-card">
      <el-table v-loading="loading" :data="roles" stripe>
        <el-table-column prop="name" label="角色名称" width="160" />
        <el-table-column prop="code" label="角色编码" width="160" />
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column label="权限数" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.permissions.length }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.builtIn ? 'warning' : ''">
              {{ row.builtIn ? '内置' : '自定义' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="openPermissions(row)">
              配置权限
            </el-button>
            <el-button type="primary" link size="small" @click="openEdit(row)">
              编辑
            </el-button>
            <el-button
              v-if="!row.builtIn"
              type="danger"
              link
              size="small"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog
      v-model="permDialogVisible"
      :title="`配置权限 — ${selectedRole?.name || ''}`"
      width="600px"
      destroy-on-close
    >
      <div class="perm-groups">
        <div
          v-for="group in groupedPermissions()"
          :key="group.group"
          class="perm-group"
        >
          <div class="perm-group-header">
            <el-checkbox
              :model-value="isGroupAllChecked(group)"
              :indeterminate="isGroupIndeterminate(group)"
              @change="(val: boolean) => toggleGroup(group, val)"
            >
              {{ groupLabel(group.group) }}
            </el-checkbox>
          </div>
          <div class="perm-group-items">
            <el-checkbox-group v-model="selectedPermissions">
              <el-checkbox
                v-for="perm in group.items"
                :key="perm.code"
                :value="perm.code"
                :label="perm.name"
              />
            </el-checkbox-group>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="permDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="savePermissions">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="formDialogVisible"
      :title="isEdit ? '编辑角色' : '新建角色'"
      width="480px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="角色名称" prop="name">
          <el-input v-model="form.name" placeholder="如：内容编辑" />
        </el-form-item>
        <el-form-item label="角色编码" prop="code">
          <el-input
            v-model="form.code"
            placeholder="如：content_editor"
            :disabled="isEdit"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="角色描述（可选）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSaveRole">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.roles-page {
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

:deep(.el-table__header th) {
  background: var(--bg-secondary, #F4F6FA);
  font-weight: 600;
}

.perm-groups {
  max-height: 480px;
  overflow-y: auto;
}

.perm-group {
  margin-bottom: 20px;

  &:last-child {
    margin-bottom: 0;
  }
}

.perm-group-header {
  padding: 8px 12px;
  background: var(--bg-secondary, #F4F6FA);
  border-radius: 6px;
  margin-bottom: 8px;
  font-weight: 600;
}

.perm-group-items {
  padding: 0 12px;

  :deep(.el-checkbox) {
    margin-right: 24px;
    margin-bottom: 8px;
  }
}
</style>
