<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Check, Close, Download, Loading } from '@element-plus/icons-vue'
import * as knowledgeApi from '@/api/admin/knowledge'
import * as wfApi from '@/api/admin/workflow'
import type { KnowledgeDocument, KnowledgeChunk } from '@/types/knowledge'
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
const reviewHistory = ref<any[]>([])
let pollTimer: ReturnType<typeof setInterval> | null = null

const isProcessing = computed(() => doc.value?.status === 'processing')

function statusLabel(status: string) {
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
    processing: '',
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
    // Silently fail during polling; only show error on initial load
  }
}

function handleChunkPageChange(page: number) {
  chunkPage.value = page
  fetchChunks()
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

async function handleReview(approved: boolean) {
  if (!doc.value) return
  submitting.value = true
  try {
    const res = await knowledgeApi.reviewDocument(doc.value.id, {
      action: approved ? 'approve' : 'reject',
      note: reviewNote.value || undefined,
    })
    if (approved) {
      doc.value = res.data as any
      ElMessage.success('已通过审核，正在切片...')
      startPolling()
      fetchReviewHistory()
    } else {
      ElMessage.success('已拒绝')
      fetchReviewHistory()
      router.push('/admin/knowledge')
    }
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

onMounted(() => {
  fetchDocument().then(() => {
    fetchChunks()
    fetchReviewHistory()
    if (doc.value?.status === 'processing') {
      startPolling()
    }
  })
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
            <span class="info-label">当前状态</span>
            <el-tag size="small" :type="(statusTagType(doc.status) as any)">
              {{ statusLabel(doc.status) }}
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
          <el-tag v-if="isProcessing" type="primary" effect="dark" class="processing-tag">
            <el-icon class="is-loading"><Loading /></el-icon>
            正在切片中...已完成 {{ chunkTotal }} 条
          </el-tag>
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
          >
            <div class="chunk-header">
              <span class="chunk-index">#{{ chunk.chunkIndex + 1 }}</span>
              <span class="chunk-tokens">{{ chunk.tokenCount }} tokens</span>
            </div>
            <div class="chunk-content">{{ chunk.content }}</div>
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

      <div
        v-if="doc.status === 'pending' || doc.status === 'reviewing'"
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
            type="success"
            :icon="Check"
            :loading="submitting"
            @click="handleReview(true)"
          >
            通过
          </el-button>
          <el-button
            type="danger"
            :icon="Close"
            :loading="submitting"
            @click="handleReview(false)"
          >
            拒绝
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
  font-size: 22px;
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
  font-size: 16px;
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
  font-size: 12px;
  color: var(--text-secondary, #5A5A72);
}

.info-value {
  font-size: 14px;
  color: var(--text-primary, #1A1A2E);
  font-weight: 500;

  &--mono {
    font-family: monospace;
    font-size: 12px;
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
    font-size: 32px;
    color: var(--bnu-blue, #003DA5);
    margin-bottom: 12px;
  }

  p {
    margin: 0;
    font-size: 14px;
  }
}

.chunks-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chunk-card {
  border: 1px solid var(--border-color, #E2E6ED);
  border-radius: 8px;
  overflow: hidden;
}

.chunk-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: var(--bg-secondary, #F4F6FA);
}

.chunk-index {
  font-size: 13px;
  font-weight: 600;
  color: var(--bnu-blue, #003DA5);
}

.chunk-tokens {
  font-size: 12px;
  color: var(--text-secondary, #5A5A72);
}

.chunk-content {
  padding: 12px 16px;
  font-size: 13px;
  color: var(--text-primary, #1A1A2E);
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 200px;
  overflow-y: auto;
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
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary, #1A1A2E);
  margin: 0 0 4px;
}

.review-note-text {
  font-size: 13px;
  color: var(--text-secondary, #5A5A72);
  margin: 0;
  line-height: 1.6;
}

@media (max-width: 768px) {
  .info-grid {
    grid-template-columns: 1fr;
  }
}
</style>
