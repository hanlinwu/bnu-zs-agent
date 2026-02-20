<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Upload, Edit, Delete } from '@element-plus/icons-vue'
import type { UploadProps } from 'element-plus'
import * as knowledgeApi from '@/api/admin/knowledge'
import * as knowledgeBaseApi from '@/api/admin/knowledgeBase'
import { getWorkflowForResource } from '@/api/admin/workflow'
import type { WorkflowNode, WorkflowAction, WorkflowTransition } from '@/api/admin/workflow'
import type { KnowledgeDocument, KnowledgeBase } from '@/types/knowledge'
import type { TabPaneName } from 'element-plus'

const router = useRouter()

// === KB Sidebar State ===
const knowledgeBases = ref<KnowledgeBase[]>([])
const selectedKbId = ref<string>('')
const kbLoading = ref(false)
const kbDialogVisible = ref(false)
const kbEditing = ref<KnowledgeBase | null>(null)
const kbForm = ref({
  name: '',
  description: '',
  sort_order: 0,
  enabled: true,
})
const kbFormSaving = ref(false)

// === Document Panel State ===
const loading = ref(false)
const documents = ref<KnowledgeDocument[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const activeTab = ref<string>('all')
const uploadDialogVisible = ref(false)
const uploading = ref(false)
const selectedDocs = ref<KnowledgeDocument[]>([])
const batchLoading = ref(false)
const tableRef = ref()

// Workflow data
const workflowNodes = ref<WorkflowNode[]>([])
const workflowActions = ref<WorkflowAction[]>([])
const workflowTransitions = ref<WorkflowTransition[]>([])

// === Computed ===
const selectedKb = computed(() =>
  knowledgeBases.value.find(kb => kb.id === selectedKbId.value) || null
)

const uploadHeaders = computed(() => {
  const token = localStorage.getItem('admin_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
})

const uploadData = computed(() => ({
  kb_id: selectedKbId.value,
}))

const statusFilter = computed<string | undefined>(() =>
  activeTab.value === 'all' ? undefined : activeTab.value
)

const batchEnabled = computed(() => activeTab.value !== 'all')

const batchActions = computed(() => {
  if (!batchEnabled.value) return []
  const nodeId = activeTab.value
  const actionIds = new Set(
    workflowTransitions.value.filter(t => t.from_node === nodeId).map(t => t.action)
  )
  return workflowActions.value.filter(a => actionIds.has(a.id))
})

// === Workflow Helpers ===
function nodeIsTerminal(nodeId: string) {
  const node = workflowNodes.value.find(n => n.id === nodeId)
  return node?.type === 'terminal'
}

function statusTagType(status: string) {
  const map: Record<string, string> = {
    pending: 'warning',
    reviewing: 'warning',
    approved: 'success',
    active: 'success',
    rejected: 'danger',
    processing: 'info',
    archived: 'info',
  }
  return map[status] || 'info'
}

function statusLabel(status: string) {
  const node = workflowNodes.value.find(n => n.id === status)
  if (node) return node.name

  const map: Record<string, string> = {
    pending: '待审核',
    reviewing: '审核中',
    approved: '已通过',
    active: '已生效',
    rejected: '已拒绝',
    processing: '正在切片...',
    archived: '已归档',
  }
  return map[status] || status
}

function fileTypeLabel(type: string) {
  const map: Record<string, string> = {
    pdf: 'PDF',
    docx: 'Word',
    txt: 'TXT',
    md: 'Markdown',
  }
  return map[type] || type.toUpperCase()
}

// === KB CRUD ===
async function fetchKnowledgeBases() {
  kbLoading.value = true
  try {
    const res = await knowledgeBaseApi.getKnowledgeBases()
    knowledgeBases.value = res.data.items
  } catch {
    ElMessage.error('加载知识库列表失败')
  } finally {
    kbLoading.value = false
  }
}

function selectKb(kbId: string) {
  if (selectedKbId.value === kbId) return
  selectedKbId.value = kbId
  currentPage.value = 1
  selectedDocs.value = []
  tableRef.value?.clearSelection()
  fetchDocuments()
}

function openKbCreateDialog() {
  kbEditing.value = null
  kbForm.value = { name: '', description: '', sort_order: 0, enabled: true }
  kbDialogVisible.value = true
}

function openKbEditDialog(kb: KnowledgeBase) {
  kbEditing.value = kb
  kbForm.value = {
    name: kb.name,
    description: kb.description || '',
    sort_order: kb.sort_order,
    enabled: kb.enabled,
  }
  kbDialogVisible.value = true
}

async function handleKbSubmit() {
  if (!kbForm.value.name.trim()) {
    ElMessage.warning('知识库名称不能为空')
    return
  }
  kbFormSaving.value = true
  try {
    if (kbEditing.value) {
      await knowledgeBaseApi.updateKnowledgeBase(kbEditing.value.id, kbForm.value)
      ElMessage.success('知识库更新成功')
    } else {
      const res = await knowledgeBaseApi.createKnowledgeBase(kbForm.value)
      ElMessage.success('知识库创建成功')
      // Auto-select the new KB
      await fetchKnowledgeBases()
      selectedKbId.value = res.data.id
      fetchDocuments()
      kbDialogVisible.value = false
      kbFormSaving.value = false
      return
    }
    await fetchKnowledgeBases()
    kbDialogVisible.value = false
  } catch {
    ElMessage.error(kbEditing.value ? '更新失败' : '创建失败')
  } finally {
    kbFormSaving.value = false
  }
}

async function handleKbDelete(kb: KnowledgeBase) {
  try {
    await ElMessageBox.confirm(
      `确定要删除知识库「${kb.name}」吗？仅可删除无文档的知识库。`,
      '删除确认',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    await knowledgeBaseApi.deleteKnowledgeBase(kb.id)
    ElMessage.success('删除成功')
    await fetchKnowledgeBases()
    // Select next available
    if (selectedKbId.value === kb.id) {
      selectedKbId.value = knowledgeBases.value[0]?.id || ''
      if (selectedKbId.value) fetchDocuments()
    }
  } catch {
    // cancelled or error
  }
}

async function handleKbToggleEnabled(enabled: string | number | boolean) {
  if (!selectedKb.value) return
  try {
    const finalEnabled = Boolean(enabled)
    await knowledgeBaseApi.updateKnowledgeBase(selectedKb.value.id, { enabled: finalEnabled })
    ElMessage.success(finalEnabled ? '已启用' : '已禁用')
    await fetchKnowledgeBases()
  } catch {
    ElMessage.error('操作失败')
  }
}

// === Workflow & Documents ===
async function fetchWorkflow() {
  try {
    const res = await getWorkflowForResource('knowledge')
    workflowNodes.value = res.data.nodes || []
    workflowActions.value = res.data.actions || []
    workflowTransitions.value = res.data.transitions || []
  } catch {
    // fallback: use static tabs
  }
}

async function fetchDocuments() {
  if (!selectedKbId.value) {
    documents.value = []
    total.value = 0
    return
  }
  loading.value = true
  try {
    const res = await knowledgeApi.getDocuments({
      page: currentPage.value,
      pageSize: pageSize.value,
      status: statusFilter.value,
      kb_id: selectedKbId.value,
    })
    documents.value = res.data.items
    total.value = res.data.total
  } catch {
    ElMessage.error('加载文档列表失败')
  } finally {
    loading.value = false
  }
}

function handleTabChange(nodeId: TabPaneName) {
  activeTab.value = String(nodeId)
  currentPage.value = 1
  tableRef.value?.clearSelection()
  selectedDocs.value = []
  fetchDocuments()
}

function handleSelectionChange(selection: KnowledgeDocument[]) {
  selectedDocs.value = selection
}

function actionButtonType(actionId: string) {
  if (actionId.includes('approve')) return 'success'
  if (actionId.includes('reject')) return 'danger'
  return 'primary'
}

async function handleBatchAction(actionId: string) {
  if (selectedDocs.value.length === 0) return
  const actionName = workflowActions.value.find(a => a.id === actionId)?.name || actionId
  try {
    await ElMessageBox.confirm(
      `确定要对选中的 ${selectedDocs.value.length} 篇文档执行「${actionName}」操作吗？`,
      '批量操作确认',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    batchLoading.value = true
    const res = await knowledgeApi.batchReviewDocuments({
      ids: selectedDocs.value.map(d => d.id),
      action: actionId,
    })
    const data = res.data as any
    ElMessage.success(`批量操作完成，成功 ${data.success_count} 项`)
    if (data.errors?.length) {
      ElMessage.warning(`${data.errors.length} 项操作失败`)
    }
    selectedDocs.value = []
    fetchDocuments()
    fetchKnowledgeBases() // Refresh doc counts
  } catch {
    // cancelled
  } finally {
    batchLoading.value = false
  }
}

function handlePageChange(page: number) {
  currentPage.value = page
  fetchDocuments()
}

function goReview(doc: KnowledgeDocument) {
  router.push({ path: '/admin/knowledge/review', query: { id: doc.id } })
}

async function handleArchive(doc: KnowledgeDocument) {
  try {
    await ElMessageBox.confirm(`确定要归档文档「${doc.title}」吗？`, '归档确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await knowledgeApi.deleteDocument(doc.id)
    ElMessage.success('归档成功')
    fetchDocuments()
    fetchKnowledgeBases() // Refresh doc counts
  } catch {
    // cancelled or error
  }
}

const handleUploadSuccess: UploadProps['onSuccess'] = () => {
  uploading.value = false
  uploadDialogVisible.value = false
  ElMessage.success('上传成功，文档已进入审核队列')
  fetchDocuments()
  fetchKnowledgeBases() // Refresh doc counts
}

const handleUploadError: UploadProps['onError'] = () => {
  uploading.value = false
  ElMessage.error('上传失败，请重试')
}

const beforeUpload: UploadProps['beforeUpload'] = (file) => {
  const allowedTypes = [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain',
    'text/markdown',
  ]
  const isAllowed = allowedTypes.includes(file.type) ||
    file.name.endsWith('.md') ||
    file.name.endsWith('.txt')

  if (!isAllowed) {
    ElMessage.error('仅支持 PDF、Word、TXT、Markdown 格式')
    return false
  }
  if (file.size > 100 * 1024 * 1024) {
    ElMessage.error('文件大小不能超过 100MB')
    return false
  }
  uploading.value = true
  return true
}

function formatDate(date: string) {
  return new Date(date).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

// === Init ===
onMounted(async () => {
  await Promise.all([fetchWorkflow(), fetchKnowledgeBases()])
  // Auto-select first KB
  if (knowledgeBases.value.length > 0) {
    selectedKbId.value = knowledgeBases.value[0]?.id || ''
    fetchDocuments()
  }
})
</script>

<template>
  <div class="knowledge-page">
    <!-- Left Panel: KB Sidebar -->
    <div class="kb-sidebar">
      <div class="kb-sidebar-header">
        <h3 class="kb-sidebar-title">知识库管理</h3>
        <el-button type="primary" size="small" :icon="Plus" @click="openKbCreateDialog">
          新建
        </el-button>
      </div>

      <div v-loading="kbLoading" class="kb-list">
        <div
          v-for="kb in knowledgeBases"
          :key="kb.id"
          class="kb-item"
          :class="{ 'kb-item--active': kb.id === selectedKbId }"
          @click="selectKb(kb.id)"
        >
          <div class="kb-item-main">
            <div class="kb-item-name">{{ kb.name }}</div>
            <div class="kb-item-meta">
              <el-tag size="small" :type="kb.enabled ? 'success' : 'danger'" effect="light">
                {{ kb.enabled ? '已启用' : '已禁用' }}
              </el-tag>
              <span class="kb-item-count">{{ kb.doc_count }} 篇文档</span>
            </div>
          </div>
          <div class="kb-item-actions">
            <el-button
              :icon="Edit"
              size="small"
              link
              @click.stop="openKbEditDialog(kb)"
            />
            <el-button
              :icon="Delete"
              size="small"
              link
              type="danger"
              @click.stop="handleKbDelete(kb)"
            />
          </div>
        </div>

        <div v-if="!kbLoading && knowledgeBases.length === 0" class="kb-empty">
          <p>暂无知识库</p>
          <el-button type="primary" size="small" @click="openKbCreateDialog">创建知识库</el-button>
        </div>
      </div>
    </div>

    <!-- Right Panel: Document Management -->
    <div class="kb-content">
      <template v-if="selectedKb">
        <div class="kb-content-header">
          <div class="kb-content-header-left">
            <h2 class="kb-content-title">{{ selectedKb.name }}</h2>
            <span class="kb-content-count">{{ selectedKb.doc_count }} 篇文档</span>
            <el-switch
              :model-value="selectedKb.enabled"
              active-text="启用"
              inactive-text="禁用"
              inline-prompt
              @change="handleKbToggleEnabled"
            />
          </div>
          <el-button type="primary" :icon="Plus" @click="uploadDialogVisible = true">
            上传文档
          </el-button>
        </div>

        <div class="content-card">
          <el-tabs :model-value="activeTab" @update:model-value="handleTabChange">
            <el-tab-pane label="全部" name="all" />
            <el-tab-pane
              v-for="node in workflowNodes"
              :key="node.id"
              :label="node.name"
              :name="node.id"
            />
          </el-tabs>

          <!-- Batch action bar -->
          <div v-if="batchEnabled && selectedDocs.length > 0" class="batch-bar">
            <span class="batch-count">已选 {{ selectedDocs.length }} 项</span>
            <el-button
              v-for="action in batchActions"
              :key="action.id"
              :type="actionButtonType(action.id)"
              size="small"
              :loading="batchLoading"
              @click="handleBatchAction(action.id)"
            >
              批量{{ action.name }}
            </el-button>
          </div>

          <el-table
            ref="tableRef"
            v-loading="loading"
            :data="documents"
            stripe
            class="doc-table"
            height="100%"
            @selection-change="handleSelectionChange"
          >
            <el-table-column v-if="batchEnabled" type="selection" width="50" />
            <el-table-column prop="title" label="文档标题" min-width="200" show-overflow-tooltip />
            <el-table-column prop="fileType" label="文件类型" width="100" align="center">
              <template #default="{ row }">
                <el-tag size="small" type="info">{{ fileTypeLabel(row.fileType) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="当前节点" width="120" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="(statusTagType(row.currentNode || row.status) as any)">
                  {{ statusLabel(row.currentNode || row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="uploaderName" label="上传人" width="120" show-overflow-tooltip />
            <el-table-column prop="chunkCount" label="切片数" width="80" align="center" />
            <el-table-column prop="createdAt" label="上传时间" width="120">
              <template #default="{ row }">{{ formatDate(row.createdAt) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="240" fixed="right">
              <template #default="{ row }">
                <el-button
                  type="primary"
                  link
                  size="small"
                  @click="knowledgeApi.downloadDocument(row.id)"
                >
                  下载
                </el-button>
                <el-button
                  v-if="!nodeIsTerminal(row.currentNode || row.status)"
                  type="primary"
                  link
                  size="small"
                  @click="goReview(row)"
                >
                  审核
                </el-button>
                <el-button
                  type="primary"
                  link
                  size="small"
                  @click="goReview(row)"
                >
                  查看切片
                </el-button>
                <el-button
                  v-if="(row.currentNode || row.status) !== 'archived'"
                  type="warning"
                  link
                  size="small"
                  @click="handleArchive(row)"
                >
                  归档
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
      </template>

      <!-- Empty state when no KB selected -->
      <div v-else class="kb-empty-state">
        <div class="kb-empty-state-inner">
          <p class="kb-empty-state-text">
            {{ knowledgeBases.length === 0 ? '请先创建知识库' : '请选择一个知识库' }}
          </p>
          <el-button v-if="knowledgeBases.length === 0" type="primary" @click="openKbCreateDialog">
            创建知识库
          </el-button>
        </div>
      </div>
    </div>

    <!-- KB Create/Edit Dialog -->
    <el-dialog
      v-model="kbDialogVisible"
      :title="kbEditing ? '编辑知识库' : '新建知识库'"
      width="480px"
      destroy-on-close
    >
      <el-form :model="kbForm" label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="kbForm.name" placeholder="请输入知识库名称" maxlength="50" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="kbForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入知识库描述（可选）"
            maxlength="200"
          />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="kbForm.sort_order" :min="0" :max="9999" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="kbForm.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="kbDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="kbFormSaving" @click="handleKbSubmit">
          {{ kbEditing ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- Upload Dialog -->
    <el-dialog
      v-model="uploadDialogVisible"
      title="上传知识文档"
      width="520px"
      destroy-on-close
    >
      <el-upload
        drag
        action="/api/v1/admin/knowledge/upload"
        :headers="uploadHeaders"
        :data="uploadData"
        accept=".pdf,.docx,.txt,.md"
        :before-upload="beforeUpload"
        :on-success="handleUploadSuccess"
        :on-error="handleUploadError"
        :show-file-list="true"
        :limit="5"
      >
        <el-icon :size="48" class="upload-icon"><Upload /></el-icon>
        <div class="upload-text">将文件拖到此处，或<em>点击上传</em></div>
        <template #tip>
          <div class="upload-tip">
            支持 PDF、Word、TXT、Markdown 格式，单文件不超过 100MB
          </div>
        </template>
      </el-upload>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.knowledge-page {
  display: flex;
  gap: 20px;
  height: 100%;
}

// === Left Panel: KB Sidebar ===
.kb-sidebar {
  width: 280px;
  flex-shrink: 0;
  background: var(--bg-primary, #ffffff);
  border-radius: 12px;
  border: 1px solid var(--border-color, #E2E6ED);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.kb-sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid var(--border-color, #E2E6ED);
}

.kb-sidebar-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary, #1A1A2E);
  margin: 0;
}

.kb-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.kb-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  cursor: pointer;
  transition: background-color 0.2s;
  border-left: 3px solid transparent;

  &:hover {
    background: var(--bg-secondary, #F4F6FA);

    .kb-item-actions {
      opacity: 1;
    }
  }

  &--active {
    background: var(--bg-secondary, #F4F6FA);
    border-left-color: var(--bnu-blue, #003DA5);

    .kb-item-name {
      color: var(--bnu-blue, #003DA5);
      font-weight: 600;
    }
  }
}

.kb-item-main {
  flex: 1;
  min-width: 0;
}

.kb-item-name {
  font-size: 0.875rem;
  color: var(--text-primary, #1A1A2E);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}

.kb-item-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.kb-item-count {
  font-size: 0.75rem;
  color: var(--text-secondary, #5A5A72);
}

.kb-item-actions {
  display: flex;
  gap: 2px;
  opacity: 0;
  transition: opacity 0.2s;
  flex-shrink: 0;
}

.kb-empty {
  padding: 40px 16px;
  text-align: center;
  color: var(--text-secondary, #5A5A72);
  font-size: 0.875rem;

  p {
    margin: 0 0 12px;
  }
}

// === Right Panel: Content ===
.kb-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.kb-content-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.kb-content-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.kb-content-title {
  font-size: 1.375rem;
  font-weight: 700;
  color: var(--text-primary, #1A1A2E);
  margin: 0;
}

.kb-content-count {
  font-size: 0.875rem;
  color: var(--text-secondary, #5A5A72);
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

.doc-table {
  flex: 1;
  overflow: hidden;
  margin-top: 8px;

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

.upload-icon {
  color: var(--text-secondary, #9E9EB3);
  margin-bottom: 8px;
}

.upload-text {
  color: var(--text-secondary, #5A5A72);
  font-size: 0.875rem;

  em {
    color: var(--bnu-blue, #003DA5);
    font-style: normal;
  }
}

.upload-tip {
  color: var(--text-secondary, #9E9EB3);
  font-size: 0.75rem;
  margin-top: 8px;
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
  font-size: 0.8125rem;
  color: var(--text-primary, #1A1A2E);
  font-weight: 500;
}

// === Empty State ===
.kb-empty-state {
  background: var(--bg-primary, #ffffff);
  border-radius: 12px;
  border: 1px solid var(--border-color, #E2E6ED);
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}

.kb-empty-state-inner {
  text-align: center;
}

.kb-empty-state-text {
  font-size: 1rem;
  color: var(--text-secondary, #5A5A72);
  margin: 0 0 16px;
}
</style>
