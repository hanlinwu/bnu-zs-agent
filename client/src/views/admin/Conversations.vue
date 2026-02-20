<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh } from '@element-plus/icons-vue'
import * as convApi from '@/api/admin/conversation'
import type { AdminConversation, AdminMessage, AdminMessageMediaItem } from '@/types/admin'
import MediaPreview from '@/components/MediaPreview.vue'

const loading = ref(false)
const conversations = ref<AdminConversation[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const searchKeyword = ref('')
const riskLevelFilter = ref('')
const sensitiveLevelFilter = ref('')
const dateRange = ref<[string, string] | null>(null)

const detailDialogVisible = ref(false)
const detailLoading = ref(false)
const detailTitle = ref('')
const detailMessages = ref<AdminMessage[]>([])

// Preview state
const previewVisible = ref(false)
const previewType = ref<'image' | 'video'>('image')
const previewSrc = ref('')
const previewTitle = ref('')

function openPreview(url: string, type: 'image' | 'video', title: string) {
  previewType.value = type
  previewSrc.value = url
  previewTitle.value = title
  previewVisible.value = true
}

function closePreview() {
  previewVisible.value = false
}

function riskTag(level: string | null): { type: 'success' | 'warning' | 'danger' | 'info'; label: string } {
  switch (level) {
    case 'low': return { type: 'success', label: '低风险' }
    case 'medium': return { type: 'warning', label: '中风险' }
    case 'high': return { type: 'danger', label: '高风险' }
    case 'blocked': return { type: 'danger', label: '已拦截' }
    default: return { type: 'info', label: '无' }
  }
}

function sensitiveTag(level: string | null): { type: 'success' | 'warning' | 'danger' | 'info'; label: string } {
  switch (level) {
    case 'block': return { type: 'danger', label: '屏蔽级' }
    case 'warn': return { type: 'warning', label: '警告级' }
    case 'review': return { type: 'info', label: '审查级' }
    default: return { type: 'info', label: '无' }
  }
}

function roleTag(role: string): { type: 'success' | 'info'; label: string } {
  switch (role) {
    case 'user': return { type: 'info', label: '用户' }
    case 'assistant': return { type: 'success', label: '助手' }
    default: return { type: 'info', label: '系统' }
  }
}

function formatDate(date?: string | null) {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

async function fetchConversations() {
  loading.value = true
  try {
    const params: convApi.ConversationQuery = {
      page: currentPage.value,
      page_size: pageSize.value,
      keyword: searchKeyword.value || undefined,
      risk_level: riskLevelFilter.value || undefined,
      sensitive_level: sensitiveLevelFilter.value || undefined,
    }
    if (dateRange.value) {
      params.start_time = dateRange.value[0]
      params.end_time = dateRange.value[1]
    }
    const res = await convApi.getConversations(params)
    conversations.value = res.data.items
    total.value = res.data.total
  } catch {
    ElMessage.error('加载对话列表失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  currentPage.value = 1
  fetchConversations()
}

function handlePageChange(page: number) {
  currentPage.value = page
  fetchConversations()
}

async function viewDetail(conv: AdminConversation) {
  detailDialogVisible.value = true
  detailLoading.value = true
  detailTitle.value = conv.title || '未命名对话'
  detailMessages.value = []
  try {
    const res = await convApi.getConversationMessages(conv.id)
    detailMessages.value = res.data.messages
  } catch {
    ElMessage.error('加载对话详情失败')
  } finally {
    detailLoading.value = false
  }
}

onMounted(() => {
  fetchConversations()
})

// Render message content with embedded media
function renderMessageContent(msg: AdminMessage): string {
  let content = msg.content || ''

  // Check if message has media items
  if (!msg.media_items || msg.media_items.length === 0) {
    return escapeHtml(content).replace(/\n/g, '<br>')
  }

  // Build media map
  const mediaMap = new Map()
  msg.media_items?.forEach((item: AdminMessageMediaItem, index: number) => {
    const key = item.slot_key || `slot_${index}`
    // Normalize URL field - API returns 'url' but we use 'file_url' in type
    const normalizedItem = {
      ...item,
      file_url: item.file_url || (item as any).url || ''
    }
    mediaMap.set(key, normalizedItem)
  })

  // Replace [[MEDIA_ITEM:slot_key]] with image HTML
  const mediaMarkerRegex = /\[\[\s*MEDIA_ITEM:([^\]]+)\s*\]\]/g
  let result = content

  for (const match of content.matchAll(mediaMarkerRegex)) {
    const slotKey = match[1]?.trim()
    const item = slotKey ? mediaMap.get(slotKey) : null

    if (item) {
      const mediaHtml = item.media_type === 'image'
        ? `<span class="inline-media" data-media-url="${escapeHtml(item.file_url)}" data-media-type="image" data-media-title="${escapeHtml(item.title || '')}">
             <img src="${escapeHtml(item.file_url)}" alt="${escapeHtml(item.title || '图片')}" class="inline-image" />
           </span>`
        : `<span class="inline-media" data-media-url="${escapeHtml(item.file_url)}" data-media-type="video" data-media-title="${escapeHtml(item.title || '')}">
             [视频: ${escapeHtml(item.title || '未命名')}<span class="media-preview-btn">点击播放</span>]
           </span>`
      result = result.replace(match[0], mediaHtml)
    }
  }

  // Append remaining media items
  const usedKeys = new Set()
  for (const match of content.matchAll(mediaMarkerRegex)) {
    const slotKey = match[1]?.trim()
    if (slotKey) usedKeys.add(slotKey)
  }

  const unusedMedia = msg.media_items?.filter((item: AdminMessageMediaItem) => !usedKeys.has(item.slot_key)) ?? []
  if (unusedMedia.length > 0) {
    result += '\n\n'
    result += unusedMedia.map((item: AdminMessageMediaItem) =>
      item.media_type === 'image'
        ? `<span class="inline-media" data-media-url="${escapeHtml(item.file_url)}" data-media-type="image" data-media-title="${escapeHtml(item.title || '')}">
             <img src="${escapeHtml(item.file_url)}" alt="${escapeHtml(item.title || '图片')}" class="inline-image" />
           </span>`
        : `<span class="inline-media" data-media-url="${escapeHtml(item.file_url)}" data-media-type="video" data-media-title="${escapeHtml(item.title || '')}">
             [视频: ${escapeHtml(item.title || '未命名')}<span class="media-preview-btn">点击播放</span>]
           </span>`
    ).join('')
  }

  return result.replace(/\n/g, '<br>')
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

// Handle click on inline media
function handleMessageClick(e: MouseEvent, _msg: AdminMessage) {
  const target = e.target as HTMLElement
  const mediaSpan = target.closest('.inline-media') as HTMLElement

  if (mediaSpan) {
    const mediaUrl = mediaSpan.dataset.mediaUrl
    const mediaType = mediaSpan.dataset.mediaType as 'image' | 'video'
    const mediaTitle = mediaSpan.dataset.mediaTitle || ''

    if (mediaUrl && mediaType) {
      openPreview(mediaUrl, mediaType, mediaTitle)
    }
  }
}
</script>

<template>
  <div class="conversations-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">对话日志</h2>
        <p class="page-desc">查看所有用户对话记录，审核风险分级</p>
      </div>
    </div>

    <div class="content-card">
      <div class="toolbar">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索用户手机号 / 昵称"
          :prefix-icon="Search"
          clearable
          style="width: 240px"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        />
        <el-select
          v-model="riskLevelFilter"
          placeholder="风险等级"
          clearable
          style="width: 140px"
          @change="handleSearch"
        >
          <el-option label="低风险" value="low" />
          <el-option label="中风险" value="medium" />
          <el-option label="高风险" value="high" />
          <el-option label="已拦截" value="blocked" />
        </el-select>
        <el-select
          v-model="sensitiveLevelFilter"
          placeholder="敏感词级别"
          clearable
          style="width: 140px"
          @change="handleSearch"
        >
          <el-option label="屏蔽级" value="block" />
          <el-option label="警告级" value="warn" />
          <el-option label="审查级" value="review" />
        </el-select>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DDTHH:mm:ss"
          style="width: 280px"
          @change="handleSearch"
        />
        <el-button type="primary" @click="handleSearch">搜索</el-button>
      </div>

      <el-table
        v-loading="loading"
        :data="conversations"
        stripe
        height="100%"
        class="conv-table"
      >
        <el-table-column label="用户" min-width="160">
          <template #default="{ row }">
            <div class="user-inline" :title="`${row.user_nickname || '-'} ${row.user_phone || ''}`">
              {{ row.user_nickname || '-' }}
              <span class="sub-text">{{ row.user_phone }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="对话标题" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ row.title || '未命名对话' }}</span>
            <el-tag v-if="row.is_deleted" size="small" type="info" class="deleted-tag">用户已删除</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message_count" label="消息数" width="80" align="center" />
        <el-table-column prop="user_char_count" label="提问字数" width="100" align="center" />
        <el-table-column prop="assistant_char_count" label="回复字数" width="100" align="center" />
        <el-table-column label="最高风险" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="riskTag(row.max_risk_level).type">
              {{ riskTag(row.max_risk_level).label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="敏感词" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.max_sensitive_level" size="small" :type="sensitiveTag(row.max_sensitive_level).type">
              {{ sensitiveTag(row.max_sensitive_level).label }}
            </el-tag>
            <span v-else class="sub-text">-</span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="160">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="viewDetail(row)">
              查看详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-button
          :icon="Refresh"
          circle
          size="small"
          @click="fetchConversations"
          title="刷新数据"
        />
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
      v-model="detailDialogVisible"
      :title="`对话详情 — ${detailTitle}`"
      width="720px"
      destroy-on-close
    >
      <div v-loading="detailLoading" class="conversation-messages">
        <div v-if="!detailLoading && detailMessages.length === 0" class="empty-messages">
          暂无消息记录
        </div>
        <div
          v-for="msg in detailMessages"
          :key="msg.id"
          class="message-item"
          :class="{ 'message-user': msg.role === 'user', 'message-assistant': msg.role === 'assistant' }"
        >
          <div class="message-header">
            <el-tag size="small" :type="roleTag(msg.role).type">
              {{ roleTag(msg.role).label }}
            </el-tag>
            <el-tag v-if="msg.risk_level" size="small" :type="riskTag(msg.risk_level).type">
              {{ riskTag(msg.risk_level).label }}
            </el-tag>
            <el-tag v-if="msg.role === 'assistant'" size="small" type="info">
              模型: {{ msg.model_version || 'unknown' }}
            </el-tag>
            <el-tag v-if="msg.sensitive_level" size="small" :type="sensitiveTag(msg.sensitive_level).type">
              {{ sensitiveTag(msg.sensitive_level).label }}
              <template v-if="msg.sensitive_words && msg.sensitive_words.length">
                ({{ msg.sensitive_words.join(', ') }})
              </template>
            </el-tag>
            <el-tag v-if="msg.review_passed === false" size="small" type="danger">
              审核未通过
            </el-tag>
            <el-tag v-if="msg.review_passed === true" size="small" type="success">
              审核通过
            </el-tag>
            <span class="message-meta">{{ msg.char_count }}字</span>
            <span class="message-time">{{ formatDate(msg.created_at) }}</span>
          </div>
          <div
            class="message-content"
            v-html="renderMessageContent(msg)"
            @click="(e) => handleMessageClick(e, msg)"
          ></div>
        </div>
      </div>
    </el-dialog>

    <MediaPreview
      :visible="previewVisible"
      :type="previewType"
      :src="previewSrc"
      :title="previewTitle"
      @close="closePreview"
    />
  </div>
</template>

<style lang="scss" scoped>
.conversations-page {
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
  font-size: 1.375rem;
  font-weight: 700;
  color: var(--text-primary, #1A1A2E);
  margin: 0 0 4px;
}

.page-desc {
  font-size: 0.875rem;
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
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.conv-table {
  flex: 1;
  overflow: hidden;

  :deep(.el-table) {
    height: 100%;
  }

  :deep(.el-table__header th) {
    background: var(--bg-secondary, #F4F6FA) !important;
    font-weight: 600;
    padding-top: 6px;
    padding-bottom: 6px;
  }

  :deep(.el-table__body td) {
    padding-top: 6px;
    padding-bottom: 6px;
  }

  :deep(.el-table .cell) {
    line-height: 1.35;
  }
}

.sub-text {
  font-size: 0.75rem;
  color: var(--text-secondary, #5A5A72);
}

.user-inline {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.deleted-tag {
  margin-left: 8px;
}

.pagination-wrapper {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  margin-top: 16px;
  gap: 12px;
}

.conversation-messages {
  max-height: 60vh;
  overflow-y: auto;
  min-height: 120px;
}

.empty-messages {
  text-align: center;
  padding: 40px 0;
  color: var(--text-secondary, #5A5A72);
  font-size: 0.875rem;
}

.message-item {
  padding: 8px 12px;
  border-radius: 8px;
  margin-bottom: 6px;

  &.message-user {
    background: var(--bg-secondary, #F4F6FA);
  }

  &.message-assistant {
    background: #f0f9eb;
  }

  &:last-child {
    margin-bottom: 0;
  }
}

.message-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}

.message-meta {
  font-size: 0.75rem;
  color: var(--text-secondary, #5A5A72);
}

.message-time {
  font-size: 0.75rem;
  color: var(--text-secondary, #5A5A72);
  margin-left: auto;
}

.message-content {
  font-size: 0.8125rem;
  line-height: 1.45;
  color: var(--text-primary, #1A1A2E);
  word-break: break-word;

  :deep(.inline-media) {
    display: inline-block;
    margin: 4px 0;
    cursor: pointer;
    border-radius: 8px;
    overflow: hidden;
    vertical-align: middle;

    &:hover {
      opacity: 0.9;
    }
  }

  :deep(.inline-image) {
    max-width: 200px;
    max-height: 150px;
    width: auto;
    height: auto;
    object-fit: contain;
    display: block;
    border-radius: 8px;
    border: 1px solid rgba(0, 0, 0, 0.1);
  }

  :deep(.media-preview-btn) {
    color: var(--bnu-blue, #003DA5);
    text-decoration: underline;
    margin-left: 4px;
  }
}
</style>
