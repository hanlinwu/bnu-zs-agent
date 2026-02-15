<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Upload } from '@element-plus/icons-vue'
import type { UploadProps } from 'element-plus'
import * as knowledgeApi from '@/api/admin/knowledge'
import type { KnowledgeDocument, DocumentStatus } from '@/types/knowledge'

const router = useRouter()
const loading = ref(false)
const documents = ref<KnowledgeDocument[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const activeTab = ref<string>('all')
const uploadDialogVisible = ref(false)
const uploading = ref(false)

const statusTabs = [
  { label: '全部', value: 'all' },
  { label: '待审核', value: 'pending' },
  { label: '已通过', value: 'approved' },
  { label: '已拒绝', value: 'rejected' },
  { label: '已归档', value: 'archived' },
]

const statusFilter = computed<string | undefined>(() =>
  activeTab.value === 'all' ? undefined : activeTab.value
)

function statusTagType(status: DocumentStatus) {
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

function statusLabel(status: DocumentStatus) {
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

function fileTypeLabel(type: string) {
  const map: Record<string, string> = {
    pdf: 'PDF',
    docx: 'Word',
    txt: 'TXT',
    md: 'Markdown',
  }
  return map[type] || type.toUpperCase()
}

async function fetchDocuments() {
  loading.value = true
  try {
    const res = await knowledgeApi.getDocuments({
      page: currentPage.value,
      pageSize: pageSize.value,
      status: statusFilter.value,
    })
    documents.value = res.data.items
    total.value = res.data.total
  } catch {
    ElMessage.error('加载文档列表失败')
  } finally {
    loading.value = false
  }
}

function handleTabChange() {
  currentPage.value = 1
  fetchDocuments()
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
  } catch {
    // cancelled or error
  }
}

const handleUploadSuccess: UploadProps['onSuccess'] = () => {
  uploading.value = false
  uploadDialogVisible.value = false
  ElMessage.success('上传成功，文档已进入审核队列')
  fetchDocuments()
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
  if (file.size > 50 * 1024 * 1024) {
    ElMessage.error('文件大小不能超过 50MB')
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

onMounted(() => {
  fetchDocuments()
})
</script>

<template>
  <div class="knowledge-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">知识库管理</h2>
        <p class="page-desc">管理招生知识文档的上传、审核与生效</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="uploadDialogVisible = true">
        上传文档
      </el-button>
    </div>

    <div class="content-card">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane
          v-for="tab in statusTabs"
          :key="tab.value"
          :label="tab.label"
          :name="tab.value"
        />
      </el-tabs>

      <el-table
        v-loading="loading"
        :data="documents"
        stripe
        class="doc-table"
      >
        <el-table-column prop="title" label="文档标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="fileType" label="文件类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ fileTypeLabel(row.fileType) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="(statusTagType(row.status) as any)">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="uploaderName" label="上传人" width="120" show-overflow-tooltip />
        <el-table-column prop="chunkCount" label="切片数" width="80" align="center" />
        <el-table-column prop="createdAt" label="上传时间" width="120">
          <template #default="{ row }">{{ formatDate(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'pending' || row.status === 'reviewing'"
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
              v-if="row.status !== 'archived'"
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

    <el-dialog
      v-model="uploadDialogVisible"
      title="上传知识文档"
      width="520px"
      destroy-on-close
    >
      <el-upload
        drag
        action="/api/admin/knowledge/documents"
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
            支持 PDF、Word、TXT、Markdown 格式，单文件不超过 50MB
          </div>
        </template>
      </el-upload>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.knowledge-page {
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

.doc-table {
  margin-top: 8px;

  :deep(.el-table__header th) {
    background: var(--bg-secondary, #F4F6FA);
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
  font-size: 14px;

  em {
    color: var(--bnu-blue, #003DA5);
    font-style: normal;
  }
}

.upload-tip {
  color: var(--text-secondary, #9E9EB3);
  font-size: 12px;
  margin-top: 8px;
}
</style>
