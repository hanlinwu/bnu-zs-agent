<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, Upload, Picture, VideoCamera, Check, Close } from '@element-plus/icons-vue'
import * as mediaApi from '@/api/admin/media'
import * as wfApi from '@/api/admin/workflow'
import type { MediaResource } from '@/types/admin'
import ReviewHistory from '@/components/admin/ReviewHistory.vue'

const loading = ref(false)
const mediaList = ref<MediaResource[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(12)
const typeFilter = ref<string>('')
const activeTab = ref<string>('all')

// Upload dialog
const uploadDialogVisible = ref(false)
const uploading = ref(false)
const uploadTitle = ref('')
const uploadSource = ref('')
const uploadTags = ref('')
const uploadFileList = ref<File[]>([])

// Review dialog
const reviewDialogVisible = ref(false)
const reviewTarget = ref<MediaResource | null>(null)
const reviewNote = ref('')
const reviewLoading = ref(false)
const reviewHistory = ref<any[]>([])

const typeOptions = [
  { label: '全部', value: '' },
  { label: '图片', value: 'image' },
  { label: '视频', value: 'video' },
]

const statusTabs = [
  { label: '全部', value: 'all' },
  { label: '待审核', value: 'pending' },
  { label: '已通过', value: 'approved' },
  { label: '已拒绝', value: 'rejected' },
]

const statusFilter = computed<string | undefined>(() =>
  activeTab.value === 'all' ? undefined : activeTab.value
)

function statusTag(status: string): { type: '' | 'success' | 'warning' | 'danger' | 'info'; label: string } {
  switch (status) {
    case 'pending': return { type: 'warning', label: '待审核' }
    case 'approved': return { type: 'success', label: '已通过' }
    case 'rejected': return { type: 'danger', label: '已拒绝' }
    case 'reviewing': return { type: 'info', label: '审核中' }
    default: return { type: 'info', label: status }
  }
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

function thumbnailUrl(media: MediaResource) {
  if (media.media_type === 'image' && media.file_url) return media.file_url
  return ''
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
  fetchMedia()
}

function handleTabChange() {
  currentPage.value = 1
  fetchMedia()
}

function handlePageChange(page: number) {
  currentPage.value = page
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
  uploadSource.value = ''
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

  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', uploadFileList.value[0])
    formData.append('title', uploadTitle.value.trim())
    if (uploadSource.value.trim()) {
      formData.append('source', uploadSource.value.trim())
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

async function handleReview(action: 'approve' | 'reject') {
  if (!reviewTarget.value) return
  reviewLoading.value = true
  try {
    await mediaApi.reviewMedia(reviewTarget.value.id, {
      action,
      note: reviewNote.value || undefined,
    })
    ElMessage.success(action === 'approve' ? '审核通过' : '已拒绝')
    reviewDialogVisible.value = false
    fetchMedia()
  } catch {
    ElMessage.error('审核操作失败')
  } finally {
    reviewLoading.value = false
  }
}

onMounted(() => {
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
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane
          v-for="tab in statusTabs"
          :key="tab.value"
          :label="tab.label"
          :name="tab.value"
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

      <div v-loading="loading" class="media-grid">
        <div
          v-for="media in mediaList"
          :key="media.id"
          class="media-card"
        >
          <div class="media-thumbnail">
            <img
              v-if="media.media_type === 'image' && thumbnailUrl(media)"
              :src="thumbnailUrl(media)"
              :alt="media.title"
              class="thumb-img"
            />
            <div v-else class="thumb-placeholder">
              <el-icon :size="40"><component :is="typeIcon(media.media_type)" /></el-icon>
            </div>
            <div class="media-badges">
              <el-tag size="small" type="info">{{ typeLabel(media.media_type) }}</el-tag>
              <el-tag size="small" :type="statusTag(media.status).type">
                {{ statusTag(media.status).label }}
              </el-tag>
            </div>
          </div>
          <div class="media-info">
            <h4 class="media-name" :title="media.title">{{ media.title }}</h4>
            <div class="media-meta">
              <span>{{ formatFileSize(media.file_size) }}</span>
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
            <el-button
              v-if="media.status === 'pending' || media.status === 'reviewing'"
              type="primary"
              text
              size="small"
              :icon="Check"
              @click="openReviewDialog(media)"
            >
              审核
            </el-button>
            <el-button
              v-else-if="media.status === 'approved' || media.status === 'rejected'"
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

      <div class="pagination-wrapper" v-if="total > pageSize">
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
        <el-form-item label="来源">
          <el-input v-model="uploadSource" placeholder="资源来源（选填）" />
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

    <!-- Review Dialog -->
    <el-dialog
      v-model="reviewDialogVisible"
      title="审核媒体资源"
      width="520px"
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
          <el-tag size="small" :type="statusTag(reviewTarget.status).type" style="margin-top: 4px;">
            {{ statusTag(reviewTarget.status).label }}
          </el-tag>
        </div>
      </div>
      <div v-if="reviewHistory.length > 0" style="margin-top: 16px;">
        <h4 class="review-section-title">审核记录</h4>
        <ReviewHistory :records="reviewHistory" />
      </div>
      <el-form v-if="reviewTarget && (reviewTarget.status === 'pending' || reviewTarget.status === 'reviewing')" label-width="80px" style="margin-top: 16px;">
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
        <el-button @click="reviewDialogVisible = false">取消</el-button>
        <template v-if="reviewTarget && (reviewTarget.status === 'pending' || reviewTarget.status === 'reviewing')">
          <el-button
            type="danger"
            :icon="Close"
            :loading="reviewLoading"
            @click="handleReview('reject')"
          >
            拒绝
          </el-button>
          <el-button
            type="success"
            :icon="Check"
            :loading="reviewLoading"
            @click="handleReview('approve')"
          >
            通过
          </el-button>
        </template>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.media-page {
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

.thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
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

@media (max-width: 768px) {
  .media-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
}
</style>
