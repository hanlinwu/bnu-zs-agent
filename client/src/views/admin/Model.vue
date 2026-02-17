<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, Connection } from '@element-plus/icons-vue'
import * as modelApi from '@/api/admin/model'
import type { ModelEndpoint, ModelGroup, ModelInstance } from '@/types/admin'
import type { FormInstance, FormRules } from 'element-plus'

const loading = ref(false)
const endpoints = ref<ModelEndpoint[]>([])
const groups = ref<ModelGroup[]>([])

// Endpoint dialog
const epDialogVisible = ref(false)
const epFormRef = ref<FormInstance>()
const epSubmitting = ref(false)
const isEditEp = ref(false)
const epForm = reactive({
  id: '',
  name: '',
  provider: 'openai_compatible',
  baseUrl: '',
  apiKey: '',
})
const epRules: FormRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  baseUrl: [{ required: true, message: '请输入接口地址', trigger: 'blur' }],
}

// Instance dialog
const instDialogVisible = ref(false)
const instFormRef = ref<FormInstance>()
const instSubmitting = ref(false)
const isEditInst = ref(false)
const instGroupId = ref('')
const instForm = reactive({
  id: '',
  endpointId: '',
  modelName: '',
  enabled: true,
  weight: 1,
  maxTokens: 4096,
  temperature: 0.7,
  priority: 0,
})
const instRules: FormRules = {
  endpointId: [{ required: true, message: '请选择接入点', trigger: 'change' }],
  modelName: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
}

// Group dialog
const grpDialogVisible = ref(false)
const grpFormRef = ref<FormInstance>()
const grpSubmitting = ref(false)
const grpForm = reactive({
  name: '',
  type: 'llm' as string,
  strategy: 'failover',
})
const grpRules: FormRules = {
  name: [{ required: true, message: '请输入组名', trigger: 'blur' }],
}

const providerOptions = [
  { label: '通义千问', value: 'qwen' },
  { label: '智谱 GLM', value: 'glm' },
  { label: '本地部署', value: 'local' },
  { label: 'OpenAI 兼容', value: 'openai_compatible' },
]

const groupTypeOptions = [
  { label: 'LLM 对话', value: 'llm' },
  { label: 'Embedding 向量', value: 'embedding' },
  { label: '审核模型', value: 'review' },
]

const strategyOptions = [
  { label: '故障转移', value: 'failover' },
  { label: '轮询', value: 'round_robin' },
  { label: '加权随机', value: 'weighted' },
]

function providerLabel(provider: string) {
  return providerOptions.find(o => o.value === provider)?.label || provider
}

function groupTypeLabel(type: string) {
  return groupTypeOptions.find(o => o.value === type)?.label || type
}

function groupTypeTag(type: string) {
  const map: Record<string, string> = { llm: 'primary', embedding: 'success', review: 'warning' }
  return map[type] || 'info'
}

async function fetchConfig() {
  loading.value = true
  try {
    const res = await modelApi.getModelConfig()
    const data = res.data as any
    endpoints.value = data.endpoints || []
    groups.value = data.groups || []
  } catch {
    ElMessage.error('加载模型配置失败')
  } finally {
    loading.value = false
  }
}

// ── Endpoint CRUD ──

function openCreateEp() {
  isEditEp.value = false
  epForm.id = ''
  epForm.name = ''
  epForm.provider = 'openai_compatible'
  epForm.baseUrl = ''
  epForm.apiKey = ''
  epDialogVisible.value = true
}

function openEditEp(ep: ModelEndpoint) {
  isEditEp.value = true
  epForm.id = ep.id
  epForm.name = ep.name
  epForm.provider = ep.provider
  epForm.baseUrl = ep.baseUrl
  epForm.apiKey = ''
  epDialogVisible.value = true
}

async function handleSaveEp() {
  const valid = await epFormRef.value?.validate().catch(() => false)
  if (!valid) return
  epSubmitting.value = true
  try {
    if (isEditEp.value) {
      const update: Record<string, string> = { name: epForm.name, provider: epForm.provider, baseUrl: epForm.baseUrl }
      if (epForm.apiKey) update.apiKey = epForm.apiKey
      await modelApi.updateEndpoint(epForm.id, update)
      ElMessage.success('接入点已更新')
    } else {
      await modelApi.createEndpoint({
        name: epForm.name, provider: epForm.provider,
        baseUrl: epForm.baseUrl, apiKey: epForm.apiKey,
      })
      ElMessage.success('接入点已创建')
    }
    epDialogVisible.value = false
    fetchConfig()
  } catch {
    ElMessage.error('操作失败')
  } finally {
    epSubmitting.value = false
  }
}

async function handleDeleteEp(ep: ModelEndpoint) {
  try {
    await ElMessageBox.confirm(
      `确定要删除接入点「${ep.name}」吗？`,
      '删除确认',
      { type: 'error', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await modelApi.deleteEndpoint(ep.id)
    ElMessage.success('删除成功')
    fetchConfig()
  } catch { /* cancelled */ }
}

// ── Group CRUD ──

function openCreateGroup() {
  grpForm.name = ''
  grpForm.type = 'llm'
  grpForm.strategy = 'failover'
  grpDialogVisible.value = true
}

async function handleSaveGroup() {
  const valid = await grpFormRef.value?.validate().catch(() => false)
  if (!valid) return
  grpSubmitting.value = true
  try {
    await modelApi.createGroup({
      name: grpForm.name, type: grpForm.type, strategy: grpForm.strategy,
    })
    ElMessage.success('模型组已创建')
    grpDialogVisible.value = false
    fetchConfig()
  } catch {
    ElMessage.error('操作失败')
  } finally {
    grpSubmitting.value = false
  }
}

async function handleDeleteGroup(grp: ModelGroup) {
  try {
    await ElMessageBox.confirm(
      `确定要删除模型组「${grp.name}」及其所有实例吗？`,
      '删除确认',
      { type: 'error', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await modelApi.deleteGroup(grp.id)
    ElMessage.success('删除成功')
    fetchConfig()
  } catch { /* cancelled */ }
}

async function handleToggleGroup(grp: ModelGroup) {
  try {
    await modelApi.updateGroup(grp.id, { enabled: !grp.enabled })
    grp.enabled = !grp.enabled
    ElMessage.success(grp.enabled ? '已启用' : '已停用')
  } catch {
    ElMessage.error('操作失败')
  }
}

async function handleStrategyChange(grp: ModelGroup, strategy: string) {
  try {
    await modelApi.updateGroup(grp.id, { strategy })
    grp.strategy = strategy as any
  } catch {
    ElMessage.error('操作失败')
    fetchConfig()
  }
}

// ── Instance CRUD ──

function openCreateInstance(groupId: string) {
  isEditInst.value = false
  instGroupId.value = groupId
  instForm.id = ''
  instForm.endpointId = ''
  instForm.modelName = ''
  instForm.enabled = true
  instForm.weight = 1
  instForm.maxTokens = 4096
  instForm.temperature = 0.7
  instForm.priority = 0
  instDialogVisible.value = true
}

function openEditInstance(inst: ModelInstance) {
  isEditInst.value = true
  instGroupId.value = inst.groupId
  instForm.id = inst.id
  instForm.endpointId = inst.endpointId
  instForm.modelName = inst.modelName
  instForm.enabled = inst.enabled
  instForm.weight = inst.weight
  instForm.maxTokens = inst.maxTokens
  instForm.temperature = inst.temperature
  instForm.priority = inst.priority
  instDialogVisible.value = true
}

async function handleSaveInstance() {
  const valid = await instFormRef.value?.validate().catch(() => false)
  if (!valid) return
  instSubmitting.value = true
  try {
    if (isEditInst.value) {
      await modelApi.updateInstance(instForm.id, {
        endpointId: instForm.endpointId,
        modelName: instForm.modelName,
        enabled: instForm.enabled,
        weight: instForm.weight,
        maxTokens: instForm.maxTokens,
        temperature: instForm.temperature,
        priority: instForm.priority,
      })
      ElMessage.success('模型实例已更新')
    } else {
      await modelApi.createInstance(instGroupId.value, {
        endpointId: instForm.endpointId,
        modelName: instForm.modelName,
        enabled: instForm.enabled,
        weight: instForm.weight,
        maxTokens: instForm.maxTokens,
        temperature: instForm.temperature,
        priority: instForm.priority,
      })
      ElMessage.success('模型实例已添加')
    }
    instDialogVisible.value = false
    fetchConfig()
  } catch {
    ElMessage.error('操作失败')
  } finally {
    instSubmitting.value = false
  }
}

async function handleDeleteInstance(inst: ModelInstance) {
  try {
    await ElMessageBox.confirm(
      `确定要删除模型「${inst.modelName}」吗？`,
      '删除确认',
      { type: 'error', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await modelApi.deleteInstance(inst.id)
    ElMessage.success('删除成功')
    fetchConfig()
  } catch { /* cancelled */ }
}

async function handleToggleInstance(inst: ModelInstance) {
  try {
    await modelApi.updateInstance(inst.id, { enabled: !inst.enabled })
    inst.enabled = !inst.enabled
    ElMessage.success(inst.enabled ? '已启用' : '已停用')
  } catch {
    ElMessage.error('操作失败')
  }
}

onMounted(() => {
  fetchConfig()
})
</script>

<template>
  <div v-loading="loading" class="model-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">模型配置</h2>
        <p class="page-desc">管理模型接入点、模型组与实例</p>
      </div>
    </div>

    <!-- Section 1: Endpoints -->
    <div class="section-card">
      <div class="section-header">
        <h3 class="card-title">
          <el-icon><Connection /></el-icon>
          接入点管理
        </h3>
        <el-button type="primary" :icon="Plus" size="small" @click="openCreateEp">
          新建接入点
        </el-button>
      </div>
      <el-table :data="endpoints" stripe>
        <el-table-column prop="name" label="名称" width="150" />
        <el-table-column label="类型" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ providerLabel(row.provider) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="baseUrl" label="接口地址" min-width="260" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="mono-text">{{ row.baseUrl }}</span>
          </template>
        </el-table-column>
        <el-table-column label="API Key" width="140">
          <template #default="{ row }">
            <span class="mono-text muted">{{ row.apiKey }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="openEditEp(row)">编辑</el-button>
            <el-button type="danger" link size="small" @click="handleDeleteEp(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Section 2: Groups + Instances -->
    <div class="section-card">
      <div class="section-header">
        <h3 class="card-title">
          <el-icon><Connection /></el-icon>
          模型组
        </h3>
        <el-button type="primary" :icon="Plus" size="small" @click="openCreateGroup">
          新建模型组
        </el-button>
      </div>

      <div v-if="groups.length === 0" class="empty-state">
        暂无模型组，请创建
      </div>

      <div v-for="grp in groups" :key="grp.id" class="group-card" :class="{ 'group-card--disabled': !grp.enabled }">
        <div class="group-header">
          <div class="group-title-row">
            <el-tag :type="(groupTypeTag(grp.type) as any)" size="small" effect="dark">
              {{ groupTypeLabel(grp.type) }}
            </el-tag>
            <h4 class="group-name">{{ grp.name }}</h4>
          </div>
          <div class="group-controls">
            <el-select
              :model-value="grp.strategy"
              size="small"
              style="width: 120px"
              @change="(val: any) => handleStrategyChange(grp, val)"
            >
              <el-option
                v-for="opt in strategyOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
            <el-switch
              :model-value="grp.enabled"
              size="small"
              active-text="启用"
              @change="handleToggleGroup(grp)"
            />
            <el-button type="danger" link size="small" :icon="Delete" @click="handleDeleteGroup(grp)" />
          </div>
        </div>

        <el-table :data="grp.instances" size="small" class="instance-table">
          <el-table-column label="模型名称" min-width="180">
            <template #default="{ row }">
              <span class="mono-text">{{ row.modelName }}</span>
            </template>
          </el-table-column>
          <el-table-column label="接入点" width="150">
            <template #default="{ row }">
              {{ row.endpoint?.name || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="权重" width="70" align="center">
            <template #default="{ row }">{{ row.weight }}</template>
          </el-table-column>
          <el-table-column label="Max Tokens" width="100" align="center">
            <template #default="{ row }">{{ row.maxTokens }}</template>
          </el-table-column>
          <el-table-column label="Temp" width="70" align="center">
            <template #default="{ row }">{{ row.temperature }}</template>
          </el-table-column>
          <el-table-column label="状态" width="70" align="center">
            <template #default="{ row }">
              <el-switch :model-value="row.enabled" size="small" @click.stop="handleToggleInstance(row)" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link size="small" @click="openEditInstance(row)">编辑</el-button>
              <el-button type="danger" link size="small" @click="handleDeleteInstance(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="group-footer">
          <el-button size="small" :icon="Plus" @click="openCreateInstance(grp.id)">
            添加模型实例
          </el-button>
        </div>
      </div>
    </div>

    <!-- Endpoint Dialog -->
    <el-dialog
      v-model="epDialogVisible"
      :title="isEditEp ? '编辑接入点' : '新建接入点'"
      width="520px"
      destroy-on-close
    >
      <el-form ref="epFormRef" :model="epForm" :rules="epRules" label-width="100px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="epForm.name" placeholder="如：通义千问" />
        </el-form-item>
        <el-form-item label="类型" prop="provider">
          <el-select v-model="epForm.provider" style="width: 100%">
            <el-option v-for="opt in providerOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="接口地址" prop="baseUrl">
          <el-input v-model="epForm.baseUrl" placeholder="如 https://dashscope.aliyuncs.com/compatible-mode/v1" />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="epForm.apiKey" type="password" show-password :placeholder="isEditEp ? '留空则不修改' : 'sk-...'" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="epDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="epSubmitting" @click="handleSaveEp">保存</el-button>
      </template>
    </el-dialog>

    <!-- Group Dialog -->
    <el-dialog
      v-model="grpDialogVisible"
      title="新建模型组"
      width="440px"
      destroy-on-close
    >
      <el-form ref="grpFormRef" :model="grpForm" :rules="grpRules" label-width="80px">
        <el-form-item label="组名" prop="name">
          <el-input v-model="grpForm.name" placeholder="如：主力LLM" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="grpForm.type" style="width: 100%">
            <el-option v-for="opt in groupTypeOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="策略">
          <el-select v-model="grpForm.strategy" style="width: 100%">
            <el-option v-for="opt in strategyOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="grpDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="grpSubmitting" @click="handleSaveGroup">保存</el-button>
      </template>
    </el-dialog>

    <!-- Instance Dialog -->
    <el-dialog
      v-model="instDialogVisible"
      :title="isEditInst ? '编辑模型实例' : '添加模型实例'"
      width="520px"
      destroy-on-close
    >
      <el-form ref="instFormRef" :model="instForm" :rules="instRules" label-width="100px">
        <el-form-item label="接入点" prop="endpointId">
          <el-select v-model="instForm.endpointId" style="width: 100%" placeholder="选择接入点">
            <el-option
              v-for="ep in endpoints"
              :key="ep.id"
              :label="`${ep.name} (${providerLabel(ep.provider)})`"
              :value="ep.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="模型名称" prop="modelName">
          <el-input v-model="instForm.modelName" placeholder="如 qwen-plus / glm-4-plus" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="权重">
              <el-input-number v-model="instForm.weight" :min="1" :max="100" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="Max Tokens">
              <el-input-number v-model="instForm.maxTokens" :min="256" :step="1024" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="Temperature">
              <el-input-number v-model="instForm.temperature" :min="0" :max="2" :step="0.1" :precision="1" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="优先级">
          <el-input-number v-model="instForm.priority" :min="0" style="width: 160px" />
          <span class="form-hint">数字越小优先级越高</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="instDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="instSubmitting" @click="handleSaveInstance">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.model-page {
}

.page-header {
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

.section-card {
  background: var(--bg-primary, #ffffff);
  border-radius: 12px;
  border: 1px solid var(--border-color, #E2E6ED);
  padding: 20px;
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary, #1A1A2E);
  margin: 0;
  display: flex;
  align-items: center;
  gap: 6px;

  .el-icon {
    color: var(--bnu-blue, #003DA5);
  }
}

.mono-text {
  font-family: monospace;
  font-size: 13px;
}

.muted {
  color: var(--text-secondary, #9E9EB3);
}

:deep(.el-table__header th) {
  background: var(--bg-secondary, #F4F6FA) !important;
  font-weight: 600;
}

.empty-state {
  text-align: center;
  padding: 40px 24px;
  color: var(--text-secondary, #9E9EB3);
  font-size: 14px;
}

.group-card {
  border: 1px solid var(--border-color, #E2E6ED);
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 16px;
  transition: opacity 0.2s;

  &:last-child {
    margin-bottom: 0;
  }

  &--disabled {
    opacity: 0.55;
  }
}

.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}

.group-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.group-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary, #1A1A2E);
  margin: 0;
}

.group-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.instance-table {
  margin-bottom: 8px;
}

.group-footer {
  padding-top: 8px;
}

.form-hint {
  font-size: 12px;
  color: var(--text-secondary, #9E9EB3);
  margin-left: 8px;
}
</style>
