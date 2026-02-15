<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  text: string
  isStreaming: boolean
}>()

/**
 * Simple markdown-to-HTML converter (same logic as MessageBubble).
 */
function renderMarkdown(text: string): string {
  let html = text

  html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_match, _lang, code) => {
    return `<pre class="md-code-block"><code>${escapeHtml(code.trim())}</code></pre>`
  })

  html = html.replace(/`([^`]+)`/g, '<code class="md-inline-code">$1</code>')
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')

  const lines = html.split('\n')
  const result: string[] = []
  let inUl = false
  let inOl = false

  for (const line of lines) {
    const ulMatch = line.match(/^[-*]\s+(.+)/)
    const olMatch = line.match(/^\d+\.\s+(.+)/)

    if (ulMatch) {
      if (!inUl) { result.push('<ul>'); inUl = true }
      result.push(`<li>${ulMatch[1]}</li>`)
      continue
    } else if (inUl) {
      result.push('</ul>')
      inUl = false
    }

    if (olMatch) {
      if (!inOl) { result.push('<ol>'); inOl = true }
      result.push(`<li>${olMatch[1]}</li>`)
      continue
    } else if (inOl) {
      result.push('</ol>')
      inOl = false
    }

    if (line.trim() === '') {
      result.push('<br />')
    } else {
      result.push(`<p>${line}</p>`)
    }
  }

  if (inUl) result.push('</ul>')
  if (inOl) result.push('</ol>')

  return result.join('')
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

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
  font-size: 14px;
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
