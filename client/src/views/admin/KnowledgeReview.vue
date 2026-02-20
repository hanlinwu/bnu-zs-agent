<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Download, Loading } from '@element-plus/icons-vue'
import * as knowledgeApi from '@/api/admin/knowledge'
import * as wfApi from '@/api/admin/workflow'
import type { WorkflowNode, WorkflowAction, WorkflowTransition, ReviewHistoryRecord } from '@/api/admin/workflow'
import type { KnowledgeDocument, KnowledgeChunk, KnowledgeChunkDetail } from '@/types/knowledge'
import ReviewHistory from '@/components/admin/ReviewHistory.vue'

const route = useRoute()
const router = useRouter()
const documentId = ref<string>((route.query.id as string) || '')

const loading = ref(false)
const doc = ref<KnowledgeDocument | null>(null)
const chunks = ref<KnowledgeChunk[]>([])
const chunkTotal = ref(0)
const chunkPage = ref(1)
const chunkPageSize = ref(20)
const reviewNote = ref('')
const submitting = ref(false)
const reembedLoading = ref(false)
const reviewHistory = ref<ReviewHistoryRecord[]>([])
const chunkDetails = ref<Record<string, KnowledgeChunkDetail>>({})
const chunkDetailLoading = ref<Record<string, boolean>>({})
const chunkDetailVisible = ref(false)
const activeChunkId = ref('')
const activeChunkPreview = ref<KnowledgeChunk | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null

// Workflow data
const workflowNodes = ref<WorkflowNode[]>([])
const workflowActions = ref<WorkflowAction[]>([])
const workflowTransitions = ref<WorkflowTransition[]>([])

const isProcessing = computed(() => doc.value?.status === 'processing')

const currentNode = computed(() => doc.value?.currentNode || doc.value?.status || 'pending')

const availableActions = computed(() => {
  const node = currentNode.value
  // Find transitions from current node
  const actionIds = new Set(
    workflowTransitions.value
      .filter(t => t.from_node === node)
      .map(t => t.action)
  )
  return workflowActions.value.filter(a => actionIds.has(a.id))
})

function actionButtonType(actionId: string) {
  if (actionId.includes('approve')) return 'success'
  if (actionId.includes('reject')) return 'danger'
  return 'primary'
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

function formatDate(date: string) {
  return new Date(date).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatFileSize(bytes: number) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

async function fetchWorkflow() {
  try {
    const res = await wfApi.getWorkflowForResource('knowledge')
    workflowNodes.value = res.data.nodes || []
    workflowActions.value = res.data.actions || []
    workflowTransitions.value = res.data.transitions || []
  } catch {
    // fallback
  }
}

async function fetchDocument() {
  if (!documentId.value) return
  loading.value = true
  try {
    const res = await knowledgeApi.getDocument(documentId.value)
    doc.value = res.data
  } catch {
    ElMessage.error('加载文档失败')
  } finally {
    loading.value = false
  }
}

async function fetchChunks() {
  if (!documentId.value) return
  try {
    const res = await knowledgeApi.getChunks(documentId.value, {
      page: chunkPage.value,
      pageSize: chunkPageSize.value,
    })
    const data = res.data as any
    chunks.value = data.items || []
    chunkTotal.value = data.total || 0
  } catch {
    // Silently fail during polling
  }
}

function handleChunkPageChange(page: number) {
  chunkPage.value = page
  fetchChunks()
}

function embeddingTagType(status?: string) {
  return status === 'generated' ? 'success' : 'warning'
}

function embeddingStatusLabel(status?: string) {
  return status === 'generated' ? '已生成' : '未生成'
}

const activeChunkDetail = computed(() => {
  if (!activeChunkId.value) return null
  return chunkDetails.value[activeChunkId.value] || null
})

const vectorValues = computed(() => {
  const raw = activeChunkDetail.value?.embeddingVector
  if (!raw) return [] as number[]

  const cleaned = raw.trim().replace(/^\[/, '').replace(/\]$/, '')
  if (!cleaned) return [] as number[]

  return cleaned
    .split(',')
    .map(item => Number(item.trim()))
    .filter(value => Number.isFinite(value))
})

const vectorCells = computed(() => {
  const values = vectorValues.value
  if (values.length === 0) {
    return [] as Array<{ index: number; value: number; opacity: number }>
  }

  const maxAbs = Math.max(...values.map(value => Math.abs(value)), 1)
  return values.slice(0, 256).map((value, index) => ({
    index: index + 1,
    value,
    opacity: 0.12 + (Math.abs(value) / maxAbs) * 0.88,
  }))
})

const vectorSummary = computed(() => {
  const values = vectorValues.value
  if (values.length === 0) {
    return { dimension: 0, min: 0, max: 0, mean: 0 }
  }

  const min = Math.min(...values)
  const max = Math.max(...values)
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length
  return { dimension: values.length, min, max, mean }
})

async function openChunkDetail(chunk: KnowledgeChunk) {
  activeChunkId.value = chunk.id
  activeChunkPreview.value = chunk
  chunkDetailVisible.value = true

  if (chunkDetails.value[chunk.id] || chunkDetailLoading.value[chunk.id]) {
    return
  }

  chunkDetailLoading.value = {
    ...chunkDetailLoading.value,
    [chunk.id]: true,
  }

  try {
    const res = await knowledgeApi.getChunkDetail(chunk.id)
    chunkDetails.value = {
      ...chunkDetails.value,
      [chunk.id]: res.data,
    }
  } catch {
    ElMessage.error('加载切片详情失败')
  } finally {
    chunkDetailLoading.value = {
      ...chunkDetailLoading.value,
      [chunk.id]: false,
    }
  }
}

async function handleReembedMissing() {
  if (!documentId.value) return
  reembedLoading.value = true
  try {
    const res = await knowledgeApi.reembedMissingChunks({
      documentId: documentId.value,
      limit: 5000,
    })
    const data = res.data as any
    ElMessage.success(`已重跑，更新 ${data.updated || 0} 条`)
    await fetchChunks()
    await fetchDocument()
  } catch {
    ElMessage.error('重跑 embedding 失败')
  } finally {
    reembedLoading.value = false
  }
}

async function fetchReviewHistory() {
  if (!documentId.value) return
  try {
    const res = await wfApi.getReviewHistory('knowledge', documentId.value)
    reviewHistory.value = res.data.items
  } catch {
    // silently fail
  }
}

async function handleAction(actionId: string) {
  if (!doc.value) return
  submitting.value = true
  try {
    const res = await knowledgeApi.reviewDocument(doc.value.id, {
      action: actionId,
      note: reviewNote.value || undefined,
    })
    doc.value = res.data as any
    fetchReviewHistory()

    if (doc.value?.status === 'processing') {
      ElMessage.success('已通过审核，正在切片...')
      startPolling()
    } else if (actionId.includes('reject')) {
      ElMessage.success('已拒绝')
      router.push('/admin/knowledge')
    } else {
      ElMessage.success('操作成功')
    }
    reviewNote.value = ''
  } catch {
    ElMessage.error('审核操作失败')
  } finally {
    submitting.value = false
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    await fetchDocument()
    await fetchChunks()
    if (doc.value && doc.value.status !== 'processing') {
      stopPolling()
      if (doc.value.status === 'approved') {
        ElMessage.success(`切片完成，共 ${doc.value.chunkCount} 个切片`)
      }
    }
  }, 1500)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function goBack() {
  router.push('/admin/knowledge')
}

onMounted(async () => {
  await fetchWorkflow()
  await fetchDocument()
  fetchChunks()
  fetchReviewHistory()
  if (doc.value?.status === 'processing') {
    startPolling()
  }
})

onUnmounted(() => {
  stopPolling()
})
</script>

<template>
  <div class="review-page" v-loading="loading">
    <div class="page-header">
      <el-button text :icon="ArrowLeft" @click="goBack">返回列表</el-button>
      <h2 class="page-title">文档审核</h2>
    </div>

    <div v-if="doc" class="review-content">
      <div class="doc-info-panel">
        <div class="panel-header">
          <h3 class="panel-title">文档信息</h3>
          <el-button type="primary" :icon="Download" size="small" @click="knowledgeApi.downloadDocument(doc.id)">
            下载原文
          </el-button>
        </div>
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">文档标题</span>
            <span class="info-value">{{ doc.title }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">文件类型</span>
            <span class="info-value">{{ doc.fileType.toUpperCase() }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">文件大小</span>
            <span class="info-value">{{ formatFileSize(doc.fileSize) }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">上传人</span>
            <span class="info-value">{{ doc.uploaderName }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">上传时间</span>
            <span class="info-value">{{ formatDate(doc.createdAt) }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">当前节点</span>
            <el-tag size="small" :type="(statusTagType(currentNode) as any)">
              {{ statusLabel(currentNode) }}
            </el-tag>
          </div>
          <div class="info-item">
            <span class="info-label">切片数量</span>
            <span class="info-value">{{ doc.chunkCount }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">文件哈希</span>
            <span class="info-value info-value--mono">{{ doc.fileHash }}</span>
          </div>
        </div>
      </div>

      <div class="chunks-panel">
        <div class="chunks-panel-header">
          <h3 class="panel-title">文档切片预览 ({{ chunkTotal }} 条)</h3>
          <div class="chunks-actions">
            <el-button
              size="small"
              :loading="reembedLoading"
              @click="handleReembedMissing"
            >
              重跑缺失 Embedding
            </el-button>
            <el-tag v-if="isProcessing" type="primary" effect="dark" class="processing-tag">
              <el-icon class="is-loading"><Loading /></el-icon>
              正在切片中...已完成 {{ chunkTotal }} 条
            </el-tag>
          </div>
        </div>
        <div v-if="isProcessing && chunks.length === 0" class="chunks-processing">
          <el-icon class="is-loading processing-icon"><Loading /></el-icon>
          <p>正在解析文档并生成切片，请稍候...</p>
        </div>
        <div v-else-if="chunks.length === 0" class="chunks-empty">
          暂无切片数据
        </div>
        <div v-else class="chunks-list">
          <div
            v-for="chunk in chunks"
            :key="chunk.id"
            class="chunk-card"
            @click="openChunkDetail(chunk)"
          >
            <div class="chunk-header">
              <div class="chunk-head-left">
                <span class="chunk-index">#{{ chunk.chunkIndex + 1 }}</span>
                <span class="chunk-model">{{ chunk.embeddingModel || '-' }}</span>
              </div>
              <div class="chunk-meta">
                <span class="chunk-tokens">{{ chunk.tokenCount }} tokens</span>
                <el-tag size="small" :type="embeddingTagType(chunk.embeddingStatus) as any">
                  {{ embeddingStatusLabel(chunk.embeddingStatus) }}
                </el-tag>
              </div>
            </div>
            <div class="chunk-content chunk-content--collapsed">
              {{ chunk.content }}
            </div>
          </div>
        </div>
        <div class="pagination-wrapper" v-if="chunkTotal > chunkPageSize">
          <el-pagination
            v-model:current-page="chunkPage"
            :page-size="chunkPageSize"
            :total="chunkTotal"
            layout="prev, pager, next"
            small
            @current-change="handleChunkPageChange"
          />
        </div>
      </div>

      <el-dialog
        v-model="chunkDetailVisible"
        title="切片详情"
        width="900px"
        destroy-on-close
      >
        <div v-if="activeChunkPreview" class="chunk-modal">
          <div class="chunk-modal-head">
            <el-tag size="small" effect="plain">#{{ activeChunkPreview.chunkIndex + 1 }}</el-tag>
            <span class="chunk-modal-model">{{ activeChunkDetail?.embeddingModel || activeChunkPreview.embeddingModel || '-' }}</span>
            <span class="chunk-modal-tokens">{{ activeChunkDetail?.tokenCount ?? activeChunkPreview.tokenCount }} tokens</span>
            <el-tag size="small" :type="embeddingTagType(activeChunkDetail?.embeddingStatus || activeChunkPreview.embeddingStatus) as any">
              {{ embeddingStatusLabel(activeChunkDetail?.embeddingStatus || activeChunkPreview.embeddingStatus) }}
            </el-tag>
          </div>

          <div v-if="chunkDetailLoading[activeChunkPreview.id]" class="chunk-detail-loading">正在加载详情...</div>

          <template v-else>
            <div class="chunk-modal-label">切片内容</div>
            <div class="chunk-modal-content">{{ activeChunkDetail?.content || activeChunkPreview.content }}</div>

            <div class="chunk-modal-label">向量可视化</div>
            <div v-if="vectorCells.length === 0" class="vector-empty">无向量数据</div>
            <template v-else>
              <div class="vector-summary">
                <span>维度：{{ vectorSummary.dimension }}</span>
                <span>最小值：{{ vectorSummary.min.toFixed(4) }}</span>
                <span>最大值：{{ vectorSummary.max.toFixed(4) }}</span>
                <span>均值：{{ vectorSummary.mean.toFixed(4) }}</span>
              </div>
              <div class="vector-heatmap">
                <div
                  v-for="cell in vectorCells"
                  :key="cell.index"
                  class="vector-cell"
                  :title="`d${cell.index}: ${cell.value.toFixed(6)}`"
                  :style="{ backgroundColor: `rgba(0, 61, 165, ${cell.opacity.toFixed(3)})` }"
                />
              </div>
              <div class="vector-legend">
                <span>浅色</span>
                <div class="vector-legend-bar"></div>
                <span>深色</span>
              </div>
              <div class="vector-note">仅展示前 256 维</div>
            </template>
          </template>
        </div>
      </el-dialog>

      <div
        v-if="availableActions.length > 0"
        class="review-panel"
      >
        <h3 class="panel-title">审核操作</h3>
        <el-input
          v-model="reviewNote"
          type="textarea"
          :rows="3"
          placeholder="审核备注（可选）"
          class="review-textarea"
        />
        <div class="review-actions">
          <el-button
            v-for="action in availableActions"
            :key="action.id"
            :type="actionButtonType(action.id)"
            :loading="submitting"
            @click="handleAction(action.id)"
          >
            {{ action.name }}
          </el-button>
        </div>
      </div>

      <div v-if="reviewHistory.length > 0" class="review-note-panel">
        <h3 class="panel-title">审核记录</h3>
        <ReviewHistory :records="reviewHistory" />
      </div>

      <div v-else-if="doc.reviewNote" class="review-note-panel">
        <h3 class="panel-title">审核记录</h3>
        <div class="review-note-content">
          <p class="review-note-reviewer">
            审核人：{{ doc.reviewerName || '未知' }}
          </p>
          <p class="review-note-text">{{ doc.reviewNote }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.review-page {
}

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.page-title {
  font-size: 1.375rem;
  font-weight: 700;
  color: var(--text-primary, #1A1A2E);
  margin: 0;
}

.review-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.doc-info-panel,
.chunks-panel,
.review-panel,
.review-note-panel {
  background: var(--bg-primary, #ffffff);
  border-radius: 12px;
  border: 1px solid var(--border-color, #E2E6ED);
  padding: 24px;
}

.panel-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary, #1A1A2E);
  margin: 0 0 16px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;

  .panel-title {
    margin-bottom: 0;
  }
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px 24px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-size: 0.75rem;
  color: var(--text-secondary, #5A5A72);
}

.info-value {
  font-size: 0.875rem;
  color: var(--text-primary, #1A1A2E);
  font-weight: 500;

  &--mono {
    font-family: monospace;
    font-size: 0.75rem;
    word-break: break-all;
  }
}

.chunks-empty {
  text-align: center;
  padding: 32px;
  color: var(--text-secondary, #9E9EB3);
}

.chunks-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;

  .panel-title {
    margin-bottom: 0;
  }
}

.chunks-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.processing-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.chunks-processing {
  text-align: center;
  padding: 48px 32px;
  color: var(--text-secondary, #5A5A72);

  .processing-icon {
    font-size: 2rem;
    color: var(--bnu-blue, #003DA5);
    margin-bottom: 12px;
  }

  p {
    margin: 0;
    font-size: 0.875rem;
  }
}

.chunks-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  max-height: 520px;
  overflow-y: auto;
  padding-right: 4px;
}

.chunk-card {
  border: 1px solid var(--border-color, #E2E6ED);
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
}

.chunk-card:hover {
  border-color: var(--bnu-blue, #003DA5);
}

.chunk-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 12px;
  background: var(--bg-secondary, #F4F6FA);
}

.chunk-head-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chunk-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chunk-index {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--bnu-blue, #003DA5);
}

.chunk-model {
  font-size: 0.75rem;
  color: var(--text-secondary, #5A5A72);
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chunk-tokens {
  font-size: 0.75rem;
  color: var(--text-secondary, #5A5A72);
}

.chunk-content {
  padding: 8px 12px;
  font-size: 0.75rem;
  color: var(--text-primary, #1A1A2E);
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.chunk-content--collapsed {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.chunk-detail-loading {
  padding: 10px 12px;
  font-size: 0.75rem;
  color: var(--text-secondary, #5A5A72);
}

.chunk-modal {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chunk-modal-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.chunk-modal-model {
  font-size: 0.8125rem;
  color: var(--text-secondary, #5A5A72);
}

.chunk-modal-tokens {
  font-size: 0.75rem;
  color: var(--text-secondary, #5A5A72);
}

.chunk-modal-label {
  font-size: 0.75rem;
  color: var(--text-secondary, #5A5A72);
}

.chunk-modal-content {
  border: 1px solid var(--border-color, #E2E6ED);
  border-radius: 8px;
  padding: 10px 12px;
  max-height: 220px;
  overflow-y: auto;
  font-size: 0.8125rem;
  line-height: 1.6;
  color: var(--text-primary, #1A1A2E);
  white-space: pre-wrap;
  word-break: break-word;
}

.vector-empty {
  padding: 12px;
  border: 1px dashed var(--border-color, #E2E6ED);
  border-radius: 8px;
  color: var(--text-secondary, #5A5A72);
  font-size: 0.75rem;
}

.vector-summary {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  font-size: 0.75rem;
  color: var(--text-secondary, #5A5A72);
}

.vector-heatmap {
  border: 1px solid var(--border-color, #E2E6ED);
  border-radius: 8px;
  padding: 6px;
  overflow: hidden;
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  align-items: flex-start;
}

.vector-cell {
  width: 6px;
  height: 6px;
  border-radius: 1px;
  border: 1px solid rgba(0, 61, 165, 0.1);
  box-sizing: border-box;
}

.vector-legend {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 0.6875rem;
  color: var(--text-secondary, #5A5A72);
}

.vector-legend-bar {
  width: 90px;
  height: 8px;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(0, 61, 165, 0.12) 0%, rgba(0, 61, 165, 1) 100%);
}

.vector-note {
  font-size: 0.6875rem;
  color: var(--text-secondary, #5A5A72);
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}

.review-textarea {
  margin-bottom: 16px;
}

.review-actions {
  display: flex;
  gap: 12px;
}

.review-note-content {
  background: var(--bg-secondary, #F4F6FA);
  border-radius: 8px;
  padding: 12px 16px;
}

.review-note-reviewer {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--text-primary, #1A1A2E);
  margin: 0 0 4px;
}

.review-note-text {
  font-size: 0.8125rem;
  color: var(--text-secondary, #5A5A72);
  margin: 0;
  line-height: 1.6;
}

@media (max-width: 768px) {
  .info-grid {
    grid-template-columns: 1fr;
  }

  .chunks-list {
    grid-template-columns: 1fr;
  }
}
</style>
