<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, Upload, Picture, VideoCamera, Edit, ZoomIn } from '@element-plus/icons-vue'
import * as mediaApi from '@/api/admin/media'
import * as wfApi from '@/api/admin/workflow'
import type { MediaResource } from '@/types/admin'
import type { WorkflowNode, WorkflowAction, WorkflowTransition, ReviewHistoryRecord, ResourceWorkflowInfo } from '@/api/admin/workflow'
import ReviewHistory from '@/components/admin/ReviewHistory.vue'
import MediaPreview from '@/components/MediaPreview.vue'

const loading = ref(false)
const mediaList = ref<MediaResource[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(12)
const typeFilter = ref<string>('')
const activeNodeFilter = ref<string>('all')

// Workflow definition for this resource type
const workflowNodes = ref<WorkflowNode[]>([])
const workflowActions = ref<WorkflowAction[]>([])
const workflowTransitions = ref<WorkflowTransition[]>([])

// Upload dialog
const uploadDialogVisible = ref(false)
const uploading = ref(false)
const uploadTitle = ref('')
const uploadDescription = ref('')
const uploadTags = ref('')
const uploadFileList = ref<File[]>([])

// Edit dialog
const editDialogVisible = ref(false)
const editSaving = ref(false)
const editTarget = ref<MediaResource | null>(null)
const editForm = ref({ title: '', description: '', tags: '' })

// Batch selection
const selectedIds = ref<Set<string>>(new Set())
const batchLoading = ref(false)

const batchEnabled = computed(() => activeNodeFilter.value !== 'all')
const batchActions = computed(() => {
  if (!batchEnabled.value) return []
  return getActionsForNode(activeNodeFilter.value)
})
const allSelected = computed(() => {
  if (mediaList.value.length === 0) return false
  return mediaList.value.every(m => selectedIds.value.has(m.id))
})

function toggleSelect(id: string) {
  const s = new Set(selectedIds.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  selectedIds.value = s
}

function toggleSelectAll() {
  if (allSelected.value) {
    selectedIds.value = new Set()
  } else {
    selectedIds.value = new Set(mediaList.value.map(m => m.id))
  }
}

function clearSelection() {
  selectedIds.value = new Set()
}

async function handleBatchAction(actionId: string) {
  if (selectedIds.value.size === 0) return
  const actionName = workflowActions.value.find(a => a.id === actionId)?.name || actionId
  try {
    await ElMessageBox.confirm(
      `确定要对选中的 ${selectedIds.value.size} 项执行「${actionName}」操作吗？`,
      '批量操作确认',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    batchLoading.value = true
    const res = await mediaApi.batchReviewMedia({
      ids: Array.from(selectedIds.value),
      action: actionId,
    })
    const data = res.data as any
    ElMessage.success(`批量操作完成，成功 ${data.success_count} 项`)
    if (data.errors?.length) {
      ElMessage.warning(`${data.errors.length} 项操作失败`)
    }
    selectedIds.value = new Set()
    fetchMedia()
  } catch {
    // cancelled
  } finally {
    batchLoading.value = false
  }
}

// Review dialog
const reviewDialogVisible = ref(false)
const reviewTarget = ref<MediaResource | null>(null)
const reviewNote = ref('')
const reviewLoading = ref(false)
const reviewHistory = ref<ReviewHistoryRecord[]>([])

// Preview state
const previewVisible = ref(false)
const previewType = ref<'image' | 'video'>('image')
const previewSrc = ref('')
const previewTitle = ref('')

const typeOptions = [
  { label: '全部', value: '' },
  { label: '图片', value: 'image' },
  { label: '视频', value: 'video' },
]

const statusFilter = computed<string | undefined>(() =>
  activeNodeFilter.value === 'all' ? undefined : activeNodeFilter.value
)

// Get available actions for a given node
function getActionsForNode(nodeId: string): WorkflowAction[] {
  const actionIds = new Set<string>()
  for (const t of workflowTransitions.value) {
    if (t.from_node === nodeId) actionIds.add(t.action)
  }
  return workflowActions.value.filter(a => actionIds.has(a.id))
}

function getNodeName(nodeId: string): string {
  const node = workflowNodes.value.find(n => n.id === nodeId)
  return node?.name || nodeId
}

function nodeIsTerminal(nodeId: string): boolean {
  const node = workflowNodes.value.find(n => n.id === nodeId)
  return node?.type === 'terminal'
}

function nodeTagType(nodeId: string): 'success' | 'danger' | 'warning' | 'info' {
  const node = workflowNodes.value.find(n => n.id === nodeId)
  if (!node) return 'info'
  if (node.type === 'start') return 'warning'
  if (node.type === 'terminal') {
    if (nodeId.includes('approved')) return 'success'
    if (nodeId.includes('rejected')) return 'danger'
    return 'info'
  }
  return 'info'
}

function actionButtonType(actionId: string): 'success' | 'danger' | 'warning' | 'primary' {
  if (actionId.includes('approve')) return 'success'
  if (actionId.includes('reject')) return 'danger'
  return 'primary'
}

function typeIcon(type: string) {
  return type === 'video' ? VideoCamera : Picture
}

function typeLabel(type: string) {
  return type === 'video' ? '视频' : '图片'
}

function formatFileSize(bytes: number | null) {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatDate(date: string) {
  return new Date(date).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

function openPreview(media: MediaResource) {
  previewType.value = media.media_type as 'image' | 'video'
  previewSrc.value = media.file_url || ''
  previewTitle.value = media.title
  previewVisible.value = true
}

function closePreview() {
  previewVisible.value = false
}

function thumbnailUrl(media: MediaResource) {
  if (media.media_type === 'image' && media.file_url) return media.file_url
  return ''
}

async function fetchWorkflow() {
  try {
    const res = await wfApi.getWorkflowForResource('media')
    const info = res.data as ResourceWorkflowInfo
    workflowNodes.value = info.nodes || []
    workflowActions.value = info.actions || []
    workflowTransitions.value = info.transitions || []
  } catch {
    workflowNodes.value = []
    workflowActions.value = []
    workflowTransitions.value = []
  }
}

async function fetchMedia() {
  loading.value = true
  try {
    const res = await mediaApi.getMediaList({
      page: currentPage.value,
      page_size: pageSize.value,
      media_type: typeFilter.value || undefined,
      status: statusFilter.value || undefined,
    })
    mediaList.value = res.data.items
    total.value = res.data.total
  } catch {
    ElMessage.error('加载资源列表失败')
  } finally {
    loading.value = false
  }
}

function handleFilterChange() {
  currentPage.value = 1
  clearSelection()
  fetchMedia()
}

function handleNodeFilterChange() {
  currentPage.value = 1
  clearSelection()
  fetchMedia()
}

function handlePageChange(page: number) {
  currentPage.value = page
  clearSelection()
  fetchMedia()
}

async function handleDelete(media: MediaResource) {
  try {
    await ElMessageBox.confirm(
      `确定要删除「${media.title}」吗？`,
      '删除确认',
      { type: 'error', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await mediaApi.deleteMedia(media.id)
    ElMessage.success('删除成功')
    fetchMedia()
  } catch {
    // cancelled
  }
}

function openUploadDialog() {
  uploadTitle.value = ''
  uploadDescription.value = ''
  uploadTags.value = ''
  uploadFileList.value = []
  uploadDialogVisible.value = true
}

function handleFileChange(file: any) {
  if (file.raw) {
    uploadFileList.value = [file.raw]
    if (!uploadTitle.value && file.name) {
      uploadTitle.value = file.name.replace(/\.[^.]+$/, '')
    }
  }
}

function handleFileRemove() {
  uploadFileList.value = []
}

async function handleUploadSubmit() {
  if (uploadFileList.value.length === 0) {
    ElMessage.warning('请选择文件')
    return
  }
  if (!uploadTitle.value.trim()) {
    ElMessage.warning('请输入资源标题')
    return
  }

  const selectedFile = uploadFileList.value[0]
  if (!selectedFile) {
    ElMessage.warning('文件无效，请重新选择')
    return
  }

  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', selectedFile)
    formData.append('title', uploadTitle.value.trim())
    if (uploadDescription.value.trim()) {
      formData.append('description', uploadDescription.value.trim())
    }
    if (uploadTags.value.trim()) {
      formData.append('tags', uploadTags.value.trim())
    }
    await mediaApi.uploadMedia(formData)
    ElMessage.success('上传成功')
    uploadDialogVisible.value = false
    fetchMedia()
  } catch {
    ElMessage.error('上传失败')
  } finally {
    uploading.value = false
  }
}

function openEditDialog(media: MediaResource) {
  editTarget.value = media
  editForm.value = {
    title: media.title,
    description: media.description || '',
    tags: (media.tags || []).join(', '),
  }
  editDialogVisible.value = true
}

async function handleEditSubmit() {
  if (!editTarget.value) return
  if (!editForm.value.title.trim()) {
    ElMessage.warning('请输入资源标题')
    return
  }
  editSaving.value = true
  try {
    const tagList = editForm.value.tags
      ? editForm.value.tags.split(',').map(t => t.trim()).filter(Boolean)
      : []
    await mediaApi.updateMedia(editTarget.value.id, {
      title: editForm.value.title.trim(),
      description: editForm.value.description.trim() || '',
      tags: tagList,
    })
    ElMessage.success('保存成功')
    editDialogVisible.value = false
    fetchMedia()
  } catch {
    ElMessage.error('保存失败')
  } finally {
    editSaving.value = false
  }
}

function openReviewDialog(media: MediaResource) {
  reviewTarget.value = media
  reviewNote.value = ''
  reviewHistory.value = []
  reviewDialogVisible.value = true
  fetchReviewHistory(media.id)
}

async function fetchReviewHistory(mediaId: string) {
  try {
    const res = await wfApi.getReviewHistory('media', mediaId)
    reviewHistory.value = res.data.items
  } catch {
    // silently fail
  }
}

async function handleReviewAction(actionId: string) {
  if (!reviewTarget.value) return
  reviewLoading.value = true
  try {
    await mediaApi.reviewMedia(reviewTarget.value.id, {
      action: actionId,
      note: reviewNote.value || undefined,
    })
    const actionName = workflowActions.value.find(a => a.id === actionId)?.name || actionId
    ElMessage.success(`操作成功: ${actionName}`)
    reviewDialogVisible.value = false
    fetchMedia()
  } catch {
    ElMessage.error('操作失败')
  } finally {
    reviewLoading.value = false
  }
}

onMounted(async () => {
  await fetchWorkflow()
  fetchMedia()
})
</script>

<template>
  <div class="media-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">多媒体资源</h2>
        <p class="page-desc">管理系统官方素材资源</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openUploadDialog">
        上传资源
      </el-button>
    </div>

    <div class="content-card">
      <!-- Dynamic workflow node tabs -->
      <el-tabs v-model="activeNodeFilter" @tab-change="handleNodeFilterChange">
        <el-tab-pane label="全部" name="all" />
        <el-tab-pane
          v-for="node in workflowNodes"
          :key="node.id"
          :label="node.name"
          :name="node.id"
        />
      </el-tabs>

      <div class="toolbar">
        <el-radio-group v-model="typeFilter" @change="handleFilterChange" size="default">
          <el-radio-button
            v-for="opt in typeOptions"
            :key="opt.value"
            :value="opt.value"
          >
            {{ opt.label }}
          </el-radio-button>
        </el-radio-group>
      </div>

      <!-- Batch action bar -->
      <div v-if="batchEnabled && selectedIds.size > 0" class="batch-bar">
        <el-checkbox :model-value="allSelected" @change="toggleSelectAll">全选</el-checkbox>
        <span class="batch-count">已选 {{ selectedIds.size }} 项</span>
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
        <el-button size="small" @click="clearSelection">取消选择</el-button>
      </div>

      <div v-loading="loading" class="media-grid">
        <div
          v-for="media in mediaList"
          :key="media.id"
          class="media-card"
        >
          <div class="media-thumbnail">
            <div
              v-if="batchEnabled"
              class="card-checkbox"
              @click.stop="toggleSelect(media.id)"
            >
              <el-checkbox
                :model-value="selectedIds.has(media.id)"
                @change="toggleSelect(media.id)"
                @click.stop
              />
            </div>
            <div
              v-if="media.media_type === 'image' && thumbnailUrl(media)"
              class="thumb-img-wrapper"
              @click="openPreview(media)"
            >
              <img
                :src="thumbnailUrl(media)"
                :alt="media.title"
                class="thumb-img"
              />
              <div class="thumb-overlay">
                <el-icon :size="24"><ZoomIn /></el-icon>
              </div>
            </div>
            <div
              v-else-if="media.media_type === 'video' && media.file_url"
              class="thumb-img-wrapper video-wrapper"
              @click="openPreview(media)"
            >
              <video
                :src="media.file_url"
                class="thumb-img"
                preload="metadata"
              />
              <div class="thumb-overlay video-overlay">
                <el-icon :size="32"><VideoCamera /></el-icon>
              </div>
            </div>
            <div class="media-badges">
              <el-tag size="small" type="info">{{ typeLabel(media.media_type) }}</el-tag>
              <el-tag size="small" :type="nodeTagType(media.current_node)">
                {{ getNodeName(media.current_node) }}
              </el-tag>
            </div>
          </div>
          <div class="media-info">
            <h4 class="media-name" :title="media.title">{{ media.title }}</h4>
            <div class="media-meta">
              <span>{{ formatFileSize(media.file_size) }}</span>
              <span v-if="media.uploader_name">{{ media.uploader_name }}</span>
              <span>{{ formatDate(media.created_at) }}</span>
            </div>
            <div v-if="media.tags && media.tags.length" class="media-tags">
              <el-tag
                v-for="tag in media.tags.slice(0, 3)"
                :key="tag"
                size="small"
                type="info"
                class="tag-item"
              >
                {{ tag }}
              </el-tag>
            </div>
          </div>
          <div class="media-actions">
            <el-button type="primary" text size="small" :icon="Edit" @click="openEditDialog(media)">
              编辑
            </el-button>
            <el-button
              v-if="!nodeIsTerminal(media.current_node)"
              type="success"
              text
              size="small"
              @click="openReviewDialog(media)"
            >
              审核
            </el-button>
            <el-button
              v-else
              type="info"
              text
              size="small"
              @click="openReviewDialog(media)"
            >
              详情
            </el-button>
            <el-button type="danger" text size="small" :icon="Delete" @click="handleDelete(media)" />
          </div>
        </div>
      </div>

      <div v-if="mediaList.length === 0 && !loading" class="empty-state">
        <el-icon :size="48" color="#E2E6ED"><Picture /></el-icon>
        <p>暂无资源</p>
      </div>

      <div class="pagination-wrapper" v-if="total > 0">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="handlePageChange"
        />
      </div>
    </div>

    <!-- Upload Dialog -->
    <el-dialog
      v-model="uploadDialogVisible"
      title="上传资源"
      width="520px"
      destroy-on-close
    >
      <el-form label-width="80px">
        <el-form-item label="资源标题" required>
          <el-input v-model="uploadTitle" placeholder="请输入资源标题" />
        </el-form-item>
        <el-form-item label="选择文件" required>
          <el-upload
            drag
            :auto-upload="false"
            :limit="1"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            accept="image/jpeg,image/png,image/webp,image/gif,video/mp4"
          >
            <el-icon :size="48" class="upload-icon"><Upload /></el-icon>
            <div class="upload-text">将文件拖到此处，或<em>点击上传</em></div>
            <template #tip>
              <div class="upload-tip">
                支持 JPG/PNG/WebP/GIF/MP4 格式，单文件不超过 100MB
              </div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="uploadDescription" type="textarea" :rows="2" placeholder="资源描述，用于检索（选填）" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="uploadTags" placeholder="多个标签用逗号分隔（选填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleUploadSubmit">
          上传
        </el-button>
      </template>
    </el-dialog>

    <!-- Edit Dialog -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑资源信息"
      width="520px"
      destroy-on-close
    >
      <el-form label-width="80px">
        <el-form-item label="资源标题" required>
          <el-input v-model="editForm.title" placeholder="请输入资源标题" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="editForm.description" type="textarea" :rows="3" placeholder="资源描述，用于检索（选填）" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="editForm.tags" placeholder="多个标签用逗号分隔（选填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="editSaving" @click="handleEditSubmit">
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- Media Preview -->
    <MediaPreview
      :visible="previewVisible"
      :type="previewType"
      :src="previewSrc"
      :title="previewTitle"
      @close="closePreview"
    />

    <!-- Review Dialog -->
    <el-dialog
      v-model="reviewDialogVisible"
      title="审核媒体资源"
      width="580px"
      destroy-on-close
    >
      <div v-if="reviewTarget" class="review-info">
        <div class="review-preview">
          <img
            v-if="reviewTarget.media_type === 'image' && reviewTarget.file_url"
            :src="reviewTarget.file_url"
            :alt="reviewTarget.title"
            class="review-img"
          />
          <div v-else class="review-placeholder">
            <el-icon :size="48"><component :is="typeIcon(reviewTarget.media_type)" /></el-icon>
          </div>
        </div>
        <div class="review-meta">
          <h4>{{ reviewTarget.title }}</h4>
          <p>类型：{{ typeLabel(reviewTarget.media_type) }} · {{ formatFileSize(reviewTarget.file_size) }}</p>
          <el-tag size="small" :type="nodeTagType(reviewTarget.current_node)" style="margin-top: 4px;">
            {{ getNodeName(reviewTarget.current_node) }}
          </el-tag>
        </div>
      </div>
      <div v-if="reviewHistory.length > 0" style="margin-top: 16px;">
        <h4 class="review-section-title">审核记录</h4>
        <ReviewHistory :records="reviewHistory" />
      </div>
      <el-form v-if="reviewTarget && !nodeIsTerminal(reviewTarget.current_node)" label-width="80px" style="margin-top: 16px;">
        <el-form-item label="审核备注">
          <el-input
            v-model="reviewNote"
            type="textarea"
            :rows="3"
            placeholder="可选填写审核备注"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reviewDialogVisible = false">关闭</el-button>
        <template v-if="reviewTarget && !nodeIsTerminal(reviewTarget.current_node)">
          <el-button
            v-for="action in getActionsForNode(reviewTarget.current_node)"
            :key="action.id"
            :type="actionButtonType(action.id)"
            :loading="reviewLoading"
            @click="handleReviewAction(action.id)"
          >
            {{ action.name }}
          </el-button>
        </template>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.media-page {
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

.toolbar {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.media-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
  max-height: calc(100vh - 300px);
  overflow-y: auto;
}

.media-card {
  border: 1px solid var(--border-color, #E2E6ED);
  border-radius: 10px;
  overflow: hidden;
  transition: all 0.2s;
  position: relative;

  &:hover {
    box-shadow: var(--shadow-md, 0 4px 16px rgba(0, 0, 0, 0.08));
  }
}

.media-thumbnail {
  position: relative;
  height: 160px;
  background: var(--bg-secondary, #F4F6FA);
  overflow: hidden;
}

.thumb-img-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  cursor: pointer;
  overflow: hidden;

  &:hover .thumb-overlay {
    opacity: 1;
  }

  &.video-wrapper {
    video {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
  }
}

.thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;

  .thumb-img-wrapper:hover & {
    transform: scale(1.05);
  }
}

.thumb-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
  color: #fff;

  &.video-overlay {
    opacity: 1;
    background: rgba(0, 0, 0, 0.3);

    &:hover {
      background: rgba(0, 0, 0, 0.5);
    }
  }
}

.thumb-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary, #9E9EB3);
}

.media-badges {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  gap: 4px;
}

.media-info {
  padding: 12px;
}

.media-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #1A1A2E);
  margin: 0 0 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.media-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--text-secondary, #5A5A72);
  margin-bottom: 6px;
}

.media-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.tag-item {
  font-size: 11px;
}

.media-actions {
  display: flex;
  justify-content: flex-end;
  padding: 0 8px 8px;
  gap: 4px;
}

.empty-state {
  text-align: center;
  padding: 60px 24px;
  color: var(--text-secondary, #9E9EB3);

  p {
    margin: 12px 0 0;
    font-size: 14px;
  }
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: auto;
  padding-top: 16px;
  border-top: 1px solid var(--border-color, #E2E6ED);
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

.review-info {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.review-preview {
  width: 120px;
  height: 90px;
  border-radius: 8px;
  overflow: hidden;
  background: var(--bg-secondary, #F4F6FA);
  flex-shrink: 0;
}

.review-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.review-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary, #9E9EB3);
}

.review-meta {
  h4 {
    font-size: 16px;
    font-weight: 600;
    margin: 0 0 8px;
    color: var(--text-primary, #1A1A2E);
  }

  p {
    font-size: 13px;
    color: var(--text-secondary, #5A5A72);
    margin: 0;
  }
}

.review-section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #1A1A2E);
  margin: 0 0 8px;
}

.batch-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--el-color-primary-light-9, #ECF5FF);
  border-radius: 8px;
  margin-bottom: 16px;
}

.batch-count {
  font-size: 13px;
  color: var(--text-primary, #1A1A2E);
  font-weight: 500;
}

.card-checkbox {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 2;
}

@media (max-width: 768px) {
  .media-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
}
</style>
