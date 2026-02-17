<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete } from '@element-plus/icons-vue'
import * as wfApi from '@/api/admin/workflow'
import type { ReviewWorkflow, WorkflowBinding, WorkflowDefinition, WorkflowNode, WorkflowAction, WorkflowTransition } from '@/api/admin/workflow'
import WorkflowGraph from '@/components/admin/WorkflowGraph.vue'

const loading = ref(false)
const workflows = ref<ReviewWorkflow[]>([])
const bindings = ref<WorkflowBinding[]>([])

// Dialog state
const dialogVisible = ref(false)
const dialogTitle = ref('')
const editId = ref<string | null>(null)
const saving = ref(false)

const formName = ref('')
const formCode = ref('')
const formNodes = ref<WorkflowNode[]>([])
const formActions = ref<WorkflowAction[]>([])
const formTransitions = ref<WorkflowTransition[]>([])

const roleOptions = [
  { label: '审核员', value: 'reviewer' },
  { label: '管理员', value: 'admin' },
  { label: '超级管理员', value: 'super_admin' },
  { label: '招生老师', value: 'teacher' },
]

const nodeTypeOptions = [
  { label: '起始', value: 'start' },
  { label: '中间', value: 'intermediate' },
  { label: '终止', value: 'terminal' },
]

const resourceTypeLabels: Record<string, string> = {
  knowledge: '知识库',
  media: '多媒体资源',
}

const currentDefinition = computed<WorkflowDefinition>(() => ({
  nodes: formNodes.value,
  actions: formActions.value,
  transitions: formTransitions.value,
}))

// Node options for transition selects
const nodeOptions = computed(() =>
  formNodes.value.map(n => ({ label: `${n.name} (${n.id})`, value: n.id }))
)

const actionOptions = computed(() =>
  formActions.value.map(a => ({ label: `${a.name} (${a.id})`, value: a.id }))
)

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
    ElMessage.error('加载工作流配置失败')
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  editId.value = null
  dialogTitle.value = '新建工作流'
  formName.value = ''
  formCode.value = ''
  formNodes.value = [
    { id: 'start', name: '开始', type: 'start', view_roles: [], edit_roles: [] },
  ]
  formActions.value = [
    { id: 'submit', name: '提交' },
  ]
  formTransitions.value = []
  dialogVisible.value = true
}

function openEditDialog(wf: ReviewWorkflow) {
  editId.value = wf.id
  dialogTitle.value = '编辑工作流'
  formName.value = wf.name
  formCode.value = wf.code
  formNodes.value = JSON.parse(JSON.stringify(wf.definition.nodes))
  formActions.value = JSON.parse(JSON.stringify(wf.definition.actions))
  formTransitions.value = JSON.parse(JSON.stringify(wf.definition.transitions))
  dialogVisible.value = true
}

// Node CRUD
function addNode() {
  const id = `node_${Date.now()}`
  formNodes.value.push({ id, name: '', type: 'intermediate', view_roles: [], edit_roles: [] })
}

function removeNode(index: number) {
  formNodes.value.splice(index, 1)
}

// Action CRUD
function addAction() {
  const id = `action_${Date.now()}`
  formActions.value.push({ id, name: '' })
}

function removeAction(index: number) {
  formActions.value.splice(index, 1)
}

// Transition CRUD
function addTransition() {
  formTransitions.value.push({ from_node: '', action: '', to_node: '' })
}

function removeTransition(index: number) {
  formTransitions.value.splice(index, 1)
}

function validateForm(): boolean {
  if (!formName.value.trim()) {
    ElMessage.warning('请输入工作流名称')
    return false
  }
  if (!editId.value && !formCode.value.trim()) {
    ElMessage.warning('请输入工作流编码')
    return false
  }

  const hasStart = formNodes.value.some(n => n.type === 'start')
  if (!hasStart) {
    ElMessage.warning('至少需要一个起始节点')
    return false
  }

  const hasTerminal = formNodes.value.some(n => n.type === 'terminal')
  if (!hasTerminal) {
    ElMessage.warning('至少需要一个终止节点')
    return false
  }

  if (formActions.value.length === 0) {
    ElMessage.warning('至少需要一个动作')
    return false
  }

  if (formTransitions.value.length === 0) {
    ElMessage.warning('至少需要一条转换规则')
    return false
  }

  for (const n of formNodes.value) {
    if (!n.id.trim() || !n.name.trim()) {
      ElMessage.warning('请填写所有节点的 ID 和名称')
      return false
    }
  }

  for (const a of formActions.value) {
    if (!a.id.trim() || !a.name.trim()) {
      ElMessage.warning('请填写所有动作的 ID 和名称')
      return false
    }
  }

  for (const t of formTransitions.value) {
    if (!t.from_node || !t.action || !t.to_node) {
      ElMessage.warning('请完整填写所有转换规则')
      return false
    }
  }

  return true
}

async function saveWorkflow() {
  if (!validateForm()) return

  const definition: WorkflowDefinition = {
    nodes: formNodes.value,
    actions: formActions.value,
    transitions: formTransitions.value,
  }

  saving.value = true
  try {
    if (editId.value) {
      await wfApi.updateWorkflow(editId.value, {
        name: formName.value,
        definition,
      })
      ElMessage.success('更新成功')
    } else {
      await wfApi.createWorkflow({
        name: formName.value,
        code: formCode.value,
        definition,
      })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
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
        <h2 class="page-title">工作流管理</h2>
        <p class="page-desc">配置工作流模板并绑定到资源类型</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openCreateDialog">
        新建工作流
      </el-button>
    </div>

    <div v-loading="loading">
      <!-- Workflow Templates Table -->
      <div class="content-card">
        <h3 class="section-title">工作流模板</h3>
        <el-table :data="workflows" stripe row-key="id">
          <el-table-column type="expand">
            <template #default="{ row }">
              <div class="expand-graph">
                <WorkflowGraph :definition="row.definition" />
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="name" label="名称" min-width="140" />
          <el-table-column prop="code" label="编码" width="140" />
          <el-table-column label="节点数" width="100" align="center">
            <template #default="{ row }">
              {{ row.definition?.nodes?.length ?? 0 }}
            </template>
          </el-table-column>
          <el-table-column label="类型" width="100" align="center">
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

      <!-- Resource Bindings Table -->
      <div class="content-card" style="margin-top: 20px;">
        <h3 class="section-title">资源绑定</h3>
        <p class="section-desc">为每种资源类型指定使用哪个工作流</p>
        <el-table :data="bindings" stripe>
          <el-table-column label="资源类型" width="160">
            <template #default="{ row }">
              {{ resourceTypeLabels[row.resource_type] || row.resource_type }}
            </template>
          </el-table-column>
          <el-table-column label="绑定工作流" min-width="240">
            <template #default="{ row }">
              <el-select
                :model-value="row.workflow_id"
                style="width: 220px"
                placeholder="选择工作流"
                @change="(val: string) => handleBindingChange(row.resource_type, val)"
              >
                <el-option
                  v-for="wf in workflows"
                  :key="wf.id"
                  :label="wf.name"
                  :value="wf.id"
                />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="启用" width="100" align="center">
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

    <!-- Workflow Editor Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="900px"
      destroy-on-close
      class="workflow-dialog"
    >
      <div class="dialog-body">
        <!-- a) 基本信息 -->
        <div class="editor-section">
          <h4 class="editor-section-title">基本信息</h4>
          <el-form label-width="80px">
            <el-form-item label="名称" required>
              <el-input v-model="formName" placeholder="例如：三级审核流程" />
            </el-form-item>
            <el-form-item label="编码" required>
              <el-input
                v-model="formCode"
                :disabled="!!editId"
                :placeholder="editId ? '' : '例如：three_step（创建后不可修改）'"
              />
            </el-form-item>
          </el-form>
        </div>

        <!-- b) 流程预览 -->
        <div class="editor-section">
          <h4 class="editor-section-title">流程预览</h4>
          <div class="graph-preview">
            <WorkflowGraph :definition="currentDefinition" />
          </div>
        </div>

        <!-- c) 节点配置 -->
        <div class="editor-section">
          <h4 class="editor-section-title">节点配置</h4>
          <el-table :data="formNodes" border size="small">
            <el-table-column label="ID" width="140">
              <template #default="{ row }">
                <el-input v-model="row.id" size="small" placeholder="节点ID" />
              </template>
            </el-table-column>
            <el-table-column label="名称" width="140">
              <template #default="{ row }">
                <el-input v-model="row.name" size="small" placeholder="节点名称" />
              </template>
            </el-table-column>
            <el-table-column label="类型" width="120">
              <template #default="{ row }">
                <el-select v-model="row.type" size="small">
                  <el-option
                    v-for="opt in nodeTypeOptions"
                    :key="opt.value"
                    :label="opt.label"
                    :value="opt.value"
                  />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="可查看角色" min-width="180">
              <template #default="{ row }">
                <el-select
                  v-model="row.view_roles"
                  multiple
                  size="small"
                  placeholder="选择角色"
                  style="width: 100%"
                >
                  <el-option
                    v-for="opt in roleOptions"
                    :key="opt.value"
                    :label="opt.label"
                    :value="opt.value"
                  />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="可操作角色" min-width="180">
              <template #default="{ row }">
                <el-select
                  v-model="row.edit_roles"
                  multiple
                  size="small"
                  placeholder="选择角色"
                  style="width: 100%"
                >
                  <el-option
                    v-for="opt in roleOptions"
                    :key="opt.value"
                    :label="opt.label"
                    :value="opt.value"
                  />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="60" align="center">
              <template #default="{ $index }">
                <el-button
                  type="danger"
                  text
                  size="small"
                  :icon="Delete"
                  @click="removeNode($index)"
                />
              </template>
            </el-table-column>
          </el-table>
          <el-button type="primary" text size="small" :icon="Plus" @click="addNode" style="margin-top: 8px;">
            添加节点
          </el-button>
        </div>

        <!-- d) 动作配置 -->
        <div class="editor-section">
          <h4 class="editor-section-title">动作配置</h4>
          <el-table :data="formActions" border size="small">
            <el-table-column label="ID" min-width="180">
              <template #default="{ row }">
                <el-input v-model="row.id" size="small" placeholder="动作ID" />
              </template>
            </el-table-column>
            <el-table-column label="名称" min-width="180">
              <template #default="{ row }">
                <el-input v-model="row.name" size="small" placeholder="动作名称" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="60" align="center">
              <template #default="{ $index }">
                <el-button
                  type="danger"
                  text
                  size="small"
                  :icon="Delete"
                  @click="removeAction($index)"
                />
              </template>
            </el-table-column>
          </el-table>
          <el-button type="primary" text size="small" :icon="Plus" @click="addAction" style="margin-top: 8px;">
            添加动作
          </el-button>
        </div>

        <!-- e) 转换规则 -->
        <div class="editor-section">
          <h4 class="editor-section-title">转换规则</h4>
          <el-table :data="formTransitions" border size="small">
            <el-table-column label="当前节点" min-width="180">
              <template #default="{ row }">
                <el-select v-model="row.from_node" size="small" placeholder="选择节点" style="width: 100%">
                  <el-option
                    v-for="opt in nodeOptions"
                    :key="opt.value"
                    :label="opt.label"
                    :value="opt.value"
                  />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="动作" min-width="180">
              <template #default="{ row }">
                <el-select v-model="row.action" size="small" placeholder="选择动作" style="width: 100%">
                  <el-option
                    v-for="opt in actionOptions"
                    :key="opt.value"
                    :label="opt.label"
                    :value="opt.value"
                  />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="下一节点" min-width="180">
              <template #default="{ row }">
                <el-select v-model="row.to_node" size="small" placeholder="选择节点" style="width: 100%">
                  <el-option
                    v-for="opt in nodeOptions"
                    :key="opt.value"
                    :label="opt.label"
                    :value="opt.value"
                  />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="60" align="center">
              <template #default="{ $index }">
                <el-button
                  type="danger"
                  text
                  size="small"
                  :icon="Delete"
                  @click="removeTransition($index)"
                />
              </template>
            </el-table-column>
          </el-table>
          <el-button type="primary" text size="small" :icon="Plus" @click="addTransition" style="margin-top: 8px;">
            添加转换规则
          </el-button>
        </div>
      </div>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveWorkflow">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.workflows-page {
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

.expand-graph {
  padding: 16px 24px;
  background: var(--bg-secondary, #F4F6FA);
}

.dialog-body {
  max-height: 65vh;
  overflow-y: auto;
  padding-right: 8px;
}

.editor-section {
  margin-bottom: 24px;

  &:last-child {
    margin-bottom: 0;
  }
}

.editor-section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary, #1A1A2E);
  margin: 0 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-color, #E2E6ED);
}

.graph-preview {
  padding: 16px;
  background: var(--bg-secondary, #F4F6FA);
  border-radius: 8px;
  min-height: 80px;
}
</style>
