<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Message, MediaItem } from '@/types/chat'
import MediaPreview from '@/components/MediaPreview.vue'
import { renderMarkdown } from '@/utils/markdown'

const props = defineProps<{
  message: Message
}>()

const isUser = computed(() => props.message.role === 'user')

const formattedTime = computed(() => {
  const d = new Date(props.message.createdAt)
  const hours = d.getHours().toString().padStart(2, '0')
  const minutes = d.getMinutes().toString().padStart(2, '0')
  return `${hours}:${minutes}`
})

const toolsUsed = computed(() => {
  const toolSet = new Set<string>()
  ;(props.message.toolsUsed || []).forEach((tool) => toolSet.add(tool))
  ;(props.message.toolTraces || []).forEach((trace) => {
    if (trace.tool) toolSet.add(trace.tool)
  })
  return Array.from(toolSet)
})

function toolLabel(tool: string) {
  const labels: Record<string, string> = {
    knowledge_search: '知识库检索',
    web_search: '网页检索',
    media_search: '媒体库检索',
  }
  return labels[tool] || tool
}

const knowledgeDocs = computed(() => {
  const docs = props.message.sources || []
  const map = new Map<string, { title: string; snippet: string }>()
  docs.forEach((item) => {
    const sourceType = String(item.source_type || '').toLowerCase()
    const hasDocId = Boolean(item.document_id || item.documentId)
    if (sourceType !== 'knowledge' && !hasDocId) return
    const key = String(item.document_id || item.documentId || item.title || '')
    if (!key) return
    if (!map.has(key)) {
      map.set(key, {
        title: item.title || '未命名文档',
        snippet: item.snippet || '',
      })
    }
  })
  return Array.from(map.values())
})

const webPages = computed(() => {
  const pages = props.message.sources || []
  const map = new Map<string, { title: string; snippet: string; url: string }>()
  pages.forEach((item) => {
    const sourceType = String(item.source_type || '').toLowerCase()
    const url = String(item.url || '').trim()
    if (sourceType !== 'web' && !url) return
    const key = url || `${item.title || ''}-${item.snippet || ''}`
    if (!key) return
    if (!map.has(key)) {
      map.set(key, {
        title: item.title || '网页来源',
        snippet: item.snippet || '',
        url,
      })
    }
  })
  return Array.from(map.values())
})

const sourceDrawerVisible = ref(false)

function openSourceDrawer() {
  sourceDrawerVisible.value = true
}

const toolSummaryTags = computed(() => {
  const tags: Array<{ key: string; text: string; icon: string; clickable: boolean }> = []
  if (webPages.value.length) {
    tags.push({ key: 'web_search', text: `浏览了${webPages.value.length}个网页`, icon: '🌐', clickable: true })
  }
  if (knowledgeDocs.value.length) {
    tags.push({ key: 'knowledge_search', text: `查询了知识库中的${knowledgeDocs.value.length}个文档`, icon: '📚', clickable: true })
  }
  // Fallback: keep other tool tags if present but no structured count text.
  toolsUsed.value
    .filter((tool) => tool !== 'web_search' && tool !== 'knowledge_search')
    .forEach((tool) => {
      tags.push({ key: tool, text: toolLabel(tool), icon: '🧰', clickable: false })
    })
  return tags
})

const mediaItems = computed(() => props.message.mediaItems || [])

// Preview state
const previewVisible = ref(false)
const previewType = ref<'image' | 'video'>('image')
const previewSrc = ref('')
const previewTitle = ref('')

function openPreview(item: MediaItem) {
  previewType.value = item.media_type as 'image' | 'video'
  previewSrc.value = item.url
  previewTitle.value = item.title
  previewVisible.value = true
}

function closePreview() {
  previewVisible.value = false
}

// Build media map by slot key
const mediaBySlotKey = computed(() => {
  const map = new Map<string, MediaItem>()
  mediaItems.value.forEach((item, index) => {
    const key = item.slot_key || `slot_${index}`
    if (!map.has(key)) {
      map.set(key, item)
    }
  })
  return map
})

// Render content with embedded media
const renderedContent = computed(() => {
  const content = props.message.content || ''
  const mediaMarkerRegex = /\[\[\s*MEDIA_ITEM:([^\]]+)\s*\]\]/g

  // If no markers, just render markdown
  if (!content.includes('MEDIA_ITEM')) {
    return renderMarkdown(content)
  }

  // Replace markers with media placeholders that we'll render as Vue components
  // Use <template> element as placeholder since HTML comments are stripped by DOMPurify
  let result = content
  let match
  let index = 0
  const replacements: { placeholder: string; item: MediaItem | null }[] = []

  while ((match = mediaMarkerRegex.exec(content)) !== null) {
    const slotKey = match[1]?.trim() || ''
    const item = slotKey ? mediaBySlotKey.value.get(slotKey) || null : null
    const placeholder = `<template data-media-index="${index}"></template>`

    result = result.replace(match[0], placeholder)
    replacements.push({ placeholder, item })
    index++
  }

  // Render markdown
  let html = renderMarkdown(result)

  // Replace placeholders with media HTML
  replacements.forEach(({ placeholder, item }) => {
    if (item) {
      const mediaHtml = item.media_type === 'image'
        ? `<span class="inline-media" data-media-id="${item.id}" data-media-type="image" data-media-url="${item.url}" data-media-title="${item.title || ''}">
             <img src="${item.url}" alt="${item.title || ''}" class="inline-image" loading="lazy" />
           </span>`
        : `<span class="inline-media" data-media-id="${item.id}" data-media-type="video" data-media-url="${item.url}" data-media-title="${item.title || ''}">
             <video controls preload="metadata" class="inline-video">
               <source src="${item.url}" type="video/mp4" />
             </video>
           </span>`
      html = html.replace(placeholder, mediaHtml)
    }
  })

  // Append remaining media items that weren't referenced in content
  const usedKeys = new Set(replacements.map(r => r.item?.id).filter(Boolean))
  const unusedMedia = mediaItems.value.filter(item => !usedKeys.has(item.id))

  if (unusedMedia.length > 0) {
    const mediaHtml = unusedMedia.map(item =>
      item.media_type === 'image'
        ? `<span class="inline-media" data-media-id="${item.id}" data-media-type="image" data-media-url="${item.url}" data-media-title="${item.title || ''}">
             <img src="${item.url}" alt="${item.title || ''}" class="inline-image" loading="lazy" />
           </span>`
        : `<span class="inline-media" data-media-id="${item.id}" data-media-type="video" data-media-url="${item.url}" data-media-title="${item.title || ''}">
             <video controls preload="metadata" class="inline-video">
               <source src="${item.url}" type="video/mp4" />
             </video>
           </span>`
    ).join('')
    html += mediaHtml
  }

  return html
})

// Handle click on inline media for preview
function handleContentClick(e: MouseEvent) {
  const target = e.target as HTMLElement
  const mediaSpan = target.closest('.inline-media') as HTMLElement

  if (mediaSpan) {
    const mediaType = mediaSpan.dataset.mediaType as 'image' | 'video'
    const mediaUrl = mediaSpan.dataset.mediaUrl
    const mediaTitle = mediaSpan.dataset.mediaTitle

    if (mediaUrl) {
      openPreview({
        id: mediaSpan.dataset.mediaId || '',
        media_type: mediaType,
        url: mediaUrl,
        title: mediaTitle || ''
      } as MediaItem)
    }
  }
}
</script>

<template>
  <div class="message-bubble" :class="{ 'is-user': isUser, 'is-assistant': !isUser }">
    <div v-if="!isUser" class="avatar-wrapper">
      <div class="ai-avatar">
        <svg viewBox="0 0 32 32" width="32" height="32" fill="none">
          <circle cx="16" cy="16" r="15" fill="var(--bnu-blue, #003DA5)" />
          <text
            x="16" y="22" text-anchor="middle"
            fill="#fff" font-size="14" font-weight="bold"
            font-family="serif"
          >智</text>
        </svg>
      </div>
    </div>

    <div class="bubble-body">
      <!-- Single bubble content with embedded media -->
      <div
        class="bubble-content"
        @click="handleContentClick"
        v-html="renderedContent"
      ></div>

      <div v-if="!isUser && toolSummaryTags.length" class="meta-row">
        <div class="bubble-time">{{ formattedTime }}</div>
        <el-tag
          v-for="tag in toolSummaryTags"
          :key="tag.key"
          size="small"
          class="tool-usage-tag"
          :class="{ 'is-clickable': tag.clickable }"
          @click="tag.clickable && openSourceDrawer()"
        >
          <span class="tool-tag-inner">
            <span class="tool-tag-icon">{{ tag.icon }}</span>
            <span>{{ tag.text }}</span>
          </span>
        </el-tag>
      </div>
    </div>

    <MediaPreview
      :visible="previewVisible"
      :type="previewType"
      :src="previewSrc"
      :title="previewTitle"
      @close="closePreview"
    />

    <el-drawer
      v-model="sourceDrawerVisible"
      direction="rtl"
      :size="420"
      title="检索详情"
    >
      <div class="source-drawer">
        <div v-if="knowledgeDocs.length" class="source-section">
          <div class="source-section-title">知识库文档（{{ knowledgeDocs.length }}）</div>
          <div v-for="(doc, idx) in knowledgeDocs" :key="`doc-${idx}`" class="source-item">
            <div class="source-item-title">{{ doc.title }}</div>
            <div v-if="doc.snippet" class="source-item-snippet">{{ doc.snippet }}</div>
          </div>
        </div>

        <div v-if="webPages.length" class="source-section">
          <div class="source-section-title">网页来源（{{ webPages.length }}）</div>
          <div v-for="(page, idx) in webPages" :key="`web-${idx}`" class="source-item">
            <div class="source-item-title">{{ page.title }}</div>
            <a
              v-if="page.url"
              class="source-item-link"
              :href="page.url"
              target="_blank"
              rel="noopener noreferrer"
            >
              {{ page.url }}
            </a>
            <div v-if="page.snippet" class="source-item-snippet">{{ page.snippet }}</div>
          </div>
        </div>

        <el-empty v-if="!knowledgeDocs.length && !webPages.length" description="暂无检索详情" />
      </div>
    </el-drawer>
  </div>
</template>

<style scoped lang="scss">
.message-bubble {
  display: flex;
  gap: 10px;
  padding: 8px 0;
  max-width: 80%;

  &.is-user {
    margin-left: auto;
    flex-direction: row-reverse;
  }

  &.is-assistant {
    margin-right: auto;
  }
}

.avatar-wrapper {
  flex-shrink: 0;
  padding-top: 2px;
}

.ai-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.bubble-body {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.bubble-content {
  padding: 12px 16px;
  border-radius: 18px;
  font-size: 0.875rem;
  line-height: 1.7;
  word-break: break-word;

  .is-user & {
    background-color: var(--bnu-blue, #003DA5);
    color: #fff;
    border-top-right-radius: 4px;
  }

  .is-assistant & {
    background-color: var(--bg-secondary, #f4f6fa);
    color: var(--text-primary, #1a1a2e);
    border-top-left-radius: 4px;
  }

  :deep(p) {
    margin: 0;
    & + p {
      margin-top: 4px;
    }
  }

  :deep(strong) {
    font-weight: 600;
  }

  :deep(ul), :deep(ol) {
    margin: 6px 0;
    padding-left: 20px;
  }

  :deep(table) {
    width: 100%;
    border-collapse: collapse;
    margin: 8px 0;
    font-size: 0.8125rem;
  }

  :deep(th), :deep(td) {
    border: 1px solid #d8deea;
    padding: 6px 8px;
    text-align: left;
    vertical-align: top;
  }

  :deep(th) {
    background: #eef3fb;
    font-weight: 600;
  }

  :deep(a) {
    color: #1d4ed8;
    text-decoration: underline;
    word-break: break-all;
  }

  :deep(li) {
    margin: 2px 0;
  }

  :deep(.md-code-block) {
    background: #1a1a2e;
    color: #e4e4ec;
    padding: 12px;
    border-radius: 8px;
    overflow-x: auto;
    margin: 8px 0;
    font-size: 0.8125rem;
    line-height: 1.5;

    code {
      font-family: 'Menlo', 'Consolas', monospace;
    }
  }

  :deep(.md-inline-code) {
    background: rgba(0, 0, 0, 0.06);
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'Menlo', 'Consolas', monospace;
    font-size: 0.8125rem;
  }

  .is-user & :deep(.md-inline-code) {
    background: rgba(255, 255, 255, 0.15);
  }

  // Inline media styles
  :deep(.inline-media) {
    display: inline-block;
    max-width: 100%;
    margin: 8px 0;
    cursor: pointer;
    border-radius: 12px;
    overflow: hidden;
    vertical-align: middle;

    &:hover {
      opacity: 0.95;
    }
  }

  :deep(.inline-image) {
    max-width: 280px;
    max-height: 200px;
    width: auto;
    height: auto;
    object-fit: contain;
    display: block;
    border-radius: 12px;
  }

  :deep(.inline-video) {
    max-width: 100%;
    max-height: 200px;
    width: auto;
    height: auto;
    display: block;
    border-radius: 12px;
    background: #000;
  }
}

.meta-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.bubble-time {
  font-size: 0.6875rem;
  color: var(--text-secondary, #5a5a72);
  padding: 0 2px;
}

.tool-usage-tag {
  margin: 0;
}

.tool-tag-inner {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.tool-tag-icon {
  font-size: 12px;
  line-height: 1;
}

.tool-usage-tag.is-clickable {
  cursor: pointer;
}

.source-drawer {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.source-section {
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 10px;
  padding: 10px 12px;
  background: var(--bg-secondary, #f9fafb);
}

.source-section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary, #111827);
  margin-bottom: 8px;
}

.source-item {
  border-top: 1px dashed var(--border-color, #e5e7eb);
  padding-top: 8px;
  margin-top: 8px;
}

.source-item:first-of-type {
  border-top: none;
  padding-top: 0;
  margin-top: 0;
}

.source-item-title {
  font-size: 13px;
  color: var(--text-primary, #111827);
}

.source-item-link {
  display: inline-block;
  margin-top: 4px;
  color: #1d4ed8;
  font-size: 12px;
  word-break: break-all;
  text-decoration: underline;
}

.source-item-snippet {
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-secondary, #4b5563);
  line-height: 1.5;
}
</style>
