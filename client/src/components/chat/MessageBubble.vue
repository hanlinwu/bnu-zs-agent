<script setup lang="ts">
import { computed } from 'vue'
import type { Message } from '@/types/chat'
import SourceCitation from './SourceCitation.vue'
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

const hasSources = computed(() => {
  return props.message.sources && props.message.sources.length > 0
})

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
      <div class="bubble-content" v-html="renderMarkdown(message.content)"></div>

      <div class="bubble-time">{{ formattedTime }}</div>

      <SourceCitation
        v-if="hasSources && message.sources"
        :sources="message.sources"
        class="bubble-sources"
      />
    </div>
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
  font-size: 14px;
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
    font-size: 13px;
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
    font-size: 13px;
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
    font-size: 13px;
  }

  .is-user & :deep(.md-inline-code) {
    background: rgba(255, 255, 255, 0.15);
  }
}

.bubble-time {
  font-size: 11px;
  color: var(--text-secondary, #5a5a72);
  margin-top: 4px;
  opacity: 0;
  transition: opacity 0.2s;
  padding: 0 4px;

  .is-user & {
    text-align: right;
  }

  .message-bubble:hover & {
    opacity: 1;
  }
}

.bubble-sources {
  margin-top: 6px;
}
</style>
