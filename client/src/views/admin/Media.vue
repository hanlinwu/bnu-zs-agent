<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, Upload, Picture, VideoCamera, Document } from '@element-plus/icons-vue'
import type { UploadProps } from 'element-plus'
import * as mediaApi from '@/api/admin/media'
import type { MediaResource } from '@/types/admin'

const loading = ref(false)
const mediaList = ref<MediaResource[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(12)
const typeFilter = ref<string>('')
const uploadDialogVisible = ref(false)
const uploading = ref(false)

const typeOptions = [
  { label: '全部', value: '' },
  { label: '图片', value: 'image' },
  { label: '视频', value: 'video' },
  { label: '文档', value: 'document' },
]

function typeIcon(type: string) {
  const map: Record<string, any> = {
    image: Picture,
    video: VideoCamera,
    document: Document,
  }
  return map[type] || Document
}

function typeLabel(type: string) {
  const map: Record<string, string> = {
    image: '图片',
    video: '视频',
    document: '文档',
  }
  return map[type] || type
}

function formatFileSize(bytes: number) {
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
  if (media.type === 'image') return media.url
  return ''
}

async function fetchMedia() {
  loading.value = true
  try {
    const res = await mediaApi.getMediaList({
      page: currentPage.value,
      pageSize: pageSize.value,
      type: typeFilter.value || undefined,
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

function handlePageChange(page: number) {
  currentPage.value = page
  fetchMedia()
}

async function handleDelete(media: MediaResource) {
  try {
    await ElMessageBox.confirm(
      `确定要删除「${media.name}」吗？`,
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

const handleUploadSuccess: UploadProps['onSuccess'] = () => {
  uploading.value = false
  uploadDialogVisible.value = false
  ElMessage.success('上传成功')
  fetchMedia()
}

const handleUploadError: UploadProps['onError'] = () => {
  uploading.value = false
  ElMessage.error('上传失败')
}

const beforeUpload: UploadProps['beforeUpload'] = (file) => {
  if (file.size > 100 * 1024 * 1024) {
    ElMessage.error('文件大小不能超过 100MB')
    return false
  }
  uploading.value = true
  return true
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
      <el-button type="primary" :icon="Plus" @click="uploadDialogVisible = true">
        上传资源
      </el-button>
    </div>

    <div class="content-card">
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
              v-if="media.type === 'image' && thumbnailUrl(media)"
              :src="thumbnailUrl(media)"
              :alt="media.name"
              class="thumb-img"
            />
            <div v-else class="thumb-placeholder">
              <el-icon :size="40"><component :is="typeIcon(media.type)" /></el-icon>
            </div>
            <div class="media-type-badge">
              <el-tag size="small" type="info">{{ typeLabel(media.type) }}</el-tag>
            </div>
          </div>
          <div class="media-info">
            <h4 class="media-name" :title="media.name">{{ media.name }}</h4>
            <div class="media-meta">
              <span>{{ formatFileSize(media.fileSize) }}</span>
              <span>{{ formatDate(media.createdAt) }}</span>
            </div>
            <div v-if="media.tags.length" class="media-tags">
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

    <el-dialog
      v-model="uploadDialogVisible"
      title="上传资源"
      width="520px"
      destroy-on-close
    >
      <el-upload
        drag
        action="/api/v1/admin/media/upload"
        :before-upload="beforeUpload"
        :on-success="handleUploadSuccess"
        :on-error="handleUploadError"
        :show-file-list="true"
        :limit="10"
        multiple
      >
        <el-icon :size="48" class="upload-icon"><Upload /></el-icon>
        <div class="upload-text">将文件拖到此处，或<em>点击上传</em></div>
        <template #tip>
          <div class="upload-tip">
            支持图片、视频、文档等格式，单文件不超过 100MB
          </div>
        </template>
      </el-upload>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.media-page {
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

.toolbar {
  margin-bottom: 16px;
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

    .media-actions {
      opacity: 1;
    }
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

.media-type-badge {
  position: absolute;
  top: 8px;
  right: 8px;
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
  position: absolute;
  top: 8px;
  left: 8px;
  opacity: 0;
  transition: opacity 0.2s;
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

@media (max-width: 768px) {
  .media-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
}
</style>
