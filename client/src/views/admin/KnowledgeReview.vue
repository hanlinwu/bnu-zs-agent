<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Check, Close } from '@element-plus/icons-vue'
import * as knowledgeApi from '@/api/admin/knowledge'
import type { KnowledgeDocument, KnowledgeChunk } from '@/types/knowledge'

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

function statusLabel(status: string) {
  const map: Record<string, string> = {
    pending: '待审核',
    reviewing: '审核中',
    approved: '已通过',
    active: '已生效',
    rejected: '已拒绝',
    processing: '处理中',
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
    chunks.value = res.data.items
    chunkTotal.value = res.data.total
  } catch {
    ElMessage.error('加载切片失败')
  }
}

function handleChunkPageChange(page: number) {
  chunkPage.value = page
  fetchChunks()
}

async function handleReview(approved: boolean) {
  if (!doc.value) return
  submitting.value = true
  try {
    await knowledgeApi.reviewDocument(doc.value.id, {
      approved,
      note: reviewNote.value || undefined,
    })
    ElMessage.success(approved ? '已通过审核' : '已拒绝')
    router.push('/admin/knowledge')
  } catch {
    ElMessage.error('审核操作失败')
  } finally {
    submitting.value = false
  }
}

function goBack() {
  router.push('/admin/knowledge')
}

onMounted(() => {
  fetchDocument()
  fetchChunks()
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
        <h3 class="panel-title">文档信息</h3>
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
            <el-tag size="small" :type="statusTagType(doc.status)">
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
        <h3 class="panel-title">文档切片预览 ({{ chunkTotal }} 条)</h3>
        <div v-if="chunks.length === 0" class="chunks-empty">
          暂无切片数据
        </div>
        <div v-else class="chunks-list">
          <div
            v-for="chunk in chunks"
            :key="chunk.id"
            class="chunk-card"
          >
            <div class="chunk-header">
              <span class="chunk-index">#{{ chunk.index + 1 }}</span>
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

      <div v-if="doc.reviewNote" class="review-note-panel">
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
  max-width: 1000px;
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
