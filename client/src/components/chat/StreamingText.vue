<script setup lang="ts">
import { computed } from 'vue'
import { renderMarkdown } from '@/utils/markdown'

const props = defineProps<{
  text: string
  isStreaming: boolean
}>()

const renderedHtml = computed(() => renderMarkdown(props.text))
</script>

<template>
  <div class="streaming-text">
    <span class="streaming-content" v-html="renderedHtml"></span>
    <span v-if="isStreaming" class="streaming-cursor">|</span>
  </div>
</template>

<style scoped lang="scss">
.streaming-text {
  font-size: 0.875rem;
  line-height: 1.7;
  word-break: break-word;

  :deep(p) {
    margin: 0;
    display: inline;
    & + p {
      display: block;
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
}

.streaming-cursor {
  display: inline-block;
  font-weight: 700;
  color: var(--bnu-blue, #003DA5);
  animation: blink 1s step-end infinite;
  margin-left: 1px;
}

@keyframes blink {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0;
  }
}
</style>
