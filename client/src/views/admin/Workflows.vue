<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete } from '@element-plus/icons-vue'
import * as wfApi from '@/api/admin/workflow'
import type { ReviewWorkflow, WorkflowBinding, WorkflowStep } from '@/api/admin/workflow'
import WorkflowSteps from '@/components/admin/WorkflowSteps.vue'

const loading = ref(false)
const workflows = ref<ReviewWorkflow[]>([])
const bindings = ref<WorkflowBinding[]>([])

// Workflow dialog
const wfDialogVisible = ref(false)
const wfDialogTitle = ref('')
const wfEditId = ref<string | null>(null)
const wfForm = ref({
  name: '',
  code: '',
  steps: [{ step: 1, name: '审核', role_code: 'reviewer' }] as WorkflowStep[],
})
const wfSaving = ref(false)

const roleOptions = [
  { label: '审核员 (reviewer)', value: 'reviewer' },
  { label: '管理员 (admin)', value: 'admin' },
  { label: '超级管理员 (super_admin)', value: 'super_admin' },
  { label: '招生老师 (teacher)', value: 'teacher' },
]

const resourceTypeLabels: Record<string, string> = {
  knowledge: '知识库',
  media: '多媒体资源',
}

async function fetchData() {
  loading.value = true
  try {
    const [wfRes, bindRes] = await Promise.all([
      wfApi.getWorkflows(),
      wfApi.getBindings(),
    ])
    workflows.value = wfRes.data.items
    bindings.value = bindRes.data.items
  } catch {
    ElMessage.error('加载审核流程配置失败')
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  wfEditId.value = null
  wfDialogTitle.value = '创建审核流程'
  wfForm.value = {
    name: '',
    code: '',
    steps: [{ step: 1, name: '审核', role_code: 'reviewer' }],
  }
  wfDialogVisible.value = true
}

function openEditDialog(wf: ReviewWorkflow) {
  wfEditId.value = wf.id
  wfDialogTitle.value = '编辑审核流程'
  wfForm.value = {
    name: wf.name,
    code: wf.code,
    steps: JSON.parse(JSON.stringify(wf.steps)),
  }
  wfDialogVisible.value = true
}

function addStep() {
  const nextStep = wfForm.value.steps.length + 1
  wfForm.value.steps.push({ step: nextStep, name: '', role_code: 'reviewer' })
}

function removeStep(index: number) {
  wfForm.value.steps.splice(index, 1)
  // Re-number steps
  wfForm.value.steps.forEach((s, i) => { s.step = i + 1 })
}

async function saveWorkflow() {
  if (!wfForm.value.name.trim()) {
    ElMessage.warning('请输入流程名称')
    return
  }
  if (wfForm.value.steps.length === 0) {
    ElMessage.warning('至少需要一个审核步骤')
    return
  }
  for (const s of wfForm.value.steps) {
    if (!s.name.trim()) {
      ElMessage.warning('请填写所有步骤名称')
      return
    }
  }

  wfSaving.value = true
  try {
    if (wfEditId.value) {
      await wfApi.updateWorkflow(wfEditId.value, {
        name: wfForm.value.name,
        steps: wfForm.value.steps,
      })
      ElMessage.success('更新成功')
    } else {
      if (!wfForm.value.code.trim()) {
        ElMessage.warning('请输入流程编码')
        wfSaving.value = false
        return
      }
      await wfApi.createWorkflow({
        name: wfForm.value.name,
        code: wfForm.value.code,
        steps: wfForm.value.steps,
      })
      ElMessage.success('创建成功')
    }
    wfDialogVisible.value = false
    fetchData()
  } catch {
    ElMessage.error('保存失败')
  } finally {
    wfSaving.value = false
  }
}

async function handleDeleteWorkflow(wf: ReviewWorkflow) {
  try {
    await ElMessageBox.confirm(
      `确定要删除「${wf.name}」吗？`,
      '删除确认',
      { type: 'error', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await wfApi.deleteWorkflow(wf.id)
    ElMessage.success('已删除')
    fetchData()
  } catch {
    // cancelled or error
  }
}

async function handleBindingChange(resourceType: string, workflowId: string) {
  try {
    await wfApi.updateBinding(resourceType, { workflow_id: workflowId })
    ElMessage.success('绑定更新成功')
    fetchData()
  } catch {
    ElMessage.error('绑定更新失败')
  }
}

async function handleBindingToggle(resourceType: string, enabled: boolean) {
  try {
    await wfApi.updateBinding(resourceType, { enabled })
    ElMessage.success(enabled ? '已启用' : '已禁用')
  } catch {
    ElMessage.error('更新失败')
    fetchData()
  }
}

onMounted(() => {
  fetchData()
})
</script>

<template>
  <div class="workflows-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">审核流程</h2>
        <p class="page-desc">配置审核流程模板并绑定到资源类型</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openCreateDialog">
        新建流程
      </el-button>
    </div>

    <div v-loading="loading">
      <!-- Workflow Templates Section -->
      <div class="content-card">
        <h3 class="section-title">流程模板</h3>
        <el-table :data="workflows" stripe>
          <el-table-column prop="name" label="名称" min-width="120" />
          <el-table-column prop="code" label="编码" width="120" />
          <el-table-column label="审核步骤" min-width="200">
            <template #default="{ row }">
              <WorkflowSteps :steps="row.steps" mode="tags" />
            </template>
          </el-table-column>
          <el-table-column label="类型" width="80" align="center">
            <template #default="{ row }">
              <el-tag size="small" :type="row.is_system ? 'info' : 'success'">
                {{ row.is_system ? '系统' : '自定义' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link size="small" :icon="Edit" @click="openEditDialog(row)">
                编辑
              </el-button>
              <el-button
                v-if="!row.is_system"
                type="danger"
                link
                size="small"
                :icon="Delete"
                @click="handleDeleteWorkflow(row)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- Bindings Section -->
      <div class="content-card" style="margin-top: 20px;">
        <h3 class="section-title">资源绑定</h3>
        <p class="section-desc">为每种资源类型指定使用哪个审核流程</p>
        <el-table :data="bindings" stripe>
          <el-table-column label="资源类型" width="160">
            <template #default="{ row }">
              {{ resourceTypeLabels[row.resource_type] || row.resource_type }}
            </template>
          </el-table-column>
          <el-table-column label="审核流程" min-width="200">
            <template #default="{ row }">
              <el-select
                :model-value="row.workflow_id"
                style="width: 200px"
                @change="(val: string) => handleBindingChange(row.resource_type, val)"
              >
                <el-option
                  v-for="wf in workflows"
                  :key="wf.id"
                  :label="`${wf.name}`"
                  :value="wf.id"
                />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="当前步骤" min-width="180">
            <template #default="{ row }">
              <WorkflowSteps :steps="row.workflow_steps" mode="tags" />
            </template>
          </el-table-column>
          <el-table-column label="启用" width="80" align="center">
            <template #default="{ row }">
              <el-switch
                :model-value="row.enabled"
                @change="(val: any) => handleBindingToggle(row.resource_type, !!val)"
              />
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- Workflow Create/Edit Dialog -->
    <el-dialog
      v-model="wfDialogVisible"
      :title="wfDialogTitle"
      width="600px"
      destroy-on-close
    >
      <el-form label-width="80px">
        <el-form-item label="流程名称" required>
          <el-input v-model="wfForm.name" placeholder="例如：单级审核" />
        </el-form-item>
        <el-form-item v-if="!wfEditId" label="流程编码" required>
          <el-input v-model="wfForm.code" placeholder="例如：single（创建后不可修改）" />
        </el-form-item>
        <el-form-item label="审核步骤" required>
          <div class="steps-editor">
            <div
              v-for="(step, index) in wfForm.steps"
              :key="index"
              class="step-row"
            >
              <span class="step-num">{{ index + 1 }}</span>
              <el-input
                v-model="step.name"
                placeholder="步骤名称"
                style="width: 160px"
              />
              <el-select v-model="step.role_code" style="width: 200px" placeholder="审核角色">
                <el-option
                  v-for="opt in roleOptions"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-select>
              <el-button
                v-if="wfForm.steps.length > 1"
                type="danger"
                text
                size="small"
                :icon="Delete"
                @click="removeStep(index)"
              />
            </div>
            <el-button type="primary" text size="small" :icon="Plus" @click="addStep">
              添加步骤
            </el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="wfDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="wfSaving" @click="saveWorkflow">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.workflows-page {
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

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary, #1A1A2E);
  margin: 0 0 4px;
}

.section-desc {
  font-size: 13px;
  color: var(--text-secondary, #5A5A72);
  margin: 0 0 16px;
}

.steps-editor {
  width: 100%;
}

.step-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.step-num {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--bnu-blue, #003DA5);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
</style>
